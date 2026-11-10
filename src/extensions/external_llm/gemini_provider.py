"""
External Google Gemini Vision-Language Model (VLM) Provider Plugin.

This module is an isolated, optional plugin for cloud-based multimodal reasoning.
It encapsulates all external `google-genai` SDK calls, API key handling, and model generation.

HOW TO REMOVE OR DISABLE:
- To completely remove external LLMs from the program: simply delete this folder (`src/extensions/external_llm`).
- To disable via configuration: set `llm.enabled = False` in your app configuration.
The core bot will automatically detect its absence and run 100% locally with zero errors.
"""

from __future__ import annotations
import os
import logging
from typing import Optional, Any, Tuple
import cv2
import numpy as np

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
    _proj_env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), ".env")
    if os.path.exists(_proj_env):
        load_dotenv(_proj_env)
except Exception:
    pass

logger = logging.getLogger(__name__)


class GeminiVLMProvider:
    """
    Pluggable external VLM provider using Google Gemini Vision.
    Uses gemini-3.5-flash-lite as fast, high-availability default with gemini-3.8-flash fallback.
    """

    DEFAULT_MODEL = "gemini-3.5-flash-lite"
    FALLBACK_MODEL = "gemini-3.8-flash"

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or self.DEFAULT_MODEL
        self.active_model = self.model_name
        self.client = None

        if self.api_key:
            self.init_client()

    def init_client(self) -> bool:
        """Initializes the google-genai client."""
        try:
            from google import genai
            from google.genai import types
            self.client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(timeout=15000)
            )
            logger.info(f"[EXTERNAL LLM PLUGIN] Connected to Gemini API with default model '{self.model_name}'.")
            return True
        except ImportError:
            logger.info("[EXTERNAL LLM PLUGIN] 'google-genai' package not installed. Provider unavailable.")
            self.client = None
            return False
        except Exception as e:
            logger.warning(f"[EXTERNAL LLM PLUGIN] Failed to initialize Gemini client: {e}")
            self.client = None
            return False

    def is_available(self) -> bool:
        """Returns True if the provider is initialized with valid credentials."""
        return self.client is not None and bool(self.api_key)

    def set_api_key(self, api_key: str) -> bool:
        """Updates the API key and reinitializes the client."""
        self.api_key = api_key
        return self.init_client()

    def query_multimodal(
        self,
        frame_bgr: np.ndarray,
        prompt: str,
        response_schema: Any
    ) -> Optional[str]:
        """
        Sends the compressed game frame to Gemini and returns raw JSON text matching response_schema.
        Returns None if offline, unauthenticated, or on error.
        """
        if not self.is_available():
            return None

        try:
            from google.genai import types

            h, w = frame_bgr.shape[:2]
            target_w = min(w, 1280)
            target_h = int(h * (target_w / float(w)))
            resized = cv2.resize(frame_bgr, (target_w, target_h), interpolation=cv2.INTER_AREA)

            success, buffer = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not success:
                return None
            jpg_bytes = buffer.tobytes()

            image_part = types.Part.from_bytes(data=jpg_bytes, mime_type="image/jpeg")

            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.1
            )

            models_to_try = [self.model_name]
            if self.FALLBACK_MODEL not in models_to_try:
                models_to_try.append(self.FALLBACK_MODEL)

            for model_id in models_to_try:
                try:
                    response = self.client.models.generate_content(
                        model=model_id,
                        contents=[image_part, prompt],
                        config=config
                    )
                    if response and response.text:
                        self.active_model = model_id
                        return response.text
                except Exception as model_err:
                    err_msg = str(model_err)
                    if "503" in err_msg or "UNAVAILABLE" in err_msg or "429" in err_msg:
                        logger.warning(f"[EXTERNAL LLM PLUGIN] Model '{model_id}' busy/unavailable (503). Retrying fallback...")
                        continue
                    else:
                        raise model_err

            return None

        except Exception as e:
            logger.warning(f"[EXTERNAL LLM PLUGIN] Gemini query error: {e}")
            return None
