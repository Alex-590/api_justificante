from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pdf2image import convert_from_bytes
import cv2
import numpy as np
import pytesseract
import requests  

app = FastAPI(
    title="PDFExtractionAPI",
    version="1.0.0",
    description="API to detect missing fields in medical justification PDFs"
)

# 🔹 Campos obligatorios (ajusta los nombres como tú los uses)
REQUIRED_FIELDS = [
    "name",
    "boss name",
    "date",
    "employee id",
    "reason",
    "doctor signature",
]


# 🔹 Modelo para el endpoint que recibe URL
class PDFUrlInput(BaseModel):
    file_url: str


# 🔹 Lógica común para analizar un PDF en bytes
def analyze_pdf_bytes(pdf_bytes: bytes) -> dict:
    # 1) PDF -> imágenes
    pages = convert_from_bytes(pdf_bytes)
    if not pages:
        return {"missing_fields": REQUIRED_FIELDS}

    first_page = pages[0]

    # 2) OCR
    text = pytesseract.image_to_string(first_page, lang="eng")
    lower = text.lower()

    missing_fields = []

    # 🔹 Revisa texto para campos
    if "name" not in lower:
        missing_fields.append("name")

    if "boss name" not in lower:
        missing_fields.append("boss name")

    if "date" not in lower:
        missing_fields.append("date")

    if "employee id" not in lower:
        missing_fields.append("employee id")

    if "reason" not in lower:
        missing_fields.append("reason")

    # 3) Revisión de firma (misma idea que tenías antes)
    cv_image = cv2.cvtColor(np.array(first_page), cv2.COLOR_RGB2BGR)
    h, w, _ = cv_image.shape

    # zona abajo a la derecha
    sign_region = cv_image[int(h * 0.6):int(h * 0.95), int(w * 0.4):int(w * 0.95)]

    gray = cv2.cvtColor(sign_region, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    ink = cv2.countNonZero(thresh)

    if ink < 50:
        missing_fields.append("doctor signature")

    return {"missing_fields": missing_fields}


# ✅ Endpoint original (recibe archivo, lo dejamos igual)
@app.post("/extract")
async def extract_fields(file: UploadFile = File(...)):
    pdf_bytes = await file.read()
    result = analyze_pdf_bytes(pdf_bytes)
    return JSONResponse(content=result)


# ✅ NUEVO endpoint: recibe URL del PDF
@app.post("/extract_from_url")
async def extract_fields_from_url(data: PDFUrlInput):
    # 1) Descargar el PDF desde la URL
    resp = requests.get(data.file_url)
    resp.raise_for_status()
    pdf_bytes = resp.content

    # 2) Reusar la lógica común
    result = analyze_pdf_bytes(pdf_bytes)
    return JSONResponse(content=result)
