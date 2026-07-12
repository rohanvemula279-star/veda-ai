import json
import sys
import time
import base64
import logging
from pathlib import Path
from typing import Optional, Any, Dict, List

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("veda_ai_client")

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR     = _get_base_dir()
API_KEY_PATH = BASE_DIR / "config" / "api_keys.json"

DEFAULT_SEEKAI_URL   = "https://seekai.cc/v1/chat/completions"
DEFAULT_SEEKAI_MODEL = "glm-5.3-flash"
OPENROUTER_API_URL   = "https://openrouter.ai/api/v1/chat/completions"

SEEKAI_MODELS: List[str] = [
    "glm-5.3-flash",
    "deepseek-v4-flash",
    "qwen3.8-flash",
    "hy3",
]

OPENROUTER_TEXT_MODELS: List[str] = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "minimax/minimax-m2.5:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-3-27b-it:free",
    "google/gemma-3-12b-it:free",
    "meta-llama/llama-3.2-3b-instruct:free",
]

TEXT_MODELS: List[str] = SEEKAI_MODELS + OPENROUTER_TEXT_MODELS

VISION_MODELS: List[str] = [
    "glm-5.3-flash",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]

DEFAULT_MAX_TOKENS    = 4096
DEFAULT_TEMPERATURE   = 0.7
REQUEST_TIMEOUT       = 60   # seconds per request
MAX_RETRIES_PER_MODEL = 2    # attempts before moving to next model
RETRY_DELAY           = 1.5  # seconds between retries
RATE_LIMIT_COOLDOWN   = 30   # seconds before retrying a rate-limited model

_rate_limited: Dict[str, float] = {}


