import pandas as pd
import os
from io import BytesIO
from fastapi.responses import StreamingResponse
from reportlab.platypus import PageBreak
from reportlab.lib.units import inch

from promotion_eligible_counter import get_promotion_eligibility
from session_manager import get_session
from constants import (
    INITIAL_MEL_HEADER_ROW, INITIAL_MEL_INELIGIBLE_HEADER_ROW,
    INITIAL_MEL_TABLE_WIDTHS, INITIAL_MEL_INELIGIBLE_TABLE_WIDTHS,
    images_dir, default_logo, PDF_MARGIN
)
from pdf_templates import PDF_Template, create_table, merge_pdfs



class InitialMELDocument(PDF_Template):
    """Document template for Initial MEL reports, inheriting from the base template."""
    def __init__(self, filename, cycle, melYear=None, **kwargs):
        super().__init__(filename, cycle, melYear, **kwargs)

def generate_pascode_pdf(eligible_data, ineligible_data, btz_data, cycle, melYear,
                         pascode, pas_info, output_filename, logo_path):
    """Generate a PDF for a single pascode."""
    try:
        doc = InitialMELDocument(
            output_filename, cycle=cycle, melYear=melYear,
            rightMargin=PDF_MARGIN, leftMargin=PDF_MARGIN,
            topMargin=PDF_MARGIN, bottomMargin=PDF_MARGIN
        )
        doc.logo_path = logo_path
        doc.pas_info = pas_info
        elements = []
        if eligible_data and len(eligible_data) > 0:
            table = create_table(doc, eligible_data, INITIAL_MEL_HEADER_ROW,
                                 INITIAL_MEL_TABLE_WIDTHS, "ELIGIBLE", len(eligible_data))
            elements.append(table)
            elements.append(PageBreak())
        if ineligible_data and len(ineligible_data) > 0:
            table = create_table(doc, ineligible_data, INITIAL_MEL_INELIGIBLE_HEADER_ROW,
                                 INITIAL_MEL_INELIGIBLE_TABLE_WIDTHS, "INELIGIBLE", len(ineligible_data))
            elements.append(table)
            elements.append(PageBreak())
        if btz_data and len(btz_data) > 0:
            table = create_table(doc, btz_data, INITIAL_MEL_HEADER_ROW,
                                 INITIAL_MEL_TABLE_WIDTHS, "BELOW THE ZONE", len(btz_data))
            elements.append(table)
            elements.append(PageBreak())
        doc.build(elements)
        return output_filename
    except Exception as e:
        print(f"Error generating PDF for pascode {pascode}: {e}")
        return None

def generate_small_unit_pdf(small_unit_data, senior_rater, cycle, melYear, pas_info, base_filename, logo_path):
    """Generate PDF for small unit data."""
    try:
        small_unit_filename = base_filename.replace('.pdf', '_small_unit.pdf')
        doc = InitialMELDocument(
            small_unit_filename, cycle=cycle, melYear=melYear,
            rightMargin=PDF_MARGIN, leftMargin=PDF_MARGIN,
            topMargin=PDF_MARGIN, bottomMargin=PDF_MARGIN
        )
        srid_list = small_unit_data.values.tolist() if hasattr(small_unit_data, 'values') else small_unit_data
        must_promote, promote_now = get_promotion_eligibility(len(srid_list), cycle)
        doc.pas_info = {
            'srid': senior_rater.get('srid', 'N/A'),
            'fd name': senior_rater.get('senior_rater_name', 'N/A'),
            'rank': senior_rater.get('senior_rater_rank', 'N/A'),
            'title': senior_rater.get('senior_rater_title', 'N/A'),
            'srid mpf': pas_info.get('srid mpf', 'N/A'),
            'mp': must_promote,
            'pn': promote_now
        }
        doc.logo_path = logo_path
        elements = []
        table = create_table(doc, srid_list, INITIAL_MEL_HEADER_ROW,
                             INITIAL_MEL_TABLE_WIDTHS, "SENIOR RATER", len(srid_list))
        elements.append(table)
        doc.build(elements)
        return small_unit_filename
    except Exception as e:
        print(f"Error generating small unit PDF: {e}")
        return None

