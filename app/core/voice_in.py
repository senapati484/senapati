import os
import logging
import threading
import queue
from typing import Optional, Callable

logger = logging.getLogger(__name__)

SENAPATI_HOME = os.path.expanduser("~/.senapati")

_oww_model = None
_whisper_model = None
_audio_buffer = queue.Queue()
_listen_thread = None
_stop_event = threading.Event()

AUDIO_SAMPLE_RATE = 16000
AUDIO_CHUNK_SIZE = 1024
SILENCE_THRESHOLD = 500
SILENCE_DURATION_MS = 1200


def is_openwakeword_available() -> bool:
    try:
        import openwakeword
        return True
    except ImportError:
        return False


def is_faster_whisper_available() -> bool:
    try:
        import faster_whisper
        return True
    except ImportError:
        return False


def get_audio_device() -> Optional[int]:
    """Get default audio input device index."""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        if devices:
            # Find the first input device
            for i, dev in enumerate(devices):
                if isinstance(dev, dict):
                    if dev.get('max_input_channels', 0) > 0:
                        logger.info(f"Using audio device {i}: {dev.get('name', 'unknown')}")
                        return i
                elif dev.get('max_input_channels', 0) > 0:
                    logger.info(f"Using audio device {i}")
                    return i
            # Fallback to default input device
            default = sd.query_devices(kind='input')
            if default:
                for i, dev in enumerate(devices):
                    if dev == default:
                        return i
    except Exception as e:
        logger.warning(f"Error querying audio devices: {e}")
    return None


def load_wakeword_model(
    model_path: str = "~/.senapati/models/hey_senapati.tflite",
    threshold: float = 0.5,
) -> bool:
    """
    Load the wake word model.
    Tries multiple fallback paths if the primary model doesn't exist.
    """
    global _oww_model

    if _oww_model is not None:
        return True

    if not is_openwakeword_available():
        logger.warning("openwakeword not available")
        return False

    # Try paths in order of preference
    model_paths_to_try = [
        os.path.expanduser("~/.senapati/models/hey_mycroft_v0.1.onnx"),
        os.path.expanduser("~/.senapati/models/hey_jarvis_v0.1.onnx"),
        os.path.expanduser("~/.senapati/models/alexa_v0.1.onnx"),
    ]

    # Also check for models bundled with openwakeword package
    try:
        import openwakeword
        pkg_models_dir = os.path.join(os.path.dirname(openwakeword.__file__), "resources", "models")
        if os.path.exists(pkg_models_dir):
            for f in os.listdir(pkg_models_dir):
                if f.endswith(".onnx") and f not in ["melspectrogram.onnx", "embedding_model.onnx", "silero_vad.onnx", "weather_v0.1.onnx"]:
                    model_paths_to_try.append(os.path.join(pkg_models_dir, f))
    except Exception as e:
        logger.warning(f"Could not check package models: {e}")

    model_path_to_use = None
    for path in model_paths_to_try:
        if os.path.exists(path):
            model_path_to_use = path
            logger.info(f"Found wake word model: {path}")
            break

    if model_path_to_use is None:
        logger.warning("No wake word model found")
        return False

    try:
        from openwakeword.model import Model

        _oww_model = Model(
            wakeword_models=[model_path_to_use],
            inference_framework="onnx",
            vad_threshold=threshold  # Pass threshold at construction time
        )
        logger.info(f"Wake word model loaded: {model_path_to_use}")
        return True

    except Exception as e:
        logger.error(f"Failed to load wake word model: {e}")
        return False


def load_stt_model(model_size: str = "small") -> bool:
    """
    Load the speech-to-text model.
    """
    global _whisper_model

    if _whisper_model is not None:
        return True

    if not is_faster_whisper_available():
        logger.warning("faster-whisper not available")
        return False

    try:
        from faster_whisper import WhisperModel

        _whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
        logger.info(f"STT model loaded: {model_size}")
        return True

    except Exception as e:
        logger.error(f"Failed to load STT model: {e}")
        return False


def listen_for_wake(
    on_wake_detected: Optional[Callable] = None,
    phrase: str = "hey senapati",
) -> None:
    """
    Listen for wake word in background thread.
    Calls on_wake_detected callback when wake word is detected.
    """
    global _listen_thread, _stop_event

    if not is_openwakeword_available():
        logger.error("openwakeword not available")
        return

    if not load_wakeword_model():
        logger.error("Wake word model not loaded")
        return

    _stop_event.clear()
    _listen_thread = threading.Thread(
        target=_wake_loop,
        args=(on_wake_detected, phrase),
        daemon=True,
    )
    _listen_thread.start()
    logger.info("Wake word listening started")


