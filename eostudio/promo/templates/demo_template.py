"""Demo video template — Manim-based product demo with typing, transitions, and subtitles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TypingSequence:
    """A simulated typing sequence for demo videos."""
    text: str
    start_time: float
    typing_speed: float = 0.05  # seconds per character
    cursor_blink: bool = True


@dataclass
class UITransition:
    """A UI state transition for demo videos."""
    from_state: str
    to_state: str
    start_time: float
    duration: float = 0.5
    effect: str = "fade"  # "fade", "slide_left", "slide_right", "zoom"


@dataclass
class DemoScene:
    """A single scene in a product demo video."""
    title: str
    duration: float
    description: str = ""
    typing_sequences: List[TypingSequence] = field(default_factory=list)
    transitions: List[UITransition] = field(default_factory=list)
    narration: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title, "duration": self.duration,
            "description": self.description, "narration": self.narration,
            "typing_count": len(self.typing_sequences),
            "transition_count": len(self.transitions),
        }


@dataclass
class DemoTemplate:
    """Complete product demo video template with scenes, typing, and transitions.

    Generates Manim scene code for rendering product demo videos with:
    - Simulated IDE typing effects
    - UI state transitions
    - Feature callout overlays
    - Subtitle/narration support
    """
    product_name: str
    scenes: List[DemoScene] = field(default_factory=list)
    width: int = 1920
    height: int = 1080
    fps: int = 30
    background_color: str = "#0f172a"
    accent_color: str = "#3b82f6"

    def add_scene(self, title: str, duration: float, **kwargs: Any) -> DemoScene:
        """Add a scene to the demo."""
        scene = DemoScene(title=title, duration=duration, **kwargs)
        self.scenes.append(scene)
        return scene

    @property
    def total_duration(self) -> float:
        return sum(s.duration for s in self.scenes)

    def to_manim_script(self) -> str:
        """Generate a Manim Python script for the demo video."""
        lines = [
            "from manim import *",
            "",
            "",
            f"class {self._class_name}(Scene):",
            f'    """Product demo for {self.product_name}."""',
            "",
            "    def construct(self):",
            f'        self.camera.background_color = "{self.background_color}"',
            "",
        ]

        for i, scene in enumerate(self.scenes):
            lines.append(f"        # --- Scene {i+1}: {scene.title} ---")

            if i == 0:
                # Intro: Product name reveal
                lines.extend([
                    f'        title = Text("{self.product_name}", font_size=72, color=WHITE)',
                    f"        title.set_weight(BOLD)",
                    f"        self.play(Write(title), run_time=1.5)",
                ])
                if scene.description:
                    lines.extend([
                        f'        subtitle = Text("{scene.description}", font_size=28, color=GRAY)',
                        f"        subtitle.next_to(title, DOWN, buff=0.5)",
                        f"        self.play(FadeIn(subtitle), run_time=0.8)",
                    ])
                lines.append(f"        self.wait({scene.duration - 2.5})")
                lines.append(f"        self.play(FadeOut(title), FadeOut(subtitle) if 'subtitle' in dir() else Wait(0))")
            else:
                # Feature scene with title
                lines.extend([
                    f'        scene_title = Text("{scene.title}", font_size=48, color=WHITE)',
                    f"        scene_title.set_weight(BOLD)",
                    f"        scene_title.to_edge(UP, buff=0.5)",
                    f"        self.play(FadeIn(scene_title), run_time=0.5)",
                ])

                # Add typing sequences
                for j, ts in enumerate(scene.typing_sequences):
                    lines.extend([
                        f'        code_{j} = Code(',
                        f'            code="""{ts.text}""",',
                        f'            language="typescript",',
                        f'            font_size=16,',
                        f'            background="rectangle",',
                        f'            background_stroke_color="{self.accent_color}",',
                        f"        )",
                        f"        self.play(Create(code_{j}), run_time={len(ts.text) * ts.typing_speed})",
                    ])

                # Add transitions
                for t in scene.transitions:
                    effect_fn = {
                        "fade": "FadeIn",
                        "slide_left": "FadeIn",
                        "slide_right": "FadeIn",
                        "zoom": "GrowFromCenter",
                    }.get(t.effect, "FadeIn")
                    lines.extend([
                        f'        transition_text = Text("{t.to_state}", font_size=24, color=GRAY)',
                        f"        self.play({effect_fn}(transition_text), run_time={t.duration})",
                    ])

                remaining = scene.duration - 1.0
                if remaining > 0:
                    lines.append(f"        self.wait({remaining:.1f})")
                lines.append(f"        self.clear()")

            lines.append("")

        # Final CTA
        lines.extend([
            f"        # --- Final CTA ---",
            f'        cta = Text("Try it now", font_size=56, color=WHITE)',
            f"        cta.set_weight(BOLD)",
            f"        self.play(Write(cta), run_time=1.0)",
            f"        self.wait(2)",
        ])

        return "\n".join(lines) + "\n"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_name": self.product_name,
            "total_duration": self.total_duration,
            "scene_count": len(self.scenes),
            "scenes": [s.to_dict() for s in self.scenes],
            "dimensions": f"{self.width}x{self.height}",
            "fps": self.fps,
        }

    @property
    def _class_name(self) -> str:
        return "".join(w.capitalize() for w in self.product_name.split()) + "Demo"


def create_quick_demo(product_name: str, features: List[str],
                      url: str = "") -> DemoTemplate:
    """Create a quick product demo template from a product name and feature list."""
    demo = DemoTemplate(product_name=product_name)

    # Intro scene
    demo.add_scene(
        title=product_name,
        duration=5.0,
        description=f"Introducing {product_name}",
    )

    # Feature scenes
    for feat in features:
        scene = demo.add_scene(title=feat, duration=8.0)
        scene.typing_sequences.append(
            TypingSequence(
                text=f"// {feat} implementation\nconst {feat.lower().replace(' ', '_')} = new Feature();",
                start_time=1.0,
            )
        )
        scene.transitions.append(
            UITransition(from_state="code", to_state="preview", start_time=4.0)
        )

    # CTA scene
    if url:
        demo.add_scene(title="Get Started", duration=4.0, description=url)

    return demo
