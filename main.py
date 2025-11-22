from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse

from pdf2image import convert_from_bytes
import cv2
import numpy as np
import pytesseract
from pytesseract import Output

app = FastAPI(
    title="PDFExtractionAPI",
    version="1.0.0",
    description="API to detect missing fields in medical justification PDFs"
)

REQUIRED_FIELDS = [
    "name",
    "boss_name",
    "date",
    "employee_id",
    "reason",
    "doctor_signature"
]


@app.post("/extract")
async def extract_fields(file: UploadFile = File(...)):
    # 1) Read PDF bytes
    pdf_bytes = await file.read()

    # 2) Convert PDF to images
    try:
        pages = convert_from_bytes(pdf_bytes)
    except Exception as e:
        return JSONResponse(
            content={"missing_fields": REQUIRED_FIELDS, "error": str(e)},
            status_code=200
        )

    if not pages:
        return JSONResponse(content={"missing_fields": REQUIRED_FIELDS})

    # Use first page
    first_page = pages[0]

    # 3) OCR TEXT (English)
    text = pytesseract.image_to_string(first_page, lang="eng")
    text_lower = text.lower()

    missing_fields = []

    # ---- TEXT FIELDS ----
    if "name" not in text_lower:
        missing_fields.append("name")

    if "boss name" not in text_lower and "boss:" not in text_lower and "manager" not in text_lower:
        missing_fields.append("boss_name")

    if "date" not in text_lower:
        missing_fields.append("date")

    if "employee id" not in text_lower and "employee id:" not in text_lower:
        missing_fields.append("employee_id")

    if "reason" not in text_lower:
        missing_fields.append("reason")

    # ---- SIGNATURE ANYWHERE ON PAGE ----
    cv_image = cv2.cvtColor(np.array(first_page), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

    # 4.1 Get OCR boxes with confidence
    ocr_data = pytesseract.image_to_data(gray, lang="eng", output_type=Output.DICT)

    # Start from the grayscale image and erase only high-confidence text
    non_text = gray.copy()
    n_boxes = len(ocr_data["text"])

    for i in range(n_boxes):
        txt = str(ocr_data["text"][i]).strip()
        conf_str = str(ocr_data["conf"][i]).strip()
        try:
            conf = float(conf_str)
        except:
            conf = -1.0

        # Skip empty or low-confidence entries (likely noise or scribbles)
        if txt == "" or conf < 60:
            continue

        x = ocr_data["left"][i]
        y = ocr_data["top"][i]
        w = ocr_data["width"][i]
        h = ocr_data["height"][i]

        # Erase only reliable printed text
        cv2.rectangle(non_text, (x, y), (x + w, y + h), 255, -1)

    # 4.3 Threshold remaining ink (non-text strokes)
    _, thresh = cv2.threshold(non_text, 200, 255, cv2.THRESH_BINARY_INV)

    # Optional noise reduction
    kernel = np.ones((3, 3), np.uint8)
    clean = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    ink_pixels = cv2.countNonZero(clean)

    # 4.4 Decide if signature exists
    INK_THRESHOLD = 300  # ajustable según tus PDFs
    if ink_pixels < INK_THRESHOLD:
        missing_fields.append("doctor_signature")

    return JSONResponse(content={"missing_fields": missing_fields})