def _wake_loop(on_wake_detected: Optional[Callable], phrase: str) -> None:
    """
    Background loop that listens for wake word.
    """
    import sounddevice as sd
    import numpy as np

    try:
        device = get_audio_device()

        if device is None:
            logger.error("No audio input device found")
            return

        logger.info(f"Opening audio stream on device {device}")

        with sd.InputStream(
            samplerate=AUDIO_SAMPLE_RATE,
            blocksize=AUDIO_CHUNK_SIZE,
            device=device,
            channels=1,
            dtype="int16",
        ) as stream:
            logger.info(f"Listening for wake word...")

            consecutive_detections = 0
            detection_threshold = 3  # Need 3 consecutive detections

            while not _stop_event.is_set():
                try:
                    audio_chunk, _ = stream.read(AUDIO_CHUNK_SIZE)

                    # Flatten to 1D if needed (sounddevice returns 2D array with shape (n, 1))
                    if len(audio_chunk.shape) > 1:
                        audio_chunk = audio_chunk.flatten()

                    if _oww_model:
                        predictions = _oww_model.predict(audio_chunk)

                        # Check for any wake word detection above threshold
                        wake_detected = False
                        for wp_name, score in predictions.items():
                            if score > 0.5:  # Threshold for wake word detection
                                logger.info(f"Wake word detected: {wp_name} ({score:.3f})")
                                wake_detected = True
                                consecutive_detections += 1
                                break

                        if wake_detected and consecutive_detections >= detection_threshold:
                            consecutive_detections = 0
                            if on_wake_detected:
                                on_wake_detected()
                        elif not wake_detected:
                            consecutive_detections = 0

                except Exception as e:
                    logger.warning(f"Audio chunk error: {e}")
                    continue

    except Exception as e:
        logger.error(f"Wake loop error: {e}")
        import traceback
        traceback.print_exc()


def stop_listening() -> None:
    """Stop listening for wake word."""
    global _stop_event

    _stop_event.set()
    if _listen_thread:
        _listen_thread.join(timeout=2)
        _listen_thread = None

    logger.info("Stopped listening for wake word")


def transcribe(audio_path: str) -> str:
    """
    Transcribe audio file to text.
    """
    if not load_stt_model():
        return ""

    try:
        segments, info = _whisper_model.transcribe(
            audio_path,
            beam_size=5,
            vad_filter=True,
        )

        text = " ".join([seg.text for seg in segments]).strip()
        logger.info(f"Transcribed: {text[:50]}...")
        return text

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return ""


def transcribe_stream(
    audio_chunk: bytes,
    sample_rate: int = AUDIO_SAMPLE_RATE,
) -> str:
    """
    Transcribe streaming audio.
    """
    if not load_stt_model():
        return ""

    try:
        import io
        import numpy as np
        from faster_whisper import decode_audio

        audio_io = io.BytesIO(audio_chunk)
        audio = np.frombuffer(audio_io.read(), dtype=np.int16)
        audio = audio.astype(np.float32) / 32768.0

        segments, info = _whisper_model.transcribe(
            audio,
            beam_size=5,
        )

        text = " ".join([seg.text for seg in segments]).strip()
        return text

    except Exception as e:
        logger.error(f"Streaming transcription failed: {e}")
        return ""


def record_audio(
    duration: float = 5.0,
    sample_rate: int = AUDIO_SAMPLE_RATE,
) -> str:
    """
    Record audio to temporary file and return path.
    """
    import sounddevice as sd
    import tempfile

    try:
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
        )

        sd.wait()

        import soundfile as sf

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sf.write(f.name, audio, sample_rate)
            return f.name

    except Exception as e:
        logger.error(f"Audio recording failed: {e}")
        return ""


def detect_silence(audio_chunk: bytes) -> bool:
    """
    Detect if audio chunk is silence.
    """
    import array
    import math

    samples = array.array("h", audio_chunk)
    rms = math.sqrt(sum(s * s for s in samples) / len(samples))

    return rms < SILENCE_THRESHOLD


def preprocess_audio(audio_path: str) -> str:
    """
    Preprocess audio file (normalize, trim silence).
    """
    try:
        import soundfile as sf
        import numpy as np

        audio, sr = sf.read(audio_path)

        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        energy = np.abs(audio)
        threshold = np.mean(energy) * 0.01

        non_silent = np.where(energy > threshold)[0]
        if len(non_silent) > 0:
            start = max(0, non_silent[0] - int(0.1 * sr))
            end = min(len(audio), non_silent[-1] + int(0.2 * sr))
            audio = audio[start:end]

        output_path = audio_path.replace(".wav", "_processed.wav")
        sf.write(output_path, audio, sr)

        return output_path

    except Exception as e:
        logger.error(f"Audio preprocessing failed: {e}")
        return audio_path
