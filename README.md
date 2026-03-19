# SeamlessM4T-TD

Local TTS and ASR server using Meta's SeamlessM4T v2 and MMS models, integrated with TouchDesigner.

## Models
- **TTS:** [facebook/seamless-m4t-v2-large](https://huggingface.co/facebook/seamless-m4t-v2-large) — natural sounding, 200 speaker voices
- **ASR:** [facebook/mms-1b-all](https://huggingface.co/facebook/mms-1b-all) — speech to text, 1100+ languages (English by default)

## Requirements
- Windows 10/11
- NVIDIA GPU (CUDA 12.4+)
- Anaconda or Miniconda
- TouchDesigner 2025

---

## Setup

1. Run `setup.bat` — creates the `seamless-td` conda environment and installs all dependencies
2. Run `start_server.bat` — activates the environment and starts the server
3. First launch downloads model weights (~2.3GB), subsequent launches are fast

---

## Server

Runs locally at `http://127.0.0.1:8766`

### Endpoints

#### `GET /health`
Check if the server is running.
```json
{ "status": "ok" }
```

#### `POST /tts`
Convert text to speech. Saves audio to `td/work/tts_output.wav`.

Request:
```json
{
  "text": "Hello from TouchDesigner",
  "speaker_id": 0
}
```
Response:
```json
{
  "status": "ok",
  "file": "C:\\...\\td\\work\\tts_output.wav"
}
```
- `speaker_id` ranges from 0–199. Each ID is a different voice (male/female, different accents). Default is `0`.

#### `POST /asr`
Transcribe an audio file. Accepts `multipart/form-data` with an `audio` field containing a `.wav` file.

Response:
```json
{ "text": "transcribed text here" }
```
- Audio is automatically converted to mono and resampled to 16kHz

---

## TouchDesigner Setup

Paste `td/seamless_client.py` into a single Script DAT named `seamless_client`. Call from anywhere in the network:

```python
op('seamless_client').module.send_tts("Hello!", speaker_id=0)
op('seamless_client').module.start_recording()
op('seamless_client').module.stop_and_transcribe()
op('seamless_client').module.check_server()
```

### Required Operators

| Operator | Type | Notes |
|---|---|---|
| `tts_out` | Audio File In CHOP | Connected to an Audio Device Out CHOP |
| *(any name)* | Audio Device In CHOP | Set to your microphone |
| `mic_record` | Record CHOP | Connected to mic, File set to `td/work/mic_input.wav` |
| `asr_result` | Text DAT | Displays transcription output |
| `seamless_client` | Script DAT | Paste contents of `td/seamless_client.py` |

---

## Files

| File | Description |
|---|---|
| `server.py` | FastAPI server — loads models and handles TTS/ASR requests |
| `setup.bat` | One-time setup — creates conda env and installs dependencies |
| `start_server.bat` | Start the server |
| `environment.yml` | Conda environment definition (`seamless-td`) |
| `td/seamless_client.py` | TouchDesigner client — paste into a Script DAT named `seamless_client` |
| `td/work/` | Temp audio I/O files |
