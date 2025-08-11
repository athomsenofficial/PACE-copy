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

base_dir = os.path.dirname(os.path.abspath(__file__))
calibri_path = os.path.join(base_dir, 'fonts', 'calibri.ttf')
calibrib_path = os.path.join(base_dir, 'fonts', 'calibrib.ttf')

# Register Calibri fonts
pdfmetrics.registerFont(TTFont('Calibri', calibri_path))
pdfmetrics.registerFont(TTFont('Calibri-Bold', calibrib_path))

promotion_map = {
    "SRA": "E5",
    "SSG": "E6",
    "TSG": "E7",
    "MSG": "E8",
    "SMS": "E9"
}

SCODs = {
    'SRA': f'31-MAR',
    'SSG': f'31-JAN',
    'TSG': f'30-NOV',
    'MSG': f'30-SEP',
    'SMS': f'31-JUL'
    }


def get_accounting_date(grade, year):
    scod = f'{SCODs.get(grade)}-{year}'
    formatted_scod_date = datetime.strptime(scod, "%d-%b-%Y")
    accounting_date = formatted_scod_date - relativedelta(days=120 - 1)
    adjusted_accounting_date = accounting_date.replace(day=3).replace(hour=23, minute=59, second=59)
    return adjusted_accounting_date.strftime("%d %B %Y")


