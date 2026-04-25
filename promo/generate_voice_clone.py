"""Voice-cloned narration using Coqui TTS — clones voice from Recording.mp3."""

import os
import subprocess

OUTPUT_DIR = "/home/spatchava/embeddedos-org/EoStudio/promo/narrated_cloned"
os.makedirs(OUTPUT_DIR, exist_ok=True)

REFERENCE_AUDIO = "/home/spatchava/embeddedos-org/EoStudio/promo/your_voice.mp3"

SEGMENTS = [
    "Hey everyone. I'm really excited to show you EoStudio. It's an open-source design suite that we built to solve a real problem. Why do we need ten different tools, when one can do it all?",
    "EoStudio has thirteen design editors built right in. You get 3D modeling, CAD design, image editing, game design, UI UX prototyping, interior design, UML diagrams, simulation, database design, hardware PCB layout, a full IDE, and a brand new promo video editor. All in one app.",
    "Now here's the part I'm most proud of. We built a complete animation engine from scratch. It has spring physics, just like Framer Motion. Twenty five animation presets. A visual timeline editor. And twenty four easing functions including cubic bezier.",
    "The AI features are seriously powerful. Describe your UI in plain English, and EoStudio generates animated components instantly. Upload a screenshot, and it extracts every component. Generate a complete design system from just a brand description.",
    "Prototyping is fully interactive. Click interactions, hover effects, swipe gestures, and state machines. Export it all as a shareable HTML prototype with one click.",
    "Code generation is where EoStudio really shines. Thirty three plus frameworks. React with Framer Motion, Flutter, Swift, Kotlin, Electron, GSAP, and many more. Design once, deploy everywhere.",
    "EoStudio version one point oh. Community Edition. Free, open source, MIT licensed. Check it out on GitHub. Thank you.",
]


def main():
    try:
        from TTS.api import TTS
    except ImportError:
        print("ERROR: Coqui TTS not installed. Run: pip3 install TTS")
        return

    print("Loading TTS model with voice cloning...")
    # Use XTTS v2 for best quality voice cloning
    try:
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
    except Exception:
        # Fallback to simpler model
        print("XTTS v2 not available, trying YourTTS...")
        try:
            tts = TTS("tts_models/multilingual/multi-dataset/your_tts")
        except Exception:
            print("Trying basic English model with voice conversion...")
            tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")

    print(f"Model loaded. Reference audio: {REFERENCE_AUDIO}")

    segment_paths = []
    for i, text in enumerate(SEGMENTS):
        out_path = os.path.join(OUTPUT_DIR, f"seg_{i:02d}.wav")
        print(f"  Generating segment {i}: {text[:50]}...")
        try:
            # Voice cloning with reference audio
            tts.tts_to_file(
                text=text,
                file_path=out_path,
                speaker_wav=REFERENCE_AUDIO,
                language="en",
            )
        except TypeError:
            # Some models don't support speaker_wav
            tts.tts_to_file(text=text, file_path=out_path)
        segment_paths.append(out_path)

    # Concatenate all segments with pauses
    print("Concatenating segments...")
    list_path = os.path.join(OUTPUT_DIR, "list.txt")
    ffmpeg = "/home/spatchava/.local/bin/ffmpeg"

    # Create 1s silence
    silence_path = os.path.join(OUTPUT_DIR, "silence.wav")
    subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i",
                    "anullsrc=r=22050:cl=mono", "-t", "1",
                    "-c:a", "pcm_s16le", silence_path], capture_output=True)

    with open(list_path, "w") as f:
        for i, sp in enumerate(segment_paths):
            f.write(f"file '{sp}'\n")
            if i < len(segment_paths) - 1:
                f.write(f"file '{silence_path}'\n")

    narration_wav = os.path.join(OUTPUT_DIR, "narration.wav")
    subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0",
                    "-i", list_path, narration_wav], capture_output=True)

    # Convert to mp3
    narration_mp3 = os.path.join(OUTPUT_DIR, "narration.mp3")
    subprocess.run([ffmpeg, "-y", "-i", narration_wav,
                    "-c:a", "libmp3lame", "-q:a", "2", narration_mp3], capture_output=True)

    # Get duration
    r = subprocess.run([ffmpeg, "-i", narration_mp3, "-f", "null", "-"],
                       capture_output=True, text=True)
    dur = 120
    for line in r.stderr.split("\n"):
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip().split(":")
            dur = float(t[0])*3600 + float(t[1])*60 + float(t[2])
    print(f"Narration duration: {dur:.1f}s")

    # Combine with video
    video = "/home/spatchava/embeddedos-org/EoStudio/promo/media/videos/eostudio_promo/1080p60/EoStudioPromo.mp4"
    output = os.path.join(OUTPUT_DIR, "EoStudio_VoiceCloned_1080p.mp4")

    subprocess.run([ffmpeg, "-y", "-stream_loop", "-1", "-i", video,
                    "-i", narration_mp3, "-c:v", "libx264", "-preset", "fast",
                    "-crf", "23", "-c:a", "aac", "-b:a", "192k",
                    "-t", str(dur), "-pix_fmt", "yuv420p", output], capture_output=True)

    if os.path.exists(output):
        sz = os.path.getsize(output) / 1024 / 1024
        print(f"Final video: {output} ({sz:.1f} MB)")
        subprocess.run(["cp", output,
                        "/mnt/c/Users/spatchava/Desktop/EoStudio_VoiceCloned_1080p.mp4"],
                       capture_output=True)
        subprocess.run(["cp", narration_mp3,
                        "/mnt/c/Users/spatchava/Desktop/EoStudio_VoiceCloned_Narration.mp3"],
                       capture_output=True)
        print("Copied to Desktop!")
    else:
        print("Video creation failed, but narration audio is at:", narration_mp3)


if __name__ == "__main__":
    main()
