"""Generate narrated EoStudio promo video — TTS audio + Manim visuals."""

import asyncio
import edge_tts
import subprocess
import os

OUTPUT_DIR = "/home/spatchava/embeddedos-org/EoStudio/promo/narrated"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Professional product narration script — timed segments
SEGMENTS = [
    {
        "text": "Introducing EoStudio. The open-source design suite that does it all.",
        "pause_after": 0.5,
    },
    {
        "text": "Thirteen powerful editors. From 3D modeling and CAD design, to UI/UX prototyping, game development, and even PCB hardware layout.",
        "pause_after": 0.5,
    },
    {
        "text": "A built-in animation engine with spring physics, twenty-five animation presets, and a visual timeline editor. Better than Framer Motion.",
        "pause_after": 0.5,
    },
    {
        "text": "AI-powered design generation. Describe your UI in plain English, and EoStudio generates animated components instantly. Upload a screenshot, and we'll extract every component. Generate full design systems from a single brand description.",
        "pause_after": 0.5,
    },
    {
        "text": "Interactive prototyping with gestures, screen transitions, and state machines. Export as a shareable HTML prototype with one click.",
        "pause_after": 0.5,
    },
    {
        "text": "Thirty-three plus code generators. Export to React with Framer Motion, Flutter, Swift, Kotlin, Electron, GSAP, and dozens more. Design once, deploy everywhere.",
        "pause_after": 0.5,
    },
    {
        "text": "Built-in video and promo generation. Create App Store previews, social media posts, and product launch videos right inside the editor.",
        "pause_after": 0.5,
    },
    {
        "text": "EoStudio version one point oh. Community Edition. Free, open source, MIT licensed. Download it today on GitHub.",
        "pause_after": 1.0,
    },
]

# Microsoft neural voice - professional male narrator
VOICE = "en-US-GuyNeural"
RATE = "+5%"
PITCH = "+0Hz"


async def generate_segment(idx, segment):
    """Generate a single audio segment."""
    output_path = os.path.join(OUTPUT_DIR, f"segment_{idx:02d}.mp3")
    communicate = edge_tts.Communicate(
        segment["text"],
        VOICE,
        rate=RATE,
        pitch=PITCH,
    )
    await communicate.save(output_path)
    print(f"  Generated segment {idx}: {segment['text'][:50]}...")
    return output_path


async def generate_all_segments():
    """Generate all audio segments."""
    print("Generating narration segments...")
    paths = []
    for i, seg in enumerate(SEGMENTS):
        path = await generate_segment(i, seg)
        paths.append(path)
    return paths


def create_silence(duration_ms, output_path):
    """Create a silent audio file."""
    subprocess.run([
        "/home/spatchava/.local/bin/ffmpeg", "-y",
        "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono",
        "-t", str(duration_ms / 1000),
        "-c:a", "libmp3lame", "-q:a", "9",
        output_path,
    ], capture_output=True)


def concatenate_with_pauses(segment_paths, segments):
    """Concatenate all segments with pauses between them."""
    print("Concatenating segments with pauses...")
    parts = []
    for i, (path, seg) in enumerate(zip(segment_paths, segments)):
        parts.append(path)
        if seg.get("pause_after", 0) > 0:
            silence_path = os.path.join(OUTPUT_DIR, f"silence_{i:02d}.mp3")
            create_silence(int(seg["pause_after"] * 1000), silence_path)
            parts.append(silence_path)

    # Create concat file list
    list_path = os.path.join(OUTPUT_DIR, "concat_list.txt")
    with open(list_path, "w") as f:
        for part in parts:
            f.write(f"file '{part}'\n")

    # Concatenate
    output = os.path.join(OUTPUT_DIR, "full_narration.mp3")
    subprocess.run([
        "/home/spatchava/.local/bin/ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_path,
        "-c:a", "libmp3lame", "-q:a", "2",
        output,
    ], capture_output=True)
    print(f"Full narration saved: {output}")
    return output


def get_audio_duration(path):
    """Get duration of audio file in seconds."""
    result = subprocess.run([
        "/home/spatchava/.local/bin/ffmpeg",
        "-i", path,
        "-f", "null", "-",
    ], capture_output=True, text=True)
    for line in result.stderr.split("\n"):
        if "Duration:" in line:
            time_str = line.split("Duration:")[1].split(",")[0].strip()
            parts = time_str.split(":")
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    return 0


async def main():
    # Step 1: Generate all TTS segments
    paths = await generate_all_segments()

    # Step 2: Concatenate with pauses
    narration_path = concatenate_with_pauses(paths, SEGMENTS)

    # Step 3: Get duration
    duration = get_audio_duration(narration_path)
    print(f"Total narration duration: {duration:.1f}s")

    # Step 4: Combine with existing video
    video_path = "/home/spatchava/embeddedos-org/EoStudio/promo/media/videos/eostudio_promo/1080p60/EoStudioPromo.mp4"
    output_path = os.path.join(OUTPUT_DIR, "EoStudio_Narrated_1080p.mp4")

    if os.path.exists(video_path):
        print("Combining video + narration...")
        subprocess.run([
            "/home/spatchava/.local/bin/ffmpeg", "-y",
            "-i", video_path,
            "-i", narration_path,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path,
        ], capture_output=True)
        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"Narrated video saved: {output_path} ({size / 1024 / 1024:.1f} MB)")
        else:
            print("Error: Video combination failed")
    else:
        print(f"Video not found at {video_path}")
        print(f"Narration audio is ready at: {narration_path}")
        print("Combine manually: ffmpeg -i video.mp4 -i full_narration.mp3 -c:v copy -c:a aac output.mp4")

    # Also save standalone narration
    standalone = "/mnt/c/Users/spatchava/Desktop/EoStudio_Narration.mp3"
    subprocess.run(["cp", narration_path, standalone], capture_output=True)
    print(f"Narration audio copied to Desktop")


if __name__ == "__main__":
    asyncio.run(main())
