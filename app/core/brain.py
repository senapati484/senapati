import os
import json
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

SENAPATI_HOME = os.path.expanduser("~/.senapati")
MODEL_PATH = os.path.join(SENAPATI_HOME, "models/qwen3-2.5b-mlx")
DRAFT_MODEL_PATH = os.path.join(SENAPATI_HOME, "models/qwen3-0.5b-mlx")

_model = None
_tokenizer = None
_draft_model = None
_draft_tokenizer = None
_use_speculative = False


def is_mlx_available() -> bool:
    try:
        import mlx_lm
        return True
    except ImportError:
        return False


def is_llama_available() -> bool:
    try:
        import llama_cpp
        return True
    except ImportError:
        return False


def load_models(speculative: bool = False) -> bool:
    """
    Load the main model (and optionally draft model for speculative decoding).
    Returns True on success, False on failure.
    """
    global _model, _tokenizer, _draft_model, _draft_tokenizer, _use_speculative
    
    if _model is not None:
        return True
    
    if is_mlx_available():
        try:
            from mlx_lm import load, generate
            
            logger.info(f"Loading main model from {MODEL_PATH}")
            _model, _tokenizer = load(MODEL_PATH)
            
            if speculative and os.path.exists(DRAFT_MODEL_PATH):
                logger.info(f"Loading draft model from {DRAFT_MODEL_PATH}")
                _draft_model, _draft_tokenizer = load(DRAFT_MODEL_PATH)
                _use_speculative = True
            
            logger.info("Models loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load MLX model: {e}")
            _model = None
    
    elif is_llama_available():
        try:
            from llama_cpp import Llama
            
            logger.info(f"Loading GGUF model from {MODEL_PATH}")
            model_path = os.path.join(MODEL_PATH, "*.gguf")
            
            for f in os.listdir(MODEL_PATH) if os.path.exists(MODEL_PATH) else []:
                if f.endswith(".gguf"):
                    model_path = os.path.join(MODEL_PATH, f)
                    break
            
            _model = Llama(model_path, n_ctx=2048, n_threads=4)
            logger.info("GGUF model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load GGUF model: {e}")
            _model = None
    
    return False


def unload_models():
    """Unload models to free memory."""
    global _model, _tokenizer, _draft_model, _draft_tokenizer
    
    _model = None
    _tokenizer = None
    _draft_model = None
    _draft_tokenizer = None
    
    if is_mlx_available():
        try:
            import mlx_lm
            mlx_lm.flush_cache()
        except:
            pass
    
    logger.info("Models unloaded")


def generate(
    prompt: str,
    max_tokens: int = 256,
    temp: float = 0.1,
    repeat_penalty: float = 1.1,
    cache_prompt: bool = True,
) -> str:
    """
    Generate a response from the model.
    """
    if _model is None:
        if not load_models():
            return json.dumps({"tool": "chat", "args": {}, "speak": "Model not loaded. Run setup first."})
    
    try:
        if is_mlx_available():
            from mlx_lm import generate as mlx_generate
            
            if _use_speculative and _draft_model is not None:
                response = mlx_generate(
                    _model,
                    _tokenizer,
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temp=temp,
                    repetition_penalty=repeat_penalty,
                    draft=_draft_model,
                    draft_retries=2,
                )
            else:
                response = mlx_generate(
                    _model,
                    _tokenizer,
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temp=temp,
                    repetition_penalty=repeat_penalty,
                )
            return response
        
        elif is_llama_available():
            response = _model(
                prompt,
                max_tokens=max_tokens,
                temperature=temp,
                repeat_penalty=repeat_penalty,
                echo=cache_prompt,
            )
            return response["choices"][0]["text"]
    
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return json.dumps({
            "tool": "chat",
            "args": {},
            "speak": f"Got confused — {str(e)[:50]}"
        })


def generate_step(prompt: str, max_tokens: int = 256) -> str:
    """
    Generate response token by token (for streaming).
    """
    if _model is None:
        if not load_models():
            return ""
    
    try:
        if is_mlx_available():
            from mlx_lm.utils import generate_step as mlx_generate_step
            
            kwargs = {
                "model": _model,
                "tokenizer": _tokenizer,
                "prompt": prompt,
                "max_tokens": max_tokens,
            }
            
            if _use_speculative and _draft_model is not None:
                kwargs["draft"] = _draft_model
                kwargs["draft_tokenizer"] = _draft_tokenizer
            
            for token in mlx_generate_step(**kwargs):
                yield token
        
        else:
            response = generate(prompt, max_tokens)
            yield response
    
    except Exception as e:
        logger.error(f"Step generation failed: {e}")
        yield ""


