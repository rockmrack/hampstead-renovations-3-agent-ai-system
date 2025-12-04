#!/usr/bin/env python3
"""
Hampstead Renovations - Professional Quote Generator
====================================================

Enterprise-grade PDF quote generation system with:
- Dynamic pricing from pricing matrix
- Multi-tier quote levels (Essential, Premium, Luxury)
- Location-based pricing adjustments
- Professional PDF output with company branding
- S3 storage integration
- HubSpot deal attachment

Author: Hampstead Renovations AI System
Version: 1.0.0
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import boto3
import httpx
import structlog
import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, EmailStr, Field, field_validator
from pydantic_settings import BaseSettings
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    # Database
    database_url: str = Field(
        default="postgresql://hampstead:password@localhost:5432/hampstead_renovations"
    )

    # AWS S3
    aws_access_key_id: str = Field(default="")
    aws_secret_access_key: str = Field(default="")
    aws_region: str = Field(default="eu-west-2")
    s3_bucket: str = Field(default="hampstead-renovations-documents")

    # HubSpot
    hubspot_api_key: str = Field(default="")

    # Paths
    templates_dir: Path = Field(default=Path(__file__).parent / "templates")
    pricing_file: Path = Field(
        default=Path(__file__).parent.parent / "pricing" / "pricing-matrix.json"
    )
    assets_dir: Path = Field(default=Path(__file__).parent / "assets")

    # Company Info
    company_name: str = "Hampstead Renovations"
    company_address: str = "123 Heath Street, Hampstead, London NW3 1QA"
    company_phone: str = "+44 20 7946 0958"
    company_email: str = "enquiries@hampsteadrenovations.co.uk"
    company_website: str = "www.hampsteadrenovations.co.uk"
    company_registration: str = "Company No: 12345678"
    vat_number: str = "VAT No: GB 123 4567 89"

    # Quote Settings
    quote_validity_days: int = 30
    deposit_percentage: Decimal = Decimal("10")

    class Config:
        env_prefix = "HAMPSTEAD_"
        env_file = ".env"


settings = Settings()


# =============================================================================
# DATA MODELS
# =============================================================================


class LineItem(BaseModel):
    """Individual line item in a quote."""

    description: str
    quantity: Decimal = Decimal("1")
    unit: str = "item"
    unit_price: Decimal
    notes: Optional[str] = None

    @property
    def total(self) -> Decimal:
        return (self.quantity * self.unit_price).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )


class QuoteSection(BaseModel):
    """Section of related items in a quote."""

    name: str
    items: list[LineItem]
    notes: Optional[str] = None

    @property
    def subtotal(self) -> Decimal:
        return sum(item.total for item in self.items)


class CustomerDetails(BaseModel):
    """Customer information for the quote."""

    name: str = Field(..., min_length=2)
    email: EmailStr
    phone: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str = "London"
    postcode: str

    @field_validator("postcode")
    @classmethod
    def validate_uk_postcode(cls, v: str) -> str:
        v = v.upper().strip()
        # Basic UK postcode format validation
        if not v or len(v) < 5:
            raise ValueError("Invalid UK postcode format")
        return v

    @property
    def location_area(self) -> Optional[str]:
        """Extract NW area from postcode for pricing adjustments."""
        postcode = self.postcode.upper().replace(" ", "")
        if postcode.startswith("NW3"):
            return "NW3"
        elif postcode.startswith("NW6"):
            return "NW6"
        elif postcode.startswith("NW11"):
            return "NW11"
        return None


class ProjectDetails(BaseModel):
    """Project specification details."""

    project_type: str  # kitchen, bathroom, extension, loft, full_house
    tier: str = "premium"  # essential, premium, luxury
    room_count: int = 1
    estimated_sqm: Optional[Decimal] = None
    requirements: list[str] = []
    special_requests: Optional[str] = None
    preferred_start_date: Optional[datetime] = None


class QuoteRequest(BaseModel):
    """Complete quote generation request."""

    customer: CustomerDetails
    project: ProjectDetails
    deal_id: Optional[str] = None  # HubSpot deal ID
    contact_id: Optional[str] = None  # HubSpot contact ID
    include_optional_items: bool = True
    notes: Optional[str] = None


class GeneratedQuote(BaseModel):
    """Result of quote generation."""

    quote_id: str
    quote_number: str
    pdf_path: str
    s3_url: Optional[str] = None
    subtotal: Decimal
    vat: Decimal
    total: Decimal
    valid_until: datetime
    created_at: datetime


# =============================================================================
# PRICING ENGINE
# =============================================================================


class PricingEngine:
    """
    Handles pricing calculations based on pricing matrix.

    Features:
    - Location-based price adjustments
    - Tier-based item selection
    - Volume discounts
    - Margin validation
    """

    def __init__(self, pricing_file: Path = settings.pricing_file):
        self.pricing_data = self._load_pricing(pricing_file)
        self.location_factors = self.pricing_data.get("location_factors", {})
        self.margin_rules = self.pricing_data.get("margin_rules", {})
        self.volume_discounts = self.pricing_data.get("volume_discounts", [])

    def _load_pricing(self, pricing_file: Path) -> dict[str, Any]:
        """Load pricing matrix from JSON file."""
        try:
            with open(pricing_file, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("pricing_file_not_found", path=str(pricing_file))
            raise
        except json.JSONDecodeError as e:
            logger.error("pricing_file_invalid", path=str(pricing_file), error=str(e))
            raise

    def get_location_factor(self, area: Optional[str]) -> Decimal:
        """Get price multiplier for location."""
        if not area:
            return Decimal("1.0")
        factor = self.location_factors.get(area, 1.0)
        return Decimal(str(factor))

    def get_base_items(
        self, project_type: str, tier: str, location_factor: Decimal
    ) -> list[LineItem]:
        """Get base items for a project type with tier and location adjustments."""
        items = []
        category = self.pricing_data.get("categories", {}).get(project_type, {})
        base_items = category.get("base_items", [])

        for item in base_items:
            # Check tier inclusion
            included_tiers = item.get("tiers", ["essential", "premium", "luxury"])
            if tier not in included_tiers:
                continue

            # Get tier-appropriate price
            price_key = f"price_{tier}"
            if price_key in item:
                price = Decimal(str(item[price_key]))
            else:
                price = Decimal(str(item.get("price_from", item.get("price", 0))))

            # Apply location factor
            adjusted_price = (price * location_factor).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            items.append(
                LineItem(
                    description=item.get("name", item.get("description", "Item")),
                    quantity=Decimal(str(item.get("quantity", 1))),
                    unit=item.get("unit", "item"),
                    unit_price=adjusted_price,
                    notes=item.get("notes"),
                )
            )

        return items

    def get_premium_upgrades(
        self, project_type: str, tier: str, location_factor: Decimal
    ) -> list[LineItem]:
        """Get premium upgrades for a project type."""
        if tier == "essential":
            return []

        items = []
        category = self.pricing_data.get("categories", {}).get(project_type, {})
        upgrades = category.get("premium_upgrades", [])

        for item in upgrades:
            # Only include upgrades appropriate for tier
            included_tiers = item.get("tiers", ["premium", "luxury"])
            if tier not in included_tiers:
                continue

            price = Decimal(str(item.get("price_from", item.get("price", 0))))
            adjusted_price = (price * location_factor).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            items.append(
                LineItem(
                    description=item.get("name", item.get("description", "Upgrade")),
                    quantity=Decimal("1"),
                    unit=item.get("unit", "item"),
                    unit_price=adjusted_price,
                    notes=item.get("notes"),
                )
            )

        return items

    def calculate_volume_discount(self, subtotal: Decimal) -> Decimal:
        """Calculate applicable volume discount."""
        discount_percentage = Decimal("0")

        for discount in sorted(self.volume_discounts, key=lambda x: x["threshold"]):
            if subtotal >= Decimal(str(discount["threshold"])):
                discount_percentage = Decimal(str(discount["discount_percentage"]))

        return discount_percentage

    def get_project_timeline(self, project_type: str) -> dict[str, Any]:
        """Get estimated timeline for project type."""
        category = self.pricing_data.get("categories", {}).get(project_type, {})
        return category.get(
            "timeline",
            {"duration_weeks": "4-6", "phases": ["Planning", "Execution", "Completion"]},
        )


# =============================================================================
# PDF GENERATOR
# =============================================================================


class QuotePDFGenerator:
    """
    Generates professional PDF quotes with company branding.

    Features:
    - A4 format with proper margins
    - Company letterhead
    - Professional typography
    - Itemized pricing tables
    - Terms and conditions
    - Payment schedule
    """

    # Hampstead Renovations brand colors
    PRIMARY_COLOR = colors.HexColor("#1a365d")  # Deep navy
    SECONDARY_COLOR = colors.HexColor("#2c5282")  # Lighter navy
    ACCENT_COLOR = colors.HexColor("#c9a227")  # Gold accent
    TEXT_COLOR = colors.HexColor("#2d3748")  # Dark gray text
    LIGHT_BG = colors.HexColor("#f7fafc")  # Light background

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Configure custom paragraph styles for branding."""
        self.styles.add(
            ParagraphStyle(
                "CompanyName",
                parent=self.styles["Heading1"],
                fontSize=24,
                textColor=self.PRIMARY_COLOR,
                spaceAfter=6,
                alignment=TA_CENTER,
            )
        )

        self.styles.add(
            ParagraphStyle(
                "CompanyTagline",
                parent=self.styles["Normal"],
                fontSize=11,
                textColor=self.SECONDARY_COLOR,
                alignment=TA_CENTER,
                spaceAfter=20,
                fontName="Helvetica-Oblique",
            )
        )

        self.styles.add(
            ParagraphStyle(
                "QuoteTitle",
                parent=self.styles["Heading1"],
                fontSize=20,
                textColor=self.PRIMARY_COLOR,
                spaceBefore=20,
                spaceAfter=10,
            )
        )

        self.styles.add(
            ParagraphStyle(
                "SectionHeader",
                parent=self.styles["Heading2"],
                fontSize=14,
                textColor=self.PRIMARY_COLOR,
                spaceBefore=15,
                spaceAfter=8,
                borderColor=self.ACCENT_COLOR,
                borderWidth=2,
                borderPadding=4,
            )
        )

        self.styles.add(
            ParagraphStyle(
                "BodyText",
                parent=self.styles["Normal"],
                fontSize=10,
                textColor=self.TEXT_COLOR,
                leading=14,
            )
        )

        self.styles.add(
            ParagraphStyle(
                "SmallText",
                parent=self.styles["Normal"],
                fontSize=8,
                textColor=colors.gray,
                leading=10,
            )
        )

        self.styles.add(
            ParagraphStyle(
                "TotalAmount",
                parent=self.styles["Normal"],
                fontSize=16,
                textColor=self.PRIMARY_COLOR,
                fontName="Helvetica-Bold",
                alignment=TA_RIGHT,
            )
        )

    def generate(
        self,
        quote_number: str,
        customer: CustomerDetails,
        sections: list[QuoteSection],
        subtotal: Decimal,
        vat: Decimal,
        total: Decimal,
        valid_until: datetime,
        project: ProjectDetails,
        timeline: dict[str, Any],
        discount_percentage: Decimal = Decimal("0"),
    ) -> BytesIO:
        """Generate complete PDF quote document."""
        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        elements = []

        # Header
        elements.extend(self._build_header())

        # Quote info box
        elements.extend(
            self._build_quote_info(quote_number, valid_until, customer)
        )

        # Customer details
        elements.extend(self._build_customer_section(customer))

        # Project summary
        elements.extend(self._build_project_summary(project, timeline))

        # Pricing sections
        elements.extend(self._build_pricing_sections(sections))

        # Totals
        elements.extend(
            self._build_totals(subtotal, discount_percentage, vat, total)
        )

        # Payment schedule
        elements.extend(self._build_payment_schedule(total))

        # Terms and conditions
        elements.append(PageBreak())
        elements.extend(self._build_terms_conditions())

        # Footer
        elements.extend(self._build_footer())

        doc.build(elements)
        buffer.seek(0)
        return buffer

    def _build_header(self) -> list:
        """Build company header section."""
        elements = []

        # Company name
        elements.append(
            Paragraph(settings.company_name, self.styles["CompanyName"])
        )

        # Tagline
        elements.append(
            Paragraph(
                "Premium Residential Renovations in North West London",
                self.styles["CompanyTagline"],
            )
        )

        # Contact info line
        contact_info = f"{settings.company_phone} | {settings.company_email} | {settings.company_website}"
        elements.append(
            Paragraph(contact_info, self.styles["SmallText"])
        )

        elements.append(Spacer(1, 15 * mm))

        return elements

    def _build_quote_info(
        self, quote_number: str, valid_until: datetime, customer: CustomerDetails
    ) -> list:
        """Build quote reference information box."""
        elements = []

        elements.append(Paragraph("QUOTATION", self.styles["QuoteTitle"]))

        # Quote details table
        quote_data = [
            ["Quote Reference:", quote_number],
            ["Date:", datetime.now().strftime("%d %B %Y")],
            ["Valid Until:", valid_until.strftime("%d %B %Y")],
            ["Prepared For:", customer.name],
        ]

        table = Table(quote_data, colWidths=[4 * cm, 8 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("TEXTCOLOR", (0, 0), (-1, -1), self.TEXT_COLOR),
                    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        elements.append(table)
        elements.append(Spacer(1, 10 * mm))

        return elements

    def _build_customer_section(self, customer: CustomerDetails) -> list:
        """Build customer address section."""
        elements = []

        elements.append(
            Paragraph("Client Details", self.styles["SectionHeader"])
        )

        address_lines = [
            customer.name,
            customer.address_line1,
        ]
        if customer.address_line2:
            address_lines.append(customer.address_line2)
        address_lines.extend([customer.city, customer.postcode])

        address_text = "<br/>".join(address_lines)
        elements.append(Paragraph(address_text, self.styles["BodyText"]))
        elements.append(
            Paragraph(f"Email: {customer.email}", self.styles["BodyText"])
        )
        elements.append(
            Paragraph(f"Phone: {customer.phone}", self.styles["BodyText"])
        )

        elements.append(Spacer(1, 10 * mm))

        return elements

    def _build_project_summary(
        self, project: ProjectDetails, timeline: dict[str, Any]
    ) -> list:
        """Build project overview section."""
        elements = []

        elements.append(
            Paragraph("Project Overview", self.styles["SectionHeader"])
        )

        project_type_display = project.project_type.replace("_", " ").title()
        tier_display = project.tier.title()

        summary_text = f"""
        <b>Project Type:</b> {project_type_display}<br/>
        <b>Service Level:</b> {tier_display}<br/>
        <b>Estimated Duration:</b> {timeline.get('duration_weeks', 'TBC')} weeks<br/>
        """

        if project.estimated_sqm:
            summary_text += f"<b>Approximate Area:</b> {project.estimated_sqm} m²<br/>"

        if project.preferred_start_date:
            summary_text += f"<b>Preferred Start:</b> {project.preferred_start_date.strftime('%B %Y')}<br/>"

        elements.append(Paragraph(summary_text, self.styles["BodyText"]))

        if project.special_requests:
            elements.append(
                Paragraph(
                    f"<b>Special Requirements:</b> {project.special_requests}",
                    self.styles["BodyText"],
                )
            )

        elements.append(Spacer(1, 10 * mm))

        return elements

    def _build_pricing_sections(self, sections: list[QuoteSection]) -> list:
        """Build itemized pricing tables for each section."""
        elements = []

        elements.append(
            Paragraph("Detailed Pricing", self.styles["SectionHeader"])
        )

        for section in sections:
            # Section header
            elements.append(
                Paragraph(
                    f"<b>{section.name}</b>", self.styles["BodyText"]
                )
            )
            elements.append(Spacer(1, 3 * mm))

            # Items table
            table_data = [["Description", "Qty", "Unit", "Unit Price", "Total"]]

            for item in section.items:
                table_data.append(
                    [
                        item.description,
                        str(item.quantity),
                        item.unit,
                        f"£{item.unit_price:,.2f}",
                        f"£{item.total:,.2f}",
                    ]
                )

            # Section subtotal
            table_data.append(
                ["", "", "", "Section Total:", f"£{section.subtotal:,.2f}"]
            )

            table = Table(
                table_data,
                colWidths=[7 * cm, 1.5 * cm, 2 * cm, 3 * cm, 3 * cm],
            )

            table.setStyle(
                TableStyle(
                    [
                        # Header row
                        ("BACKGROUND", (0, 0), (-1, 0), self.PRIMARY_COLOR),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 9),
                        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                        # Data rows
                        ("FONTSIZE", (0, 1), (-1, -2), 9),
                        ("ALIGN", (1, 1), (1, -1), "CENTER"),
                        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
                        # Subtotal row
                        ("FONTNAME", (3, -1), (-1, -1), "Helvetica-Bold"),
                        ("LINEABOVE", (3, -1), (-1, -1), 1, self.PRIMARY_COLOR),
                        # Alternating row colors
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -2),
                            [colors.white, self.LIGHT_BG],
                        ),
                        # Grid
                        ("GRID", (0, 0), (-1, -2), 0.5, colors.lightgrey),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )

            elements.append(table)
            elements.append(Spacer(1, 5 * mm))

        return elements

    def _build_totals(
        self,
        subtotal: Decimal,
        discount_percentage: Decimal,
        vat: Decimal,
        total: Decimal,
    ) -> list:
        """Build quote totals section."""
        elements = []

        elements.append(Spacer(1, 10 * mm))

        totals_data = [
            ["Subtotal:", f"£{subtotal:,.2f}"],
        ]

        if discount_percentage > 0:
            discount_amount = subtotal * (discount_percentage / 100)
            totals_data.append(
                [f"Volume Discount ({discount_percentage}%):", f"-£{discount_amount:,.2f}"]
            )

        totals_data.extend(
            [
                ["VAT (20%):", f"£{vat:,.2f}"],
                ["TOTAL:", f"£{total:,.2f}"],
            ]
        )

        table = Table(totals_data, colWidths=[12 * cm, 4.5 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("FONTSIZE", (0, 0), (-1, -2), 11),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, -1), (-1, -1), 14),
                    ("TEXTCOLOR", (0, -1), (-1, -1), self.PRIMARY_COLOR),
                    ("LINEABOVE", (0, -1), (-1, -1), 2, self.ACCENT_COLOR),
                    ("TOPPADDING", (0, -1), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        elements.append(table)
        elements.append(Spacer(1, 10 * mm))

        return elements

    def _build_payment_schedule(self, total: Decimal) -> list:
        """Build payment schedule section."""
        elements = []

        elements.append(
            Paragraph("Payment Schedule", self.styles["SectionHeader"])
        )

        deposit = total * (settings.deposit_percentage / 100)
        stage_payment = (total - deposit) / 2
        final_payment = total - deposit - stage_payment

        payment_data = [
            ["Stage", "Percentage", "Amount", "When Due"],
            [
                "Deposit",
                f"{settings.deposit_percentage}%",
                f"£{deposit:,.2f}",
                "Upon acceptance",
            ],
            [
                "First Stage Payment",
                "45%",
                f"£{stage_payment:,.2f}",
                "At project midpoint",
            ],
            ["Final Payment", "45%", f"£{final_payment:,.2f}", "Upon completion"],
        ]

        table = Table(payment_data, colWidths=[4 * cm, 3 * cm, 4 * cm, 5.5 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), self.PRIMARY_COLOR),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (1, 0), (2, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, self.LIGHT_BG]),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        elements.append(table)
        elements.append(Spacer(1, 5 * mm))

        return elements

    def _build_terms_conditions(self) -> list:
        """Build terms and conditions section."""
        elements = []

        elements.append(
            Paragraph("Terms & Conditions", self.styles["QuoteTitle"])
        )

        terms = [
            "<b>1. Quote Validity</b><br/>This quotation is valid for 30 days from the date of issue. Prices may be subject to change after this period.",
            "<b>2. Scope of Work</b><br/>This quote covers the works as described above. Any additional works requested will be quoted separately and agreed in writing before commencement.",
            "<b>3. Payment Terms</b><br/>Payment schedule as outlined above. All payments to be made within 7 days of invoice. We accept bank transfer, credit/debit card, and cheque.",
            "<b>4. Project Timeline</b><br/>Estimated timelines are provided in good faith but may vary due to unforeseen circumstances, supply chain issues, or client-requested changes.",
            "<b>5. Materials</b><br/>All materials will be sourced from reputable UK suppliers. Specific brands or products can be specified at client's request, which may affect pricing.",
            "<b>6. Access Requirements</b><br/>Client agrees to provide reasonable access to the property during normal working hours (8:00 AM - 6:00 PM, Monday to Friday).",
            "<b>7. Insurance</b><br/>Hampstead Renovations maintains comprehensive public liability insurance (£5 million) and employer's liability insurance. Certificates available upon request.",
            "<b>8. Guarantees</b><br/>All workmanship is guaranteed for 2 years from completion. Product warranties as per manufacturer specifications.",
            "<b>9. Variations</b><br/>Any changes to the agreed specification must be confirmed in writing. A revised quotation will be provided for significant changes.",
            "<b>10. Cancellation</b><br/>Cancellation after contract signing may incur charges for work already completed and materials ordered.",
            "<b>11. Disputes</b><br/>We are members of the Federation of Master Builders and follow their code of practice. Any disputes will be handled in accordance with their resolution procedures.",
            "<b>12. GDPR</b><br/>Your personal data will be processed in accordance with our Privacy Policy, available at www.hampsteadrenovations.co.uk/privacy",
        ]

        for term in terms:
            elements.append(Paragraph(term, self.styles["BodyText"]))
            elements.append(Spacer(1, 3 * mm))

        elements.append(Spacer(1, 10 * mm))

        # Acceptance signature block
        elements.append(
            Paragraph("Quote Acceptance", self.styles["SectionHeader"])
        )
        elements.append(
            Paragraph(
                "I confirm that I have read and agree to the terms and conditions above, and wish to proceed with the works as quoted.",
                self.styles["BodyText"],
            )
        )
        elements.append(Spacer(1, 15 * mm))

        signature_data = [
            ["Signature: ___________________________", "Date: _______________"],
            ["Print Name: ___________________________", ""],
        ]

        sig_table = Table(signature_data, colWidths=[10 * cm, 6.5 * cm])
        sig_table.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 15),
                ]
            )
        )

        elements.append(sig_table)

        return elements

    def _build_footer(self) -> list:
        """Build document footer."""
        elements = []

        elements.append(Spacer(1, 15 * mm))

        footer_text = f"""
        {settings.company_name} | {settings.company_address}<br/>
        {settings.company_registration} | {settings.vat_number}<br/>
        Member of the Federation of Master Builders | TrustMark Registered
        """

        elements.append(
            Paragraph(footer_text, self.styles["SmallText"])
        )

        return elements


