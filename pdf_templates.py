import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
from io import BytesIO
from fastapi.responses import StreamingResponse
from reportlab.platypus import PageBreak, Table, TableStyle, Frame
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from PyPDF2 import PdfMerger
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Image

from constants import (
    PDF_PAGE_WIDTH, PDF_PAGE_HEIGHT, PDF_MARGIN, PDF_CONTENT_FRAME_X,
    PDF_CONTENT_FRAME_Y, PDF_CONTENT_FRAME_WIDTH, PDF_CONTENT_FRAME_HEIGHT,
    PDF_HEADER_COLOR, PDF_HEADER_CUI_Y, PDF_HEADER_MAIN_Y, PDF_HEADER_LINE_HEIGHT,
    PDF_HEADER_UNIT_DATA_X, PDF_HEADER_PROMOTION_X, PDF_HEADER_SIGNATURE_X,
    PDF_FOOTER_BORDER_Y, PDF_FOOTER_TEXT_Y, PDF_FOOTER_BOTTOM_Y,
    PDF_CUI_HEADER, PDF_FOOTER_DISCLAIMER, PDF_FOOTER_CUI,
    PDF_FONT_SIZE_CUI, PDF_FONT_SIZE_HEADER, PDF_FONT_SIZE_SUBHEADER,
    PDF_FONT_SIZE_FOOTER, PDF_FONT_SIZE_FOOTER_BOTTOM,
    BODY_FONT, BOLD_FONT, PROMOTION_MAP, date_display_format,
    PDF_LOGO_SIZE, PDF_LOGO_X, PDF_LOGO_Y_OFFSET, SCODS
)


