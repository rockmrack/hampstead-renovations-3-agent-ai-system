"""
Hampstead Renovations - Invoice Generator Service
FastAPI microservice for generating professional PDF invoices
"""

import os
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from io import BytesIO
from typing import Optional, List

import boto3
from botocore.config import Config
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

class Settings:
    """Application settings from environment variables."""
    APP_NAME: str = "Hampstead Renovations Invoice Generator"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "eu-west-2")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "hampstead-renovations-docs")
    S3_PREFIX: str = "invoices"
    
    # Company Details
    COMPANY_NAME: str = "Hampstead Renovations Ltd"
    COMPANY_ADDRESS_1: str = "45 Heath Street"
    COMPANY_ADDRESS_2: str = "Hampstead, London NW3 6TE"
    COMPANY_PHONE: str = "020 7123 4567"
    COMPANY_EMAIL: str = "accounts@hampsteadrenovations.co.uk"
    COMPANY_REG: str = "12345678"
    COMPANY_VAT: str = "GB 123 4567 89"
    
    # Bank Details
    BANK_NAME: str = "Barclays Bank"
    BANK_ACCOUNT_NAME: str = "Hampstead Renovations Ltd"
    BANK_SORT_CODE: str = "20-00-00"
    BANK_ACCOUNT_NUMBER: str = "12345678"
    BANK_IBAN: str = "GB00BARC20000012345678"
    
    # Invoice Terms
    PAYMENT_TERMS_DAYS: int = 7


settings = Settings()


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class InvoiceType(str, Enum):
    DEPOSIT = "deposit"
    INTERIM = "interim"
    FINAL = "final"
    VARIATION = "variation"
    RETENTION = "retention"


class CustomerDetails(BaseModel):
    """Customer billing details."""
    name: str
    company: Optional[str] = None
    address_line1: str
    address_line2: Optional[str] = None
    city: str = "London"
    postcode: str
    email: EmailStr
    phone: Optional[str] = None


class LineItem(BaseModel):
    """Invoice line item."""
    description: str
    quantity: Decimal = Field(default=Decimal("1"))
    unit: str = Field(default="item")
    unit_price: Decimal
    vat_rate: Decimal = Field(default=Decimal("20"))
    
    @property
    def net_amount(self) -> Decimal:
        return self.quantity * self.unit_price
    
    @property
    def vat_amount(self) -> Decimal:
        return self.net_amount * self.vat_rate / 100
    
    @property
    def gross_amount(self) -> Decimal:
        return self.net_amount + self.vat_amount


class InvoiceRequest(BaseModel):
    """Request to generate an invoice."""
    # References
    contract_reference: Optional[str] = None
    quote_reference: Optional[str] = None
    project_reference: Optional[str] = None
    
    # Invoice Type
    invoice_type: InvoiceType = InvoiceType.INTERIM
    invoice_description: str = Field(..., description="e.g., 'First Fix Complete'")
    
    # Customer
    customer: CustomerDetails
    
    # Property (if different from billing address)
    property_address: Optional[str] = None
    
    # Line Items
    line_items: List[LineItem]
    
    # Financials (calculated if not provided)
    subtotal: Decimal = Field(default=Decimal("0"))
    vat_total: Decimal = Field(default=Decimal("0"))
    total: Decimal = Field(default=Decimal("0"))
    
    # Payment already received
    amount_paid: Decimal = Field(default=Decimal("0"))
    
    # Due date
    invoice_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    payment_terms_days: int = Field(default=settings.PAYMENT_TERMS_DAYS)
    
    # Notes
    notes: Optional[str] = None
    
    # Options
    include_bank_details: bool = True
    send_email: bool = False


class InvoiceResponse(BaseModel):
    """Response from invoice generation."""
    success: bool
    invoice_number: str
    pdf_url: str
    total_due: Decimal
    due_date: datetime
    generated_at: datetime
    message: str