def generate_roster_pdf(session_id, output_filename, logo_path=None):
    """Generate a military roster PDF from session data."""
    try:
        session = get_session(session_id)
        if not session:
            return None
        eligible_df = pd.DataFrame.from_records(session.get('eligible_df', []))
        ineligible_df = pd.DataFrame.from_records(session.get('ineligible_df', []))
        btz_df = pd.DataFrame.from_records(session.get('btz_df', []))
        small_unit_df = pd.DataFrame(session.get('small_unit_df', []))
        cycle = session.get('cycle')
        melYear = session.get('year')
        pascode_map = session.get('pascode_map', {})
        senior_rater = session.get('small_unit_sr', {})
        if not logo_path:
            logo_path = os.path.join(images_dir, default_logo)
        eligible_data = eligible_df.values.tolist() if not eligible_df.empty else []
        btz_data = btz_df.values.tolist() if not btz_df.empty else []
        ineligible_columns = ['FULL_NAME', 'GRADE', 'ASSIGNED_PAS', 'DAFSC', 'ASSIGNED_PAS_CLEARTEXT', 'REASON']
        available_columns = [col for col in ineligible_columns if col in ineligible_df.columns]
        ineligible_data = ineligible_df[available_columns].values.tolist() if not ineligible_df.empty else []
        unique_pascodes = set()
        for row in eligible_data:
            if len(row) > 7:
                unique_pascodes.add(row[7])
        for row in ineligible_data:
            if len(row) > 2:
                unique_pascodes.add(row[2])
        for row in btz_data:
            if len(row) > 7:
                unique_pascodes.add(row[7])
        unique_pascodes = sorted(list(unique_pascodes))
        temp_pdfs = []
        if not unique_pascodes and not small_unit_df.empty and senior_rater:
            small_unit_temp_filename = f"temp_small_unit.pdf"
            small_unit_pas_info = {
                'fdid': f'{senior_rater.get("srid", "")}',
                'srid mpf': senior_rater.get("srid", "")[:2] if senior_rater.get("srid") else 'N/A'
            }
            small_unit_pdf = generate_small_unit_pdf(
                small_unit_df, senior_rater, cycle, melYear, small_unit_pas_info, small_unit_temp_filename, logo_path
            )
            if small_unit_pdf:
                temp_pdfs.append(small_unit_pdf)
            return merge_pdfs(temp_pdfs, session_id)
        for pascode in unique_pascodes:
            if pascode not in pascode_map:
                continue
            pascode_eligible = [row for row in eligible_data if len(row) > 7 and row[7] == pascode]
            pascode_ineligible = [row for row in ineligible_data if len(row) > 2 and row[2] == pascode]
            pascode_btz = [row for row in btz_data if len(row) > 7 and row[7] == pascode]
            if not pascode_eligible and not pascode_ineligible and not pascode_btz:
                continue
            eligible_candidates = len(pascode_eligible)
            must_promote, promote_now = get_promotion_eligibility(eligible_candidates, cycle)
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
            temp_filename = f"temp_{pascode}.pdf"
            temp_pdf = generate_pascode_pdf(
                pascode_eligible, pascode_ineligible, pascode_btz, cycle, melYear,
                pascode, pas_info, temp_filename, logo_path
            )
            if temp_pdf:
                temp_pdfs.append(temp_pdf)
        if not small_unit_df.empty and senior_rater:
            small_unit_temp_filename = f"temp_small_unit.pdf"
            small_unit_pas_info = {
                'fdid': f'{senior_rater.get("srid", "")}',
                'srid mpf': senior_rater.get("srid", "")[:2] if senior_rater.get("srid") else 'N/A'
            }
            small_unit_pdf = generate_small_unit_pdf(
                small_unit_df, senior_rater, cycle, melYear, small_unit_pas_info, small_unit_temp_filename, logo_path
            )
            if small_unit_pdf:
                temp_pdfs.append(small_unit_pdf)
        return merge_pdfs(temp_pdfs, session_id)
    except Exception as e:
        print(f"Error generating roster PDF: {e}")
        return None