class PDF_Template(BaseDocTemplate):
    def __init__(self, filename, cycle, melYear, **kwargs):
        super().__init__(filename, **kwargs)
        self.pagesize = landscape(letter)
        self.page_width, self.page_height = self.pagesize
        self.cycle = cycle
        self.melYear = melYear
        self.logo_path = None
        self.pas_info = {}

        # Create content frame using constants
        content_frame = Frame(
            x1=PDF_CONTENT_FRAME_X,
            y1=PDF_CONTENT_FRAME_Y,
            width=PDF_CONTENT_FRAME_WIDTH,
            height=PDF_CONTENT_FRAME_HEIGHT,
            id='normal'
        )

        template = PageTemplate(
            id='military_roster',
            frames=content_frame,
            onPage=self.add_page_elements
        )
        self.addPageTemplates([template])

    def add_page_elements(self, canvas, doc):
        """Add header and footer to each page."""
        canvas.saveState()
        try:
            self.add_header(canvas, doc)
            self.add_footer(canvas, doc)
        except Exception as e:
            print(f"Error adding page elements: {e}")
        canvas.restoreState()

    def add_header(self, canvas, doc):
        """Add header section to page."""
        canvas.setFont(BOLD_FONT, PDF_FONT_SIZE_CUI)
        canvas.drawCentredString(self.page_width / 2, PDF_HEADER_CUI_Y, PDF_CUI_HEADER)
        header_top = PDF_HEADER_MAIN_Y
        self._add_logo(canvas, doc, header_top)
        self._add_unit_data(canvas, doc, header_top)
        self._add_promotion_data(canvas, doc, header_top)
        self._add_signature_block(canvas, doc, header_top)

    def _add_logo(self, canvas, doc, header_top):
        """Add logo to header."""
        try:
            if doc.logo_path and os.path.exists(doc.logo_path):
                logo = Image(doc.logo_path, width=PDF_LOGO_SIZE, height=PDF_LOGO_SIZE)
                logo.drawOn(canvas, PDF_LOGO_X, header_top - PDF_LOGO_Y_OFFSET)
        except Exception as e:
            print(f"Error adding logo: {e}")

    def _add_unit_data(self, canvas, doc, header_top):
        """Add unit data section."""
        canvas.setFont(BOLD_FONT, PDF_FONT_SIZE_HEADER)
        title_y = header_top + 0.1 * inch
        canvas.drawString(PDF_HEADER_UNIT_DATA_X, title_y, "Unit Data")
        pas_info = doc.pas_info
        canvas.setFont(BOLD_FONT, PDF_FONT_SIZE_SUBHEADER)
        text_start_y = header_top - 0.1 * inch
        canvas.drawString(PDF_HEADER_UNIT_DATA_X, text_start_y, f"SRID: {pas_info.get('srid', 'N/A')}")
        if self.cycle not in ['SMS', 'MSG']:
            canvas.drawString(PDF_HEADER_UNIT_DATA_X, text_start_y - PDF_HEADER_LINE_HEIGHT,
                              f"FD NAME: {pas_info.get('fd name', 'N/A')}")
            canvas.drawString(PDF_HEADER_UNIT_DATA_X, text_start_y - 2 * PDF_HEADER_LINE_HEIGHT,
                              f"FDID: {pas_info.get('fdid', 'N/A')}")
            canvas.drawString(PDF_HEADER_UNIT_DATA_X, text_start_y - 3 * PDF_HEADER_LINE_HEIGHT,
                              f"SRID MPF: {pas_info.get('srid mpf', 'N/A')}")
        else:
            canvas.drawString(PDF_HEADER_UNIT_DATA_X, text_start_y - PDF_HEADER_LINE_HEIGHT,
                              f"SRID MPF: {pas_info.get('srid mpf', 'N/A')}")

    def _add_promotion_data(self, canvas, doc, header_top):
        """Add promotion eligibility data section."""
        pas_info = doc.pas_info
        if pas_info.get('pn', 'NA') != 'NA':
            canvas.setFont(BOLD_FONT, PDF_FONT_SIZE_HEADER)
            title_y = header_top + 0.1 * inch
            canvas.drawString(PDF_HEADER_PROMOTION_X, title_y, "Promotion Eligibility Data")
            canvas.setFont(BOLD_FONT, PDF_FONT_SIZE_SUBHEADER)
            text_start_y = header_top - 0.1 * inch
            canvas.drawString(PDF_HEADER_PROMOTION_X, text_start_y,
                              f"PROMOTE NOW: {pas_info.get('pn', 'N/A')}")
            canvas.drawString(PDF_HEADER_PROMOTION_X, text_start_y - PDF_HEADER_LINE_HEIGHT,
                              f"MUST PROMOTE: {pas_info.get('mp', 'N/A')}")
            if pas_info.get('is_small_unit', False):
                canvas.drawString(PDF_HEADER_PROMOTION_X, text_start_y - 2 * PDF_HEADER_LINE_HEIGHT,
                                  "UNIT SIZE: SMALL")

    def _add_signature_block(self, canvas, doc, header_top):
        """Add signature block."""
        pas_info = doc.pas_info
        canvas.setFont(BOLD_FONT, PDF_FONT_SIZE_HEADER)
        title_y = header_top - 0.5 * inch
        officer_name = pas_info.get('fd name', 'N/A')
        rank = pas_info.get('rank', 'N/A')
        title = pas_info.get('title', 'N/A')
        canvas.drawString(PDF_HEADER_SIGNATURE_X, title_y, f"{officer_name}, {rank}, USAF")
        canvas.drawString(PDF_HEADER_SIGNATURE_X, title_y - PDF_HEADER_LINE_HEIGHT, title)

    def add_footer(self, canvas, doc):
        """Add footer section."""
        canvas.setLineWidth(0.1)
        canvas.setStrokeColorRGB(0, 0, 0)
        canvas.line(PDF_MARGIN, PDF_FOOTER_BORDER_Y, self.page_width - PDF_MARGIN, PDF_FOOTER_BORDER_Y)
        self._draw_wrapped_text(canvas, PDF_FOOTER_DISCLAIMER, PDF_FOOTER_TEXT_Y)
        self._add_bottom_footer(canvas, doc)

    def _draw_wrapped_text(self, canvas, text, y_position):
        """Draw text wrapped to multiple lines."""
        canvas.setFont(BOLD_FONT, PDF_FONT_SIZE_FOOTER)
        words = text.split()
        lines = []
        current_line = []
        current_width = 0
        max_width = self.page_width - (2 * PDF_MARGIN)
        for word in words:
            word_width = stringWidth(word + ' ', BOLD_FONT, PDF_FONT_SIZE_FOOTER)
            if current_width + word_width <= max_width:
                current_line.append(word)
                current_width += word_width
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_width = word_width
        if current_line:
            lines.append(' '.join(current_line))
        for i, line in enumerate(lines):
            line_width = stringWidth(line, BOLD_FONT, PDF_FONT_SIZE_FOOTER)
            center_x = (self.page_width - line_width) / 2
            canvas.drawString(center_x, y_position + (len(lines) - 1 - i) * 10, line)

    def _add_bottom_footer(self, canvas, doc):
        """Add bottom footer elements."""
        from initial_mel_generator import InitialMELDocument
        canvas.setFillColorRGB(0, 0, 0)
        canvas.setFont(BOLD_FONT, PDF_FONT_SIZE_FOOTER_BOTTOM)
        canvas.drawString(PDF_MARGIN, PDF_FOOTER_BOTTOM_Y, datetime.now().strftime(date_display_format))
        cui_width = stringWidth(PDF_FOOTER_CUI, BOLD_FONT, PDF_FONT_SIZE_FOOTER_BOTTOM)
        cui_center_x = (self.page_width / 2) - (cui_width / 2)
        canvas.drawString(cui_center_x, PDF_FOOTER_BOTTOM_Y, PDF_FOOTER_CUI)
        identifier_text = f"{str(self.melYear + 1)[-2:]}{PROMOTION_MAP.get(self.cycle, 'XX')} - {'Initial MEL' if isinstance(doc, InitialMELDocument) else 'Final MEL'}"
        identifier_width = stringWidth(identifier_text, BOLD_FONT, PDF_FONT_SIZE_FOOTER_BOTTOM)
        identifier_center_x = (self.page_width / 2) - (identifier_width / 2)
        canvas.drawString(identifier_center_x, PDF_FOOTER_BOTTOM_Y - 18, identifier_text)
        accounting_text = f"Accounting Date: {self._get_accounting_date()}"
        accounting_width = stringWidth(accounting_text, BOLD_FONT, PDF_FONT_SIZE_FOOTER_BOTTOM)
        canvas.drawString(self.page_width - PDF_MARGIN - accounting_width, PDF_FOOTER_BOTTOM_Y, accounting_text)

    def _get_accounting_date(self):
        """Calculate accounting date."""
        try:
            scod = f'{SCODS.get(self.cycle)}-{self.melYear}'
            formatted_scod_date = datetime.strptime(scod, "%d-%b-%Y")
            accounting_date = formatted_scod_date - relativedelta(days=119)
            adjusted_accounting_date = accounting_date.replace(day=3, hour=23, minute=59, second=59)
            return adjusted_accounting_date.strftime(date_display_format)
        except Exception as e:
            print(f"Error calculating accounting date: {e}")
            return "Error calculating date"

