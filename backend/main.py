import io
import base64
import re
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from PIL import Image
import zipfile
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")


def encode_image_to_base64(image: Image.Image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def call_gpt4_vision(base64_image: str):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Lue kuvasta teksti ja anonymisoi se. Korvaa nimet muotoon Henkilö 1, Henkilö 2 jne. Palauta pelkkä puhdistettu teksti."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "auto"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Vision-API epäonnistui: {e}"


@app.post("/process-stream/")
async def process_images(files: list[UploadFile] = File(...)):
    print("==> Aloitetaan tiedostojen käsittely")
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for index, file in enumerate(files):
            print(f"--> Käsitellään tiedosto: {file.filename}")
            image = Image.open(io.BytesIO(await file.read())).convert("RGB")

            base64_image = encode_image_to_base64(image)
            processed_text = call_gpt4_vision(base64_image)

            # Puhdistetaan teksti
            cleaned_text = re.sub(r"(PK.*|I'm sorry, I can't help with that\.|[^ -~\nÄÖäöÅå€—•“”’‘])", "", processed_text)
            cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text.strip())  # ylimääräiset tyhjät rivit

            print(f"    OpenAI vastasi, pituus: {len(cleaned_text)} merkkiä")

            name = f"kuva_{index + 1}.txt"
            zip_file.writestr(name, cleaned_text)

    zip_buffer.seek(0)
    print("==> Kaikki tiedostot käsitelty ja tallennettu ZIP-tiedostoon")
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": "attachment; filename=analyysi.zip"}
    )


@app.get("/")
async def serve_frontend():
    try:
        with open("frontend/index.html", encoding="utf-8") as f:
            html = f.read()
        return HTMLResponse(content=html, status_code=200)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