# ═══════════════════════════════════════════════════════════════════════════════
# INVOICE NUMBER GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

class InvoiceNumberGenerator:
    """Generates sequential invoice numbers."""
    
    _counter_file = "/tmp/invoice_counter.txt"
    
    @classmethod
    def get_next(cls) -> str:
        """Get next invoice number."""
        try:
            with open(cls._counter_file, 'r') as f:
                counter = int(f.read().strip())
        except (FileNotFoundError, ValueError):
            counter = 1000
        
        counter += 1
        
        with open(cls._counter_file, 'w') as f:
            f.write(str(counter))
        
        year = datetime.now().year
        return f"INV-{year}-{counter:04d}"


# ═══════════════════════════════════════════════════════════════════════════════
# PDF GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

class InvoicePDFGenerator:
    """Generates professional invoice PDFs."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """Create custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            fontSize=18,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#253956'),
            spaceAfter=5
        ))
        
        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            fontSize=28,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#d4b814'),
            alignment=TA_RIGHT
        ))
        
        self.styles.add(ParagraphStyle(
            name='InvoiceNumber',
            fontSize=12,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#253956'),
            alignment=TA_RIGHT
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#253956'),
            spaceBefore=10,
            spaceAfter=5
        ))
        
        self.styles.add(ParagraphStyle(
            name='BodyText',
            fontSize=9,
            leading=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='SmallText',
            fontSize=8,
            textColor=colors.HexColor('#666666')
        ))
        
        self.styles.add(ParagraphStyle(
            name='TotalLabel',
            fontSize=11,
            fontName='Helvetica-Bold',
            alignment=TA_RIGHT
        ))
        
        self.styles.add(ParagraphStyle(
            name='TotalAmount',
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#253956'),
            alignment=TA_RIGHT
        ))
    
    def generate(self, request: InvoiceRequest, invoice_number: str) -> BytesIO:
        """Generate the invoice PDF."""
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=20*mm,
            rightMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        story = []
        
        # Calculate totals if not provided
        if request.subtotal == 0:
            request.subtotal = sum(item.net_amount for item in request.line_items)
        if request.vat_total == 0:
            request.vat_total = sum(item.vat_amount for item in request.line_items)
        if request.total == 0:
            request.total = request.subtotal + request.vat_total
        
        # Set dates
        invoice_date = request.invoice_date or datetime.now()
        due_date = request.due_date or (invoice_date + timedelta(days=request.payment_terms_days))
        
        # Header
        story.extend(self._build_header(invoice_number, invoice_date, due_date))
        
        # Addresses
        story.extend(self._build_addresses(request))
        
        # References
        story.extend(self._build_references(request))
        
        # Line Items
        story.extend(self._build_line_items(request))
        
        # Totals
        story.extend(self._build_totals(request))
        
        # Bank Details
        if request.include_bank_details:
            story.extend(self._build_bank_details())
        
        # Notes
        if request.notes:
            story.extend(self._build_notes(request.notes))
        
        # Footer
        story.extend(self._build_footer())
        
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def _build_header(self, invoice_number: str, invoice_date: datetime, due_date: datetime) -> list:
        """Build invoice header."""
        elements = []
        
        # Two-column header
        header_data = [
            [
                Paragraph(settings.COMPANY_NAME, self.styles['CompanyName']),
                Paragraph("INVOICE", self.styles['InvoiceTitle'])
            ],
            [
                Paragraph(f"{settings.COMPANY_ADDRESS_1}<br/>{settings.COMPANY_ADDRESS_2}", self.styles['BodyText']),
                Paragraph(f"<b>{invoice_number}</b>", self.styles['InvoiceNumber'])
            ],
            [
                Paragraph(f"Tel: {settings.COMPANY_PHONE}<br/>Email: {settings.COMPANY_EMAIL}", self.styles['SmallText']),
                Paragraph(
                    f"Date: {invoice_date.strftime('%d %B %Y')}<br/>Due: {due_date.strftime('%d %B %Y')}",
                    ParagraphStyle('DateStyle', fontSize=9, alignment=TA_RIGHT)
                )
            ]
        ]
        
        header_table = Table(header_data, colWidths=[100*mm, 70*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 5*mm))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#d4b814')))
        elements.append(Spacer(1, 8*mm))
        
        return elements
    
    def _build_addresses(self, request: InvoiceRequest) -> list:
        """Build billing address section."""
        elements = []
        
        # Build address string
        billing_address = f"{request.customer.name}"
        if request.customer.company:
            billing_address += f"<br/>{request.customer.company}"
        billing_address += f"<br/>{request.customer.address_line1}"
        if request.customer.address_line2:
            billing_address += f"<br/>{request.customer.address_line2}"
        billing_address += f"<br/>{request.customer.city}, {request.customer.postcode}"
        
        address_data = [
            [
                Paragraph("<b>Bill To:</b>", self.styles['SectionHeader']),
                Paragraph("<b>Project Address:</b>", self.styles['SectionHeader']) if request.property_address else ""
            ],
            [
                Paragraph(billing_address, self.styles['BodyText']),
                Paragraph(request.property_address or "", self.styles['BodyText'])
            ]
        ]
        
        address_table = Table(address_data, colWidths=[85*mm, 85*mm])
        address_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        elements.append(address_table)
        elements.append(Spacer(1, 8*mm))
        
        return elements
    
    def _build_references(self, request: InvoiceRequest) -> list:
        """Build reference information."""
        elements = []
        
        refs = []
        if request.contract_reference:
            refs.append(f"Contract: {request.contract_reference}")
        if request.quote_reference:
            refs.append(f"Quote: {request.quote_reference}")
        if request.project_reference:
            refs.append(f"Project: {request.project_reference}")
        
        if refs:
            elements.append(Paragraph(
                f"<b>References:</b> {' | '.join(refs)}",
                self.styles['BodyText']
            ))
            elements.append(Spacer(1, 3*mm))
        
        elements.append(Paragraph(
            f"<b>Invoice Type:</b> {request.invoice_type.value.title()} - {request.invoice_description}",
            self.styles['BodyText']
        ))
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_line_items(self, request: InvoiceRequest) -> list:
        """Build line items table."""
        elements = []
        
        # Table header
        table_data = [
            ["Description", "Qty", "Unit", "Unit Price", "VAT %", "Net Amount"]
        ]
        
        # Add line items
        for item in request.line_items:
            table_data.append([
                item.description,
                f"{item.quantity:.2f}",
                item.unit,
                f"£{item.unit_price:,.2f}",
                f"{item.vat_rate:.0f}%",
                f"£{item.net_amount:,.2f}"
            ])
        
        # Create table
        items_table = Table(
            table_data,
            colWidths=[75*mm, 15*mm, 15*mm, 25*mm, 15*mm, 25*mm]
        )
        
        items_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#253956')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Body
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),
            ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            
            # Alternating rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        elements.append(items_table)
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_totals(self, request: InvoiceRequest) -> list:
        """Build totals section."""
        elements = []
        
        amount_due = request.total - request.amount_paid
        
        totals_data = [
            ["Subtotal:", f"£{request.subtotal:,.2f}"],
            ["VAT:", f"£{request.vat_total:,.2f}"],
            ["Total:", f"£{request.total:,.2f}"],
        ]
        
        if request.amount_paid > 0:
            totals_data.append(["Amount Paid:", f"£{request.amount_paid:,.2f}"])
        
        totals_data.append(["AMOUNT DUE:", f"£{amount_due:,.2f}"])
        
        totals_table = Table(totals_data, colWidths=[130*mm, 40*mm])
        
        style_commands = [
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#253956')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#253956')),
            ('TOPPADDING', (0, -1), (-1, -1), 8),
        ]
        
        if request.amount_paid > 0:
            # Highlight total row
            style_commands.append(('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#f5f5f5')))
            style_commands.append(('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'))
        
        totals_table.setStyle(TableStyle(style_commands))
        
        elements.append(totals_table)
        elements.append(Spacer(1, 10*mm))
        
        return elements
    
    def _build_bank_details(self) -> list:
        """Build bank details section."""
        elements = []
        
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc')))
        elements.append(Spacer(1, 5*mm))
        
        elements.append(Paragraph("<b>Payment Details</b>", self.styles['SectionHeader']))
        
        bank_data = [
            ["Bank:", settings.BANK_NAME],
            ["Account Name:", settings.BANK_ACCOUNT_NAME],
            ["Sort Code:", settings.BANK_SORT_CODE],
            ["Account Number:", settings.BANK_ACCOUNT_NUMBER],
            ["IBAN:", settings.BANK_IBAN],
        ]
        
        bank_table = Table(bank_data, colWidths=[30*mm, 80*mm])
        bank_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        
        elements.append(bank_table)
        elements.append(Spacer(1, 5*mm))
        
        elements.append(Paragraph(
            f"Please quote the invoice number when making payment. Payment is due within {settings.PAYMENT_TERMS_DAYS} days.",
            self.styles['SmallText']
        ))
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_notes(self, notes: str) -> list:
        """Build notes section."""
        elements = []
        
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc')))
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph("<b>Notes</b>", self.styles['SectionHeader']))
        elements.append(Paragraph(notes, self.styles['BodyText']))
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_footer(self) -> list:
        """Build invoice footer."""
        elements = []
        
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc')))
        elements.append(Spacer(1, 3*mm))
        
        footer_text = f"""
        {settings.COMPANY_NAME} | Company Registration: {settings.COMPANY_REG} | VAT Registration: {settings.COMPANY_VAT}
        <br/>
        {settings.COMPANY_ADDRESS_1}, {settings.COMPANY_ADDRESS_2} | {settings.COMPANY_PHONE} | {settings.COMPANY_EMAIL}
        """
        
        elements.append(Paragraph(footer_text, ParagraphStyle(
            'Footer',
            fontSize=7,
            textColor=colors.HexColor('#888888'),
            alignment=TA_CENTER
        )))
        
        return elements


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
        
        # Generate presigned URL valid for 30 days
        url = self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.S3_BUCKET, 'Key': key},
            ExpiresIn=2592000
        )
        
        return url


# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Generate professional PDF invoices for Hampstead Renovations"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pdf_generator = InvoicePDFGenerator()
s3_uploader = S3Uploader()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.APP_NAME, "version": settings.VERSION}


@app.post("/generate", response_model=InvoiceResponse)
async def generate_invoice(request: InvoiceRequest):
    """Generate an invoice PDF."""
    try:
        # Generate invoice number
        invoice_number = InvoiceNumberGenerator.get_next()
        
        # Set dates
        invoice_date = request.invoice_date or datetime.now()
        due_date = request.due_date or (invoice_date + timedelta(days=request.payment_terms_days))
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{invoice_number}_{timestamp}.pdf"
        
        # Generate PDF
        pdf_buffer = pdf_generator.generate(request, invoice_number)
        
        # Upload to S3
        pdf_url = s3_uploader.upload(pdf_buffer, filename)
        
        # Calculate amount due
        subtotal = request.subtotal if request.subtotal > 0 else sum(item.net_amount for item in request.line_items)
        vat_total = request.vat_total if request.vat_total > 0 else sum(item.vat_amount for item in request.line_items)
        total = request.total if request.total > 0 else subtotal + vat_total
        amount_due = total - request.amount_paid
        
        return InvoiceResponse(
            success=True,
            invoice_number=invoice_number,
            pdf_url=pdf_url,
            total_due=amount_due,
            due_date=due_date,
            generated_at=datetime.now(),
            message="Invoice generated successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