def create_table(doc, data, header, col_widths, table_type=None, count=None):
    """Create a generic table with consistent styling."""
    table_width = doc.page_width - (2 * PDF_MARGIN)
    col_widths = [table_width * x for x in col_widths]
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
        ('ALIGN', (0, repeat_rows), (0, -1), 'LEFT'),
        ('ALIGN', (1, repeat_rows), (1, -1), 'CENTER'),
        ('VALIGN', (0, repeat_rows), (-1, -1), 'MIDDLE'),
    ]
    if table_type and count is not None:
        style.extend([
            ('SPAN', (0, 0), (len(header) - 2, 0)),
            ('ALIGN', (len(header) - 1, 0), (len(header) - 1, 0), 'RIGHT'),
        ])
    table.setStyle(TableStyle(style))
    return table

def merge_pdfs(temp_pdfs, session_id):
    """Merge multiple PDFs into a single PDF."""
    if not temp_pdfs:
        return None
    merger = PdfMerger()
    try:
        for pdf_path in temp_pdfs:
            if pdf_path and os.path.exists(pdf_path):
                merger.append(pdf_path)
        buffer = BytesIO()
        merger.write(buffer)
        merger.close()
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=merged_roster.pdf"}
        )
    except Exception as e:
        print(f"Error during PDF merge: {e}")
        return None
    finally:
        for path in temp_pdfs:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Warning: could not delete {path}: {e}")
