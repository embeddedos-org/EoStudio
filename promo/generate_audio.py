"""Generate narration audio using Google Text-to-Speech."""
from gtts import gTTS

NARRATION = (
    "Introducing EoStudio. A cross-platform design suite powered by AI. Feature one: AI code generation turns natural language into production-ready code. Feature two: Spec-driven development generates requirements, design, and tasks automatically. Feature three: Production UI kit with 39 accessible React components. EoStudio. Open source and AI powered. Visit github dot com slash embeddedos-org slash EoStudio."
)

tts = gTTS(text=NARRATION, lang="en", slow=False)
tts.save("narration.mp3")
print(f"Generated narration.mp3 ({len(NARRATION)} chars)")
