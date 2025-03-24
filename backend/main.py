
import os
import zipfile
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import List
from PIL import Image
import pytesseract
import io
import openai
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
async def process_stream(files: List[UploadFile] = File(...)):
    print("🔵 Aloitetaan käsittely...")
    collected_texts = []

    for idx, file in enumerate(files):
        print(f"➡️ Käsitellään tiedosto {idx+1}/{len(files)}: {file.filename}")

        contents = await file.read()
        image = Image.open(io.BytesIO(contents))

        print("🔡 Suoritetaan OCR...")
        try:
            raw_text = pytesseract.image_to_string(image, lang="fin")
        except Exception as e:
            print(f"❌ OCR-virhe: {e}")
            raw_text = "[OCR epäonnistui]"

        prompt = (
            "Alla on teksti kuvankaappauksesta. Poista siitä nimet ja yksilöivät tiedot, "
            "ja stilisoi teksti luettavampaan muotoon:\n\n"
            f"{raw_text}\n\n"
            "Palauta ainoastaan muokattu teksti ilman lisäselityksiä."
        )

        print("🤖 Lähetetään ChatGPT:lle...")
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            cleaned_text = response.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ OpenAI-virhe: {e}")
            cleaned_text = "[Virhe OpenAI-käsittelyssä]"

        collected_texts.append(f"Tiedosto: {file.filename}\n{cleaned_text}\n{'-'*40}\n")

    print("📦 Luodaan ZIP-tiedosto...")
    output_path = "/tmp/output.zip"
    with zipfile.ZipFile(output_path, "w") as zipf:
        zipf.writestr("anonymisoitu_teksti.txt", "\n".join(collected_texts))

    print("✅ Valmis, palautetaan tiedosto.")
    return FileResponse(output_path, filename="anonymisoitu_teksti.zip", media_type="application/zip")

from fastapi.staticfiles import StaticFiles
app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")

