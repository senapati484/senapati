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
    """Get or load Piper voice."""
    global _model
    
    if _model is not None:
        return _model
    
    if not is_piper_available():
        return None
    
    model_path = os.path.join(SENAPATI_HOME, "models/piper/en_US-lessac-high.onnx")
    config_path = model_path + ".json"
    
    if not os.path.exists(model_path):
        logger.warning(f"Piper voice not found: {model_path}")
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
    length_scale: float = 0.95,
    sentence_silence: float = 0.2,
    blocking: bool = True,
) -> None:
    """
    Synthesize and play audio.
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