# Project Context

**SeamlessM4T-TD** — Local TTS and ASR server built for a Meta brand activation. Uses Meta/Facebook models exclusively via HuggingFace Transformers, integrated with TouchDesigner 2025.

## Key Constraint
All AI models must be from Meta/Facebook. Do not suggest or introduce models from other organizations (OpenAI, Google, Microsoft, etc.).

## Stack
- **Language:** Python 3.11
- **Environment:** Conda (`seamless-td`)
- **Server:** FastAPI + uvicorn on `http://127.0.0.1:8766`
- **GPU:** NVIDIA with CUDA 12.4 (driver 13.1)
- **Client:** TouchDesigner 2025 on Windows 11

## Models
- **TTS:** `facebook/seamless-m4t-v2-large` — supports ~200 speaker IDs (0–199)
- **ASR:** `facebook/mms-1b-all` — English, adapter-based, requires `set_target_lang("eng")` and `load_adapter("eng")`

## Architecture
- `server.py` loads both models once via FastAPI lifespan context manager
- Global state uses underscore-prefixed variables: `_tts_model`, `_asr_model`, `_tts_processor`, `_asr_processor`, `_device`, `_lock`
- `threading.Lock` prevents concurrent requests (single GPU, shared memory)
- `torch.inference_mode()` used for all inference (not `torch.no_grad()`)
- TD communicates over HTTP using stdlib `urllib` only (no third-party HTTP libs in TD)
- TD scripts use worker thread + `run()` callback pattern to avoid freezing TD
- Job tracking via `_counter` / `_results` dict in TD scripts

## Server API
| Method | Endpoint  | Description |
|--------|-----------|-------------|
| GET    | /health   | Returns `{"status": "ok"}` |
| POST   | /tts      | JSON body: `{"text": "...", "speaker_id": 0}` → saves to `temp/tts_output.wav` |
| POST   | /asr      | Multipart file upload (`audio` field, WAV) → returns `{"text": "..."}` |

## Audio Requirements
- ASR requires 16kHz mono float32 — resampling handled in `server.py` via `scipy.signal.resample`
- TTS output sample rate is 16000Hz

## TouchDesigner Operator Names
- `tts_out` — Audio File In CHOP for TTS playback
- `mic_record` — Record CHOP for mic input, file set to `td/work/mic_input.wav`
- `asr_result` — Text DAT for transcription output
- Reload audio CHOP with `chop.par.reloadpulse.pulse()`

## Code Patterns (match SAM-Audio conventions)
- Private functions/vars prefixed with underscore: `_post_json`, `_worker`, `_finish`, `_results`
- Config block at top of TD scripts: `SERVER_URL`, `TTS_CHOP`, etc.
- `_post_json(endpoint, payload)` helper for JSON requests in TD scripts
- `_post_file(endpoint, file_path)` helper for multipart uploads in TD scripts
- Pydantic `BaseModel` for all request validation
- `HTTPException(503, ...)` when server is busy, `HTTPException(400, ...)` for bad input
- Print log messages prefixed with `[MMS-TTS]` or `[MMS-ASR]`