class MilitaryRosterDocument(BaseDocTemplate):
    def __init__(self, filename, cycle, melYear=None, **kwargs):
        super().__init__(filename, **kwargs)
        self.page_width, self.page_height = landscape(letter)
        self.cycle = cycle
        self.melYear = melYear
        # Define the main content frame - start below header
        content_frame = Frame(
            x1=0.5 * inch,  # left margin
            y1=1.05 * inch,  # bottom margin (increased to make room for footer)
            width=self.page_width - inch,  # width with margins
            height=self.page_height - 2.735 * inch,  # reduced height to make room for header
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
        self.add_header(canvas, doc)

        # Add footer border
        canvas.setLineWidth(0.1)
        canvas.setStrokeColorRGB(0, 0, 0)
        canvas.line(
            0.5 * inch,
            1.2 * inch,
            self.page_width - 0.5 * inch,
            1.2 * inch
        )
        self.add_footer(canvas, doc)
        canvas.restoreState()

    def add_header(self, canvas, doc):
        # CUI Header at the very top
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawCentredString(
            self.page_width / 2,
            self.page_height - 0.3 * inch,
            'CUI// CONTROLLED UNCLASSIFIED INFORMATION'
        )

        # Start the main header content below the CUI line
        header_top = self.page_height - 0.8 * inch

        # Logo on the left
        logo_path = doc.logo_path
        logo = Image(logo_path, width=1 * inch, height=1 * inch)
        logo.drawOn(canvas, 0.5 * inch, header_top - 0.8 * inch)

        # Title "Unit Data"
        canvas.setFont('Calibri-Bold', 12)
        text_start_x = 2 * inch
        title_y = header_top + 0.1 * inch
        canvas.drawString(text_start_x, title_y, "Unit Data")

        # PAS Information
        canvas.setFont('Calibri-Bold', 10)
        line_height = 0.2 * inch
        text_start_y = header_top - 0.1 * inch

        canvas.drawString(text_start_x, text_start_y, f"SRID: {doc.pas_info['srid']}")
        if self.cycle != 'SMS' and self.cycle != 'MSG':
            canvas.drawString(text_start_x, text_start_y - line_height, f"FD NAME: {doc.pas_info['fd name']}")
            canvas.drawString(text_start_x, text_start_y - 2 * line_height, f"FDID: {doc.pas_info['fdid']}")
            canvas.drawString(text_start_x, text_start_y - 3 * line_height, f"SRID MPF: {doc.pas_info['srid mpf']}")
        else:
            canvas.drawString(text_start_x, text_start_y - line_height, f"SRID MPF: {doc.pas_info['srid mpf']}")

        if not doc.pas_info['pn'] == 'NA':
            # Promotion Key Title
            canvas.setFont('Calibri-Bold', 12)
            text_start_x = 5 * inch
            canvas.drawString(text_start_x, title_y, "Promotion Eligibility Data")

            # Promotion Key Information
            canvas.setFont('Calibri-Bold', 10)
            line_height = 0.2 * inch
            text_start_y = header_top - 0.1 * inch
            canvas.drawString(text_start_x, text_start_y, f"PROMOTE NOW: {doc.pas_info['pn']}")
            canvas.drawString(text_start_x, text_start_y - line_height, f"MUST PROMOTE: {doc.pas_info['mp']}")

        # Signature Block
        canvas.setFont('Calibri-Bold', 12)
        text_start_s = 7.5 * inch
        line_height_s = 0.2 * inch
        title_s = header_top - 0.5 * inch
        officer_name = doc.pas_info['fd name']
        rank = doc.pas_info['rank']
        title = doc.pas_info['title']
        canvas.drawString(text_start_s, title_s, f"{officer_name}, {rank}, USAF")
        canvas.drawString(text_start_s, title_s - line_height_s, title)

    def add_footer(self, canvas, doc):
        footer_text = (
            "The information herein is FOR OFFICIAL USE ONLY (CUI) information which must be protected under "
            "the Freedom of Information Act (5 U.S.C. 552) and/or the Privacy Act of 1974 (5 U.S.C. 552a). "
            "Unauthorized disclosure or misuse of this PERSONAL INFORMATION may result in disciplinary action, "
            "criminal and/or civil penalties."
        )

        canvas.setFont('Calibri-Bold', 8)
        x = 0.5 * inch
        y = 0.75 * inch

        # Split footer text into lines
        words = footer_text.split()
        lines = []
        current_line = []
        current_width = 0
        max_width = self.page_width - inch

        for word in words:
            word_width = stringWidth(word + ' ', 'Calibri-Bold', 8)
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
            line_width = stringWidth(line, 'Calibri', 8)
            center_x = (self.page_width - line_width) / 2
            canvas.drawString(center_x, y + (len(lines) - 1 - i) * 10, line)

        # Bottom footer elements
        bottom_y = 0.3 * inch
        canvas.setFillColorRGB(0, 0, 0)

        # Left: Date
        canvas.setFont('Calibri-Bold', 12)
        canvas.drawString(x, bottom_y, datetime.now().strftime('%d %B %Y'))

        # Center: CUI and identifier
        cui_text = "CUI"
        cui_width = stringWidth(cui_text, 'Calibri-Bold', 12)
        cui_center_x = (self.page_width / 2) - (cui_width / 2)
        canvas.drawString(cui_center_x, bottom_y, cui_text)

        identifier_text = f"{str(self.melYear + 1)[-2:]}{promotion_map[self.cycle]} - Initial MEL"
        identifier_width = stringWidth(identifier_text, 'Calibri-Bold', 12)
        identifier_center_x = (self.page_width / 2) - (identifier_width / 2)
        canvas.drawString(identifier_center_x, bottom_y - 18, identifier_text)

        # Right: Page numbers
        page_text = f"Accounting Date: {get_accounting_date(self.cycle, self.melYear)}"
        page_width = stringWidth(page_text, 'Calibri-Bold', 12)
        canvas.drawString(self.page_width - 0.5 * inch - page_width, bottom_y, page_text)


def create_table(doc, data, header, table_type=None, count=None):
    """Create table with optional status row"""
    table_width = doc.page_width - inch
    col_widths = [table_width * x for x in [0.22, 0.07, 0.1, 0.08, 0.23, 0.1, 0.1, 0.1]]

    # Prepare table data
    table_data = [header] + data
    repeat_rows = 1

    # Add status row if provided
    if table_type and count is not None:
        status_row = [[table_type, "", "", "", "", "", "", f"Total: {count}"]]
        table_data = status_row + table_data
        repeat_rows = 2

    # Convert hex #17365d to RGB values (23, 54, 93)
    dark_blue = colors.Color(23 / 255, 54 / 255, 93 / 255)

    table = Table(table_data, repeatRows=repeat_rows, colWidths=col_widths)

    style = [
        # Header styling (for both status row and column headers)
        ('BACKGROUND', (0, 0), (-1, repeat_rows - 1), dark_blue),
        ('TEXTCOLOR', (0, 0), (-1, repeat_rows - 1), colors.white),
        ('FONTNAME', (0, 0), (-1, repeat_rows - 1), 'Calibri-Bold'),
        ('FONTSIZE', (0, 0), (-1, repeat_rows - 1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, repeat_rows - 1), 4),
        ('ROWHEIGHT', (0, 0), (-1, -1), 30),

        # Data rows styling
        ('FONTNAME', (0, repeat_rows), (-1, -1), 'Calibri'),
        ('FONTSIZE', (0, repeat_rows), (-1, -1), 10),
        ('LINEBELOW', (0, 0), (-1, -1), .5, colors.lightgrey),

        # Column alignments
        ('ALIGN', (0, repeat_rows - 1), (0, -1), 'LEFT'),  # FULL NAME
        ('ALIGN', (1, repeat_rows - 1), (1, -1), 'CENTER'),  # GRADE
        ('ALIGN', (2, repeat_rows - 1), (2, repeat_rows - 1), 'CENTER'),  # DAS header
        ('ALIGN', (2, repeat_rows), (2, -1), 'RIGHT'),  # DAS data
        ('ALIGN', (3, repeat_rows - 1), (3, -1), 'LEFT'),  # DAFSC
        ('ALIGN', (4, repeat_rows - 1), (4, repeat_rows - 1), 'CENTER'),  # UNIT header
        ('ALIGN', (4, repeat_rows), (4, -1), 'CENTER'),  # UNIT data
        ('ALIGN', (5, repeat_rows - 1), (5, repeat_rows - 1), 'CENTER'),  # DOR header
        ('ALIGN', (5, repeat_rows), (5, -1), 'RIGHT'),  # DOR data
        ('ALIGN', (6, repeat_rows - 1), (6, -1), 'RIGHT'),  # TAFMSD
        ('ALIGN', (7, repeat_rows - 1), (7, -1), 'RIGHT'),  # PASCODE
    ]

    # Add status row styling if present
    if table_type:
        style.extend([
            ('SPAN', (0, 0), (6, 0)),  # Span ELIGIBLE/INELIGIBLE across
            ('ALIGN', (7, 0), (7, 0), 'RIGHT'),  # Right align the count
        ])

    table.setStyle(TableStyle(style))
    return table

def create_ineligible_table(doc, data, header, table_type=None, count=None):
    """Create table with optional status row"""
    table_width = doc.page_width - inch
    col_widths = [table_width * x for x in [0.22, 0.07, 0.1, 0.08, 0.3, 0.23]]  # Adjusted last column to be wider

    # Prepare table data
    table_data = [header] + data
    repeat_rows = 1

    # Add status row if provided
    if table_type and count is not None:
        # For 6 columns, the status row should only have 6 cells
        status_row = [[table_type, "", "", "", "", f"Total: {count}"]]
        table_data = status_row + table_data
        repeat_rows = 2

    # Convert hex #17365d to RGB values (23, 54, 93)
    dark_blue = colors.Color(23 / 255, 54 / 255, 93 / 255)

    table = Table(table_data, repeatRows=repeat_rows, colWidths=col_widths)

    style = [
        # Header styling (for both status row and column headers)
        ('BACKGROUND', (0, 0), (-1, repeat_rows - 1), dark_blue),
        ('TEXTCOLOR', (0, 0), (-1, repeat_rows - 1), colors.white),
        ('FONTNAME', (0, 0), (-1, repeat_rows - 1), 'Calibri-Bold'),
        ('FONTSIZE', (0, 0), (-1, repeat_rows - 1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, repeat_rows - 1), 4),
        ('ROWHEIGHT', (0, 0), (-1, -1), 30),

        # Data rows styling
        ('FONTNAME', (0, repeat_rows), (-1, -1), 'Calibri'),
        ('FONTSIZE', (0, repeat_rows), (-1, -1), 10),
        ('LINEBELOW', (0, 0), (-1, -1), .5, colors.lightgrey),

        # Column alignments
        ('ALIGN', (0, repeat_rows - 1), (0, -1), 'LEFT'),  # FULL NAME
        ('ALIGN', (1, repeat_rows - 1), (1, -1), 'CENTER'),  # GRADE
        ('ALIGN', (2, repeat_rows - 1), (2, repeat_rows - 1), 'CENTER'),  # DAS header
        ('ALIGN', (2, repeat_rows), (2, -1), 'CENTER'),  # DAS data
        ('ALIGN', (3, repeat_rows - 1), (3, -1), 'CENTER'),  # DAFSC
        ('ALIGN', (4, repeat_rows - 1), (4, repeat_rows - 1), 'CENTER'),  # UNIT header
        ('ALIGN', (4, repeat_rows), (4, -1), 'CENTER'),  # UNIT data
        ('ALIGN', (5, repeat_rows - 1), (5, repeat_rows - 1), 'LEFT'),  # DOR header
        ('ALIGN', (5, repeat_rows), (5, -1), 'LEFT'),  # DOR data
    ]

    # Add status row styling if present
    if table_type:
        style.extend([
            ('SPAN', (0, 0), (4, 0)),  # Span across first 5 columns (0-4)
            ('ALIGN', (5, 0), (5, 0), 'RIGHT'),  # Right align the count in last column
        ])

    table.setStyle(TableStyle(style))
    return table

def create_btz_table(doc, data, header, table_type=None, count=None):
    """Create table with optional status row"""
    table_width = doc.page_width - inch
    col_widths = [table_width * x for x in [0.22, 0.07, 0.1, 0.08, 0.23, 0.1, 0.1, 0.1]]

    # Prepare table data
    table_data = [header] + data
    repeat_rows = 1

    # Add status row if provided
    if table_type and count is not None:
        status_row = [[table_type, "", "", "", "", "", "", f"Total: {count}"]]
        table_data = status_row + table_data
        repeat_rows = 2

    # Convert hex #17365d to RGB values (23, 54, 93)
    dark_blue = colors.Color(23 / 255, 54 / 255, 93 / 255)

    table = Table(table_data, repeatRows=repeat_rows, colWidths=col_widths)

    style = [
        # Header styling (for both status row and column headers)
        ('BACKGROUND', (0, 0), (-1, repeat_rows - 1), dark_blue),
        ('TEXTCOLOR', (0, 0), (-1, repeat_rows - 1), colors.white),
        ('FONTNAME', (0, 0), (-1, repeat_rows - 1), 'Calibri-Bold'),
        ('FONTSIZE', (0, 0), (-1, repeat_rows - 1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, repeat_rows - 1), 4),
        ('ROWHEIGHT', (0, 0), (-1, -1), 30),

        # Data rows styling
        ('FONTNAME', (0, repeat_rows), (-1, -1), 'Calibri'),
        ('FONTSIZE', (0, repeat_rows), (-1, -1), 10),
        ('LINEBELOW', (0, 0), (-1, -1), .5, colors.lightgrey),

        # Column alignments
        ('ALIGN', (0, repeat_rows - 1), (0, -1), 'LEFT'),  # FULL NAME
        ('ALIGN', (1, repeat_rows - 1), (1, -1), 'CENTER'),  # GRADE
        ('ALIGN', (2, repeat_rows - 1), (2, repeat_rows - 1), 'CENTER'),  # DAS header
        ('ALIGN', (2, repeat_rows), (2, -1), 'RIGHT'),  # DAS data
        ('ALIGN', (3, repeat_rows - 1), (3, -1), 'LEFT'),  # DAFSC
        ('ALIGN', (4, repeat_rows - 1), (4, repeat_rows - 1), 'CENTER'),  # UNIT header
        ('ALIGN', (4, repeat_rows), (4, -1), 'CENTER'),  # UNIT data
        ('ALIGN', (5, repeat_rows - 1), (5, repeat_rows - 1), 'CENTER'),  # DOR header
        ('ALIGN', (5, repeat_rows), (5, -1), 'RIGHT'),  # DOR data
        ('ALIGN', (6, repeat_rows - 1), (6, -1), 'RIGHT'),  # TAFMSD
        ('ALIGN', (7, repeat_rows - 1), (7, -1), 'RIGHT'),  # PASCODE
    ]

    # Add status row styling if present
    if table_type:
        style.extend([
            ('SPAN', (0, 0), (6, 0)),  # Span ELIGIBLE/INELIGIBLE across
            ('ALIGN', (7, 0), (7, 0), 'RIGHT'),  # Right align the count
        ])

    table.setStyle(TableStyle(style))
    return table




def generate_pascode_pdf(eligible_data, ineligible_data, btz_data, small_unit_data, senior_rater, senior_raters, is_last, cycle, melYear, pascode, pas_info,
                         output_filename, logo_path):
    """Generate a PDF for a single pascode"""
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

    doc2 = MilitaryRosterDocument(
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
    # doc.pas_members = [pas_info]  # Only include this pascode's info
    doc.pas_info = pas_info  # Set directly

    elements = []
    header_row = ['FULL NAME', 'GRADE', 'DAS', 'DAFSC', 'UNIT', 'DOR', 'TAFMSD', 'PASCODE']
    ineligible_header_row = ['FULL NAME', 'GRADE', 'PASCODE', 'DAFSC', 'UNIT', 'REASON']


    # Create eligible section if there are eligible records
    if eligible_data and len(eligible_data) != 0:
        table = create_table(
            doc,
            data=eligible_data,
            header=header_row,
            table_type="ELIGIBLE",
            count=len(eligible_data)
        )
        elements.append(table)
        elements.append(PageBreak())
    # Add page break before ineligible section
    if ineligible_data and len(ineligible_data) != 0:
        table = create_ineligible_table(
            doc,
            data=ineligible_data,
            header=ineligible_header_row,
            table_type="INELIGIBLE",
            count=len(ineligible_data)
        )
        elements.append(table)
        elements.append(PageBreak())
    # add btz table
    if btz_data and len(btz_data) != 0:
        table = create_btz_table(
            doc,
            data=btz_data,
            header=header_row,
            table_type="BELOW THE ZONE",
            count=len(btz_data)
        )
        elements.append(table)
        elements.append(PageBreak())

    doc.build(elements)

    if is_last and len(small_unit_data) > 0:
        srid_df = small_unit_data
        srid_list = srid_df.values.tolist()
        senior_rater_srid = senior_rater['srid']
        senior_rater_name = senior_rater['senior_rater_name']
        senior_rater_rank = senior_rater['senior_rater_rank']
        senior_rater_title = senior_rater['senior_rater_title']
        must_promote, promote_now = get_promotion_eligibility(len(small_unit_data), cycle)
    
        doc2.pas_info = {
            'srid': senior_rater['srid'],
            'fd name': senior_rater_name,
            'rank': senior_rater_rank,
            'title': senior_rater_title,
            'fdid': pas_info['fdid'],
            'srid mpf': pas_info['srid mpf'],
            'mp': must_promote,
            'pn': promote_now
        }
    
    
        doc2.logo_path = logo_path
    
        elements = []
    
        table = create_table(
            doc2,
            data=srid_list,
            header=header_row,
            table_type="SENIOR RATER",
            count=len(srid_list)
        )
        elements.append(table)
        if senior_rater_srid != list(senior_raters.keys())[-1]:
            elements.append(PageBreak())
    
        doc2.build(elements)

    # Build PDF for this pascode
    return output_filename


def merge_pdfs(temp_pdfs, session_id):
    """Merge multiple PDFs into a single PDF"""
    merger = PdfMerger()

    # Add each PDF to the merger
    for pdf_path in temp_pdfs:
        try:
            merger.append(pdf_path)
        except Exception as e:
            print(f"Error adding {pdf_path} to merged document: {e}")

    buffer = BytesIO()
    try:
        merger.write(buffer)
        merger.close()
        buffer.seek(0)

        # Store in Redis (base64 encode)
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=initial_mel_roster.pdf"}
        )


    except Exception as e:
        print(f"Error during PDF merge or Redis store: {e}")
    finally:
        # Clean up disk files
        for path in temp_pdfs:
            try:
                os.remove(path)
            except Exception as e:
                print(f"Warning: could not delete {path}: {e}")


def generate_roster_pdf(session_id, output_filename, logo_path='/images/afpc.png'):
    """Generate a military roster PDF from eligible and ineligible DataFrames by creating separate PDFs for each pascode"""
    # eligible_df, ineligible_df, btz_df, small_unit_df, senior_raters, cycle, melYear, pascode_map,
    session = get_session(session_id)
    eligible_df = pd.DataFrame.from_records(session['eligible_df'])
    ineligible_df = pd.DataFrame.from_records(session['ineligible_df'])
    btz_df = pd.DataFrame.from_records(session['btz_df']) 
    small_unit_df = pd.DataFrame(session['small_unit_df'])
    senior_raters = session['srid_pascode_map']
    cycle = session['cycle']
    melYear = session['year']
    pascode_map = session['pascode_map']
    senior_rater = session['small_unit_sr']
    senior_raters = session['srid_pascode_map']


    # Convert DataFrames to lists
    eligible_data = eligible_df.values.tolist()
    ineligible_columns = ['FULL_NAME', 'GRADE', 'ASSIGNED_PAS', 'DAFSC', 'ASSIGNED_PAS_CLEARTEXT', 'REASON']
    ineligible_data = ineligible_df[ineligible_columns].values.tolist()
    btz_data = btz_df.values.tolist()

    # Get unique PASCODEs from both eligible and ineligible data
    unique_pascodes = set()
    for row in eligible_data:
        unique_pascodes.add(row[7])  # PASCODE is the 8th column
    for row in ineligible_data:
        unique_pascodes.add(row[2])
    for row in btz_data:
        unique_pascodes.add(row[7])
    unique_pascodes = sorted(list(unique_pascodes))


    # Create a list to store temporary PDF filenames
    temp_pdfs = []


    # Generate a separate PDF for each pascode
    for pascode in unique_pascodes:
        is_last = False
        # Skip if this pascode is not in the pascode_map
        if pascode not in pascode_map:
            print(f"Warning: No info for pascode {pascode}, skipping")
            continue

        # Filter data for current pascode
        pascode_eligible = [row for row in eligible_data if row[7] == pascode]
        pascode_ineligible = [row for row in ineligible_data if row[2] == pascode]
        pascode_btz = [row for row in btz_data if row[7] == pascode]



        # Skip if there's no data for this pascode
        if not pascode_eligible and not pascode_ineligible:
            print(f"No data for pascode {pascode}, skipping")
            continue

        # Create PAS info for this pascode
        try:
            if 'ASSIGNED_PAS' in eligible_df.columns:
                eligible_candidates = (eligible_df['ASSIGNED_PAS'] == pascode).sum()
            else:
                eligible_candidates = len(pascode_eligible)
        except:
            eligible_candidates = len(pascode_eligible)
        must_promote, promote_now = get_promotion_eligibility(eligible_candidates, cycle)

        pas_info = {
            'srid': pascode_map[pascode]['srid'],
            'rank': pascode_map[pascode]['senior_rater_rank'],
            'title': pascode_map[pascode]['senior_rater_title'],
            'fd name': pascode_map[pascode]['senior_rater_name'],
            'fdid': f'{pascode_map[pascode]['srid']}{pascode[-4:]}',
            'srid mpf': pascode[:2],
            'mp': must_promote,
            'pn': promote_now
        }

        # Create temporary filename

        # Always generate this PASCODE's base document
        temp_pdf = generate_pascode_pdf(
            pascode_eligible,
            pascode_ineligible,
            pascode_btz,
            small_unit_df,
            senior_rater,
            senior_raters,
            is_last,  # we still signal whether this is the final pascode
            cycle,
            melYear,
            pascode,
            pas_info,
            f"temp_{pascode}.pdf",
            logo_path
        )
        temp_pdfs.append(temp_pdf)

        is_last = (pascode == unique_pascodes[-1])

        # Then if it’s the last pascode, trigger senior rater documents
        if is_last:
            print(f"Creating PDF for small unit: {len(small_unit_df)} eligible candidates")
            sr_temp_pdf = generate_pascode_pdf(
                [],  # no eligible
                [],  # no ineligible
                [],  # no btz
                small_unit_df,
                senior_rater,
                senior_raters,
                is_last,
                cycle,
                melYear,
                pascode,
                pas_info,
                f"temp_small_unit.pdf",
                logo_path
            )
            temp_pdfs.append(sr_temp_pdf)

    # Merge all the temporary PDFs into the final output file
    if temp_pdfs:
        response = merge_pdfs(temp_pdfs, session_id)
        return response
    else:
        print("No PDFs were generated. Check your data and pascode_map.")