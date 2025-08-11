from io import BytesIO
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak, Image, Frame, Paragraph
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
from dateutil.relativedelta import relativedelta
from promotion_eligible_counter import get_promotion_eligibility
import os
import fitz  # PyMuPDF
from PyPDF2 import PdfMerger
import pandas as pd

from session_manager import get_session

# Register Calibri fonts
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

SCODs = {'SRA': f'31-MAR',
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


class FinalMELDocument(BaseDocTemplate):
    def __init__(self, filename, cycle=None, melYear=None, **kwargs):
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
        if os.path.exists(logo_path):
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
        canvas.drawString(text_start_x, text_start_y - line_height, f"FD NAME: {doc.pas_info['fd name']}")
        canvas.drawString(text_start_x, text_start_y - 2 * line_height, f"FDID: {doc.pas_info['fdid']}")
        canvas.drawString(text_start_x, text_start_y - 3 * line_height, f"SRID MPF: {doc.pas_info['srid mpf']}")

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

            # Add unit size in the Promotion Eligibility Data section
            unit_size_txt = "SMALL" if doc.pas_info.get('is_small_unit', False) else "LARGE"
            canvas.drawString(text_start_x, text_start_y - 2 * line_height, f"UNIT SIZE: {unit_size_txt}")

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
        from reportlab.pdfbase.pdfmetrics import stringWidth
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

        # Final MEL
        identifier_text = f"{str(self.melYear + 1)[-2:]}{promotion_map[self.cycle]} - Final MEL"
        identifier_width = stringWidth(identifier_text, 'Calibri-Bold', 12)
        identifier_center_x = (self.page_width / 2) - (identifier_width / 2)
        canvas.drawString(identifier_center_x, bottom_y - 18, identifier_text)

        # Right: Page numbers
        page_text = f"Accounting Date: {get_accounting_date(self.cycle, self.melYear)}"
        page_width = stringWidth(page_text, 'Calibri-Bold', 12)
        canvas.drawString(self.page_width - 0.5 * inch - page_width, bottom_y, page_text)


def create_final_mel_table(doc, data, header, table_type=None, count=None):
    """Create table without checkbox graphics for final MEL (checkboxes will be added with PyMuPDF)"""
    table_width = doc.page_width - inch

    # Column widths for eligible table
    # Format: [NAME, GRADE, PASCODE, DAFSC, UNIT, NRN, P, MP, PN]
    col_widths = [table_width * x for x in [0.26, 0.08, 0.1, 0.1, 0.26, 0.05, 0.05, 0.05, 0.05]]

    # Process data to include empty cells for checkboxes
    processed_data = []
    for row in data:
        # Create a new row with empty cells for checkboxes
        new_row = row[:5] + ["", "", "", ""]
        processed_data.append(new_row)

    # Prepare table data
    table_data = [header] + processed_data
    repeat_rows = 1

    # Add status row if provided
    if table_type and count is not None:
        status_row = [[table_type, "", "", "", "", "", "", "", f"Total: {count}"]]
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
        ('ALIGN', (2, repeat_rows - 1), (2, -1), 'CENTER'),  # PASCODE
        ('ALIGN', (3, repeat_rows - 1), (3, -1), 'LEFT'),  # DAFSC
        ('ALIGN', (4, repeat_rows - 1), (4, -1), 'CENTER'),  # UNIT
        ('ALIGN', (5, repeat_rows - 1), (8, -1), 'CENTER'),  # Checkbox columns

        # Vertical alignment for all cells
        ('VALIGN', (0, repeat_rows), (-1, -1), 'MIDDLE'),
    ]

    # Add status row styling if present
    if table_type:
        style.extend([
            ('SPAN', (0, 0), (7, 0)),  # Span heading across
            ('ALIGN', (8, 0), (8, 0), 'RIGHT'),  # Right align the count
        ])

    table.setStyle(TableStyle(style))
    return table