def _load_config_data() -> Dict[str, Any]:
    try:
        with open(API_KEY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


class VedaAIClient:
    """
    Unified AI Client for Veda AI - Lite / Veda Echo.
    Prioritizes SeekAI (glm-5.3-flash) with seamless fallback to OpenRouter free models.
    """

    def __init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        cfg = _load_config_data()
        self.seekai_key = (
            cfg.get("seekai_api_key", "").strip()
            or (cfg.get("gemini_api_key", "").strip() if cfg.get("gemini_api_key", "").strip().startswith("sk-") else "")
        )
        self.seekai_url = cfg.get("seekai_api_url", DEFAULT_SEEKAI_URL).strip()
        self.seekai_model = cfg.get("seekai_model", DEFAULT_SEEKAI_MODEL).strip()

        self.openrouter_key = cfg.get("openrouter_api_key", "").strip()

        # Backward compatibility field
        self.api_key = self.seekai_key or self.openrouter_key

    def _is_rate_limited(self, model: str) -> bool:
        ts = _rate_limited.get(model)
        if ts is None:
            return False
        if time.time() - ts > RATE_LIMIT_COOLDOWN:
            del _rate_limited[model]
            return False
        return True

    def _mark_rate_limited(self, model: str) -> None:
        _rate_limited[model] = time.time()
        logger.warning(
            f"[VedaAI] Rate limited: {model} — cooling down for {RATE_LIMIT_COOLDOWN}s"
        )

    def _call(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        # Choose provider endpoint and credentials
        is_seekai_model = model in SEEKAI_MODELS or "glm" in model.lower() or "deepseek" in model.lower() or "qwen3.8" in model.lower() or "hy3" in model.lower()

        if self.seekai_key and (is_seekai_model or not self.openrouter_key):
            url = self.seekai_url
            api_key = self.seekai_key
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        elif self.openrouter_key:
            url = OPENROUTER_API_URL
            api_key = self.openrouter_key
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/rohan/veda-ai-lite",
                "X-Title": "Veda AI - Lite",
            }
        elif self.seekai_key:
            url = self.seekai_url
            api_key = self.seekai_key
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        else:
            raise PermissionError(
                "[VedaAI] API key is missing. Add SeekAI or OpenRouter credentials in config/api_keys.json."
            )

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):
            try:
                resp = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=REQUEST_TIMEOUT,
                )

                if resp.status_code == 401:
                    raise PermissionError(
                        f"[VedaAI] Authentication failed for model {model} at {url}. "
                        "Check your API key in config/api_keys.json."
                    )

                if resp.status_code == 403:
                    raise PermissionError(
                        f"[VedaAI] Access denied for model {model} (HTTP 403). "
                        "Check your account permissions and model access."
                    )

                if resp.status_code == 429:
                    self._mark_rate_limited(model)
                    return None

                if resp.status_code == 200:
                    data = resp.json()
                    content = (
                        data.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                    )
                    return content.strip() if content else None

                logger.warning(
                    f"[VedaAI] {model} ({url}) → HTTP {resp.status_code} "
                    f"(attempt {attempt}/{MAX_RETRIES_PER_MODEL})"
                )

            except requests.exceptions.Timeout:
                logger.warning(
                    f"[VedaAI] {model} → Timeout (attempt {attempt}/{MAX_RETRIES_PER_MODEL})"
                )
            except PermissionError:
                raise
            except Exception as e:
                logger.error(f"[VedaAI] {model} → Unexpected error: {e}")

            if attempt < MAX_RETRIES_PER_MODEL:
                time.sleep(RETRY_DELAY)

        return None

    def _call_with_fallback(
        self,
        pool: List[str],
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        self.reload()

        target_model = model or (self.seekai_model if self.seekai_key else (pool[0] if pool else DEFAULT_SEEKAI_MODEL))

        if target_model and not self._is_rate_limited(target_model):
            try:
                result = self._call(target_model, messages, max_tokens, temperature, response_format)
                if result:
                    return result
                logger.info(
                    f"[VedaAI] Primary model failed or empty, falling back: {target_model}"
                )
            except PermissionError:
                raise
            except Exception as e:
                logger.warning(f"[VedaAI] Call to {target_model} failed: {e}")

        # Try models in pool
        for m in pool:
            if m == target_model or self._is_rate_limited(m):
                continue
            logger.info(f"[VedaAI] Trying model: {m}")
            try:
                result = self._call(m, messages, max_tokens, temperature, response_format)
                if result:
                    logger.info(f"[VedaAI] ✓ Success with model: {m}")
                    return result
            except Exception as e:
                logger.warning(f"[VedaAI] Model {m} failed: {e}")

        raise RuntimeError(
            "[VedaAI] All models failed or are rate-limited. "
            "Check your API key and network connection."
        )

    def chat(
        self,
        prompt: str,
        system: str = (
            "You are Veda AI - Lite, a smart, fast, and helpful personal desktop assistant for Rohan. "
            "Reply naturally, concisely, and directly. Do not mention internal system mechanics."
        ),
        history: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> str:
        messages = [{"role": "system", "content": system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        return self._call_with_fallback(
            TEXT_MODELS, messages, model, max_tokens, temperature
        )

    def chat_json(
        self,
        prompt: str,
        system: str = (
            "Return ONLY valid JSON. "
            "No markdown fences, no extra text, no explanation."
        ),
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> dict:
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ]
        raw = self._call_with_fallback(
            TEXT_MODELS, messages, model, max_tokens, temperature=0.1
        )

        clean = raw.strip()
        if clean.startswith("```"):
            parts = clean.split("```")
            clean = parts[1] if len(parts) > 1 else clean
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip().rstrip("`").strip()

        # If there is leading text before JSON '{' or '['
        first_brace = clean.find("{")
        first_bracket = clean.find("[")
        if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
            last_brace = clean.rfind("}")
            if last_brace != -1:
                clean = clean[first_brace : last_brace + 1]
        elif first_bracket != -1:
            last_bracket = clean.rfind("]")
            if last_bracket != -1:
                clean = clean[first_bracket : last_bracket + 1]

        try:
            return json.loads(clean)
        except json.JSONDecodeError as e:
            logger.error(
                f"[VedaAI] JSON parse failed: {e}\n"
                f"Raw response: {raw[:300]}"
            )
            raise ValueError(
                f"Model returned unparseable JSON: {e}\n"
                f"Raw output: {raw[:200]}"
            )

    def vision(
        self,
        prompt: str,
        image_b64: str,
        mime: str = "image/png",
        system: str = "Analyze the image and describe what you see clearly and concisely.",
        model: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{image_b64}"
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            },
        ]
        return self._call_with_fallback(
            VISION_MODELS, messages, model, max_tokens, temperature=0.2
        )

    def vision_from_file(
        self,
        prompt: str,
        image_path: str,
        system: str = "Analyze the image and describe what you see clearly and concisely.",
        model: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        path = Path(image_path)
        mime_map = {
            ".png":  "image/png",
            ".jpg":  "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif":  "image/gif",
        }
        mime = mime_map.get(path.suffix.lower(), "image/png")

        with open(path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        return self.vision(prompt, image_b64, mime, system, model, max_tokens)

    def multi_turn(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> str:
        return self._call_with_fallback(
            TEXT_MODELS, messages, model, max_tokens, temperature
        )

    def available_models(self) -> Dict[str, Any]:
        return {
            "seekai_models": SEEKAI_MODELS,
            "openrouter_models": OPENROUTER_TEXT_MODELS,
            "text_models": TEXT_MODELS,
            "vision_models": VISION_MODELS,
            "rate_limited": list(_rate_limited.keys()),
            "active_model": self.seekai_model if self.seekai_key else (OPENROUTER_TEXT_MODELS[0] if self.openrouter_key else "None"),
        }


# Aliases for backward compatibility
OpenRouterClient = VedaAIClient
client = VedaAIClient()
openrouter_client = client


if __name__ == "__main__":
    print("=" * 60)
    print("  Veda AI - Lite / SeekAI Client Self-Test")
    print("=" * 60)

    print("\n[TEST 1] Basic Chat (SeekAI glm-5.3-flash)...")
    try:
        reply = client.chat("Introduce yourself in one short sentence.")
        print(f"  Response : {reply}")
        print("  Status   : PASS ✓")
    except Exception as e:
        print(f"  Status   : FAIL ✗ — {e}")

    print("\n[TEST 2] JSON Extraction Mode...")
    try:
        data = client.chat_json(
            'List 3 colors. Format: {"colors": ["red", "green", "blue"]}',
            system="Return ONLY valid JSON."
        )
        print(f"  Response : {data}")
        print("  Status   : PASS ✓")
    except Exception as e:
        print(f"  Status   : FAIL ✗ — {e}")

    print("\n[TEST 3] Available Models...")
    print(f"  Models: {client.available_models()}")

    print("\n" + "=" * 60)
    print("  Self-test complete.")
    print("=" * 60)
