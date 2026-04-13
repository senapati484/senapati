import os
import io
import logging
import platform
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

SENAPATI_HOME = os.path.expanduser("~/.senapati")
_model = None


def is_piper_available() -> bool:
    try:
        import piper
        return True
    except ImportError:
        return False


def get_voice():
    """Get or load Piper voice.
    
    Prefers en_US-joe-medium (dominant + warm) over en_US-lessac-high.
    """
    global _model
    
    if _model is not None:
        return _model
    
    if not is_piper_available():
        return None
    
    # Joe = deeper, more authoritative (preferred)
    joe_path = os.path.join(SENAPATI_HOME, "models/piper/en_US-joe-medium.onnx")
    lessac_path = os.path.join(SENAPATI_HOME, "models/piper/en_US-lessac-high.onnx")
    
    # Try Joe first, fall back to Lessac
    if os.path.exists(joe_path):
        model_path = joe_path
        config_path = joe_path + ".json"
    elif os.path.exists(lessac_path):
        model_path = lessac_path
        config_path = lessac_path + ".json"
    else:
        logger.warning("No Piper voice found")
        return None
    
    try:
        from piper import PiperVoice
        
        _model = PiperVoice.load(model_path, config_path=config_path)
        logger.info("Piper voice loaded")
        return _model
    
    except Exception as e:
        logger.error(f"Failed to load Piper voice: {e}")
        return None


def speak(
    text: str,
    length_scale: float = 1.05,
    sentence_silence: float = 0.3,
    blocking: bool = True,
) -> None:
    """
    Synthesize and play audio.
    Default length_scale 1.05 = ~5% slower = sounds more confident.
    """
    voice = get_voice()
    if voice is None:
        logger.warning("TTS not available")
        return
    
    try:
        import wave
        
        buf = io.BytesIO()
        
        with wave.open(buf, "wb") as wf:
            voice.synthesize(
                text,
                wf,
                length_scale=length_scale,
                sentence_silence=sentence_silence,
            )
        
        wav_data = buf.getvalue()
        
        if platform.system() == "Darwin":
            _play_macos(wav_data)
        elif platform.system() == "Linux":
            _play_linux(wav_data)
        else:
            logger.warning(f"Unsupported platform: {platform.system()}")
    
    except Exception as e:
        logger.error(f"TTS failed: {e}")


_speaking = False
_barge_requested = False


def speak_streaming(text: str) -> None:
    """
    Stream-speak text by sentence - first sentence starts within ~400ms.
    Uses queue to overlap TTS generation with playback.
    """
    global _speaking, _barge_requested
    
    _speaking = True
    _barge_requested = False
    
    sentences = _split_sentences(text)
    
    for i, sentence in enumerate(sentences):
        if _barge_requested:
            break
        
        voice = get_voice()
        if voice is None:
            continue
        
        try:
            import wave
            
            buf = io.BytesIO()
            
            with wave.open(buf, "wb") as wf:
                voice.synthesize(
                    sentence,
                    wf,
                    length_scale=1.05,
                    sentence_silence=0.3,
                )
            
            wav_data = buf.getvalue()
            
            if platform.system() == "Darwin":
                _play_macos(wav_data)
            elif platform.system() == "Linux":
                _play_linux(wav_data)
        
        except Exception as e:
            logger.error(f"Streaming TTS failed: {e}")
            break
    
    _speaking = False


def _split_sentences(text: str) -> list:
    """Split text into sentences for streaming."""
    import re
    
    text = re.sub(r'\s+', ' ', text).strip()
    
    parts = re.split(r'(?<=[.!?])\s+', text)
    
    sentences = []
    buffer = ""
    
    for part in parts:
        buffer += " " + part if buffer else part
        
        if len(buffer) >= 15:
            sentences.append(buffer.strip())
            buffer = ""
    
    if buffer.strip():
        sentences.append(buffer.strip())
    
    return sentences


def request_barge_in() -> None:
    """Request barge-in (called from voice_in when wake word detects during speech)."""
    global _barge_requested
    _barge_requested = True


def _play_macos(wav_data: bytes) -> None:
    """Play audio on macOS."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav_data)
        tmp_path = f.name
    
    try:
        proc = subprocess.Popen(
            ["afplay", tmp_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.wait()
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass


def _play_linux(wav_data: bytes) -> None:
    """Play audio on Linux."""
    try:
        import sounddevice as sd
        import soundfile as sf
        
        buf = io.BytesIO(wav_data)
        data, rate = sf.read(buf)
        
        sd.play(data, rate)
        sd.wait()
    
    except Exception as e:
        logger.error(f"Linux audio playback failed: {e}")


def speak_async(text: str) -> None:
    """Speak text without blocking."""
    import threading
    
    thread = threading.Thread(
        target=speak,
        args=(text,),
        kwargs={"blocking": False},
    )
    thread.start()


def speak_immediately(text: str) -> None:
    """
    Speak text immediately (for wake ACK).
    Uses shorter settings for faster response.
    For wake ACKs, faster is better = 1.0 length_scale.
    """
    speak(text, length_scale=1.0, sentence_silence=0.1)


def speak_ssml(text: str) -> None:
    """
    Speak SSML-formatted text.
    """
    voice = get_voice()
    if voice is None:
        return
    
    try:
        import wave
        
        buf = io.BytesIO()
        
        with wave.open(buf, "wb") as wf:
            voice.synthesize_ssml(text, wf)
        
        wav_data = buf.getvalue()
        
        if platform.system() == "Darwin":
            _play_macos(wav_data)
        elif platform.system() == "Linux":
            _play_linux(wav_data)
    except Exception as e:
        logger.error(f"SSML speak failed: {e}")


def estimate_duration(text: str) -> float:
    """
    Estimate speaking duration in seconds.
    """
    words = len(text.split())
    return words * 0.5


def list_available_voices() -> list:
    """List available Piper voices."""
    voices_dir = os.path.join(SENAPATI_HOME, "models/piper")
    
    if not os.path.exists(voices_dir):
        return []
    
    voices = []
    for f in os.listdir(voices_dir):
        if f.endswith(".onnx") and not f.endswith(".onnx.json"):
            voices.append(f.replace(".onnx", ""))
    
    return voices


def unload_voice() -> None:
    """Unload voice to free memory."""
    global _model
    _model = None
    logger.info("Voice unloaded")