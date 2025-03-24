from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image
import pytesseract
import os
import shutil
import openai
from typing import List
import uuid
import zipfile

from dotenv import load_dotenv
load_dotenv()

from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")

TEMP_DIR = "temp_uploads"
RESULTS_DIR = "results"
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

@app.post("/process-stream/")
async def process_images_stream(files: List[UploadFile] = File(...)):
    texts = []
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(TEMP_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    for i, file in enumerate(files):
        file_location = os.path.join(session_dir, file.filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        image = Image.open(file_location)
        raw_text = pytesseract.image_to_string(image, lang="fin")

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Olet avustaja, joka stilisoi ja anonymisoi kuvankaappauksista poimitun tekstin."},
                {"role": "user", "content": raw_text},
            ]
        )

        styled_text = response.choices[0].message.content.strip()
        texts.append(styled_text)

    result_text = "\n\n---\n\n".join(texts)
    result_filename = f"result_{session_id}.txt"
    result_path = os.path.join(RESULTS_DIR, result_filename)

    with open(result_path, "w", encoding="utf-8") as f:
        f.write(result_text)

    # Pakkaa tulos zip-tiedostoksi
    zip_filename = f"result_{session_id}.zip"
    zip_path = os.path.join(RESULTS_DIR, zip_filename)
    with zipfile.ZipFile(zip_path, "w") as zipf:
        zipf.write(result_path, arcname=result_filename)

    return {"download_url": f"/download/{zip_filename}"}

@app.get("/download/{zip_filename}")
def download_result(zip_filename: str):
    return FileResponse(os.path.join(RESULTS_DIR, zip_filename), media_type='application/zip', filename=zip_filename)

@app.get("/")
def serve_index():
    return FileResponse("frontend/index.html")
