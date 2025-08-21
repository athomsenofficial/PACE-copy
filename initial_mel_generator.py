import base64
from io import BytesIO
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph, Image, Frame
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus.flowables import PageBreak
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
from dateutil.relativedelta import relativedelta
from promotion_eligible_counter import get_promotion_eligibility
from reportlab.pdfbase.pdfmetrics import stringWidth
import pandas as pd
import os
from PyPDF2 import PdfMerger
from session_manager import get_session, store_pdf_in_redis
from constants import (
    SCODS, PROMOTION_MAP, INITIAL_MEL_TABLE_WIDTHS, INITIAL_MEL_INELIGIBLE_TABLE_WIDTHS,
    INITIAL_MEL_HEADER_ROW, INITIAL_MEL_INELIGIBLE_HEADER_ROW, DATE_FORMAT_DISPLAY,
    IMAGE_BASE_DIR, DEFAULT_LOGO_PATH, PDF_FONTS
)

# Get font names from the pre-registered fonts
BODY_FONT, BOLD_FONT = PDF_FONTS


def get_accounting_date(grade, year):
    """Calculate accounting date for given grade and year"""
    try:
        scod = f'{SCODS.get(grade)}-{year}'
        formatted_scod_date = datetime.strptime(scod, "%d-%b-%Y")
        accounting_date = formatted_scod_date - relativedelta(days=119)  # 120-1
        adjusted_accounting_date = accounting_date.replace(day=3, hour=23, minute=59, second=59)
        return adjusted_accounting_date.strftime(DATE_FORMAT_DISPLAY)
    except Exception as e:
        print(f"Error calculating accounting date: {e}")
        return "Error calculating date"


