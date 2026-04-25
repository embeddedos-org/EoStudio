"""Generate narrated EoStudio promo — American accent, confident founder style."""

import asyncio
import edge_tts
import subprocess
import os

OUTPUT_DIR = "/home/spatchava/embeddedos-org/EoStudio/promo/narrated_v3"
os.makedirs(OUTPUT_DIR, exist_ok=True)

SEGMENTS = [
    {
        "text": "Hey everyone. I'm really excited to show you EoStudio. It's an open-source design suite that we built to solve a real problem. Why do we need ten different tools, when one can do it all?",
        "pause_after": 0.8,
    },
    {
        "text": "EoStudio has thirteen design editors built right in. You get 3D modeling, CAD design, image editing, game design, UI/UX prototyping, interior design, UML diagrams, simulation, database design, hardware PCB layout, a full IDE, and a brand new promo video editor. All in one app.",
        "pause_after": 0.8,
    },
    {
        "text": "Now here's the part I'm most proud of. We built a complete animation engine from scratch. It has spring physics, just like Framer Motion. Twenty five animation presets. A visual timeline editor where you can drag keyframes around. And twenty four easing functions including cubic bezier support.",
        "pause_after": 0.8,
    },
    {
        "text": "The AI features are seriously powerful. You can describe your UI in plain English, and EoStudio generates the entire component tree with entrance animations. You can upload a screenshot of any app, and it'll extract every single component. You can even generate a complete design system from just a brand description.",
        "pause_after": 0.6,
    },
    {
        "text": "We also built an accessibility auditor. It checks your designs against WCAG two point one double A standards and gives you specific fix suggestions. Because great design should be accessible to everyone.",
        "pause_after": 0.8,
    },
    {
        "text": "Prototyping is fully interactive. You can add click interactions, hover effects, swipe gestures, and even build state machines with variables and conditions. And you can export the whole thing as a shareable HTML prototype with one click.",
        "pause_after": 0.8,
    },
    {
        "text": "Code generation is where EoStudio really shines. We support thirty three plus frameworks. React with Framer Motion, React with GSAP, Flutter, Swift, Kotlin, Electron, Tauri, Vue, Angular, Django, FastAPI, and many more. Design once, deploy everywhere.",
        "pause_after": 0.8,
    },
    {
        "text": "And we didn't stop there. There's a built-in promo editor for creating App Store previews, social media posts, and product launch videos. Because you shouldn't need Runway or Canva just to promote your own product.",
        "pause_after": 0.8,
    },
    {
        "text": "EoStudio version one point oh. Community Edition. It's completely free, open source, MIT licensed. Go check it out on GitHub. We'd love to hear what you build with it. Thank you.",
        "pause_after": 1.5,
    },
]

VOICE = "en-US-AndrewNeural"
RATE = "-3%"
PITCH = "+0Hz"


async def generate_segment(idx, segment):
    output_path = os.path.join(OUTPUT_DIR, f"segment_{idx:02d}.mp3")
    communicate = edge_tts.Communicate(segment["text"], VOICE, rate=RATE, pitch=PITCH)
    await communicate.save(output_path)
    print(f"  [{idx}] {segment['text'][:60]}...")
    return output_path


async def generate_all():
    print(f"Voice: {VOICE} (American, Warm, Confident)")
    paths = []
    for i, seg in enumerate(SEGMENTS):
        paths.append(await generate_segment(i, seg))
    return paths


def create_silence(duration_ms, output_path):
    subprocess.run([
        "/home/spatchava/.local/bin/ffmpeg", "-y",
        "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
        "-t", str(duration_ms / 1000),
        "-c:a", "libmp3lame", "-q:a", "9", output_path,
    ], capture_output=True)


def concatenate(segment_paths, segments):
    print("Joining segments...")
    parts = []
    for i, (path, seg) in enumerate(zip(segment_paths, segments)):
        parts.append(path)
        if seg.get("pause_after", 0) > 0:
            sp = os.path.join(OUTPUT_DIR, f"silence_{i:02d}.mp3")
            create_silence(int(seg["pause_after"] * 1000), sp)
            parts.append(sp)

    lp = os.path.join(OUTPUT_DIR, "concat_list.txt")
    with open(lp, "w") as f:
        for p in parts:
            f.write(f"file '{p}'\n")

    out = os.path.join(OUTPUT_DIR, "full_narration.mp3")
    subprocess.run([
        "/home/spatchava/.local/bin/ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", lp,
        "-c:a", "libmp3lame", "-q:a", "2", out,
    ], capture_output=True)
    return out


def get_duration(path):
    r = subprocess.run(["/home/spatchava/.local/bin/ffmpeg", "-i", path, "-f", "null", "-"],
                       capture_output=True, text=True)
    for line in r.stderr.split("\n"):
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip().split(":")
            return float(t[0]) * 3600 + float(t[1]) * 60 + float(t[2])
    return 0


async def main():
    paths = await generate_all()
    narration = concatenate(paths, SEGMENTS)
    dur = get_duration(narration)
    print(f"Narration: {dur:.1f}s")

    video = "/home/spatchava/embeddedos-org/EoStudio/promo/media/videos/eostudio_promo/1080p60/EoStudioPromo.mp4"
    output = os.path.join(OUTPUT_DIR, "EoStudio_Narrated_American_1080p.mp4")

    if os.path.exists(video):
        print("Combining video (looped) + audio...")
        subprocess.run([
            "/home/spatchava/.local/bin/ffmpeg", "-y",
            "-stream_loop", "-1", "-i", video,
            "-i", narration,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(dur), "-pix_fmt", "yuv420p", output,
        ], capture_output=True)

        if os.path.exists(output):
            sz = os.path.getsize(output) / 1024 / 1024
            print(f"Final: {output} ({sz:.1f} MB)")
            subprocess.run(["cp", output, "/mnt/c/Users/spatchava/Desktop/EoStudio_Narrated_American_1080p.mp4"], capture_output=True)
            subprocess.run(["cp", narration, "/mnt/c/Users/spatchava/Desktop/EoStudio_American_Narration.mp3"], capture_output=True)
            print("Copied to Desktop!")

if __name__ == "__main__":
    asyncio.run(main())
