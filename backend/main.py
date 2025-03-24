import os
import io
import zipfile
import pytesseract
import openai
from PIL import Image
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
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

@app.post("/process-stream/")
async def process_stream(files: list[UploadFile] = File(...)):
    print("==> Aloitetaan tiedostojen käsittely")
    texts = []
    for idx, file in enumerate(files):
        print(f"--> Käsitellään tiedosto: {file.filename}")
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        try:
            raw_text = pytesseract.image_to_string(image, lang="fin")
            print(f"    OCR-tunnistus valmis, tekstiä löytyi {len(raw_text)} merkkiä")
        except Exception as e:
            print(f"    OCR epäonnistui: {e}")
            raw_text = ""

        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Puhdista ja anonymisoi seuraava teksti: pidä henkilöiden nimet muodossa Henkilö 1, Henkilö 2 jne."},
                    {"role": "user", "content": raw_text}
                ]
            )
            cleaned_text = response.choices[0].message.content.strip()
            print(f"    OpenAI vastasi, pituus: {len(cleaned_text)} merkkiä")
        except Exception as e:
            print(f"    OpenAI-kutsu epäonnistui: {e}")
            cleaned_text = raw_text

        texts.append(f"{file.filename}\n\n{cleaned_text}\n\n{'='*40}\n")

    output_path = "processed_output.zip"
    with zipfile.ZipFile(output_path, "w") as zipf:
        zipf.writestr("processed.txt", "\n".join(texts))

    print("==> Kaikki tiedostot käsitelty ja tallennettu ZIP-tiedostoon")
    return FileResponse(output_path, media_type="application/x-zip-compressed", filename="processed_output.zip")

# Staattiset tiedostot frontendille
app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")