class MilitaryRosterDocument(BaseDocTemplate):
    """Custom document template for military rosters"""

    def __init__(self, filename, cycle, melYear=None, **kwargs):
        super().__init__(filename, **kwargs)
        self.page_width, self.page_height = landscape(letter)
        self.cycle = cycle
        self.melYear = melYear

        # Define the main content frame
        content_frame = Frame(
            x1=0.5 * inch,
            y1=1.05 * inch,
            width=self.page_width - inch,
            height=self.page_height - 2.735 * inch,
            id='normal'
        )

        template = PageTemplate(
            id='military_roster',
            frames=content_frame,
            onPage=self.add_page_elements
        )
        self.addPageTemplates([template])

    def add_page_elements(self, canvas, doc):
        """Add header and footer to each page"""
        canvas.saveState()
        try:
            self.add_header(canvas, doc)
            self.add_footer_border(canvas)
            self.add_footer(canvas, doc)
        except Exception as e:
            print(f"Error adding page elements: {e}")
        canvas.restoreState()

    def add_header(self, canvas, doc):
        """Add header section to page"""
        # CUI Header at the very top
        canvas.setFont(BOLD_FONT, 10)
        canvas.drawCentredString(
            self.page_width / 2,
            self.page_height - 0.3 * inch,
            'CUI// CONTROLLED UNCLASSIFIED INFORMATION'
        )

        # Main header content
        header_top = self.page_height - 0.8 * inch

        # Add logo if it exists
        self.add_logo(canvas, doc, header_top)

        # Add unit data section
        self.add_unit_data(canvas, doc, header_top)

        # Add promotion eligibility data if applicable
        self.add_promotion_data(canvas, doc, header_top)

        # Add signature block
        self.add_signature_block(canvas, doc, header_top)

    def add_logo(self, canvas, doc, header_top):
        """Add logo to header"""
        try:
            logo_path = getattr(doc, 'logo_path', os.path.join(IMAGE_BASE_DIR, DEFAULT_LOGO_PATH))
            if os.path.exists(logo_path):
                logo = Image(logo_path, width=1 * inch, height=1 * inch)
                logo.drawOn(canvas, 0.5 * inch, header_top - 0.8 * inch)
        except Exception as e:
            print(f"Error adding logo: {e}")

    def add_unit_data(self, canvas, doc, header_top):
        """Add unit data section"""
        canvas.setFont(BOLD_FONT, 12)
        text_start_x = 2 * inch
        title_y = header_top + 0.1 * inch
        canvas.drawString(text_start_x, title_y, "Unit Data")

        # PAS Information
        canvas.setFont(BOLD_FONT, 10)
        line_height = 0.2 * inch
        text_start_y = header_top - 0.1 * inch

        pas_info = getattr(doc, 'pas_info', {})
        canvas.drawString(text_start_x, text_start_y, f"SRID: {pas_info.get('srid', 'N/A')}")

        # Different layout for SMS/MSG vs others
        if self.cycle not in ['SMS', 'MSG']:
            canvas.drawString(text_start_x, text_start_y - line_height, f"FD NAME: {pas_info.get('fd name', 'N/A')}")
            canvas.drawString(text_start_x, text_start_y - 2 * line_height, f"FDID: {pas_info.get('fdid', 'N/A')}")
            canvas.drawString(text_start_x, text_start_y - 3 * line_height,
                              f"SRID MPF: {pas_info.get('srid mpf', 'N/A')}")
        else:
            canvas.drawString(text_start_x, text_start_y - line_height, f"SRID MPF: {pas_info.get('srid mpf', 'N/A')}")

    def add_promotion_data(self, canvas, doc, header_top):
        """Add promotion eligibility data section"""
        pas_info = getattr(doc, 'pas_info', {})

        if pas_info.get('pn', 'NA') != 'NA':
            canvas.setFont(BOLD_FONT, 12)
            text_start_x = 5 * inch
            title_y = header_top + 0.1 * inch
            canvas.drawString(text_start_x, title_y, "Promotion Eligibility Data")

            canvas.setFont(BOLD_FONT, 10)
            line_height = 0.2 * inch
            text_start_y = header_top - 0.1 * inch
            canvas.drawString(text_start_x, text_start_y, f"PROMOTE NOW: {pas_info.get('pn', 'N/A')}")
            canvas.drawString(text_start_x, text_start_y - line_height, f"MUST PROMOTE: {pas_info.get('mp', 'N/A')}")

    def add_signature_block(self, canvas, doc, header_top):
        """Add signature block"""
        pas_info = getattr(doc, 'pas_info', {})

        canvas.setFont(BOLD_FONT, 12)
        text_start_s = 7.5 * inch
        line_height_s = 0.2 * inch
        title_s = header_top - 0.5 * inch

        officer_name = pas_info.get('fd name', 'N/A')
        rank = pas_info.get('rank', 'N/A')
        title = pas_info.get('title', 'N/A')

        canvas.drawString(text_start_s, title_s, f"{officer_name}, {rank}, USAF")
        canvas.drawString(text_start_s, title_s - line_height_s, title)

    def add_footer_border(self, canvas):
        """Add footer border line"""
        canvas.setLineWidth(0.1)
        canvas.setStrokeColorRGB(0, 0, 0)
        canvas.line(
            0.5 * inch,
            1.2 * inch,
            self.page_width - 0.5 * inch,
            1.2 * inch
        )

    def add_footer(self, canvas, doc):
        """Add footer section"""
        # Footer disclaimer text
        footer_text = (
            "The information herein is FOR OFFICIAL USE ONLY (CUI) information which must be protected under "
            "the Freedom of Information Act (5 U.S.C. 552) and/or the Privacy Act of 1974 (5 U.S.C. 552a). "
            "Unauthorized disclosure or misuse of this PERSONAL INFORMATION may result in disciplinary action, "
            "criminal and/or civil penalties."
        )

        canvas.setFont(BOLD_FONT, 8)
        self.draw_wrapped_text(canvas, footer_text, 0.75 * inch)

        # Bottom footer elements
        self.add_bottom_footer(canvas)

    def draw_wrapped_text(self, canvas, text, y_position):
        """Draw text wrapped to multiple lines"""
        words = text.split()
        lines = []
        current_line = []
        current_width = 0
        max_width = self.page_width - inch

        for word in words:
            word_width = stringWidth(word + ' ', BOLD_FONT, 8)
            if current_width + word_width <= max_width:
                current_line.append(word)
                current_width += word_width
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_width = word_width

        if current_line:
            lines.append(' '.join(current_line))

        # Draw footer lines centered
        for i, line in enumerate(lines):
            line_width = stringWidth(line, BOLD_FONT, 8)
            center_x = (self.page_width - line_width) / 2
            canvas.drawString(center_x, y_position + (len(lines) - 1 - i) * 10, line)

    def add_bottom_footer(self, canvas):
        """Add bottom footer elements"""
        bottom_y = 0.3 * inch
        canvas.setFillColorRGB(0, 0, 0)
        canvas.setFont(BOLD_FONT, 12)

        # Left: Date
        canvas.drawString(0.5 * inch, bottom_y, datetime.now().strftime(DATE_FORMAT_DISPLAY))

        # Center: CUI and identifier
        cui_text = "CUI"
        cui_width = stringWidth(cui_text, BOLD_FONT, 12)
        cui_center_x = (self.page_width / 2) - (cui_width / 2)
        canvas.drawString(cui_center_x, bottom_y, cui_text)

        # MEL identifier
        identifier_text = f"{str(self.melYear + 1)[-2:]}{PROMOTION_MAP.get(self.cycle, 'XX')} - Initial MEL"
        identifier_width = stringWidth(identifier_text, BOLD_FONT, 12)
        identifier_center_x = (self.page_width / 2) - (identifier_width / 2)
        canvas.drawString(identifier_center_x, bottom_y - 18, identifier_text)

        # Right: Accounting date
        accounting_text = f"Accounting Date: {get_accounting_date(self.cycle, self.melYear)}"
        accounting_width = stringWidth(accounting_text, BOLD_FONT, 12)
        canvas.drawString(self.page_width - 0.5 * inch - accounting_width, bottom_y, accounting_text)


