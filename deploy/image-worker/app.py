"""Small authenticated bridge from the local beta to Vertex image generation."""
import base64
import io
import os
import secrets

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from PIL import Image

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=10, max_length=6000)
    refs: list[str] = Field(default_factory=list, max_length=2)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/generate")
async def generate(body: GenerateRequest, authorization: str | None = Header(default=None)):
    expected = os.environ.get("WORKER_TOKEN", "")
    supplied = (authorization or "").removeprefix("Bearer ")
    if not expected or not secrets.compare_digest(supplied, expected):
        raise HTTPException(401, "Image worker authorization failed")

    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    if not project:
        raise HTTPException(503, "Cloud project is not configured")

    parts = [body.prompt]
    for encoded in body.refs:
        try:
            data = base64.b64decode(encoded, validate=True)
            if len(data) > 5_000_000:
                raise ValueError("Reference image exceeds 5 MB")
            with Image.open(io.BytesIO(data)) as image:
                mime_type = Image.MIME.get(image.format, "image/png")
                image.verify()
            parts.append(types.Part.from_bytes(data=data, mime_type=mime_type))
        except Exception as exc:
            raise HTTPException(400, "Invalid reference image") from exc

    try:
        provider = genai.Client(vertexai=True, project=project,
                                location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"))
        async with provider.aio as client:
            result = await client.models.generate_content(
                model=os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image"),
                contents=parts,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio="9:16", image_size="1K")),
            )
        for part in result.parts or []:
            if part.inline_data and part.inline_data.data:
                return {"image_base64": base64.b64encode(part.inline_data.data).decode("ascii"),
                        "mime_type": part.inline_data.mime_type or "image/png"}
    except Exception as exc:
        message = str(exc).lower()
        if "quota" in message or "429" in message:
            raise HTTPException(429, "Vertex image quota reached; retry later") from exc
        if "403" in message or "permission" in message:
            raise HTTPException(503, "Vertex image access denied for worker identity") from exc
        raise HTTPException(502, "Vertex image request failed") from exc
    raise HTTPException(502, "Vertex returned no image")
