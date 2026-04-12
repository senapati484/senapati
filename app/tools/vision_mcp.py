import os
import platform
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _ocr(img) -> str:
    """Perform OCR on image - cross-platform."""
    if platform.system() == "Darwin":
        return _ocr_macos(img)
    else:
        return _ocr_linux(img)


def _ocr_macos(img) -> str:
    """OCR using macOS Vision framework (built-in, no extra deps)."""
    try:
        from ocrmac import ocrmac
        results = ocrmac.text_from_image(img)
        if not results:
            return "No text found on screen."
        return "\n".join([r[0] for r in results])
    except ImportError:
        return _ocr_pytesseract(img)
    except Exception as e:
        return f"Error: {e}"


def _ocr_linux(img) -> str:
    """OCR using EasyOCR."""
    try:
        import easyocr
        if not hasattr(_ocr_linux, "_reader"):
            _ocr_linux._reader = easyocr.Reader(["en"], verbose=False)
        results = _ocr_linux._reader.readtext(img)
        if not results:
            return "No text found on screen."
        return " ".join([r[1] for r in results])
    except ImportError:
        return _ocr_pytesseract(img)
    except Exception as e:
        return f"Error: {e}"


def _ocr_pytesseract(img) -> str:
    """Fallback OCR using pytesseract."""
    try:
        import pytesseract
        text = pytesseract.image_to_string(img)
        return text.strip() if text.strip() else "No text found."
    except ImportError:
        return "OCR not available. Install ocrmac (macOS) or easyocr (Linux)."


def read_screen() -> str:
    """Take a screenshot and extract all text via OCR."""
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        return _ocr(img).strip()
    except Exception as e:
        logger.error(f"Screen read failed: {e}")
        return f"Error: {e}"


def find_text_on_screen(query: str) -> bool:
    """Check if specific text is visible on screen."""
    try:
        text = read_screen()
        return query.lower() in text.lower()
    except Exception as e:
        logger.error(f"Text search failed: {e}")
        return False


def find_text_on_screen(query: str) -> bool:
    """Check if specific text is visible on screen."""
    try:
        text = read_screen()
        
        return query.lower() in text.lower()
    
    except Exception as e:
        logger.error(f"Text search failed: {e}")
        return False


def describe_screen() -> str:
    """Read screen and describe what's visible."""
    try:
        text = read_screen()
        
        if not text or text.startswith("Error"):
            return "Your screen appears to be empty or OCR failed."
        
        lines = text.split("\n")
        
        if not lines:
            return "Nothing notable on screen."
        
        desc_parts = []
        
        for line in lines[:5]:
            line = line.strip()
            if line:
                desc_parts.append(line)
        
        if desc_parts:
            return "On your screen: " + ", ".join(desc_parts[:3])
        
        return "Your screen shows a blank or unreadable area."
    
    except Exception as e:
        logger.error(f"Screen description failed: {e}")
        return f"Error: {e}"


def save_screenshot(path: str = "") -> str:
    """Save screenshot to file."""
    try:
        from PIL import ImageGrab
        
        if not path:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            senapati_home = os.path.expanduser("~/.senapati")
            cache_dir = os.path.join(senapati_home, "cache/screenshots")
            os.makedirs(cache_dir, exist_ok=True)
            path = os.path.join(cache_dir, f"screenshot_{timestamp}.png")
        
        img = ImageGrab.grab()
        img.save(path)
        
        return f"Saved to {path}"
    
    except Exception as e:
        return f"Error: {e}"


def get_screen_region(x: int, y: int, width: int, height: int) -> str:
    """Capture and OCR a specific screen region."""
    try:
        from PIL import ImageGrab
        
        bbox = (x, y, x + width, y + height)
        img = ImageGrab.grab(bbox=bbox)
        
        return _ocr(img)
    
    except Exception as e:
        return f"Error: {e}"


def get_clickable_elements() -> list:
    """Get list of clickable elements on screen."""
    try:
        text = read_screen()
        
        elements = []
        
        keywords = ["button", "link", "click", "https://", "http://", ".com", ".org"]
        
        for line in text.split("\n"):
            line = line.strip().lower()
            
            for kw in keywords:
                if kw in line:
                    elements.append(line)
                    break
        
        return elements[:10]
    
    except Exception as e:
        return []


def detect_screen_content_type() -> str:
    """Detect what type of content is on screen."""
    try:
        text = read_screen().lower()
        
        if not text:
            return "empty"
        
        if any(kw in text for kw in ["error", "exception", "failed"]):
            return "error"
        
        if any(kw in text for kw in ["def ", "class ", "import ", "function"]):
            return "code"
        
        if any(kw in text for kw in ["https://", "http://", "<html", "<div"]):
            return "webpage"
        
        if any(kw in text for kw in ["email", "from:", "subject:"]):
            return "email"
        
        if any(kw in text for kw in ["terminal", "command", "$", "~"]):
            return "terminal"
        
        return "unknown"
    
    except Exception as e:
        return "error"