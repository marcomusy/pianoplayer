"""Minimal web API for upload -> annotate -> download workflow."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from pianoplayer import core
from pianoplayer.errors import PianoPlayerError

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {".xml", ".mxl", ".mid", ".midi", ".mscz", ".mscx", ".txt"}
VALID_HAND_SIZES = {"XXS", "XS", "S", "M", "L", "XL", "XXL"}
INDEX_HTML = Path(__file__).with_name("index.html")
IMAGES_DIR = Path(__file__).with_name("images")


def _allowed_origins() -> list[str]:
    raw = os.getenv("PIANOPLAYER_WEBAPI_ALLOW_ORIGINS", "*").strip()
    if not raw:
        return ["*"]
    return [item.strip() for item in raw.split(",") if item.strip()]


app = FastAPI(title="PianoPlayer Web API", version="1.0.0")
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    """Serve the minimal upload/download frontend."""
    return HTMLResponse(INDEX_HTML.read_text(encoding="utf-8"))


@app.post("/annotate")
async def annotate(
    file: UploadFile = File(...),
    hand_size: str = Form("M"),
    depth: int = Form(0),
    n_measures: int = Form(1000),
    start_measure: int = Form(1),
    left_only: bool = Form(False),
    right_only: bool = Form(False),
    below_beam: bool = Form(False),
    rbeam: int = Form(0),
    lbeam: int = Form(1),
    chord_note_stagger_s: float = Form(0.05),
) -> Response:
    """Run PianoPlayer on an uploaded score and return annotated MusicXML bytes."""
    incoming_name = file.filename or "score.xml"
    suffix = Path(incoming_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported extension '{suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    hand_size = hand_size.upper()
    if hand_size not in VALID_HAND_SIZES:
        raise HTTPException(status_code=400, detail=f"Invalid hand_size '{hand_size}'")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Input file too large ({len(content)} bytes). Max is {MAX_UPLOAD_BYTES} bytes.",
        )

    try:
        with TemporaryDirectory(prefix="pianoplayer_webapi_") as tmpdir:
            tmp = Path(tmpdir)
            input_path = tmp / f"input{suffix}"
            output_path = tmp / "annotated.xml"
            input_path.write_bytes(content)

            def _run_annotate() -> None:
                core.run_annotate(
                    filename=str(input_path),
                    outputfile=str(output_path),
                    n_measures=max(1, int(n_measures)),
                    start_measure=max(1, int(start_measure)),
                    depth=max(0, int(depth)),
                    rbeam=max(0, int(rbeam)),
                    lbeam=max(0, int(lbeam)),
                    quiet=True,
                    musescore=False,
                    below_beam=bool(below_beam),
                    with_vedo=False,
                    sound_off=True,
                    left_only=bool(left_only),
                    right_only=bool(right_only),
                    hand_size=hand_size,
                    chord_note_stagger_s=max(0.0, float(chord_note_stagger_s)),
                )

            await run_in_threadpool(_run_annotate)

            if not output_path.exists():
                raise HTTPException(
                    status_code=500,
                    detail="Annotation finished with no output file.",
                )

            output_bytes = output_path.read_bytes()
    except (PianoPlayerError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Annotation failed with unexpected error.")
        raise HTTPException(status_code=500, detail="Internal server error.") from exc

    base_name = Path(incoming_name).stem or "annotated"
    download_name = f"{base_name}_annotated.xml"
    headers = {"Content-Disposition": f'attachment; filename="{download_name}"'}
    return Response(
        content=output_bytes,
        media_type="application/vnd.recordare.musicxml+xml",
        headers=headers,
    )


def main() -> None:
    """Run local development server."""
    import uvicorn

    uvicorn.run("webapi.app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