def create_table(doc, data, header, table_type=None, count=None):
    """Create standard table with optional status row"""
    table_width = doc.page_width - inch
    col_widths = [table_width * x for x in INITIAL_MEL_TABLE_WIDTHS]

    # Prepare table data
    table_data = [header] + data
    repeat_rows = 1

    # Add status row if provided
    if table_type and count is not None:
        status_row = [[table_type, "", "", "", "", "", "", f"Total: {count}"]]
        table_data = status_row + table_data
        repeat_rows = 2

    # Create table
    table = Table(table_data, repeatRows=repeat_rows, colWidths=col_widths)

    # Apply styling
    table.setStyle(get_table_style(repeat_rows, is_standard=True))

    return table


def create_ineligible_table(doc, data, header, table_type=None, count=None):
    """Create ineligible table with reason column"""
    table_width = doc.page_width - inch
    col_widths = [table_width * x for x in INITIAL_MEL_INELIGIBLE_TABLE_WIDTHS]

    # Prepare table data
    table_data = [header] + data
    repeat_rows = 1

    # Add status row if provided
    if table_type and count is not None:
        status_row = [[table_type, "", "", "", "", f"Total: {count}"]]
        table_data = status_row + table_data
        repeat_rows = 2

    # Create table
    table = Table(table_data, repeatRows=repeat_rows, colWidths=col_widths)

    # Apply styling
    table.setStyle(get_table_style(repeat_rows, is_standard=False))

    return table


