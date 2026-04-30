"""XTTS v2 voice clone — medium segments + crossfade for continuous natural flow."""
import os
os.environ["LD_LIBRARY_PATH"] = "/home/spatchava/miniconda3/envs/tts/lib:" + os.environ.get("LD_LIBRARY_PATH", "")
os.environ["COQUI_TOS_AGREED"] = "1"

import subprocess

OUTPUT_DIR = "/home/spatchava/embeddedos-org/EoStudio/promo/narrated_xtts2"
os.makedirs(OUTPUT_DIR, exist_ok=True)
REFERENCE = "/home/spatchava/embeddedos-org/EoStudio/promo/narrated_xtts/reference.wav"
FFMPEG = "/home/spatchava/.local/bin/ffmpeg"

# Medium-length segments — short enough for no word drops, long enough for natural flow
SEGMENTS = [
    "Hey everyone. I'm really excited to show you EoStudio.",
    "It's an open source design suite we built to solve a real problem.",
    "EoStudio has thirteen design editors built right in.",
    "3D modeling, CAD design, image editing, game design, UI UX prototyping, and more.",
    "We built a complete animation engine from scratch. Spring physics and twenty five presets.",
    "The AI features are seriously powerful. Describe your UI in plain English.",
    "EoStudio generates animated components instantly. Upload a screenshot and it extracts every component.",
    "Prototyping is fully interactive. Click interactions, hover effects, swipe gestures.",
    "Code generation is where EoStudio really shines. Thirty three plus frameworks.",
    "React with Framer Motion, Flutter, Swift, Kotlin, and many more.",
    "EoStudio version one point oh. Community Edition. Free, open source, MIT licensed.",
    "Check it out on GitHub. Thank you.",
]

from TTS.api import TTS

print("Loading XTTS v2...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True)
print("Generating segments...")

seg_paths = []
for i, text in enumerate(SEGMENTS):
    out = os.path.join(OUTPUT_DIR, f"seg_{i:02d}.wav")
    print(f"  [{i}] {text[:60]}...")
    tts.tts_to_file(text=text, file_path=out, speaker_wav=REFERENCE, language="en")
    print(f"      -> {os.path.getsize(out)} bytes")
    seg_paths.append(out)

# Use crossfade instead of silence for continuous flow
print("Crossfading segments for continuous audio...")

# First, concat all WAVs raw (no gaps)
raw_list = os.path.join(OUTPUT_DIR, "raw_list.txt")
with open(raw_list, "w") as f:
    for sp in seg_paths:
        f.write(f"file '{sp}'\n")

raw_concat = os.path.join(OUTPUT_DIR, "raw_concat.wav")
subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", raw_list, raw_concat], capture_output=True)

# Apply crossfade using acrossfade filter between segments
# Build a complex filter that crossfades each pair
if len(seg_paths) > 1:
    # Use a simpler approach: concat with small overlap via adelay + amix
    # Or just use raw concat with 100ms fade between segments

    # Add tiny fade-in/fade-out to each segment, then concat
    faded_paths = []
    for i, sp in enumerate(seg_paths):
        faded = os.path.join(OUTPUT_DIR, f"faded_{i:02d}.wav")
        # 50ms fade-in, 100ms fade-out for smooth transitions
        subprocess.run([FFMPEG, "-y", "-i", sp,
                       "-af", "afade=t=in:st=0:d=0.05,afade=t=out:st=999:d=0.1",
                       faded], capture_output=True)
        # The fade-out start time 999 won't match, so use a smarter approach
        # Get duration first
        r = subprocess.run([FFMPEG, "-i", sp, "-f", "null", "-"], capture_output=True, text=True)
        dur = 2.0
        for line in r.stderr.split("\n"):
            if "Duration:" in line:
                t = line.split("Duration:")[1].split(",")[0].strip().split(":")
                dur = float(t[0])*3600 + float(t[1])*60 + float(t[2])

        fade_out_start = max(0, dur - 0.1)
        subprocess.run([FFMPEG, "-y", "-i", sp,
                       "-af", f"afade=t=in:st=0:d=0.05,afade=t=out:st={fade_out_start}:d=0.1",
                       faded], capture_output=True)
        faded_paths.append(faded)

    # Concat faded segments with tiny 50ms silence (just enough for breath)
    breath = os.path.join(OUTPUT_DIR, "breath.wav")
    subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono",
                   "-t", "0.05", "-c:a", "pcm_s16le", breath], capture_output=True)

    final_list = os.path.join(OUTPUT_DIR, "final_list.txt")
    with open(final_list, "w") as f:
        for i, fp in enumerate(faded_paths):
            f.write(f"file '{fp}'\n")
            if i < len(faded_paths) - 1:
                f.write(f"file '{breath}'\n")

    narration_wav = os.path.join(OUTPUT_DIR, "narration.wav")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", final_list, narration_wav],
                  capture_output=True)
else:
    narration_wav = seg_paths[0]

narration_mp3 = os.path.join(OUTPUT_DIR, "narration.mp3")
subprocess.run([FFMPEG, "-y", "-i", narration_wav, "-c:a", "libmp3lame", "-q:a", "2", narration_mp3],
              capture_output=True)

# Get duration
r = subprocess.run([FFMPEG, "-i", narration_mp3, "-f", "null", "-"], capture_output=True, text=True)
dur = 120
for line in r.stderr.split("\n"):
    if "Duration:" in line:
        t = line.split("Duration:")[1].split(",")[0].strip().split(":")
        dur = float(t[0])*3600 + float(t[1])*60 + float(t[2])
print(f"Total: {dur:.1f}s")

# Combine with video
video = "/home/spatchava/embeddedos-org/EoStudio/promo/media/videos/eostudio_promo/1080p60/EoStudioPromo.mp4"
output = os.path.join(OUTPUT_DIR, "EoStudio_XTTS_Final_1080p.mp4")
subprocess.run([FFMPEG, "-y", "-stream_loop", "-1", "-i", video, "-i", narration_mp3,
               "-c:v", "libx264", "-preset", "fast", "-crf", "23",
               "-c:a", "aac", "-b:a", "192k", "-t", str(dur),
               "-pix_fmt", "yuv420p", output], capture_output=True)

if os.path.exists(output):
    sz = os.path.getsize(output) / 1024 / 1024
    print(f"Final: {output} ({sz:.1f} MB)")
    subprocess.run(["cp", output, "/mnt/c/Users/spatchava/Desktop/EoStudio_XTTS_Final_1080p.mp4"], capture_output=True)
    subprocess.run(["cp", narration_mp3, "/mnt/c/Users/spatchava/Desktop/EoStudio_XTTS_Final.mp3"], capture_output=True)
    print("Copied to Desktop!")