# =============================================================================
# QUOTE SERVICE
# =============================================================================


class QuoteService:
    """
    Main quote generation service.

    Orchestrates:
    - Pricing calculations
    - PDF generation
    - S3 upload
    - HubSpot integration
    - Audit logging
    """

    def __init__(self):
        self.pricing_engine = PricingEngine()
        self.pdf_generator = QuotePDFGenerator()
        self.s3_client = self._init_s3_client()

    def _init_s3_client(self):
        """Initialize S3 client if credentials available."""
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            return boto3.client(
                "s3",
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region,
            )
        return None

    def generate_quote_number(self) -> str:
        """Generate unique quote reference number."""
        date_part = datetime.now().strftime("%Y%m")
        random_part = uuid.uuid4().hex[:6].upper()
        return f"HR-{date_part}-{random_part}"

    async def generate(self, request: QuoteRequest) -> GeneratedQuote:
        """Generate complete quote from request."""
        logger.info(
            "generating_quote",
            customer=request.customer.name,
            project_type=request.project.project_type,
            tier=request.project.tier,
        )

        # Generate quote number
        quote_number = self.generate_quote_number()
        quote_id = str(uuid.uuid4())

        # Calculate location factor
        location_factor = self.pricing_engine.get_location_factor(
            request.customer.location_area
        )

        # Build quote sections
        sections = []

        # Base items section
        base_items = self.pricing_engine.get_base_items(
            request.project.project_type,
            request.project.tier,
            location_factor,
        )
        if base_items:
            sections.append(
                QuoteSection(
                    name=f"{request.project.project_type.replace('_', ' ').title()} - Core Works",
                    items=base_items,
                )
            )

        # Premium upgrades section (if applicable)
        if request.project.tier in ["premium", "luxury"]:
            upgrades = self.pricing_engine.get_premium_upgrades(
                request.project.project_type,
                request.project.tier,
                location_factor,
            )
            if upgrades:
                sections.append(
                    QuoteSection(
                        name="Premium Upgrades & Enhancements",
                        items=upgrades,
                    )
                )

        # Calculate totals
        subtotal = sum(section.subtotal for section in sections)

        # Apply volume discount
        discount_percentage = self.pricing_engine.calculate_volume_discount(subtotal)
        if discount_percentage > 0:
            discount_amount = subtotal * (discount_percentage / 100)
            subtotal = subtotal - discount_amount

        # Calculate VAT
        vat_rate = Decimal("0.20")
        vat = (subtotal * vat_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total = subtotal + vat

        # Set validity date
        valid_until = datetime.now() + timedelta(days=settings.quote_validity_days)

        # Get timeline info
        timeline = self.pricing_engine.get_project_timeline(request.project.project_type)

        # Generate PDF
        pdf_buffer = self.pdf_generator.generate(
            quote_number=quote_number,
            customer=request.customer,
            sections=sections,
            subtotal=subtotal,
            vat=vat,
            total=total,
            valid_until=valid_until,
            project=request.project,
            timeline=timeline,
            discount_percentage=discount_percentage,
        )

        # Save PDF locally
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        pdf_path = output_dir / f"{quote_number}.pdf"

        with open(pdf_path, "wb") as f:
            f.write(pdf_buffer.read())
        pdf_buffer.seek(0)

        # Upload to S3 if configured
        s3_url = None
        if self.s3_client:
            s3_url = await self._upload_to_s3(
                pdf_buffer, f"quotes/{quote_number}.pdf"
            )

        # Update HubSpot if deal_id provided
        if request.deal_id and settings.hubspot_api_key:
            await self._attach_to_hubspot(
                request.deal_id, quote_number, s3_url or str(pdf_path), total
            )

        logger.info(
            "quote_generated",
            quote_number=quote_number,
            total=float(total),
            s3_url=s3_url,
        )

        return GeneratedQuote(
            quote_id=quote_id,
            quote_number=quote_number,
            pdf_path=str(pdf_path),
            s3_url=s3_url,
            subtotal=subtotal,
            vat=vat,
            total=total,
            valid_until=valid_until,
            created_at=datetime.now(),
        )

    async def _upload_to_s3(self, pdf_buffer: BytesIO, key: str) -> Optional[str]:
        """Upload PDF to S3 bucket."""
        try:
            self.s3_client.upload_fileobj(
                pdf_buffer,
                settings.s3_bucket,
                key,
                ExtraArgs={
                    "ContentType": "application/pdf",
                    "Metadata": {
                        "generator": "hampstead-quote-builder",
                        "version": "1.0.0",
                    },
                },
            )
            return f"https://{settings.s3_bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"
        except Exception as e:
            logger.error("s3_upload_failed", error=str(e))
            return None

    async def _attach_to_hubspot(
        self, deal_id: str, quote_number: str, document_url: str, total: Decimal
    ):
        """Attach quote to HubSpot deal and update properties."""
        try:
            async with httpx.AsyncClient() as client:
                # Update deal properties
                await client.patch(
                    f"https://api.hubapi.com/crm/v3/objects/deals/{deal_id}",
                    headers={
                        "Authorization": f"Bearer {settings.hubspot_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "properties": {
                            "quote_number": quote_number,
                            "quote_amount": str(total),
                            "quote_date": datetime.now().isoformat(),
                            "quote_document_url": document_url,
                        }
                    },
                )

                # Create note with quote details
                await client.post(
                    "https://api.hubapi.com/crm/v3/objects/notes",
                    headers={
                        "Authorization": f"Bearer {settings.hubspot_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "properties": {
                            "hs_note_body": f"Quote {quote_number} generated. Total: £{total:,.2f}. Document: {document_url}",
                            "hs_timestamp": datetime.now().isoformat(),
                        },
                        "associations": [
                            {
                                "to": {"id": deal_id},
                                "types": [
                                    {
                                        "associationCategory": "HUBSPOT_DEFINED",
                                        "associationTypeId": 214,  # Note to Deal
                                    }
                                ],
                            }
                        ],
                    },
                )

            logger.info(
                "hubspot_updated",
                deal_id=deal_id,
                quote_number=quote_number,
            )
        except Exception as e:
            logger.error("hubspot_update_failed", deal_id=deal_id, error=str(e))


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

