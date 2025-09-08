import pandas as pd
import os
import shutil
import fitz # PyMuPDF
from reportlab.platypus import PageBreak, Table, TableStyle, Frame
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import landscape, letter
from promotion_eligible_counter import get_promotion_eligibility
from session_manager import get_session
from constants import (
    ELIGIBLE_HEADER_ROW, INELIGIBLE_HEADER_ROW,
    ELIGIBLE_TABLE_WIDTHS, INELIGIBLE_TABLE_WIDTHS,
    images_dir, default_logo, max_name_length, small_unit_threshold,
    PDF_MARGIN, PDF_HEADER_COLOR, BODY_FONT, BOLD_FONT,
    PDF_CHECKBOX_SIZE, PDF_CHECKBOX_START_X_PERCENT, PDF_CHECKBOX_START_Y_PERCENT,
    PDF_CHECKBOX_ROW_HEIGHT_PERCENT, PDF_CHECKBOX_COL_WIDTH_PERCENT,
    PDF_CHECKBOX_MAX_ROWS_PER_PAGE, PDF_FONT_SIZE_HEADER, PDF_FONT_SIZE_SUBHEADER
)
from pdf_templates import PDF_Template, create_table, merge_pdfs


class FinalMELDocument(PDF_Template):
    """Document template for Final MEL reports, inheriting from the base template."""
    def __init__(self, filename, cycle, melYear=None, **kwargs):
        super().__init__(filename, cycle, melYear, **kwargs)

def create_final_mel_table(doc, data, header, table_type=None, count=None):
    """Create a table for final MEL with empty checkbox columns."""
    table_width = doc.page_width - (2 * PDF_MARGIN)
    col_widths = [table_width * x for x in ELIGIBLE_TABLE_WIDTHS]
    processed_data = []
    for row in data:
        new_row = row[:5] + ["", "", "", ""]
        processed_data.append(new_row)
    table_data = [header] + processed_data
    repeat_rows = 1
    if table_type and count is not None:
        status_row = [table_type] + [""] * (len(header) - 2) + [f"Total: {count}"]
        table_data = [status_row] + table_data
        repeat_rows = 2
    table = Table(table_data, repeatRows=repeat_rows, colWidths=col_widths)
    style = [
        ('BACKGROUND', (0, 0), (-1, repeat_rows - 1), PDF_HEADER_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, repeat_rows - 1), colors.white),
        ('FONTNAME', (0, 0), (-1, repeat_rows - 1), BOLD_FONT),
        ('FONTSIZE', (0, 0), (-1, repeat_rows - 1), PDF_FONT_SIZE_HEADER),
        ('BOTTOMPADDING', (0, 0), (-1, repeat_rows - 1), 4),
        ('ROWHEIGHT', (0, 0), (-1, -1), 30),
        ('FONTNAME', (0, repeat_rows), (-1, -1), BODY_FONT),
        ('FONTSIZE', (0, repeat_rows), (-1, -1), PDF_FONT_SIZE_SUBHEADER),
        ('LINEBELOW', (0, 0), (-1, -1), .5, colors.lightgrey),
        ('ALIGN', (0, repeat_rows - 1), (0, -1), 'LEFT'),
        ('ALIGN', (1, repeat_rows - 1), (1, -1), 'CENTER'),
        ('ALIGN', (2, repeat_rows - 1), (2, -1), 'CENTER'),
        ('ALIGN', (3, repeat_rows - 1), (3, -1), 'LEFT'),
        ('ALIGN', (4, repeat_rows - 1), (4, -1), 'CENTER'),
        ('ALIGN', (5, repeat_rows - 1), (8, -1), 'CENTER'),
        ('VALIGN', (0, repeat_rows), (-1, -1), 'MIDDLE'),
    ]
    if table_type and count is not None:
        style.extend([
            ('SPAN', (0, 0), (7, 0)),
            ('ALIGN', (8, 0), (8, 0), 'RIGHT'),
        ])
    table.setStyle(TableStyle(style))
    return table

