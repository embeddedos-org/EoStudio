"""Generate per-segment narration audio and output durations for Manim sync."""
import json
from gtts import gTTS
from mutagen.mp3 import MP3

SEGMENTS = [
    {"id": "intro", "text": "Introducing EoStudio. Design Suite with LLM Integration."},
    {"id": "f1", "text": "Feature one. AI Code Generation. Natural language prompts generate production-ready TypeScript and Python code."},
    {"id": "f2", "text": "Feature two. Spec-Driven Development. Auto-generates requirements, design specs, tech specs, and task breakdowns."},
    {"id": "f3", "text": "Feature three. Production UI Kit. 39 accessible React components with responsive variants and Framer Motion animations."},
    {"id": "arch", "text": "Under the hood, EoStudio is built with Python, React, TypeScript. The architecture flows from LLM Client, to Spec Engine, to Code Gen, to UI Kit, to Deploy."},
    {"id": "cta", "text": "EoStudio. Open source and production ready. Visit github dot com slash embeddedos-org slash EoStudio."},
]

durations = {}
audio_files = []

for seg in SEGMENTS:
    filename = f"seg_{seg['id']}.mp3"
    tts = gTTS(text=seg["text"], lang="en", slow=False)
    tts.save(filename)
    dur = MP3(filename).info.length
    durations[seg["id"]] = round(dur + 0.5, 1)  # add 0.5s padding
    audio_files.append(filename)
    print(f"  {seg['id']}: {dur:.1f}s -> padded {durations[seg['id']]}s")

# Write durations JSON for Manim to read
with open("durations.json", "w") as f:
    json.dump(durations, f, indent=2)

# Concatenate all segments into single narration.mp3
import subprocess
list_file = "concat_list.txt"
with open(list_file, "w") as f:
    for af in audio_files:
        f.write(f"file '{af}'\n")

subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
    "-i", list_file, "-c", "copy", "narration.mp3"
], check=True)

total = sum(durations.values())
print(f"\nTotal narration: {total:.1f}s")
print(f"Durations: {json.dumps(durations)}")
