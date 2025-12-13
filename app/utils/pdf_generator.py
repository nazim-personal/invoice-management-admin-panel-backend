import os
import io
from datetime import datetime
from decimal import Decimal
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.pdfgen import canvas
import qrcode

class InvoicePDFGenerator:
    """
    Professional invoice PDF generator with QR code for payment
    """

    def __init__(self):
        self.width, self.height = A4
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

        # Company details from environment or defaults
        self.company_name = os.getenv('COMPANY_NAME', 'Your Company Name')
        self.company_address = os.getenv('COMPANY_ADDRESS', 'Company Address Line 1')
        self.company_city = os.getenv('COMPANY_CITY', 'City, State, PIN')
        self.company_phone = os.getenv('COMPANY_PHONE', '+91 1234567890')
        self.company_email = os.getenv('COMPANY_EMAIL', 'info@company.com')
        self.company_gst = os.getenv('COMPANY_GST', 'GST: 12ABCDE1234F1Z5')
        self.upi_id = os.getenv('UPI_ID', 'company@upi')
        self.currency_symbol = os.getenv('CURRENCY_SYMBOL', '₹')  # Dynamic currency

    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.style_title = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        )

        self.style_heading = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#4a4a4a'),
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )

        self.style_normal = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            spaceAfter=4
        )

        self.style_right = ParagraphStyle(
            'CustomRight',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_RIGHT,
            textColor=colors.HexColor('#333333')
        )

    def _generate_qr_code(self, data):
        """Generate QR code image"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to bytes
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)

        return img_io

    def _create_payment_qr(self, invoice_number, amount):
        """Create UPI payment QR code"""
        # UPI payment string format
        upi_string = f"upi://pay?pa={self.upi_id}&pn={self.company_name}&am={amount}&tn=Invoice-{invoice_number}"
        return self._generate_qr_code(upi_string)

    def generate_invoice_pdf(self, invoice_data):
        """
        Generate professional invoice PDF

        Args:
            invoice_data: Dict containing invoice details

        Returns:
            BytesIO object containing PDF
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                               rightMargin=inch*0.75, leftMargin=inch*0.75,
                               topMargin=inch*0.75, bottomMargin=inch*0.75)

        story = []

        # Header Section
        story.extend(self._create_header(invoice_data))
        story.append(Spacer(1, 0.3*inch))

        # Bill To Section
        story.extend(self._create_bill_to_section(invoice_data))
        story.append(Spacer(1, 0.3*inch))

        # Items Table
        story.extend(self._create_items_table(invoice_data))
        story.append(Spacer(1, 0.3*inch))

        # Payment QR andFooter
        story.extend(self._create_footer(invoice_data))

        doc.build(story)
        buffer.seek(0)
        return buffer

    def _create_header(self, invoice_data):
        """Create invoice header"""
        elements = []

        # Company name and invoice title in table format
        header_data = [
            [
                Paragraph(f"<b>{self.company_name}</b>", self.style_title),
                Paragraph("<b>INVOICE</b>", self.style_right)
            ],
            [
                Paragraph(self.company_address, self.style_normal),
                Paragraph(f"<b>#{invoice_data.get('invoice_number', 'N/A')}</b>", self.style_right)
            ],
            [
                Paragraph(self.company_city, self.style_normal),
                Paragraph(f"Date: {invoice_data.get('invoice_date', 'N/A')}", self.style_right)
            ],
            [
                Paragraph(f"Phone: {self.company_phone}", self.style_normal),
                Paragraph(f"Due: {invoice_data.get('due_date', 'N/A')}", self.style_right)
            ],
            [
                Paragraph(self.company_gst, self.style_normal),
                ''
            ]
        ]

        header_table = Table(header_data, colWidths=[3.5*inch, 3*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))

        elements.append(header_table)

        # Separator line
        line_data = [['_' * 100]]
        line_table = Table(line_data, colWidths=[6.5*inch])
        line_table.setStyle(TableStyle([
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        elements.append(line_table)

        return elements

    def _create_bill_to_section(self, invoice_data):
        """Create bill to section"""
        elements = []

        customer = invoice_data.get('customer', {})

        bill_to_data = [
            [
                Paragraph("<b>BILL TO:</b>", self.style_heading),
                Paragraph("<b>INVOICE DETAILS:</b>", self.style_heading)
            ],
            [
                Paragraph(customer.get('name', 'N/A'), self.style_normal),
                Paragraph(f"Invoice Number: <b>{invoice_data.get('invoice_number', 'N/A')}</b>", self.style_normal)
            ],
            [
                Paragraph(customer.get('address', ''), self.style_normal),
                Paragraph(f"Date: {invoice_data.get('invoice_date', 'N/A')}", self.style_normal)
            ],
            [
                Paragraph(f"{customer.get('city', '')}, {customer.get('state', '')}", self.style_normal),
                Paragraph(f"Due Date: {invoice_data.get('due_date', 'N/A')}", self.style_normal)
            ],
            [
                Paragraph(f"GST: {customer.get('gst_number', 'N/A')}", self.style_normal),
                Paragraph(f"Status: <b>{invoice_data.get('status', 'N/A').upper()}</b>", self.style_normal)
            ]
        ]

        bill_table = Table(bill_to_data, colWidths=[3.5*inch, 3*inch])
        bill_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        elements.append(bill_table)

        return elements

    def _create_items_table(self, invoice_data):
        """Create items table with products"""
        elements = []

        # Table header
        items_data = [
            ['ITEM', 'QTY', 'PRICE', 'TAX', 'TOTAL']
        ]

        # Add items
        items = invoice_data.get('items', [])
        for item in items:
            items_data.append([
                item.get('product_name', 'N/A'),
                str(item.get('quantity', 0)),
                f"{self.currency_symbol}{float(item.get('price', 0)):.2f}",
                f"{float(item.get('tax_rate', 0)):.1f}%",
                f"{self.currency_symbol}{float(item.get('total', 0)):.2f}"
            ])

        # Calculate totals
        subtotal = float(invoice_data.get('subtotal', 0))
        tax_amount = float(invoice_data.get('tax_amount', 0))
        total = float(invoice_data.get('total', 0))

        # Add spacing row
        items_data.append(['', '', '', '', ''])

        # Add totals
        items_data.extend([
            ['', '', '', 'Subtotal:', f"{self.currency_symbol}{subtotal:.2f}"],
            ['', '', '', 'Tax:', f"{self.currency_symbol}{tax_amount:.2f}"],
            ['', '', '', 'TOTAL:', f"{self.currency_symbol}{total:.2f}"]
        ])

        items_table = Table(items_data, colWidths=[2.5*inch, 0.7*inch, 1.2*inch, 1*inch, 1.1*inch])
        items_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a90e2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

            # Body
            ('ALIGN', (1, 1), (-1, -4), 'RIGHT'),
            ('FONTNAME', (0, 1), (-1, -4), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -4), 10),
            ('GRID', (0, 0), (-1, -4), 0.5, colors.grey),

            # Totals
            ('ALIGN', (3, -3), (-1, -1), 'RIGHT'),
            ('FONTNAME', (3, -2), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (4, -1), (4, -1), 12),
            ('TEXTCOLOR', (4, -1), (4, -1), colors.HexColor('#1a1a1a')),
            ('LINEABOVE', (3, -1), (-1, -1), 2, colors.HexColor('#4a90e2')),
        ]))

        elements.append(items_table)

        return elements

    def _create_footer(self, invoice_data):
        """Create footer with QR code and notes"""
        elements = []

        # Generate QR code
        total = float(invoice_data.get('total', 0))
        invoice_number = invoice_data.get('invoice_number', 'N/A')

        qr_img_io = self._create_payment_qr(invoice_number, total)
        qr_image = Image(qr_img_io, width=1.5*inch, height=1.5*inch)

        # Notes section
        notes = invoice_data.get('notes', 'Thank you for your business!')

        # Footer table with QR and text
        footer_data = [
            [
                Paragraph(f"<b>Scan to Pay via UPI</b><br/><br/>{notes}", self.style_normal),
                qr_image
            ],
            [
                Paragraph(f"<i>Payment Terms: Due within {invoice_data.get('payment_terms', '30')} days</i>", self.style_normal),
                Paragraph(f"<i>UPI ID: {self.upi_id}</i>", self.style_right)
            ]
        ]

        footer_table = Table(footer_data, colWidths=[4.5*inch, 2*inch])
        footer_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))

        elements.append(footer_table)

        return elements