def create_ineligible_table(doc, data, header, table_type=None, count=None):
    """Create a table for ineligible members with a reason column."""
    table_width = doc.page_width - (2 * PDF_MARGIN)
    col_widths = [table_width * x for x in INELIGIBLE_TABLE_WIDTHS]
    table_data = [header] + data
    repeat_rows = 1
    if table_type and count is not None:
        status_row = [table_type] + [""] * (len(header) - 2) + [f"Total: {count}"]
        table_data = [status_row] + table_data
        repeat_rows = 2
    table = Table(table_data, repeatRows=repeat_rows, colWidths=col_widths)
    style = [
        ('BACKGROUND', (0, 0), (-1, repeat_rows - 1), PDF_HEADER_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, repeat_rows - 1), colors.white),
        ('FONTNAME', (0, 0), (-1, repeat_rows - 1), BOLD_FONT),
        ('FONTSIZE', (0, 0), (-1, repeat_rows - 1), PDF_FONT_SIZE_HEADER),
        ('BOTTOMPADDING', (0, 0), (-1, repeat_rows - 1), 4),
        ('ROWHEIGHT', (0, 0), (-1, -1), 30),
        ('FONTNAME', (0, repeat_rows), (-1, -1), BODY_FONT),
        ('FONTSIZE', (0, repeat_rows), (-1, -1), PDF_FONT_SIZE_SUBHEADER),
        ('LINEBELOW', (0, 0), (-1, -1), .5, colors.lightgrey),
        ('ALIGN', (0, repeat_rows - 1), (0, -1), 'LEFT'),
        ('ALIGN', (1, repeat_rows - 1), (1, -1), 'CENTER'),
        ('ALIGN', (2, repeat_rows - 1), (2, -1), 'CENTER'),
        ('ALIGN', (3, repeat_rows - 1), (3, -1), 'LEFT'),
        ('ALIGN', (4, repeat_rows - 1), (4, -1), 'CENTER'),
        ('ALIGN', (5, repeat_rows - 1), (5, -1), 'LEFT'),
    ]
    if table_type and count is not None:
        style.extend([
            ('SPAN', (0, 0), (4, 0)),
            ('ALIGN', (5, 0), (5, 0), 'RIGHT'),
        ])
    table.setStyle(TableStyle(style))
    return table

def add_interactive_checkboxes(pdf_path, eligible_data, pascode):
    """Add interactive checkboxes using PyMuPDF with precise positioning."""
    try:
        doc = fitz.open(pdf_path)
        current_page_index = 0
        rows_on_current_page = 0
        page_width = doc[0].rect.width
        page_height = doc[0].rect.height
        start_x = page_width * PDF_CHECKBOX_START_X_PERCENT
        start_y = page_height * PDF_CHECKBOX_START_Y_PERCENT
        row_height = page_height * PDF_CHECKBOX_ROW_HEIGHT_PERCENT
        col_width = page_width * PDF_CHECKBOX_COL_WIDTH_PERCENT
        checkbox_labels = ["NRN", "P", "MP", "PN"]
        for i, row in enumerate(eligible_data):
            if rows_on_current_page >= PDF_CHECKBOX_MAX_ROWS_PER_PAGE:
                current_page_index += 1
                rows_on_current_page = 0
            page = doc[current_page_index]
            if rows_on_current_page == 0:
                current_y = start_y
            else:
                current_y = start_y + (rows_on_current_page * row_height)
            for j, label in enumerate(checkbox_labels):
                x_pos = start_x + (j * col_width)
                widget = fitz.Widget()
                widget.rect = fitz.Rect(
                    x_pos, current_y, x_pos + PDF_CHECKBOX_SIZE, current_y + PDF_CHECKBOX_SIZE
                )
                widget.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
                widget.field_name = f"{pascode}_{i}_{label}"
                widget.field_value = "Off"
                widget.field_flags = 0
                widget.border_width = 1
                widget.border_color = (0, 0, 0)
                widget.fill_color = (1, 1, 1)
                page.add_widget(widget)
            rows_on_current_page += 1
        temp_dir = os.path.dirname(pdf_path)
        temp_filename = os.path.join(temp_dir, f"temp_{os.path.basename(pdf_path)}")
        doc.save(temp_filename, garbage=4, deflate=True, clean=True)
        doc.close()
        shutil.move(temp_filename, pdf_path)
        return pdf_path
    except Exception as e:
        try:
            doc.close()
        except:
            pass
        return pdf_path