def get_table_style(repeat_rows, is_standard=True):
    """Get table style configuration"""
    # Convert hex #17365d to RGB values (23, 54, 93)
    dark_blue = colors.Color(23 / 255, 54 / 255, 93 / 255)

    style = [
        # Header styling
        ('BACKGROUND', (0, 0), (-1, repeat_rows - 1), dark_blue),
        ('TEXTCOLOR', (0, 0), (-1, repeat_rows - 1), colors.white),
        ('FONTNAME', (0, 0), (-1, repeat_rows - 1), BOLD_FONT),
        ('FONTSIZE', (0, 0), (-1, repeat_rows - 1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, repeat_rows - 1), 4),
        ('ROWHEIGHT', (0, 0), (-1, -1), 30),

        # Data rows styling
        ('FONTNAME', (0, repeat_rows), (-1, -1), BODY_FONT),
        ('FONTSIZE', (0, repeat_rows), (-1, -1), 10),
        ('LINEBELOW', (0, 0), (-1, -1), .5, colors.lightgrey),

        # Common alignments
        ('ALIGN', (0, repeat_rows - 1), (0, -1), 'LEFT'),  # FULL NAME
        ('ALIGN', (1, repeat_rows - 1), (1, -1), 'CENTER'),  # GRADE
        ('VALIGN', (0, repeat_rows), (-1, -1), 'MIDDLE'),
    ]

    if is_standard:
        # Standard table specific alignments
        style.extend([
            ('ALIGN', (2, repeat_rows - 1), (2, repeat_rows - 1), 'CENTER'),  # DAS header
            ('ALIGN', (2, repeat_rows), (2, -1), 'RIGHT'),  # DAS data
            ('ALIGN', (3, repeat_rows - 1), (3, -1), 'LEFT'),  # DAFSC
            ('ALIGN', (4, repeat_rows - 1), (4, repeat_rows - 1), 'CENTER'),  # UNIT header
            ('ALIGN', (4, repeat_rows), (4, -1), 'CENTER'),  # UNIT data
            ('ALIGN', (5, repeat_rows - 1), (5, repeat_rows - 1), 'CENTER'),  # DOR header
            ('ALIGN', (5, repeat_rows), (5, -1), 'RIGHT'),  # DOR data
            ('ALIGN', (6, repeat_rows - 1), (6, -1), 'RIGHT'),  # TAFMSD
            ('ALIGN', (7, repeat_rows - 1), (7, -1), 'RIGHT'),  # PASCODE
        ])

        # Status row for standard table
        if repeat_rows == 2:
            style.extend([
                ('SPAN', (0, 0), (6, 0)),  # Span across first 7 columns
                ('ALIGN', (7, 0), (7, 0), 'RIGHT'),  # Right align the count
            ])
    else:
        # Ineligible table specific alignments
        style.extend([
            ('ALIGN', (2, repeat_rows - 1), (2, -1), 'CENTER'),  # PASCODE
            ('ALIGN', (3, repeat_rows - 1), (3, -1), 'CENTER'),  # DAFSC
            ('ALIGN', (4, repeat_rows - 1), (4, -1), 'CENTER'),  # UNIT
            ('ALIGN', (5, repeat_rows - 1), (5, -1), 'LEFT'),  # REASON
        ])

        # Status row for ineligible table
        if repeat_rows == 2:
            style.extend([
                ('SPAN', (0, 0), (4, 0)),  # Span across first 5 columns
                ('ALIGN', (5, 0), (5, 0), 'RIGHT'),  # Right align the count
            ])

    return TableStyle(style)


def generate_pascode_pdf(eligible_data, ineligible_data, btz_data, small_unit_data,
                         senior_rater, senior_raters, is_last, cycle, melYear,
                         pascode, pas_info, output_filename, logo_path):
    """Generate a PDF for a single pascode"""
    try:
        doc = MilitaryRosterDocument(
            output_filename,
            cycle=cycle,
            melYear=melYear,
            pagesize=landscape(letter),
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch
        )

        # Store additional information
        doc.logo_path = logo_path
        doc.pas_info = pas_info

        elements = []

        # Create eligible section
        if eligible_data and len(eligible_data) > 0:
            table = create_table(
                doc,
                data=eligible_data,
                header=INITIAL_MEL_HEADER_ROW,
                table_type="ELIGIBLE",
                count=len(eligible_data)
            )
            elements.append(table)
            elements.append(PageBreak())

        # Create ineligible section
        if ineligible_data and len(ineligible_data) > 0:
            table = create_ineligible_table(
                doc,
                data=ineligible_data,
                header=INITIAL_MEL_INELIGIBLE_HEADER_ROW,
                table_type="INELIGIBLE",
                count=len(ineligible_data)
            )
            elements.append(table)
            elements.append(PageBreak())

        # Create BTZ section
        if btz_data and len(btz_data) > 0:
            table = create_table(
                doc,
                data=btz_data,
                header=INITIAL_MEL_HEADER_ROW,
                table_type="BELOW THE ZONE",
                count=len(btz_data)
            )
            elements.append(table)
            elements.append(PageBreak())

        # Build the main PDF
        doc.build(elements)

        # Handle small unit processing if this is the last pascode
        if is_last and small_unit_data is not None and len(small_unit_data) > 0:
            generate_small_unit_pdf(small_unit_data, senior_rater, senior_raters,
                                    cycle, melYear, pas_info, output_filename, logo_path)

        return output_filename

    except Exception as e:
        print(f"Error generating PDF for pascode {pascode}: {e}")
        return None


