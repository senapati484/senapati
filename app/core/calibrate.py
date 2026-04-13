import os
import json
import logging
import sounddevice as sd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

SENAPATI_HOME = os.path.expanduser("~/.senapati")
CONFIG_PATH = os.path.join(SENAPATI_HOME, "config.json")
NOISE_FLOOR_PATH = os.path.join(SENAPATI_HOME, ".noise_floor")


def record_audio(duration: float = 5.0, sample_rate: int = 16000) -> np.ndarray:
    """Record audio for noise calibration."""
    print(f"Calibrating... please stay silent for {int(duration)} seconds.")
    
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
    )
    
    sd.wait()
    
    return audio.flatten()


def calculate_rms_db(audio: np.ndarray) -> float:
    """Calculate RMS in dB."""
    rms = np.sqrt(np.mean(audio ** 2))
    
    if rms < 1e-10:
        return -100.0
    
    db = 20 * np.log10(rms)
    
    return db


def calibrate_noise_floor() -> float:
    """Calibrate noise floor for current environment."""
    noise_floor_db = -40.0
    
    print("Calibrating ambient noise level...")
    print("Please stay silent for 5 seconds.")
    
    audio = record_audio(duration=5.0)
    noise_floor_db = calculate_rms_db(audio)
    
    print(f"Measured noise floor: {noise_floor_db:.1f} dB")
    
    sensitivity = _map_noise_to_sensitivity(noise_floor_db)
    
    _save_noise_floor(noise_floor_db)
    _update_config_sensitivity(sensitivity)
    
    print(f"Calibrated. Wake sensitivity set to {sensitivity:.2f}")
    
    return sensitivity


def _map_noise_to_sensitivity(noise_floor_db: float) -> float:
    """
    Map noise floor to wake word sensitivity.
    
    -40dB (quiet room) → 0.8 sensitivity
    -30dB (moderate) → 0.7
    -20dB (busy office) → 0.6
    -10dB (loud) → 0.5
    """
    sensitivity = 0.8 - (noise_floor_db + 40) * 0.01
    
    return round(max(0.5, min(0.85, sensitivity)), 2)


def _save_noise_floor(db: float) -> None:
    """Save noise floor measurement."""
    with open(NOISE_FLOOR_PATH, "w") as f:
        f.write(f"{db}\n")


def get_noise_floor() -> float:
    """Get saved noise floor."""
    if os.path.exists(NOISE_FLOOR_PATH):
        try:
            with open(NOISE_FLOOR_PATH) as f:
                return float(f.read().strip())
        except:
            pass
    return -40.0


def _update_config_sensitivity(sensitivity: float) -> None:
    """Update config with calibrated sensitivity."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                config = json.load(f)
            
            config.setdefault("wake_sensitivity", sensitivity)
            config["wake_sensitivity"] = sensitivity
            
            with open(CONFIG_PATH, "w") as f:
                json.dump(config, f, indent=2)
        
        except Exception as e:
            logger.error(f"Failed to update config: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("Senapati Noise Calibration")
    print("=" * 50)
    print()
    print("This calibrates the wake word sensitivity for your environment.")
    print("A quieter room = higher sensitivity.")
    print()
    
    calibrate_noise_floor()
    
    print()
    print("Calibration complete!")