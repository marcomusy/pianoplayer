# PianoPlayer Web API (MVP)

Minimal browser flow:
1. Upload score file (`.xml`, `.mxl`, `.mid`, `.midi`, `.mscz`, `.mscx`, `.txt`)
2. Run pianoplayer on the server
3. Download annotated MusicXML output

## Run locally

```bash
pip install "pianoplayer[web]"
uvicorn webapi.app:app --host 127.0.0.1 --port 8000
```

Open:
- http://127.0.0.1:8000

## API

- `GET /health` -> `{"status":"ok"}`
- `POST /annotate` (multipart form-data)
  - required: `file`
  - optional: `hand_size`, `depth`, `n_measures`, `start_measure`,
    `left_only`, `right_only`, `below_beam`, `rbeam`, `lbeam`,
    `chord_note_stagger_s`

Response:
- annotated MusicXML file as an attachment (`*_annotated.xml`)
