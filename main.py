import os
import io
from fastapi import Body, FastAPI, Form, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
import pandas as pd
from final_mel_generator import generate_final_roster_pdf
from session_manager import create_session, get_pdf_from_redis, get_session, update_session, delete_session
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
from initial_mel_generator import generate_roster_pdf
from roster_processor import roster_processor
from classes import PasCodeInfo, PasCodeSubmission
from constants import (
    REQUIRED_COLUMNS, OPTIONAL_COLUMNS, PDF_COLUMNS,
    cors_origins, allowed_types, images_dir, default_logo
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/upload/initial-mel")
async def upload_file(
        file: UploadFile = File(...),
        cycle: str = Form(...),
        year: int = Form(...)
):
    return_object = {}

    if file.content_type not in allowed_types:
        return JSONResponse(content={"error": "Invalid file type. Only CSV or Excel files are allowed."},
                            status_code=400)

    contents = await file.read()

    if file.filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(contents))
    elif file.filename.endswith(".xlsx"):
        df = pd.read_excel(io.BytesIO(contents))
    else:
        return JSONResponse(content={"error": "Unsupported file extension."}, status_code=400)

    processed_df = df[REQUIRED_COLUMNS + OPTIONAL_COLUMNS]
    pdf_df = processed_df[PDF_COLUMNS]
    session_id = create_session(processed_df, pdf_df)
    update_session(session_id, cycle=cycle)
    update_session(session_id, year=year)
    roster_processor(df, session_id, cycle, year)

    session = get_session(session_id)

    # Use .get() to safely access session keys that might not exist
    if session.get('pascodes') is not None:
        return_object['pascodes'] = session['pascodes']

    if session.get('pascode_unit_map') is not None:
        return_object['pascode_unit_map'] = session['pascode_unit_map']

    if session.get('small_unit_df') is not None:
        return_object['senior_rater_needed'] = True
    else:
        return_object["senior_rater_needed"] = False

    return_object['message'] = "Upload successful."
    return_object['session_id'] = session_id
    return_object['errors'] = session.get('error_log', [])

    return JSONResponse(content=return_object)


@app.get("/api/download/initial-mel/{session_id}")
async def download_initial_mel(session_id: str):
    try:
        pdf_buffer: io.BytesIO | None = get_pdf_from_redis(session_id)

        if not pdf_buffer:
            return JSONResponse(
                content={"error": "PDF not found for this session"},
                status_code=404
            )

        return StreamingResponse(
            pdf_buffer,
            media_type='application/pdf',
            headers={
                "Content-Disposition": f"attachment; filename=initial_mel_roster.pdf"
            }
        )
    except Exception as e:
        return JSONResponse(
            content={"error": f"Failed to retrieve PDF: {str(e)}"},
            status_code=500
        )


@app.post("/api/initial-mel/submit/pascode-info")
async def submit_pascode_info(payload: PasCodeSubmission):
    pascode_map = {pascode: info.model_dump() for pascode, info in payload.pascode_info.items()}
    if 'small_unit_sr' in pascode_map:
        small_unit_sr = pascode_map.pop('small_unit_sr')
    else:
        small_unit_sr = None

    if small_unit_sr:
        update_session(payload.session_id, small_unit_sr=small_unit_sr)
    update_session(payload.session_id, pascode_map=pascode_map)
    srid_pascode_map = {}
    session = get_session(payload.session_id)

    for pascode in session['pascodes']:
        srid = session['pascode_map'][pascode]['srid']
        if srid in srid_pascode_map:
            srid_pascode_map[srid].append(pascode)
        else:
            srid_pascode_map[srid] = [pascode]

    update_session(payload.session_id, srid_pascode_map=srid_pascode_map)

    # Use constants for logo path
    logo_path = os.path.join(images_dir, default_logo)

    response = generate_roster_pdf(payload.session_id,
                                   output_filename=rf"tmp/{payload.session_id}_initial_mel_roster.pdf",
                                   logo_path=logo_path)

    if response:
        return response
    return JSONResponse(content={"error": "PDF generation failed"}, status_code=500)


@app.post("/api/upload/final-mel")
async def upload_final_mel_file(
        file: UploadFile = File(...),
        cycle: str = Form(...),
        year: int = Form(...)
):
    return_object = {}

    if file.content_type not in allowed_types:
        return JSONResponse(content={"error": "Invalid file type. Only CSV or Excel files are allowed."},
                            status_code=400)

    contents = await file.read()

    if file.filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(contents))
    elif file.filename.endswith(".xlsx"):
        df = pd.read_excel(io.BytesIO(contents))
    else:
        return JSONResponse(content={"error": "Unsupported file extension."}, status_code=400)

    processed_df = df[REQUIRED_COLUMNS + OPTIONAL_COLUMNS]
    pdf_df = processed_df[PDF_COLUMNS]
    session_id = create_session(processed_df, pdf_df)
    update_session(session_id, cycle=cycle)
    update_session(session_id, year=year)
    roster_processor(df, session_id, cycle, year)

    session = get_session(session_id)

    # Use .get() to safely access session keys that might not exist
    if session.get('pascodes') is not None:
        return_object['pascodes'] = session['pascodes']

    if session.get('pascode_unit_map') is not None:
        return_object['pascode_unit_map'] = session['pascode_unit_map']

    if session.get('small_unit_df') is not None:
        return_object['senior_rater_needed'] = True
    else:
        return_object["senior_rater_needed"] = False

    return_object['message'] = "Upload successful."
    return_object['session_id'] = session_id
    return_object['errors'] = session.get('error_log', [])

    return JSONResponse(content=return_object)


@app.post("/api/final-mel/submit/pascode-info")
async def submit_final_pascode_info(payload: PasCodeSubmission):
    pascode_map = {pascode: info.model_dump() for pascode, info in payload.pascode_info.items()}
    if 'small_unit_sr' in pascode_map:
        small_unit_sr = pascode_map.pop('small_unit_sr')
    else:
        small_unit_sr = None

    if small_unit_sr:
        update_session(payload.session_id, small_unit_sr=small_unit_sr)
    update_session(payload.session_id, pascode_map=pascode_map)
    srid_pascode_map = {}
    session = get_session(payload.session_id)

    for pascode in session['pascodes']:
        srid = session['pascode_map'][pascode]['srid']
        if srid in srid_pascode_map:
            srid_pascode_map[srid].append(pascode)
        else:
            srid_pascode_map[srid] = [pascode]

    update_session(payload.session_id, srid_pascode_map=srid_pascode_map)

    # Use constants for logo path
    logo_path = os.path.join(images_dir, default_logo)

    response = generate_final_roster_pdf(payload.session_id,
                                         output_filename=rf"tmp/{payload.session_id}_final_mel_roster.pdf",
                                         logo_path=logo_path)

    if response:
        return response
    return JSONResponse(content={"error": "PDF generation failed"}, status_code=500)


@app.get("/api/download/final-mel/{session_id}")
async def download_final_mel(session_id: str):
    try:
        pdf_buffer: io.BytesIO | None = get_pdf_from_redis(session_id)

        if not pdf_buffer:
            return JSONResponse(
                content={"error": "PDF not found for this session"},
                status_code=404
            )

        return StreamingResponse(
            pdf_buffer,
            media_type='application/pdf',
            headers={
                "Content-Disposition": f"attachment; filename=final_mel_roster.pdf"
            }
        )
    except Exception as e:
        return JSONResponse(
            content={"error": f"Failed to retrieve PDF: {str(e)}"},
            status_code=500
        )