# Initialize service
quote_service = QuoteService()

# Create FastAPI app
app = FastAPI(
    title="Hampstead Renovations Quote Builder",
    description="Professional quote generation service for renovation projects",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QuoteResponse(BaseModel):
    """API response model for quote generation."""
    quote_number: str
    total: float
    subtotal: float
    vat: float
    discount: float
    pdf_url: Optional[str] = None
    pdf_path: Optional[str] = None
    valid_until: str
    generated_at: str
    message: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    timestamp: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="quote-builder",
        version="1.0.0",
        timestamp=datetime.now().isoformat(),
    )


@app.post("/generate", response_model=QuoteResponse)
async def generate_quote(request: QuoteRequest, background_tasks: BackgroundTasks):
    """
    Generate a professional PDF quote.
    
    This endpoint creates a detailed quote based on customer and project details,
    generates a PDF, and optionally uploads to S3.
    """
    try:
        logger.info(
            "quote_generation_requested",
            customer_name=request.customer.name,
            project_type=request.project.project_type,
            tier=request.project.tier,
        )
        
        result = await quote_service.generate(request)
        
        # Calculate valid until date
        valid_until = datetime.now() + timedelta(days=30)
        
        return QuoteResponse(
            quote_number=result.quote_number,
            total=float(result.total),
            subtotal=float(result.subtotal),
            vat=float(result.vat),
            discount=float(result.discount),
            pdf_url=result.s3_url,
            pdf_path=result.pdf_path,
            valid_until=valid_until.strftime("%Y-%m-%d"),
            generated_at=datetime.now().isoformat(),
            message="Quote generated successfully",
        )
        
    except ValueError as e:
        logger.error("quote_validation_error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("quote_generation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Quote generation failed: {str(e)}")


@app.get("/pricing-matrix")
async def get_pricing_matrix():
    """Get the current pricing matrix."""
    try:
        pricing_engine = PricingEngine()
        return {
            "status": "success",
            "pricing_matrix": pricing_engine.pricing_matrix,
            "location_multipliers": pricing_engine.location_multipliers,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/project-types")
async def get_project_types():
    """Get available project types and tiers."""
    return {
        "project_types": [
            "kitchen", "bathroom", "extension", "loft_conversion",
            "full_renovation", "flooring", "electrical", "plumbing",
            "painting", "landscaping",
        ],
        "tiers": ["essential", "premium", "luxury"],
        "description": {
            "essential": "Quality materials and workmanship at competitive prices",
            "premium": "Enhanced finishes with premium materials and extended warranties",
            "luxury": "Bespoke solutions with the finest materials and white-glove service",
        },
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
