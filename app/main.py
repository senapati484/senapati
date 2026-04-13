#!/usr/bin/env python3
"""
Senapati - Local AI Assistant
"""

import os
import sys
import argparse
import logging
from datetime import datetime

SENAPATI_HOME = os.path.expanduser("~/.senapati")

# Create required directories
os.makedirs(SENAPATI_HOME, exist_ok=True)
os.makedirs(f"{SENAPATI_HOME}/logs", exist_ok=True)
os.makedirs(f"{SENAPATI_HOME}/cache", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(f"{SENAPATI_HOME}/logs/senapati.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Senapati - Local AI Assistant")
    
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as daemon (default)",
    )
    
    parser.add_argument(
        "--brief",
        action="store_true",
        help="Run morning brief",
    )
    
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Run terminal UI",
    )
    
    parser.add_argument(
        "--mini",
        action="store_true",
        help="Run minimal HUD mode",
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Voice input/output mode",
    )
    
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version",
    )
    
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Calibrate wake word sensitivity for environment",
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    if args.version:
        print("Senapati v0.1.0")
        return 0
    
    if args.calibrate:
        return run_calibrate()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Starting Senapati...")
    
    os.makedirs(SENAPATI_HOME, exist_ok=True)
    os.makedirs(f"{SENAPATI_HOME}/logs", exist_ok=True)
    os.makedirs(f"{SENAPATI_HOME}/cache", exist_ok=True)
    
    if args.brief:
        return run_brief()
    
    if args.tui:
        return run_tui()
    
    if args.mini:
        return run_mini()
    
    if args.voice:
        return run_voice()
    
    if args.daemon or (not args.tui and not args.brief):
        return run_daemon()
    
    return run_daemon()


def run_daemon():
    """Run as daemon."""
    logger.info("Running daemon...")
    
    try:
        from app.core import agent
        
        a = agent.get_agent()
        a.start()
        
        logger.info("Senapati is running. Say 'Hey Senapati' to activate.")
        logger.info("Press Ctrl+C to stop.")
        
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            a.stop()
    
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.info("Installing dependencies...")
        
        os.system(f"{SENAPATI_HOME}/venv/bin/pip install -r {SENAPATI_HOME}/requirements.txt")
        
        return 1
    
    return 0


def run_brief():
    """Run morning brief."""
    logger.info("Generating morning brief...")
    
    try:
        from app.core import agent
        
        a = agent.get_agent()
        return a.run_morning_brief()
    
    except Exception as e:
        logger.error(f"Brief failed: {e}")
        return 1


def run_tui():
    """Run terminal UI."""
    logger.info("Starting terminal UI...")
    
    try:
        from app.ui import tui
        
        tui.run_tui()
    
    except Exception as e:
        logger.error(f"UI failed: {e}")
        return 1


def run_mini():
    """Run minimal HUD mode."""
    logger.info("Running minimal HUD...")
    
    try:
        import psutil
        
        print(f"✨ Senapati | CPU: {psutil.cpu_percent()}% | RAM: {psutil.virtual_memory().percent}%")
        
        import time
        try:
            while True:
                time.sleep(1)
                print(f"✨ Senapati | CPU: {psutil.cpu_percent()}% | RAM: {psutil.virtual_memory().percent}%")
        except KeyboardInterrupt:
            pass
    
    except Exception as e:
        logger.error(f"Mini mode failed: {e}")
        return 1


def run_calibrate():
    """Calibrate wake word sensitivity."""
    logger.info("Running noise calibration...")
    
    try:
        from app.core import calibrate
        
        calibrate.calibrate_noise_floor()
        return 0
    
    except Exception as e:
        logger.error(f"Calibration failed: {e}")
        return 1


def run_voice():
    """Run in voice mode."""
    logger.info("Starting voice mode...")
    
    try:
        from app.core import voice_in, voice_out, agent
        
        a = agent.get_agent()
        
        def on_wake():
            logger.info("Wake word detected!")
            
            voice_in.record_audio(duration=5.0)
            
            audio_path = voice_in.record_audio(duration=3.0)
            user_input = voice_in.transcribe(audio_path)
            
            if user_input:
                response = a._process_input(user_input)
                
                speak = response.get("speak", "")
                if speak:
                    voice_out.speak(speak)
        
        voice_in.listen_for_wake(on_wake_detected=on_wake)
        
        logger.info("Voice mode active. Say 'Hey Senapati'...")
        
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            voice_in.stop_listening()
            logger.info("Voice mode stopped.")
    
    except Exception as e:
        logger.error(f"Voice mode failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())