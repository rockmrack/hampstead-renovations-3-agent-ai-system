"""
Hampstead Renovations - Contract Generator Service
FastAPI microservice for generating professional PDF contracts
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from io import BytesIO
from typing import Optional, List

import boto3
from botocore.config import Config
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

class Settings:
    """Application settings from environment variables."""
    APP_NAME: str = "Hampstead Renovations Contract Generator"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "eu-west-2")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "hampstead-renovations-docs")
    S3_PREFIX: str = "contracts"
    
    # Company Details
    COMPANY_NAME: str = "Hampstead Renovations Ltd"
    COMPANY_ADDRESS: str = "45 Heath Street, Hampstead, London NW3 6TE"
    COMPANY_PHONE: str = "020 7123 4567"
    COMPANY_EMAIL: str = "contracts@hampsteadrenovations.co.uk"
    COMPANY_REG: str = "12345678"
    COMPANY_VAT: str = "GB 123 4567 89"
    
    # Contract Terms
    DEPOSIT_PERCENTAGE: int = 25
    RETENTION_PERCENTAGE: int = 5
    WARRANTY_MONTHS: int = 12


settings = Settings()


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class PaymentScheduleType(str, Enum):
    STANDARD = "standard"
    PHASED = "phased"
    CUSTOM = "custom"


class PaymentMilestone(BaseModel):
    """Individual payment milestone."""
    stage: str = Field(..., description="Stage description (e.g., 'Foundation complete')")
    percentage: int = Field(..., ge=0, le=100)
    amount: Decimal = Field(default=Decimal("0"))
    due_description: str = Field(default="", description="When payment is due")


class ContractParty(BaseModel):
    """Party to the contract (client details)."""
    name: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str = "London"
    postcode: str
    email: EmailStr
    phone: str


class ProjectScope(BaseModel):
    """Detailed project scope item."""
    category: str = Field(..., description="e.g., 'Kitchen Extension', 'Structural'")
    description: str
    included_items: List[str] = Field(default_factory=list)
    excluded_items: List[str] = Field(default_factory=list)


class ContractRequest(BaseModel):
    """Request to generate a contract."""
    # Reference
    quote_reference: str = Field(..., description="Original quote reference (e.g., HR-2024-0123)")
    
    # Client
    client: ContractParty
    
    # Property
    property_address_line1: str
    property_address_line2: Optional[str] = None
    property_city: str = "London"
    property_postcode: str
    
    # Project Details
    project_title: str = Field(..., description="e.g., 'Kitchen Extension and Renovation'")
    project_description: str
    scope_items: List[ProjectScope]
    
    # Financials
    contract_value: Decimal = Field(..., gt=0)
    vat_rate: Decimal = Field(default=Decimal("20"))
    vat_amount: Decimal = Field(default=Decimal("0"))
    total_including_vat: Decimal = Field(default=Decimal("0"))
    
    # Payment
    payment_schedule_type: PaymentScheduleType = PaymentScheduleType.STANDARD
    payment_milestones: List[PaymentMilestone] = Field(default_factory=list)
    
    # Timeline
    estimated_start_date: Optional[datetime] = None
    estimated_duration_weeks: int = Field(default=12, ge=1)
    estimated_completion_date: Optional[datetime] = None
    
    # Planning & Permissions
    planning_required: bool = False
    planning_reference: Optional[str] = None
    building_control_required: bool = True
    party_wall_required: bool = False
    
    # Special Terms
    special_conditions: List[str] = Field(default_factory=list)
    
    # Options
    send_email: bool = False


class ContractResponse(BaseModel):
    """Response from contract generation."""
    success: bool
    contract_reference: str
    pdf_url: str
    generated_at: datetime
    valid_for_days: int = 14
    message: str


# ═══════════════════════════════════════════════════════════════════════════════
# PDF GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

class ContractPDFGenerator:
    """Generates professional contract PDFs."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """Create custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='ContractTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#253956')
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.HexColor('#253956'),
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='SubHeading',
            parent=self.styles['Heading3'],
            fontSize=10,
            spaceBefore=10,
            spaceAfter=5,
            textColor=colors.HexColor('#253956'),
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='ContractBody',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=12,
            alignment=TA_JUSTIFY,
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='ClauseNumber',
            parent=self.styles['Normal'],
            fontSize=9,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='SmallText',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#666666')
        ))
        
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=9,
            fontName='Helvetica-Bold',
            textColor=colors.white
        ))
    
    def generate(self, request: ContractRequest) -> BytesIO:
        """Generate the contract PDF."""
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=20*mm,
            rightMargin=20*mm,
            topMargin=25*mm,
            bottomMargin=25*mm
        )
        
        story = []
        
        # Header
        story.extend(self._build_header(request))
        
        # Parties
        story.extend(self._build_parties_section(request))
        
        # Property & Project
        story.extend(self._build_project_section(request))
        
        # Scope of Works
        story.extend(self._build_scope_section(request))
        
        # Contract Sum
        story.extend(self._build_financial_section(request))
        
        # Payment Schedule
        story.extend(self._build_payment_section(request))
        
        # Timeline
        story.extend(self._build_timeline_section(request))
        
        # Terms & Conditions
        story.append(PageBreak())
        story.extend(self._build_terms_section(request))
        
        # Special Conditions
        if request.special_conditions:
            story.extend(self._build_special_conditions(request))
        
        # Signatures
        story.append(PageBreak())
        story.extend(self._build_signature_section(request))
        
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
        buffer.seek(0)
        return buffer
    
    def _build_header(self, request: ContractRequest) -> list:
        """Build document header."""
        elements = []
        
        # Company name as header
        elements.append(Paragraph(settings.COMPANY_NAME.upper(), self.styles['ContractTitle']))
        elements.append(Spacer(1, 5*mm))
        
        # Contract title
        elements.append(Paragraph("BUILDING CONTRACT", ParagraphStyle(
            'ContractType',
            fontSize=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#d4b814'),
            fontName='Helvetica-Bold'
        )))
        
        elements.append(Spacer(1, 3*mm))
        
        # Reference and date
        contract_ref = f"CONTRACT-{request.quote_reference}"
        date_str = datetime.now().strftime("%d %B %Y")
        
        ref_data = [
            [f"Contract Reference: {contract_ref}", f"Date: {date_str}"]
        ]
        ref_table = Table(ref_data, colWidths=[85*mm, 85*mm])
        ref_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        elements.append(ref_table)
        
        elements.append(Spacer(1, 8*mm))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#d4b814')))
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_parties_section(self, request: ContractRequest) -> list:
        """Build the parties section."""
        elements = []
        
        elements.append(Paragraph("1. THE PARTIES", self.styles['SectionHeading']))
        
        # Contractor details
        elements.append(Paragraph("<b>The Contractor:</b>", self.styles['ContractBody']))
        elements.append(Paragraph(f"""
            {settings.COMPANY_NAME}<br/>
            {settings.COMPANY_ADDRESS}<br/>
            Company Registration: {settings.COMPANY_REG}<br/>
            VAT Registration: {settings.COMPANY_VAT}
        """, self.styles['ContractBody']))
        
        elements.append(Spacer(1, 3*mm))
        
        # Client details
        elements.append(Paragraph("<b>The Client:</b>", self.styles['ContractBody']))
        client_address = f"{request.client.address_line1}"
        if request.client.address_line2:
            client_address += f", {request.client.address_line2}"
        client_address += f", {request.client.city}, {request.client.postcode}"
        
        elements.append(Paragraph(f"""
            {request.client.name}<br/>
            {client_address}<br/>
            Email: {request.client.email}<br/>
            Phone: {request.client.phone}
        """, self.styles['ContractBody']))
        
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_project_section(self, request: ContractRequest) -> list:
        """Build project details section."""
        elements = []
        
        elements.append(Paragraph("2. THE PROJECT", self.styles['SectionHeading']))
        
        # Property address
        property_address = f"{request.property_address_line1}"
        if request.property_address_line2:
            property_address += f", {request.property_address_line2}"
        property_address += f", {request.property_city}, {request.property_postcode}"
        
        elements.append(Paragraph(f"<b>Property Address:</b> {property_address}", self.styles['ContractBody']))
        elements.append(Paragraph(f"<b>Project Title:</b> {request.project_title}", self.styles['ContractBody']))
        elements.append(Paragraph(f"<b>Project Description:</b>", self.styles['ContractBody']))
        elements.append(Paragraph(request.project_description, self.styles['ContractBody']))
        
        # Planning & permissions
        permissions = []
        if request.planning_required:
            permissions.append(f"Planning Permission: {'Ref: ' + request.planning_reference if request.planning_reference else 'Required'}")
        if request.building_control_required:
            permissions.append("Building Control: Required")
        if request.party_wall_required:
            permissions.append("Party Wall Agreement: Required")
        
        if permissions:
            elements.append(Spacer(1, 3*mm))
            elements.append(Paragraph("<b>Permissions & Approvals:</b>", self.styles['ContractBody']))
            for perm in permissions:
                elements.append(Paragraph(f"• {perm}", self.styles['ContractBody']))
        
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_scope_section(self, request: ContractRequest) -> list:
        """Build scope of works section."""
        elements = []
        
        elements.append(Paragraph("3. SCOPE OF WORKS", self.styles['SectionHeading']))
        elements.append(Paragraph(
            "The Contractor agrees to carry out and complete the following works:",
            self.styles['ContractBody']
        ))
        
        for i, scope in enumerate(request.scope_items, 1):
            elements.append(Paragraph(f"<b>3.{i} {scope.category}</b>", self.styles['SubHeading']))
            elements.append(Paragraph(scope.description, self.styles['ContractBody']))
            
            if scope.included_items:
                elements.append(Paragraph("<i>Included in this section:</i>", self.styles['SmallText']))
                for item in scope.included_items:
                    elements.append(Paragraph(f"  • {item}", self.styles['ContractBody']))
            
            if scope.excluded_items:
                elements.append(Paragraph("<i>Excluded from this section:</i>", self.styles['SmallText']))
                for item in scope.excluded_items:
                    elements.append(Paragraph(f"  • {item}", self.styles['ContractBody']))
        
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_financial_section(self, request: ContractRequest) -> list:
        """Build the contract sum section."""
        elements = []
        
        elements.append(Paragraph("4. CONTRACT SUM", self.styles['SectionHeading']))
        
        # Calculate values if not provided
        if request.vat_amount == 0:
            vat_amount = request.contract_value * request.vat_rate / 100
        else:
            vat_amount = request.vat_amount
            
        if request.total_including_vat == 0:
            total = request.contract_value + vat_amount
        else:
            total = request.total_including_vat
        
        # Financial table
        fin_data = [
            ["Description", "Amount"],
            ["Contract Sum (excluding VAT)", f"£{request.contract_value:,.2f}"],
            [f"VAT @ {request.vat_rate}%", f"£{vat_amount:,.2f}"],
            ["Total Contract Sum (including VAT)", f"£{total:,.2f}"]
        ]
        
        fin_table = Table(fin_data, colWidths=[120*mm, 50*mm])
        fin_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#253956')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5f5f5')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(fin_table)
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_payment_section(self, request: ContractRequest) -> list:
        """Build the payment schedule section."""
        elements = []
        
        elements.append(Paragraph("5. PAYMENT SCHEDULE", self.styles['SectionHeading']))
        
        total = request.total_including_vat if request.total_including_vat > 0 else request.contract_value * Decimal("1.2")
        
        # Generate standard schedule if not provided
        if not request.payment_milestones:
            milestones = [
                PaymentMilestone(
                    stage="Deposit on signing",
                    percentage=settings.DEPOSIT_PERCENTAGE,
                    amount=total * settings.DEPOSIT_PERCENTAGE / 100,
                    due_description="Due upon contract signing"
                ),
                PaymentMilestone(
                    stage="First Fix Complete",
                    percentage=25,
                    amount=total * 25 / 100,
                    due_description="Upon completion of first fix"
                ),
                PaymentMilestone(
                    stage="Second Fix Complete",
                    percentage=25,
                    amount=total * 25 / 100,
                    due_description="Upon completion of second fix"
                ),
                PaymentMilestone(
                    stage="Practical Completion",
                    percentage=20,
                    amount=total * 20 / 100,
                    due_description="Upon practical completion"
                ),
                PaymentMilestone(
                    stage="Retention Release",
                    percentage=settings.RETENTION_PERCENTAGE,
                    amount=total * settings.RETENTION_PERCENTAGE / 100,
                    due_description=f"{settings.WARRANTY_MONTHS} months after completion"
                ),
            ]
        else:
            milestones = request.payment_milestones
            # Calculate amounts if not provided
            for m in milestones:
                if m.amount == 0:
                    m.amount = total * m.percentage / 100
        
        # Payment table
        pay_data = [["Stage", "Percentage", "Amount", "Due"]]
        for m in milestones:
            pay_data.append([m.stage, f"{m.percentage}%", f"£{m.amount:,.2f}", m.due_description])
        
        pay_table = Table(pay_data, colWidths=[55*mm, 25*mm, 35*mm, 55*mm])
        pay_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#253956')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (2, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(pay_table)
        elements.append(Spacer(1, 3*mm))
        
        elements.append(Paragraph(
            "Payments are due within 7 days of invoice. Late payments may incur interest at 4% above Bank of England base rate.",
            self.styles['SmallText']
        ))
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_timeline_section(self, request: ContractRequest) -> list:
        """Build timeline section."""
        elements = []
        
        elements.append(Paragraph("6. PROJECT TIMELINE", self.styles['SectionHeading']))
        
        start_date = request.estimated_start_date or datetime.now() + timedelta(days=14)
        completion_date = request.estimated_completion_date or (start_date + timedelta(weeks=request.estimated_duration_weeks))
        
        elements.append(Paragraph(f"<b>Estimated Start Date:</b> {start_date.strftime('%d %B %Y')}", self.styles['ContractBody']))
        elements.append(Paragraph(f"<b>Estimated Duration:</b> {request.estimated_duration_weeks} weeks", self.styles['ContractBody']))
        elements.append(Paragraph(f"<b>Target Completion:</b> {completion_date.strftime('%d %B %Y')}", self.styles['ContractBody']))
        
        elements.append(Spacer(1, 3*mm))
        elements.append(Paragraph(
            "The above dates are estimates. The Contractor will notify the Client of any changes to the programme. "
            "Completion may be affected by unforeseen circumstances, weather conditions, or client-requested variations.",
            self.styles['SmallText']
        ))
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_terms_section(self, request: ContractRequest) -> list:
        """Build terms and conditions section."""
        elements = []
        
        elements.append(Paragraph("7. TERMS AND CONDITIONS", self.styles['SectionHeading']))
        
        terms = [
            ("7.1", "Variations", "Any changes to the scope of works must be agreed in writing. Variations may affect the contract sum and completion date."),
            ("7.2", "Access", "The Client shall provide the Contractor with access to the property during normal working hours (Monday to Friday, 8am to 5pm)."),
            ("7.3", "Insurance", "The Contractor maintains Public Liability Insurance of £5,000,000 and Employer's Liability Insurance of £10,000,000."),
            ("7.4", "Health & Safety", "The Contractor will comply with all relevant health and safety legislation and maintain a safe working environment."),
            ("7.5", "Materials", "All materials shall be new and of good quality unless otherwise agreed. Reasonable substitutions may be made with Client approval."),
            ("7.6", "Subcontractors", "The Contractor may employ specialist subcontractors for specific works. The Contractor remains responsible for their work."),
            ("7.7", "Defects Liability", f"The Contractor will rectify any defects arising from workmanship or materials for a period of {settings.WARRANTY_MONTHS} months from practical completion."),
            ("7.8", "Disputes", "In the event of a dispute, both parties agree to attempt resolution through mediation before legal proceedings."),
            ("7.9", "Termination", "Either party may terminate this contract with 14 days written notice. The Client shall pay for all works completed to date."),
            ("7.10", "Governing Law", "This contract shall be governed by and construed in accordance with the laws of England and Wales."),
        ]
        
        for num, title, text in terms:
            elements.append(Paragraph(f"<b>{num} {title}</b>", self.styles['ClauseNumber']))
            elements.append(Paragraph(text, self.styles['ContractBody']))
        
        return elements
    
    def _build_special_conditions(self, request: ContractRequest) -> list:
        """Build special conditions section."""
        elements = []
        
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph("8. SPECIAL CONDITIONS", self.styles['SectionHeading']))
        
        for i, condition in enumerate(request.special_conditions, 1):
            elements.append(Paragraph(f"8.{i} {condition}", self.styles['ContractBody']))
        
        return elements
    
    def _build_signature_section(self, request: ContractRequest) -> list:
        """Build signature section."""
        elements = []
        
        elements.append(Paragraph("SIGNATURES", self.styles['SectionHeading']))
        elements.append(Spacer(1, 5*mm))
        
        elements.append(Paragraph(
            "By signing below, both parties agree to be bound by the terms of this contract.",
            self.styles['ContractBody']
        ))
        elements.append(Spacer(1, 10*mm))
        
        # Signature boxes
        sig_style = TableStyle([
            ('LINEBELOW', (0, 0), (0, 0), 1, colors.black),
            ('LINEBELOW', (0, 2), (0, 2), 1, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 20),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ])
        
        # Contractor signature
        elements.append(Paragraph("<b>For and on behalf of the Contractor:</b>", self.styles['ContractBody']))
        contractor_sig = Table([
            [""],
            ["Signature"],
            [""],
            ["Name: Ross Davidson, Director"],
            [f"Date: _______________________"],
        ], colWidths=[80*mm])
        contractor_sig.setStyle(sig_style)
        elements.append(contractor_sig)
        
        elements.append(Spacer(1, 15*mm))
        
        # Client signature
        elements.append(Paragraph("<b>For and on behalf of the Client:</b>", self.styles['ContractBody']))
        client_sig = Table([
            [""],
            ["Signature"],
            [""],
            [f"Name: {request.client.name}"],
            [f"Date: _______________________"],
        ], colWidths=[80*mm])
        client_sig.setStyle(sig_style)
        elements.append(client_sig)
        
        elements.append(Spacer(1, 20*mm))
        
        # Witness section
        elements.append(Paragraph("<b>Witness (optional):</b>", self.styles['ContractBody']))
        witness_table = Table([
            ["Signature: _______________________", "Name: _______________________"],
            ["Address: _______________________", "Date: _______________________"],
        ], colWidths=[85*mm, 85*mm])
        witness_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(witness_table)
        
        return elements
    
    def _add_page_number(self, canvas, doc):
        """Add page number to each page."""
        canvas.saveState()
        
        # Footer
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawString(20*mm, 15*mm, f"{settings.COMPANY_NAME} | {settings.COMPANY_PHONE} | {settings.COMPANY_EMAIL}")
        canvas.drawRightString(A4[0] - 20*mm, 15*mm, f"Page {doc.page}")
        
        canvas.restoreState()