def generate_final_mel_pdf(eligible_data, ineligible_data, senior_rater, senior_raters, cycle, melYear, pascode, pas_info, output_filename, logo_path):
    """Generate a PDF for a single pascode for final MEL with interactive form fields."""
    name_idx = 0; grade_idx = 1; dafsc_idx = 3; unit_idx = 4; pascode_idx = 7
    doc = FinalMELDocument(
        output_filename, cycle=cycle, melYear=melYear,
        rightMargin=PDF_MARGIN, leftMargin=PDF_MARGIN,
        topMargin=PDF_MARGIN, bottomMargin=PDF_MARGIN
    )
    doc.logo_path = logo_path
    doc.pas_info = pas_info
    elements = []
    processed_eligible_data = []
    if eligible_data:
        for row in eligible_data:
            if len(row) <= max(name_idx, grade_idx, dafsc_idx, unit_idx, pascode_idx): continue
            name = str(row[name_idx]) if name_idx < len(row) else "Unknown"
            if len(name) > max_name_length: name = name[:max_name_length - 3] + "..."
            grade = str(row[grade_idx]) if grade_idx < len(row) else "Unknown"
            dafsc = str(row[dafsc_idx]) if dafsc_idx < len(row) else "Unknown"
            unit = str(row[unit_idx]) if unit_idx < len(row) else "Unknown"
            pascode_val = str(row[pascode_idx]) if pascode_idx < len(row) else "Unknown"
            new_row = [name, grade, pascode_val, dafsc, unit]
            processed_eligible_data.append(new_row)
        if processed_eligible_data:
            table = create_final_mel_table(
                doc, data=processed_eligible_data, header=ELIGIBLE_HEADER_ROW,
                table_type="ELIGIBLE", count=len(processed_eligible_data)
            )
            elements.append(table)
    processed_ineligible_data = []
    if ineligible_data:
        if elements: elements.append(PageBreak())
        for row in ineligible_data:
            if len(row) <= max(name_idx, grade_idx, dafsc_idx, unit_idx, pascode_idx): continue
            name = str(row[name_idx]) if name_idx < len(row) else "Unknown"
            if len(name) > max_name_length: name = name[:max_name_length - 3] + "..."
            grade = str(row[grade_idx]) if grade_idx < len(row) else "Unknown"
            dafsc = str(row[dafsc_idx]) if dafsc_idx < len(row) else "Unknown"
            unit = str(row[unit_idx]) if unit_idx < len(row) else "Unknown"
            pascode_val = str(row[pascode_idx]) if pascode_idx < len(row) else "Unknown"
            reason = "Ineligible"
            if isinstance(row, pd.Series) and 'REASON' in row.index and pd.notna(row['REASON']):
                reason = str(row['REASON'])
            elif len(row) > 8 and row[8] is not None:
                reason = str(row[8])
            elif len(row) > 5 and isinstance(row[5], str):
                reason = row[5]
            new_row = [name, grade, pascode_val, dafsc, unit, reason]
            processed_ineligible_data.append(new_row)
        if processed_ineligible_data:
            table = create_ineligible_table(
                doc, data=processed_ineligible_data, header=INELIGIBLE_HEADER_ROW,
                table_type="INELIGIBLE", count=len(processed_ineligible_data)
            )
            elements.append(table)
    doc.build(elements)
    if processed_eligible_data:
        add_interactive_checkboxes(output_filename, processed_eligible_data, pascode)
    return output_filename

