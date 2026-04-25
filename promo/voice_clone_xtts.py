"""Voice clone using XTTS v2 — higher quality, more confident output."""
import os
os.environ["LD_LIBRARY_PATH"] = "/home/spatchava/miniconda3/envs/tts/lib:" + os.environ.get("LD_LIBRARY_PATH", "")
os.environ["COQUI_TOS_AGREED"] = "1"

import subprocess

OUTPUT_DIR = "/home/spatchava/embeddedos-org/EoStudio/promo/narrated_xtts"
os.makedirs(OUTPUT_DIR, exist_ok=True)
REFERENCE = "/home/spatchava/embeddedos-org/EoStudio/promo/your_voice.mp3"
FFMPEG = "/home/spatchava/.local/bin/ffmpeg"

# Convert reference to WAV first (XTTS prefers WAV)
REF_WAV = os.path.join(OUTPUT_DIR, "reference.wav")
subprocess.run([FFMPEG, "-y", "-i", REFERENCE, "-ar", "22050", "-ac", "1", REF_WAV], capture_output=True)
print(f"Reference WAV: {os.path.getsize(REF_WAV)} bytes")

SEGMENTS = [
    "Hey everyone.",
    "I'm really excited to show you EoStudio.",
    "It's an open source design suite.",
    "We built it to solve a real problem.",
    "Why do we need ten different tools when one can do it all?",
    "EoStudio has thirteen design editors.",
    "3D modeling. CAD design. Image editing.",
    "Game design. UI UX prototyping. And more.",
    "All in one app.",
    "We built a complete animation engine from scratch.",
    "Spring physics. Twenty five animation presets.",
    "A visual timeline editor.",
    "The AI features are seriously powerful.",
    "Describe your UI in plain English.",
    "EoStudio generates animated components instantly.",
    "Upload a screenshot and it extracts every component.",
    "Prototyping is fully interactive.",
    "Click interactions. Hover effects. Swipe gestures.",
    "Export as HTML prototype with one click.",
    "Code generation is where EoStudio really shines.",
    "Thirty three plus frameworks.",
    "React with Framer Motion. Flutter. Swift. Kotlin.",
    "Design once. Deploy everywhere.",
    "EoStudio version one point oh.",
    "Community Edition.",
    "Free. Open source. MIT licensed.",
    "Check it out on GitHub. Thank you.",
]

from TTS.api import TTS

print("Loading XTTS v2 model (best quality voice cloning)...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True)
print("Model loaded. Generating with your cloned voice...")

seg_paths = []
for i, text in enumerate(SEGMENTS):
    out = os.path.join(OUTPUT_DIR, f"seg_{i:02d}.wav")
    print(f"  [{i}] {text[:60]}...")
    tts.tts_to_file(text=text, file_path=out, speaker_wav=REF_WAV, language="en")
    sz = os.path.getsize(out)
    print(f"      -> {sz} bytes")
    seg_paths.append(out)

# Silence between segments
sil = os.path.join(OUTPUT_DIR, "silence.wav")
subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono",
                "-t", "0.4", "-c:a", "pcm_s16le", sil], capture_output=True)

# Concatenate
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
output = os.path.join(OUTPUT_DIR, "EoStudio_XTTS_1080p.mp4")
subprocess.run([FFMPEG, "-y", "-stream_loop", "-1", "-i", video, "-i", nar_mp3,
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "192k", "-t", str(dur),
                "-pix_fmt", "yuv420p", output], capture_output=True)

if os.path.exists(output):
    sz = os.path.getsize(output) / 1024 / 1024
    print(f"Final: {output} ({sz:.1f} MB)")
    subprocess.run(["cp", output, "/mnt/c/Users/spatchava/Desktop/EoStudio_XTTS_VoiceClone_1080p.mp4"], capture_output=True)
    subprocess.run(["cp", nar_mp3, "/mnt/c/Users/spatchava/Desktop/EoStudio_XTTS_VoiceClone.mp3"], capture_output=True)
    print("Copied to Desktop!")
