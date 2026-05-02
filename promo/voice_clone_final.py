"""Voice clone — runs with LD_LIBRARY_PATH fix."""
import os
os.environ["LD_LIBRARY_PATH"] = "/home/spatchava/miniconda3/envs/tts/lib:" + os.environ.get("LD_LIBRARY_PATH", "")

import subprocess

OUTPUT_DIR = "/home/spatchava/embeddedos-org/EoStudio/promo/narrated_cloned"
os.makedirs(OUTPUT_DIR, exist_ok=True)
REFERENCE = "/home/spatchava/embeddedos-org/EoStudio/promo/your_voice.mp3"
FFMPEG = "/home/spatchava/.local/bin/ffmpeg"

SEGMENTS = [
    "Hey everyone. I'm really excited to show you EoStudio. It's an open source design suite we built to solve a real problem.",
    "EoStudio has thirteen design editors. 3D modeling, CAD, image editing, game design, UI UX prototyping, and more. All in one app.",
    "We built a complete animation engine from scratch. Spring physics, twenty five presets, and a visual timeline editor.",
    "The AI features are powerful. Describe your UI in plain English and get animated components instantly.",
    "Prototyping is interactive. Click interactions, gestures, state machines. Export as HTML with one click.",
    "Thirty three plus code generators. React with Framer Motion, Flutter, Swift, GSAP, and many more.",
    "EoStudio version one. Community Edition. Free, open source, MIT licensed. Check it out on GitHub. Thank you.",
]

from TTS.api import TTS
print("Loading YourTTS voice cloning model...")
tts = TTS("tts_models/multilingual/multi-dataset/your_tts", progress_bar=True)
print(f"Model loaded. Cloning from: {REFERENCE}")

seg_paths = []
for i, text in enumerate(SEGMENTS):
    out = os.path.join(OUTPUT_DIR, f"seg_{i:02d}.wav")
    print(f"  [{i}] {text[:55]}...")
    tts.tts_to_file(text=text, file_path=out, speaker_wav=REFERENCE, language="en")
    seg_paths.append(out)
    print(f"      -> {os.path.getsize(out)} bytes")

# Silence
sil = os.path.join(OUTPUT_DIR, "silence.wav")
subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
                "-t", "1.0", "-c:a", "pcm_s16le", sil], capture_output=True)

# Concat
lp = os.path.join(OUTPUT_DIR, "list.txt")
with open(lp, "w") as f:
    for i, sp in enumerate(seg_paths):
        f.write(f"file '{sp}'\n")
        if i < len(seg_paths) - 1:
            f.write(f"file '{sil}'\n")

nar_wav = os.path.join(OUTPUT_DIR, "narration.wav")
subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lp, nar_wav], capture_output=True)

nar_mp3 = os.path.join(OUTPUT_DIR, "narration.mp3")
subprocess.run([FFMPEG, "-y", "-i", nar_wav, "-c:a", "libmp3lame", "-q:a", "2", nar_mp3], capture_output=True)

# Duration
r = subprocess.run([FFMPEG, "-i", nar_mp3, "-f", "null", "-"], capture_output=True, text=True)
dur = 120
for line in r.stderr.split("\n"):
    if "Duration:" in line:
        t = line.split("Duration:")[1].split(",")[0].strip().split(":")
        dur = float(t[0])*3600 + float(t[1])*60 + float(t[2])
print(f"Total narration: {dur:.1f}s")

# Combine with video
video = "/home/spatchava/embeddedos-org/EoStudio/promo/media/videos/eostudio_promo/1080p60/EoStudioPromo.mp4"
output = os.path.join(OUTPUT_DIR, "EoStudio_VoiceCloned_1080p.mp4")
subprocess.run([FFMPEG, "-y", "-stream_loop", "-1", "-i", video, "-i", nar_mp3,
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "192k", "-t", str(dur),
                "-pix_fmt", "yuv420p", output], capture_output=True)

if os.path.exists(output):
    sz = os.path.getsize(output) / 1024 / 1024
    print(f"Final: {output} ({sz:.1f} MB)")
    subprocess.run(["cp", output, "/mnt/c/Users/spatchava/Desktop/EoStudio_VoiceCloned_1080p.mp4"], capture_output=True)
    subprocess.run(["cp", nar_mp3, "/mnt/c/Users/spatchava/Desktop/EoStudio_VoiceCloned.mp3"], capture_output=True)
    print("Copied to Desktop!")
else:
    print("Video failed, but audio at:", nar_mp3)