# ═══════════════════════════════════════════════════════════════════════════════
# S3 UPLOAD
# ═══════════════════════════════════════════════════════════════════════════════

class S3Uploader:
    """Handles S3 uploads."""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            config=Config(signature_version='s3v4')
        )
    
    def upload(self, file_buffer: BytesIO, filename: str) -> str:
        """Upload file to S3 and return URL."""
        key = f"{settings.S3_PREFIX}/{filename}"
        
        self.s3_client.upload_fileobj(
            file_buffer,
            settings.S3_BUCKET,
            key,
            ExtraArgs={
                'ContentType': 'application/pdf',
                'ContentDisposition': f'inline; filename="{filename}"'
            }
        )
        
        # Generate presigned URL valid for 7 days
        url = self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.S3_BUCKET, 'Key': key},
            ExpiresIn=604800
        )
        
        return url


# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Generate professional PDF contracts for Hampstead Renovations"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pdf_generator = ContractPDFGenerator()
s3_uploader = S3Uploader()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.APP_NAME, "version": settings.VERSION}


@app.post("/generate", response_model=ContractResponse)
async def generate_contract(request: ContractRequest, background_tasks: BackgroundTasks):
    """Generate a contract PDF."""
    try:
        # Generate reference
        contract_ref = f"CONTRACT-{request.quote_reference}"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{contract_ref}_{timestamp}.pdf"
        
        # Generate PDF
        pdf_buffer = pdf_generator.generate(request)
        
        # Upload to S3
        pdf_url = s3_uploader.upload(pdf_buffer, filename)
        
        return ContractResponse(
            success=True,
            contract_reference=contract_ref,
            pdf_url=pdf_url,
            generated_at=datetime.now(),
            valid_for_days=14,
            message="Contract generated successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
