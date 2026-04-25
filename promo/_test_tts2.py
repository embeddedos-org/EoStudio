import os
os.environ["LD_LIBRARY_PATH"] = "/home/spatchava/miniconda3/envs/tts/lib:" + os.environ.get("LD_LIBRARY_PATH", "")
try:
    from TTS.api import TTS
    print("TTS_OK")
except Exception as e:
    print(f"ERR: {e}")
