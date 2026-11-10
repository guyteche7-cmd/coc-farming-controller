# External LLM / Cloud VLM Extension Plugin

This directory contains optional external Cloud LLM/VLM integrations (Google Gemini API).

## Modular Decoupling Architecture

The CoC Farming Controller does **not** require this folder or any external LLM to operate. All core bot functionalities (deterministic glyph matching, PP-OCRv4, and Florence-2 open-vocabulary perception) operate 100% locally.

### How to Completely Remove or Disable External LLMs:

1. **Option A: Delete this Directory**
   - You can simply delete the entire `src/extensions/external_llm/` directory.
   - The core bot (`MultimodalVLMEngine`) will automatically detect that the module is absent, log a single informational notice, and fall back to 100% self-contained local perception without throwing any errors or exceptions.

2. **Option B: Disable in Configuration**
   - In `config.json` or your application configuration, set:
     ```json
     "llm": {
       "enabled": false
     }
     ```
   - No network calls or external API queries will be performed.

3. **Option C: Uninstall Dependencies**
   - You can uninstall `google-genai` from your Python environment (`pip uninstall google-genai`). The bot will continue running smoothly.