def create_ineligible_table(doc, data, header, table_type=None, count=None):
    """Create table for ineligible members with reason column"""
    table_width = doc.page_width - inch

    # Column widths for ineligible table
    # Format: [NAME, GRADE, PASCODE, DAFSC, UNIT, REASON NOT ELIGIBLE]
    col_widths = [table_width * x for x in [0.25, 0.08, 0.1, 0.1, 0.25, 0.2]]

    # Prepare table data
    table_data = [header] + data
    repeat_rows = 1

    # Add status row if provided
    if table_type and count is not None:
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
        ('ALIGN', (2, repeat_rows - 1), (2, -1), 'CENTER'),  # PASCODE
        ('ALIGN', (3, repeat_rows - 1), (3, -1), 'LEFT'),  # DAFSC
        ('ALIGN', (4, repeat_rows - 1), (4, -1), 'CENTER'),  # UNIT
        ('ALIGN', (5, repeat_rows - 1), (5, -1), 'LEFT'),  # REASON NOT ELIGIBLE
    ]

    # Add status row styling if present
    if table_type:
        style.extend([
            ('SPAN', (0, 0), (4, 0)),  # Span heading across
            ('ALIGN', (5, 0), (5, 0), 'RIGHT'),  # Right align the count
        ])

    table.setStyle(TableStyle(style))
    return table


def add_interactive_checkboxes(pdf_path, eligible_data, pascode):
    """Add interactive checkboxes using PyMuPDF with precise positioning across multiple pages"""
    try:
        # Open the PDF
        doc = fitz.open(pdf_path)

        # Track the current page and row count
        current_page_index = 0
        rows_on_current_page = 0
        max_rows_per_page = 20  # Adjust based on your PDF layout

        # Get page dimensions
        page_width = doc[0].rect.width
        page_height = doc[0].rect.height

        # Refined positioning calculations
        start_x = page_width * 0.79  # Adjusted for checkbox column
        start_y = page_height * 0.276  # Initial start position
        row_height = page_height * 0.0295  # Proportional to page height
        col_width = page_width * 0.045  # Spacing between checkbox columns

        # Checkbox size
        checkbox_size = 11  # Slightly larger for easier clicking

        # Labels for the checkboxes
        checkbox_labels = ["NRN", "P", "MP", "PN"]

        # Add checkboxes for each row in eligible data
        for i, row in enumerate(eligible_data):
            # Check if we need to move to a new page
            if rows_on_current_page >= max_rows_per_page:
                current_page_index += 1
                rows_on_current_page = 0

            # Get the current page
            page = doc[current_page_index]

            # Reset y position for new page
            if rows_on_current_page == 0:
                current_y = start_y
            else:
                current_y = start_y + (rows_on_current_page * row_height)

            # Add checkboxes for NRN, P, MP, PN
            for j, label in enumerate(checkbox_labels):
                # Calculate x position for this checkbox
                x_pos = start_x + (j * col_width)

                # Create a checkbox widget
                widget = fitz.Widget()
                widget.rect = fitz.Rect(
                    x_pos,
                    current_y,
                    x_pos + checkbox_size,
                    current_y + checkbox_size
                )
                widget.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
                widget.field_name = f"{pascode}_{i}_{label}"
                widget.field_value = "Off"
                widget.field_flags = 0  # Normal behavior
                widget.border_width = 1
                widget.border_color = (0, 0, 0)  # Black border
                widget.fill_color = (1, 1, 1)  # White fill

                # Add the checkbox to the page
                page.add_widget(widget)

            # Increment rows on current page
            rows_on_current_page += 1

        # Generate a temporary filename
        import tempfile
        import os

        # Create a temporary file in the same directory as the original PDF
        temp_dir = os.path.dirname(pdf_path)
        temp_filename = os.path.join(temp_dir, f"temp_{os.path.basename(pdf_path)}")

        # Save to a new file
        doc.save(temp_filename, garbage=4, deflate=True, clean=True)
        doc.close()

        # Replace the original file with the temporary file
        import shutil
        shutil.move(temp_filename, pdf_path)

        return pdf_path

    except Exception as e:
        try:
            doc.close()
        except:
            pass

        return pdf_path

