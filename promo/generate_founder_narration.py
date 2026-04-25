"""Generate narrated EoStudio promo with Indian English voice — founder style."""

import asyncio
import edge_tts
import subprocess
import os

OUTPUT_DIR = "/home/spatchava/embeddedos-org/EoStudio/promo/narrated_v2"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Natural founder-style narration — conversational, passionate
SEGMENTS = [
    {
        "text": "Hey everyone. I'm really excited to introduce EoStudio. It's an open-source design suite that we built to solve a real problem. Why do we need ten different tools when one can do it all?",
        "pause_after": 0.8,
    },
    {
        "text": "EoStudio has thirteen design editors built in. You get 3D modeling, CAD design, image editing, game design, UI/UX prototyping, interior design, UML diagrams, simulation, database design, hardware PCB layout, a full IDE, and a new promo video editor. All in one application.",
        "pause_after": 0.8,
    },
    {
        "text": "Now here's the part I'm most proud of. We built a complete animation engine from scratch. It has spring physics, just like Framer Motion. Twenty-five animation presets. A visual timeline editor where you can drag keyframes. And twenty-four easing functions including cubic bezier support.",
        "pause_after": 0.8,
    },
    {
        "text": "The AI features are really powerful. You can describe your UI in plain English, and EoStudio generates the entire component tree with entrance animations. You can upload a screenshot of any app, and it extracts every component. You can even generate a complete design system from just a brand description.",
        "pause_after": 0.6,
    },
    {
        "text": "We also built an accessibility auditor. It checks your designs against WCAG 2.1 double A standards and gives you specific fix suggestions. Because great design should be accessible to everyone.",
        "pause_after": 0.8,
    },
    {
        "text": "Prototyping is interactive. You can add click interactions, hover effects, swipe gestures, even build state machines with variables and conditions. And you can export the whole thing as a shareable HTML prototype with one click.",
        "pause_after": 0.8,
    },
    {
        "text": "Code generation is where EoStudio really shines. We support thirty-three plus frameworks. React with Framer Motion, React with GSAP, Flutter, Swift, Kotlin, Electron, Tauri, Vue, Angular, Django, FastAPI, and many more. Design once, deploy everywhere.",
        "pause_after": 0.8,
    },
    {
        "text": "And we didn't stop there. There's a built-in promo editor for creating App Store previews, social media posts, and product launch videos. Because you shouldn't need Runway or Canva just to promote your own product.",
        "pause_after": 0.8,
    },
    {
        "text": "EoStudio version one point oh. Community Edition. It's completely free, open source, MIT licensed. Go check it out on GitHub. We'd love to hear what you think. Thank you.",
        "pause_after": 1.5,
    },
]

VOICE = "en-IN-PrabhatNeural"
RATE = "-5%"  # Slightly slower for natural feel
PITCH = "-2Hz"  # Slightly lower for warmth


async def generate_segment(idx, segment):
    output_path = os.path.join(OUTPUT_DIR, f"segment_{idx:02d}.mp3")
    communicate = edge_tts.Communicate(
        segment["text"],
        VOICE,
        rate=RATE,
        pitch=PITCH,
    )
    await communicate.save(output_path)
    print(f"  [{idx}] {segment['text'][:60]}...")
    return output_path


async def generate_all():
    print(f"Generating narration with voice: {VOICE}")
    paths = []
    for i, seg in enumerate(SEGMENTS):
        path = await generate_segment(i, seg)
        paths.append(path)
    return paths


def create_silence(duration_ms, output_path):
    subprocess.run([
        "/home/spatchava/.local/bin/ffmpeg", "-y",
        "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
        "-t", str(duration_ms / 1000),
        "-c:a", "libmp3lame", "-q:a", "9",
        output_path,
    ], capture_output=True)


def concatenate(segment_paths, segments):
    print("Concatenating with pauses...")
    parts = []
    for i, (path, seg) in enumerate(zip(segment_paths, segments)):
        parts.append(path)
        if seg.get("pause_after", 0) > 0:
            silence_path = os.path.join(OUTPUT_DIR, f"silence_{i:02d}.mp3")
            create_silence(int(seg["pause_after"] * 1000), silence_path)
            parts.append(silence_path)

    list_path = os.path.join(OUTPUT_DIR, "concat_list.txt")
    with open(list_path, "w") as f:
        for part in parts:
            f.write(f"file '{part}'\n")

    output = os.path.join(OUTPUT_DIR, "full_narration.mp3")
    subprocess.run([
        "/home/spatchava/.local/bin/ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", list_path,
        "-c:a", "libmp3lame", "-q:a", "2",
        output,
    ], capture_output=True)
    print(f"Narration saved: {output}")
    return output


def get_duration(path):
    result = subprocess.run([
        "/home/spatchava/.local/bin/ffmpeg", "-i", path, "-f", "null", "-",
    ], capture_output=True, text=True)
    for line in result.stderr.split("\n"):
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            parts = t.split(":")
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    return 0


def combine_video_audio(video_path, audio_path, output_path):
    """Combine video + audio, looping video if audio is longer."""
    audio_dur = get_duration(audio_path)
    print(f"Audio duration: {audio_dur:.1f}s")

    # Loop video to match audio length
    subprocess.run([
        "/home/spatchava/.local/bin/ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(audio_dur),
        "-pix_fmt", "yuv420p",
        output_path,
    ], capture_output=True)

    if os.path.exists(output_path):
        size = os.path.getsize(output_path) / 1024 / 1024
        print(f"Final video: {output_path} ({size:.1f} MB)")
    else:
        print("ERROR: Video combination failed")


async def main():
    # Generate TTS
    paths = await generate_all()
    narration = concatenate(paths, SEGMENTS)
    duration = get_duration(narration)
    print(f"Total narration: {duration:.1f}s")

    # Combine with main promo video (looped to match narration)
    video = "/home/spatchava/embeddedos-org/EoStudio/promo/media/videos/eostudio_promo/1080p60/EoStudioPromo.mp4"
    output = os.path.join(OUTPUT_DIR, "EoStudio_Founder_Narrated_1080p.mp4")

    if os.path.exists(video):
        combine_video_audio(video, narration, output)

        # Copy to Desktop
        desktop = "/mnt/c/Users/spatchava/Desktop/EoStudio_Founder_Narrated_1080p.mp4"
        subprocess.run(["cp", output, desktop], capture_output=True)

        desktop_mp3 = "/mnt/c/Users/spatchava/Desktop/EoStudio_Founder_Narration.mp3"
        subprocess.run(["cp", narration, desktop_mp3], capture_output=True)
        print("Copied to Desktop!")
    else:
        print(f"Video not found: {video}")
        print(f"Audio ready at: {narration}")


if __name__ == "__main__":
    asyncio.run(main())
