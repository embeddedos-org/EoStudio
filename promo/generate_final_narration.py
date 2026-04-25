"""Generate improved narration — deeper, natural American voice, no pitch issues."""

import asyncio
import edge_tts
import subprocess
import os

OUTPUT_DIR = "/home/spatchava/embeddedos-org/EoStudio/promo/narrated_v4"
os.makedirs(OUTPUT_DIR, exist_ok=True)

SEGMENTS = [
    {"text": "Hey everyone. I'm really excited to show you EoStudio. It's an open-source design suite that we built to solve a real problem. Why do we need ten different tools, when one can do it all?", "pause_after": 1.0},
    {"text": "EoStudio has thirteen design editors built right in. You get 3D modeling, CAD design, image editing, game design, UI UX prototyping, interior design, UML diagrams, simulation, database design, hardware PCB layout, a full IDE, and a brand new promo video editor. All in one app.", "pause_after": 1.0},
    {"text": "Now here's the part I'm most proud of. We built a complete animation engine from scratch. It has spring physics, just like Framer Motion. Twenty five animation presets. A visual timeline editor. And twenty four easing functions including cubic bezier.", "pause_after": 1.0},
    {"text": "The AI features are seriously powerful. Describe your UI in plain English, and EoStudio generates animated components instantly. Upload a screenshot, and it extracts every component. Generate a complete design system from just a brand description.", "pause_after": 0.8},
    {"text": "We also built an accessibility auditor. It checks your designs against WCAG two point one double A standards and gives you specific fix suggestions. Because great design should be accessible to everyone.", "pause_after": 1.0},
    {"text": "Prototyping is fully interactive. Click interactions, hover effects, swipe gestures, and state machines. Export it all as a shareable HTML prototype with one click.", "pause_after": 1.0},
    {"text": "Code generation is where EoStudio really shines. Thirty three plus frameworks. React with Framer Motion, Flutter, Swift, Kotlin, Electron, GSAP, and many more. Design once, deploy everywhere.", "pause_after": 1.0},
    {"text": "And we didn't stop there. There's a built-in promo editor for creating App Store previews, social media posts, and product launch videos. Because you shouldn't need Runway or Canva just to promote your own product.", "pause_after": 1.0},
    {"text": "EoStudio version one point oh. Community Edition. It's completely free, open source, MIT licensed. Go check it out on GitHub. We'd love to hear what you build with it. Thank you.", "pause_after": 1.5},
]

# GuyNeural = deeper male voice, lower pitch for warmth, slower for natural feel
VOICE = "en-US-GuyNeural"
RATE = "-8%"
PITCH = "-6Hz"


async def generate_segment(idx, seg):
    path = os.path.join(OUTPUT_DIR, f"seg_{idx:02d}.mp3")
    comm = edge_tts.Communicate(seg["text"], VOICE, rate=RATE, pitch=PITCH)
    await comm.save(path)
    print(f"  [{idx}] {seg['text'][:55]}...")
    return path

async def generate_all():
    print(f"Voice: {VOICE} | Rate: {RATE} | Pitch: {PITCH}")
    return [await generate_segment(i, s) for i, s in enumerate(SEGMENTS)]

def silence(ms, path):
    subprocess.run(["/home/spatchava/.local/bin/ffmpeg", "-y", "-f", "lavfi",
                    "-i", "anullsrc=r=24000:cl=mono", "-t", str(ms/1000),
                    "-c:a", "libmp3lame", "-q:a", "9", path], capture_output=True)

def concat(paths, segs):
    parts = []
    for i, (p, s) in enumerate(zip(paths, segs)):
        parts.append(p)
        if s.get("pause_after", 0) > 0:
            sp = os.path.join(OUTPUT_DIR, f"sil_{i:02d}.mp3")
            silence(int(s["pause_after"] * 1000), sp)
            parts.append(sp)
    lp = os.path.join(OUTPUT_DIR, "list.txt")
    with open(lp, "w") as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    out = os.path.join(OUTPUT_DIR, "narration.mp3")
    subprocess.run(["/home/spatchava/.local/bin/ffmpeg", "-y", "-f", "concat",
                    "-safe", "0", "-i", lp, "-c:a", "libmp3lame", "-q:a", "2", out],
                   capture_output=True)
    return out

def duration(path):
    r = subprocess.run(["/home/spatchava/.local/bin/ffmpeg", "-i", path, "-f", "null", "-"],
                       capture_output=True, text=True)
    for l in r.stderr.split("\n"):
        if "Duration:" in l:
            t = l.split("Duration:")[1].split(",")[0].strip().split(":")
            return float(t[0])*3600 + float(t[1])*60 + float(t[2])
    return 0

async def main():
    paths = await generate_all()
    audio = concat(paths, SEGMENTS)
    dur = duration(audio)
    print(f"Duration: {dur:.1f}s")

    video = "/home/spatchava/embeddedos-org/EoStudio/promo/media/videos/eostudio_promo/1080p60/EoStudioPromo.mp4"
    out = os.path.join(OUTPUT_DIR, "EoStudio_Final_1080p.mp4")

    subprocess.run(["/home/spatchava/.local/bin/ffmpeg", "-y",
                    "-stream_loop", "-1", "-i", video, "-i", audio,
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-c:a", "aac", "-b:a", "192k", "-t", str(dur),
                    "-pix_fmt", "yuv420p", out], capture_output=True)

    if os.path.exists(out):
        sz = os.path.getsize(out) / 1024 / 1024
        print(f"Video: {out} ({sz:.1f} MB)")
        subprocess.run(["cp", out, "/mnt/c/Users/spatchava/Desktop/EoStudio_Final_Narrated_1080p.mp4"], capture_output=True)
        subprocess.run(["cp", audio, "/mnt/c/Users/spatchava/Desktop/EoStudio_Final_Narration.mp3"], capture_output=True)
        print("Copied to Desktop!")

if __name__ == "__main__":
    asyncio.run(main())
