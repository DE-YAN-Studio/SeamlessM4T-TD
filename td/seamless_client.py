# Paste this into a single Script DAT named "seamless_client" in TouchDesigner.
# Call from anywhere in the network:
#
#   op('seamless_client').module.send_tts("Hello from TouchDesigner")
#   op('seamless_client').module.send_tts("Hello", speaker_id=5)
#   op('seamless_client').module.start_recording()
#   op('seamless_client').module.stop_and_transcribe()
#   op('seamless_client').module.check_server()
#
# Requirements:
#   - Audio File In CHOP named "tts_out" connected to an Audio Device Out CHOP
#   - Audio File Out CHOP named "mic_record" receiving audio from your Audio Device In CHOP
#     - Set its File parameter to the RECORD_FILE path below
#   - Text DAT named "asr_result" to display transcriptions
#   - The server must be running (start_server.bat)

import urllib.request
import json
import threading

SERVER_URL  = "http://127.0.0.1:8766"
TTS_CHOP    = "tts_out"
MIC_CHOP    = "mic_record"
RESULT_DAT  = "asr_result"
RECORD_FILE = "C:/Users/Zach/Desktop/Meta_AI/SeamlessM4T-TD/td/work/mic_input.wav"

_results = {}
_counter = 0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _post_json(endpoint, payload):
    url  = SERVER_URL + endpoint
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_file(endpoint, file_path):
    with open(file_path, "rb") as f:
        audio_data = f.read()

    boundary = "----MMS_BOUNDARY"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="audio"; filename="mic_input.wav"\r\n'
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode("utf-8") + audio_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        SERVER_URL + endpoint,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── TTS ───────────────────────────────────────────────────────────────────────

def send_tts(text, speaker_id=0):
    """
    Convert text to speech. Runs in a background thread — TD will not freeze.

    Parameters
    ----------
    text        : str — text to synthesize
    speaker_id  : int — voice ID 0–199 (default 0)
    """
    global _counter
    _counter += 1
    job_id    = _counter
    this_path = op(me).path

    def _worker():
        try:
            result = _post_json("/tts", {"text": text, "speaker_id": speaker_id})
            _results[job_id] = result
            run(f"op('{this_path}').module._finish_tts({job_id})", delayFrames=1)
        except Exception as e:
            print(f"[SeamlessM4T-TTS] Error: {e}")

    threading.Thread(target=_worker, daemon=True).start()


def _finish_tts(job_id):
    result = _results.pop(job_id, None)
    if result and result.get("status") == "ok":
        file_path = result["file"].replace("\\", "/")
        chop = op(TTS_CHOP)
        chop.par.file = file_path
        chop.par.reloadpulse.pulse()
        print(f"[SeamlessM4T-TTS] Playing audio.")


# ── ASR ───────────────────────────────────────────────────────────────────────

def start_recording():
    """Start recording from the microphone via the Record CHOP."""
    op(MIC_CHOP).par.record = 1
    print("[SeamlessM4T-ASR] Recording started...")


def stop_and_transcribe():
    """
    Stop recording and transcribe the audio. Runs in a background thread — TD will not freeze.
    Result is written to the Text DAT named asr_result.
    Waits a few frames after stopping so the Audio File Out CHOP can flush to disk.
    """
    op(MIC_CHOP).par.record = 0
    print("[SeamlessM4T-ASR] Recording stopped. Transcribing...")
    this_path = op(me).path
    run(f"op('{this_path}').module._dispatch_asr()", delayFrames=6)


def _dispatch_asr():
    global _counter
    _counter += 1
    job_id    = _counter
    this_path = op(me).path

    def _worker():
        try:
            result = _post_file("/asr", RECORD_FILE)
            _results[job_id] = result
            run(f"op('{this_path}').module._finish_asr({job_id})", delayFrames=1)
        except Exception as e:
            print(f"[SeamlessM4T-ASR] Error: {e}")

    threading.Thread(target=_worker, daemon=True).start()


def _finish_asr(job_id):
    result = _results.pop(job_id, None)
    if result:
        text = result.get("text", "")
        print(f"[SeamlessM4T-ASR] Transcription: {text}")
        try:
            op(RESULT_DAT).text = text
        except Exception:
            pass


# ── Utility ───────────────────────────────────────────────────────────────────

def check_server():
    """Check if the server is reachable."""
    try:
        url = SERVER_URL + "/health"
        with urllib.request.urlopen(url, timeout=5) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            print(f"[SeamlessM4T] Server status: {result}")
    except Exception as e:
        print(f"[SeamlessM4T] Server not reachable: {e}")
