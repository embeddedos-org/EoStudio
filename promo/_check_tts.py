import sys
try:
    from TTS.api import TTS
    print("TTS_IMPORT_OK")
    # List available models that support voice cloning
    models = TTS.list_models()
    clone_models = [m for m in models if "multi" in m or "your" in m.lower() or "xtts" in m.lower()]
    print(f"Voice cloning models: {clone_models[:5]}")
except Exception as e:
    print(f"TTS_ERROR: {e}")