def generate_final_mel_pdf(eligible_data, ineligible_data, small_unit_data, senior_rater, senior_raters, is_last, cycle, melYear, pascode, pas_info,
                           output_filename, logo_path):
    """Generate a PDF for a single pascode for final MEL with interactive form fields"""
    # Standard columns we know about
    name_idx = 0  # FULL_NAME
    grade_idx = 1  # GRADE
    dafsc_idx = 3  # DAFSC
    unit_idx = 4  # UNIT
    pascode_idx = 7  # ASSIGNED_PAS/PASCODE

    doc = FinalMELDocument(
        output_filename,
        cycle=cycle,
        melYear=melYear,
        pagesize=landscape(letter),
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch
    )

    doc2 = FinalMELDocument(
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
    doc.pas_members = [pas_info]
    doc.pas_info = pas_info

    elements = []

    # Header rows
    eligible_header_row = ['FULL NAME', 'GRADE', 'PASCODE', 'DAFSC', 'UNIT', 'NRN', 'P', 'MP', 'PN']
    ineligible_header_row = ['FULL NAME', 'GRADE', 'PASCODE', 'DAFSC', 'UNIT', 'REASON NOT ELIGIBLE']

    # Process eligible data
    processed_eligible_data = []
    if eligible_data:
        for row in eligible_data:
            # Make sure the row has enough elements
            if len(row) <= max(name_idx, grade_idx, dafsc_idx, unit_idx, pascode_idx):
                continue

            # Extract data safely with defaults for missing fields
            name = str(row[name_idx]) if name_idx < len(row) else "Unknown"
            if len(name) > 30:
                name = name[:27] + "..."

            grade = str(row[grade_idx]) if grade_idx < len(row) else "Unknown"
            dafsc = str(row[dafsc_idx]) if dafsc_idx < len(row) else "Unknown"
            unit = str(row[unit_idx]) if unit_idx < len(row) else "Unknown"
            pascode_val = str(row[pascode_idx]) if pascode_idx < len(row) else "Unknown"

            # Prepare row data for table
            new_row = [name, grade, pascode_val, dafsc, unit]
            processed_eligible_data.append(new_row)

        # Create eligible table
        if processed_eligible_data:
            table = create_final_mel_table(
                doc,
                data=processed_eligible_data,
                header=eligible_header_row,
                table_type="ELIGIBLE",
                count=len(processed_eligible_data)
            )
            elements.append(table)

    # Process ineligible data
    processed_ineligible_data = []
    if ineligible_data:
        # Add page break before ineligible section if needed
        if elements:
            elements.append(PageBreak())

        for row in ineligible_data:
            # Make sure the row has enough elements
            if len(row) <= max(name_idx, grade_idx, dafsc_idx, unit_idx, pascode_idx):
                continue

            # Extract data safely with defaults for missing fields
            name = str(row[name_idx]) if name_idx < len(row) else "Unknown"
            if len(name) > 30:
                name = name[:27] + "..."

            grade = str(row[grade_idx]) if grade_idx < len(row) else "Unknown"
            dafsc = str(row[dafsc_idx]) if dafsc_idx < len(row) else "Unknown"
            unit = str(row[unit_idx]) if unit_idx < len(row) else "Unknown"
            pascode_val = str(row[pascode_idx]) if pascode_idx < len(row) else "Unknown"

            # Determine reason
            reason = "Ineligible"
            if isinstance(row, pd.Series) and 'REASON' in row.index and pd.notna(row['REASON']):
                # Use the specific reason we added
                reason = str(row['REASON'])
            elif len(row) > 8 and row[8] is not None:
                reason = str(row[8])
            elif len(row) > 5 and isinstance(row[5], str):
                reason = row[5]

            # Format: [NAME, GRADE, PASCODE, DAFSC, UNIT, REASON]
            new_row = [name, grade, pascode_val, dafsc, unit, reason]
            processed_ineligible_data.append(new_row)

        # Create ineligible table
        if processed_ineligible_data:
            table = create_ineligible_table(
                doc,
                data=processed_ineligible_data,
                header=ineligible_header_row,
                table_type="INELIGIBLE",
                count=len(processed_ineligible_data)
            )
            elements.append(table)

    # Build the PDF with ReportLab
    doc.build(elements)

    if is_last and len(small_unit_data) > 0 and not eligible_data and not ineligible_data:
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
            'pn': promote_now,  # Add small unit flag
            "is_small_unit": is_last
        }


        doc2.logo_path = logo_path

        elements = []

        table = create_final_mel_table(
            doc2,
            data=srid_list,
            header=eligible_header_row,
            table_type="SENIOR RATER",
            count=len(srid_list)
        )
        elements.append(table)
        if senior_rater_srid != list(senior_raters.keys())[-1]:
            elements.append(PageBreak())

        doc2.build(elements)

    # Add interactive checkboxes with PyMuPDF if we have eligible data
    if processed_eligible_data:
        add_interactive_checkboxes(output_filename, processed_eligible_data, pascode)

        # Add checkboxes to senior rater page
    if is_last and len(small_unit_data) > 0 and not eligible_data and not ineligible_data:
        add_interactive_checkboxes(output_filename, srid_list, pascode + "_SR")

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