def generate_small_unit_pdf(small_unit_data, senior_rater, senior_raters,
                            cycle, melYear, pas_info, base_filename, logo_path):
    """Generate PDF for small unit data"""
    try:
        # Create new filename for small unit
        small_unit_filename = base_filename.replace('.pdf', '_small_unit.pdf')

        doc = MilitaryRosterDocument(
            small_unit_filename,
            cycle=cycle,
            melYear=melYear,
            pagesize=landscape(letter),
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch
        )

        srid_list = small_unit_data.values.tolist() if hasattr(small_unit_data, 'values') else small_unit_data
        must_promote, promote_now = get_promotion_eligibility(len(srid_list), cycle)

        doc.pas_info = {
            'srid': senior_rater.get('srid', 'N/A'),
            'fd name': senior_rater.get('senior_rater_name', 'N/A'),
            'rank': senior_rater.get('senior_rater_rank', 'N/A'),
            'title': senior_rater.get('senior_rater_title', 'N/A'),
            'fdid': pas_info.get('fdid', 'N/A'),
            'srid mpf': pas_info.get('srid mpf', 'N/A'),
            'mp': must_promote,
            'pn': promote_now
        }

        doc.logo_path = logo_path

        elements = []
        table = create_table(
            doc,
            data=srid_list,
            header=INITIAL_MEL_HEADER_ROW,
            table_type="SENIOR RATER",
            count=len(srid_list)
        )
        elements.append(table)

        # Add page break if not the last senior rater
        senior_rater_srid = senior_rater.get('srid')
        if senior_rater_srid != list(senior_raters.keys())[-1]:
            elements.append(PageBreak())

        doc.build(elements)
        return small_unit_filename

    except Exception as e:
        print(f"Error generating small unit PDF: {e}")
        return None


def merge_pdfs(temp_pdfs, session_id):
    """Merge multiple PDFs into a single PDF"""
    if not temp_pdfs:
        return None

    merger = PdfMerger()

    try:
        # Add each PDF to the merger
        for pdf_path in temp_pdfs:
            if pdf_path and os.path.exists(pdf_path):
                try:
                    merger.append(pdf_path)
                except Exception as e:
                    print(f"Error adding {pdf_path} to merged document: {e}")

        # Create output buffer
        buffer = BytesIO()
        merger.write(buffer)
        merger.close()
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=initial_mel_roster.pdf"}
        )

    except Exception as e:
        print(f"Error during PDF merge: {e}")
        return None
    finally:
        # Clean up disk files
        for path in temp_pdfs:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Warning: could not delete {path}: {e}")