def embed(text: str) -> List[float]:
    """
    Generate embeddings for text using the embedding model.
    """
    embed_model_path = os.path.join(SENAPATI_HOME, "models/nomic-embed-mlx")
    
    if not os.path.exists(embed_model_path):
        logger.warning(f"Embed model not found at {embed_model_path}")
        return [0.0] * 768
    
    try:
        if is_mlx_available():
            from mlx_lm import load
            
            model, tokenizer = load(embed_model_path)
            
            if hasattr(tokenizer, 'encode'):
                ids = tokenizer.encode(text)
            else:
                ids = tokenizer(text)
            
            return ids.tolist() if hasattr(ids, 'tolist') else list(ids)
    
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return [0.0] * 768


VOICE_STYLE_PROMPT = """
Voice style rules (applies to everything in "speak"):
- Never start with "Sure", "Of course", "Certainly", "Absolutely", "Great".
- Be direct. State what you're doing, then do it.
- Confident, not apologetic. Say "I'll do that" not "I can try to do that".
- Warm but brief. Max 2 sentences in "speak" unless explaining something complex.
- Use contractions. "I'll" not "I will". "You're" not "You are".
- Address the user as "you" not by name unless they explicitly introduce themselves.
- When confirming an action: just say what happened. "Done. Chrome is open." not "I've successfully opened the Chrome browser for you!"
- When unsure: "I'm not sure about that — let me check" not "I apologize, I don't have information..."
"""


def think(
    user_input: str,
    system_prompt: str = "",
    memory_context: str = "",
    session_history: str = "",
    max_tokens: int = 256,
) -> Dict[str, Any]:
    """
    Main thinking function - processes user input and returns structured response.
    PROMPT_1 + PROMPT_2 chain.
    """
    from app.prompts import (
        build_system_prompt,
        build_tool_prompt,
        parse_json_response,
        FEW_SHOT_EXAMPLES,
    )
    
    # PROMPT_1: Core system prompt with voice style (already built in agent.py)
    full_prompt = system_prompt
    if not full_prompt:
        full_prompt = build_system_prompt(
            user_name="there",
            memory_context=memory_context,
            session_history=session_history,
        )
    
    full_prompt += "\n\n" + VOICE_STYLE_PROMPT
    
    # PROMPT_2: Tool routing with available tools
    plugin_tools = _get_plugin_tool_descriptions()
    disabled_tools = _get_disabled_tools()
    tool_prompt = build_tool_prompt(user_input, plugin_tools, disabled_tools)
    
    full_prompt += "\n\n" + tool_prompt + "\n\n" + FEW_SHOT_EXAMPLES
    
    response = generate(full_prompt, max_tokens=max_tokens)
    
    return parse_json_response(response)


def _get_plugin_tool_descriptions() -> str:
    """Get enabled plugin tool descriptions."""
    import os
    import json
    
    config_path = os.path.expanduser("~/.senapati/config.json")
    
    if not os.path.exists(config_path):
        return ""
    
    try:
        with open(config_path) as f:
            config = json.load(f)
        
        plugins = config.get("plugins", {})
        parts = []
        
        for name, settings in plugins.items():
            if settings.get("enabled"):
                if name == "telegram":
                    parts.append("- send_telegram(chat_id: str, message: str) — send a Telegram message")
                elif name == "github":
                    parts.append("- get_github_notifications() — get GitHub notifications")
                elif name == "spotify":
                    parts.append("- spotify_play(song: str) — play a song on Spotify")
        
        return "\n".join(parts) if parts else ""
    
    except:
        return ""


def _get_disabled_tools() -> str:
    """Get list of disabled tools."""
    import os
    import json
    
    config_path = os.path.expanduser("~/.senapati/config.json")
    
    if not os.path.exists(config_path):
        return ""
    
    try:
        with open(config_path) as f:
            config = json.load(f)
        
        disabled = config.get("disabled_tools", [])
        return ", ".join(disabled) if disabled else ""
    
    except:
        return ""


def reload_if_needed() -> bool:
    """
    Reload models if they're not loaded.
    """
    if _model is None:
        return load_models()
    return True