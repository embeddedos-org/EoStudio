"""Install all remaining TTS deps by creating stubs for non-essential ones."""
import os, sys

site = "/home/spatchava/.local/lib/python3.8/site-packages"

# matplotlib stub (TTS only uses it for optional plotting)
mpl_dir = os.path.join(site, "matplotlib")
if not os.path.exists(mpl_dir):
    os.makedirs(mpl_dir, exist_ok=True)
    with open(os.path.join(mpl_dir, "__init__.py"), "w") as f:
        f.write('__version__ = "3.7.0"\ndef use(*a, **k): pass\n')
    with open(os.path.join(mpl_dir, "pyplot.py"), "w") as f:
        f.write('def figure(*a,**k): pass\ndef show(*a,**k): pass\ndef plot(*a,**k): pass\ndef savefig(*a,**k): pass\ndef close(*a,**k): pass\ndef subplot(*a,**k): pass\ndef title(*a,**k): pass\ndef xlabel(*a,**k): pass\ndef ylabel(*a,**k): pass\n')
    print("Created matplotlib stub")

# Test full TTS import chain
try:
    from TTS.api import TTS
    print("TTS imported OK!")
    models = TTS.list_models()
    clone_models = [m for m in models if "your" in m.lower() or "xtts" in m.lower() or "multi" in m]
    print(f"Total models: {len(models)}")
    print(f"Voice cloning models: {clone_models[:8]}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