def generate_roster_pdf(session_id, output_filename, logo_path=None):
    """Generate a military roster PDF from session data"""
    try:
        # Get session data
        session = get_session(session_id)
        if not session:
            print(f"Session {session_id} not found")
            return None

        # Extract data from session
        eligible_df = pd.DataFrame.from_records(session.get('eligible_df', []))
        ineligible_df = pd.DataFrame.from_records(session.get('ineligible_df', []))
        btz_df = pd.DataFrame.from_records(session.get('btz_df', []))
        small_unit_df = pd.DataFrame(session.get('small_unit_df', []))

        senior_raters = session.get('srid_pascode_map', {})
        cycle = session.get('cycle')
        melYear = session.get('year')
        pascode_map = session.get('pascode_map', {})
        senior_rater = session.get('small_unit_sr', {})

        # Set default logo path
        if not logo_path:
            logo_path = os.path.join(IMAGE_BASE_DIR, DEFAULT_LOGO_PATH)

        # Convert DataFrames to lists
        eligible_data = eligible_df.values.tolist() if not eligible_df.empty else []
        btz_data = btz_df.values.tolist() if not btz_df.empty else []

        # Handle ineligible data columns
        ineligible_columns = ['FULL_NAME', 'GRADE', 'ASSIGNED_PAS', 'DAFSC', 'ASSIGNED_PAS_CLEARTEXT', 'REASON']
        available_columns = [col for col in ineligible_columns if col in ineligible_df.columns]
        ineligible_data = ineligible_df[available_columns].values.tolist() if not ineligible_df.empty else []

        # Get unique PASCODEs
        unique_pascodes = set()

        # Collect PASCODEs from all data sources
        for row in eligible_data:
            if len(row) > 7:
                unique_pascodes.add(row[7])  # PASCODE is 8th column

        for row in ineligible_data:
            if len(row) > 2:
                unique_pascodes.add(row[2])  # PASCODE is 3rd column in ineligible

        for row in btz_data:
            if len(row) > 7:
                unique_pascodes.add(row[7])

        unique_pascodes = sorted(list(unique_pascodes))

        if not unique_pascodes:
            print("No PASCODEs found in data")
            return None

        # Generate PDFs for each pascode
        temp_pdfs = []

        for pascode in unique_pascodes:
            # Skip if pascode not in mapping
            if pascode not in pascode_map:
                print(f"Warning: No info for pascode {pascode}, skipping")
                continue

            # Filter data for current pascode
            pascode_eligible = [row for row in eligible_data if len(row) > 7 and row[7] == pascode]
            pascode_ineligible = [row for row in ineligible_data if len(row) > 2 and row[2] == pascode]
            pascode_btz = [row for row in btz_data if len(row) > 7 and row[7] == pascode]

            # Skip if no data for this pascode
            if not pascode_eligible and not pascode_ineligible and not pascode_btz:
                print(f"No data for pascode {pascode}, skipping")
                continue

            # Calculate promotion eligibility
            eligible_candidates = len(pascode_eligible)
            must_promote, promote_now = get_promotion_eligibility(eligible_candidates, cycle)

            # Create PAS info
            pas_info = {
                'srid': pascode_map[pascode].get('srid', 'N/A'),
                'rank': pascode_map[pascode].get('senior_rater_rank', 'N/A'),
                'title': pascode_map[pascode].get('senior_rater_title', 'N/A'),
                'fd name': pascode_map[pascode].get('senior_rater_name', 'N/A'),
                'fdid': f'{pascode_map[pascode].get("srid", "")}{pascode[-4:]}',
                'srid mpf': pascode[:2],
                'mp': must_promote,
                'pn': promote_now
            }

            # Generate PDF for this pascode
            is_last = (pascode == unique_pascodes[-1])
            temp_filename = f"temp_{pascode}.pdf"

            temp_pdf = generate_pascode_pdf(
                pascode_eligible,
                pascode_ineligible,
                pascode_btz,
                small_unit_df,
                senior_rater,
                senior_raters,
                is_last,
                cycle,
                melYear,
                pascode,
                pas_info,
                temp_filename,
                logo_path
            )

            if temp_pdf:
                temp_pdfs.append(temp_pdf)

        # Merge all PDFs
        if temp_pdfs:
            return merge_pdfs(temp_pdfs, session_id)
        else:
            print("No PDFs were generated")
            return None

    except Exception as e:
        print(f"Error generating roster PDF: {e}")
        return None