def generate_small_unit_final_mel_pdf(small_unit_data, senior_rater, cycle, melYear, output_filename, logo_path):
    """Generate a separate PDF for small unit data in final MEL."""
    try:
        srid_list = small_unit_data.values.tolist() if hasattr(small_unit_data, 'values') else small_unit_data
        must_promote, promote_now = get_promotion_eligibility(len(srid_list), cycle)
        doc = FinalMELDocument(
            output_filename, cycle=cycle, melYear=melYear,
            rightMargin=PDF_MARGIN, leftMargin=PDF_MARGIN,
            topMargin=PDF_MARGIN, bottomMargin=PDF_MARGIN
        )
        doc.pas_info = {
            'srid': senior_rater['srid'],
            'fd name': senior_rater['senior_rater_name'],
            'rank': senior_rater['senior_rater_rank'],
            'title': senior_rater['senior_rater_title'],
            'srid mpf': senior_rater['srid'][:2] if len(senior_rater['srid']) >= 2 else senior_rater['srid'],
            'mp': must_promote,
            'pn': promote_now,
            "is_small_unit": True
        }
        doc.logo_path = logo_path
        elements = []
        table = create_final_mel_table(
            doc, data=srid_list, header=ELIGIBLE_HEADER_ROW,
            table_type="SENIOR RATER", count=len(srid_list)
        )
        elements.append(table)
        doc.build(elements)
        add_interactive_checkboxes(output_filename, srid_list, senior_rater['srid'] + "_SR")
        return output_filename
    except Exception as e:
        print(f"Error generating small unit final MEL PDF: {e}")
        return None

def generate_final_roster_pdf(session_id, output_filename="final_military_roster.pdf", logo_path=None):
    """Generate a final MEL PDF with interactive form fields."""
    session = get_session(session_id)
    eligible_df = pd.DataFrame.from_records(session['eligible_df'])
    ineligible_df = pd.DataFrame.from_records(session['ineligible_df'])
    small_unit_df = pd.DataFrame(session['small_unit_df'])
    senior_raters = session['srid_pascode_map']
    cycle = session['cycle']
    melYear = session['year']
    pascode_map = session['pascode_map']
    senior_rater = session['small_unit_sr']
    if not logo_path: logo_path = os.path.join(images_dir, default_logo)
    eligible_data = eligible_df.values.tolist()
    ineligible_data = ineligible_df.values.tolist()
    unique_pascodes = set()
    for row in eligible_data + ineligible_data:
        if len(row) > 7 and row[7] is not None:
            unique_pascodes.add(row[7])
    unique_pascodes = sorted(list(unique_pascodes))
    temp_pdfs = []
    for pascode in unique_pascodes:
        if pascode not in pascode_map: continue
        pascode_eligible = [row for row in eligible_data if len(row) > 7 and row[7] == pascode]
        pascode_ineligible = [row for row in ineligible_data if len(row) > 7 and row[7] == pascode]
        if not pascode_eligible and not pascode_ineligible: continue
        try:
            if 'ASSIGNED_PAS' in eligible_df.columns:
                eligible_candidates = (eligible_df['ASSIGNED_PAS'] == pascode).sum()
            else:
                eligible_candidates = len(pascode_eligible)
        except:
            eligible_candidates = len(pascode_eligible)
        is_small_unit = eligible_candidates <= small_unit_threshold
        must_promote, promote_now = get_promotion_eligibility(eligible_candidates, cycle)
        pas_info = {
            'srid': pascode_map[pascode]['srid'], 'fd name': pascode_map[pascode]['senior_rater_name'],
            'rank': pascode_map[pascode]['senior_rater_rank'], 'title': pascode_map[pascode]['senior_rater_title'],
            'fdid': f'{pascode_map[pascode]["srid"]}{pascode[-4:]}', 'srid mpf': pascode[:2],
            'mp': must_promote, 'pn': promote_now, 'is_small_unit': is_small_unit
        }
        temp_filename = f"temp_final_{pascode}.pdf"
        temp_pdf = generate_final_mel_pdf(
            pascode_eligible, pascode_ineligible, senior_rater, senior_raters,
            cycle, melYear, pascode, pas_info, temp_filename, logo_path
        )
        if temp_pdf: temp_pdfs.append(temp_pdf)
    if len(small_unit_df) > 0 and senior_rater:
        try:
            small_unit_filename = f"temp_final_small_unit.pdf"
            small_unit_pdf = generate_small_unit_final_mel_pdf(
                small_unit_df, senior_rater, cycle, melYear, small_unit_filename, logo_path
            )
            if small_unit_pdf: temp_pdfs.append(small_unit_pdf)
        except Exception as e:
            print(f"Error generating small unit final MEL PDF: {e}")
    return merge_pdfs(temp_pdfs, session_id) if temp_pdfs else None
