from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import torch
import scipy.io.wavfile
import soundfile as sf
import numpy as np
import io
import os
import threading
from scipy import signal
from transformers import SeamlessM4Tv2Model, AutoProcessor as SeamlessProcessor, Wav2Vec2ForCTC, AutoProcessor

# --- Global state ---
_tts_processor  = None
_tts_model      = None
_asr_processor  = None
_asr_model      = None
_device         = None
_lock           = threading.Lock()

TEMP_DIR        = "./temp"
TTS_OUTPUT      = os.path.join(TEMP_DIR, "tts_output.wav")
TTS_SAMPLE_RATE = 16000

os.makedirs(TEMP_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _tts_processor, _tts_model, _asr_processor, _asr_model, _device

    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {_device}")

    print("Loading TTS model (facebook/seamless-m4t-v2-large)...")
    _tts_processor = SeamlessProcessor.from_pretrained("facebook/seamless-m4t-v2-large")
    _tts_model     = SeamlessM4Tv2Model.from_pretrained("facebook/seamless-m4t-v2-large").to(_device).eval()
    print("TTS model ready.")

    print("Loading ASR model (facebook/mms-1b-all)...")
    _asr_processor = AutoProcessor.from_pretrained("facebook/mms-1b-all")
    _asr_model     = Wav2Vec2ForCTC.from_pretrained("facebook/mms-1b-all").to(_device).eval()
    _asr_processor.tokenizer.set_target_lang("eng")
    _asr_model.load_adapter("eng")
    print("ASR model ready.")

    print("\nServer ready. Listening on http://127.0.0.1:8766\n")
    yield


app = FastAPI(lifespan=lifespan)


class TTSRequest(BaseModel):
    text:       str
    speaker_id: int = 0


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/tts")
def tts(req: TTSRequest):
    if not req.text.strip():
        raise HTTPException(400, "text is required")

    if not _lock.acquire(blocking=False):
        raise HTTPException(503, "Server busy — a request is already in progress")
    try:
        inputs = _tts_processor(text=req.text, src_lang="eng", return_tensors="pt").to(_device)
        with torch.inference_mode():
            audio = _tts_model.generate(**inputs, tgt_lang="eng", speaker_id=req.speaker_id)[0].cpu().numpy().squeeze()

        scipy.io.wavfile.write(TTS_OUTPUT, rate=TTS_SAMPLE_RATE, data=audio)
        return {"status": "ok", "file": os.path.abspath(TTS_OUTPUT)}
    finally:
        _lock.release()


@app.post("/asr")
def asr(audio: UploadFile = File(...)):
    audio_bytes  = audio.file.read()
    if not audio_bytes:
        raise HTTPException(400, "Received empty audio file — recording may not have flushed yet")
    try:
        audio_array, sample_rate = sf.read(io.BytesIO(audio_bytes))
    except Exception:
        rate, data = scipy.io.wavfile.read(io.BytesIO(audio_bytes))
        audio_array = data.astype(np.float32) / np.iinfo(data.dtype).max if np.issubdtype(data.dtype, np.integer) else data.astype(np.float32)
        sample_rate = rate

    # Convert to mono
    if len(audio_array.shape) > 1:
        audio_array = audio_array.mean(axis=1)

    # Resample to 16kHz (required by MMS ASR)
    if sample_rate != 16000:
        num_samples = int(len(audio_array) * 16000 / sample_rate)
        audio_array = signal.resample(audio_array, num_samples)

    audio_array = audio_array.astype(np.float32)

    if not _lock.acquire(blocking=False):
        raise HTTPException(503, "Server busy — a request is already in progress")
    try:
        inputs = _asr_processor(audio_array, sampling_rate=16000, return_tensors="pt").to(_device)
        with torch.inference_mode():
            logits = _asr_model(**inputs).logits

        ids           = torch.argmax(logits, dim=-1)[0]
        transcription = _asr_processor.decode(ids)
        return {"text": transcription}
    finally:
        _lock.release()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8766)
