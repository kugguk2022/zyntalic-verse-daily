"""Claude's Verse Space: serves the entrance, the stage and the bundled sample.

The daily evolution lives in the dataset kugguk/zyntalic-verse-archive and is
read by the browser at runtime, so the Space evolves without redeploys.
Deployed from GitHub (kugguk2022/zyntalic-verse-daily, workflow deploy-space).
"""
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

SITE = Path(__file__).resolve().parent / "site"
app = FastAPI(title="Zyntalic Verse", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/", StaticFiles(directory=SITE, html=True), name="site")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