def generate_final_roster_pdf(session_id,
                              output_filename="final_military_roster.pdf",
                              logo_path='images/fiftyonefss.jpeg'):
    """Generate a final MEL PDF with interactive form fields"""
    session = get_session(session_id)
    eligible_df = pd.DataFrame.from_records(session['eligible_df'])
    ineligible_df = pd.DataFrame.from_records(session['ineligible_df'])
    small_unit_df = pd.DataFrame(session['small_unit_df'])
    senior_raters = session['srid_pascode_map']
    cycle = session['cycle']
    melYear = session['year']
    pascode_map = session['pascode_map']
    senior_rater = session['small_unit_sr']
    senior_raters = session['srid_pascode_map']

    # Convert DataFrames to lists
    eligible_data = eligible_df.values.tolist()
    ineligible_data = ineligible_df.values.tolist()

    # Get unique PASCODEs from eligible and ineligible data
    unique_pascodes = set()
    for row in eligible_data + ineligible_data:
        if len(row) > 7 and row[7] is not None:
            unique_pascodes.add(row[7])  # PASCODE is the 8th column
    unique_pascodes = sorted(list(unique_pascodes))

    # Create a list to store temporary PDF filenames
    temp_pdfs = []

    # Generate a separate PDF for each pascode
    for pascode in unique_pascodes:
        # Skip if this pascode is not in the pascode_map
        if pascode not in pascode_map:
            continue

        # Filter data for current pascode
        pascode_eligible = [row for row in eligible_data if len(row) > 7 and row[7] == pascode]
        pascode_ineligible = [row for row in ineligible_data if len(row) > 7 and row[7] == pascode]

        # Skip if there's no data for this pascode
        if not pascode_eligible and not pascode_ineligible:
            continue

        # Create PAS info for this pascode
        try:
            if 'ASSIGNED_PAS' in eligible_df.columns:
                eligible_candidates = (eligible_df['ASSIGNED_PAS'] == pascode).sum()
            else:
                eligible_candidates = len(pascode_eligible)
        except:
            eligible_candidates = len(pascode_eligible)

        # Determine if this is a small unit (10 or fewer eligible members)
        is_small_unit = eligible_candidates <= 10


        must_promote, promote_now = get_promotion_eligibility(eligible_candidates, cycle)
        pas_info = {
            'srid': pascode_map[pascode]['srid'],
            'fd name': pascode_map[pascode]['senior_rater_name'],
            'rank': pascode_map[pascode]['senior_rater_rank'],
            'title': pascode_map[pascode]['senior_rater_title'],
            'fdid': f'{pascode_map[pascode]['srid']}{pascode[-4:]}',
            'srid mpf': pascode[:2],
            'mp': must_promote,
            'pn': promote_now,
            'is_small_unit': is_small_unit  # Add small unit flag
        }

        # Create temporary filename
        temp_filename = f"temp_final_{pascode}.pdf"
        is_last = (pascode == unique_pascodes[-1])
        
        # Generate PDF for this pascode with interactive form fields
        temp_pdf = generate_final_mel_pdf(
            pascode_eligible,
            pascode_ineligible,
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

        temp_pdfs.append(temp_pdf)

        if is_last:
            print(f"Creating PDF for small unit : {len(small_unit_df)} eligible candidates")
            sr_temp_pdf = generate_final_mel_pdf(
                [],  # no eligible
                [],  # no ineligible
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
        return merge_pdfs(temp_pdfs, session_id) 
    else: 
        return None