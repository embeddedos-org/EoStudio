"""EoStudio v1.0 Promo Video — rendered with Manim."""

from manim import *

# Colors
BG = "#0a0a1a"
PRIMARY = "#3b82f6"
SECONDARY = "#8b5cf6"
ACCENT = "#ec4899"
CYAN = "#22d3ee"
GREEN = "#22c55e"
AMBER = "#f59e0b"
SLATE = "#94a3b8"
DARK_SLATE = "#64748b"
CARD_BG = "#1e1e2e"


class EoStudioPromo(Scene):
    def construct(self):
        self.camera.background_color = BG
        self.slide_hero()
        self.slide_editors()
        self.slide_animation()
        self.slide_ai()
        self.slide_cta()

    # ---- Slide 1: Hero ----
    def slide_hero(self):
        # Glow
        glow = Circle(radius=3, fill_opacity=0.15, fill_color=SECONDARY, stroke_width=0)
        glow.set_opacity(0)

        # Title
        title = Text("EoStudio", font_size=96, font="Inter", weight=BOLD)
        title.set_color_by_gradient(PRIMARY, SECONDARY, ACCENT)

        tagline = Text("Design Everything.", font_size=40, color=SLATE, font="Inter")
        tagline.next_to(title, DOWN, buff=0.3)

        version = Text("v1.0.0 — Community Edition", font_size=20, color=PRIMARY, font="Inter")
        version_box = SurroundingRectangle(version, color=PRIMARY, buff=0.15, corner_radius=0.2, stroke_width=1)
        version_group = VGroup(version, version_box).next_to(tagline, DOWN, buff=0.4)

        subtitle = Text(
            "13 editors · 33+ code generators · AI-powered · Animation engine",
            font_size=18, color=DARK_SLATE, font="Inter"
        )
        subtitle.next_to(version_group, DOWN, buff=0.5)

        self.play(FadeIn(glow, scale=0.5), run_time=0.5)
        self.play(glow.animate.set_opacity(0.12), run_time=0.3)
        self.play(Write(title), run_time=0.8)
        self.play(FadeIn(tagline, shift=UP * 0.3), run_time=0.5)
        self.play(Create(version_box), FadeIn(version), run_time=0.4)
        self.play(FadeIn(subtitle, shift=UP * 0.2), run_time=0.4)
        self.wait(1.5)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.5)

    # ---- Slide 2: 13 Editors ----
    def slide_editors(self):
        title = Text("13 Design Editors", font_size=56, font="Inter", weight=BOLD)
        title.set_color_by_gradient(PRIMARY, CYAN)
        title.to_edge(UP, buff=0.8)

        editors = [
            ("3D", PRIMARY), ("CAD", CYAN), ("Image", GREEN), ("Game", ACCENT),
            ("UI/UX", SECONDARY), ("Product", AMBER), ("Interior", GREEN), ("UML", PRIMARY),
            ("Sim", CYAN), ("DB", SECONDARY), ("HW", ACCENT), ("IDE", PRIMARY),
            ("Promo", SECONDARY),
        ]

        cards = VGroup()
        for name, color in editors:
            card = VGroup()
            bg = RoundedRectangle(
                width=1.6, height=1.1, corner_radius=0.15,
                fill_color=CARD_BG, fill_opacity=0.8,
                stroke_color=color, stroke_width=1
            )
            label = Text(name, font_size=16, color=WHITE, font="Inter", weight=BOLD)
            label.move_to(bg)
            card.add(bg, label)
            cards.add(card)

        # Arrange in rows
        row1 = VGroup(*cards[:4]).arrange(RIGHT, buff=0.2)
        row2 = VGroup(*cards[4:8]).arrange(RIGHT, buff=0.2)
        row3 = VGroup(*cards[8:12]).arrange(RIGHT, buff=0.2)
        row4 = VGroup(cards[12]).arrange(RIGHT, buff=0.2)
        grid = VGroup(row1, row2, row3, row4).arrange(DOWN, buff=0.2)
        grid.next_to(title, DOWN, buff=0.5)

        # Highlight the new Promo editor
        cards[12][0].set_stroke(color=SECONDARY, width=2)

        self.play(Write(title), run_time=0.5)
        for i, card in enumerate(cards):
            self.play(FadeIn(card, scale=0.7), run_time=0.12)
        self.wait(1.5)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.5)

    # ---- Slide 3: Animation Engine ----
    def slide_animation(self):
        title = Text("Animation Engine", font_size=56, font="Inter", weight=BOLD)
        title.set_color_by_gradient(SECONDARY, ACCENT)
        title.to_edge(UP, buff=0.8)

        sub = Text(
            "Spring physics · 25 presets · Framer Motion + GSAP codegen",
            font_size=20, color="#c4b5fd", font="Inter"
        )
        sub.next_to(title, DOWN, buff=0.3)

        # Animated boxes
        boxes = VGroup()
        for label, color in [("Bounce", PRIMARY), ("Pulse", SECONDARY), ("Shake", ACCENT), ("Spin", CYAN)]:
            bg = RoundedRectangle(
                width=1.8, height=1.4, corner_radius=0.2,
                fill_color=color, fill_opacity=0.9, stroke_width=0
            )
            txt = Text(label, font_size=18, color=WHITE, font="Inter", weight=BOLD)
            txt.move_to(bg)
            boxes.add(VGroup(bg, txt))
        boxes.arrange(RIGHT, buff=0.4)
        boxes.next_to(sub, DOWN, buff=0.6)

        # Preset tags
        preset_names = ["fadeIn", "fadeInUp", "slideUp", "scaleIn", "popIn",
                        "bounceIn", "pulse", "shake", "wobble", "revealUp",
                        "spring:gentle", "spring:wobbly", "spring:stiff"]
        tags = VGroup()
        for name in preset_names:
            tag_bg = RoundedRectangle(
                width=len(name) * 0.13 + 0.4, height=0.35, corner_radius=0.15,
                fill_color="#1a1a2e", fill_opacity=0.8,
                stroke_color=SECONDARY, stroke_width=0.5
            )
            tag_txt = Text(name, font_size=12, color="#c4b5fd", font="Inter")
            tag_txt.move_to(tag_bg)
            tags.add(VGroup(tag_bg, tag_txt))
        tags.arrange_in_grid(rows=2, buff=0.1)
        tags.next_to(boxes, DOWN, buff=0.5)

        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=0.5)
        self.play(LaggedStart(*[FadeIn(b, scale=0.5) for b in boxes], lag_ratio=0.15), run_time=0.8)

        # Animate each box
        self.play(
            boxes[0].animate.shift(UP * 0.4),  # bounce up
            boxes[1].animate.scale(1.15),  # pulse
            boxes[2].animate.shift(RIGHT * 0.15),  # shake
            boxes[3].animate.rotate(PI / 4),  # spin start
            run_time=0.4
        )
        self.play(
            boxes[0].animate.shift(DOWN * 0.4),
            boxes[1].animate.scale(1 / 1.15),
            boxes[2].animate.shift(LEFT * 0.15),
            boxes[3].animate.rotate(-PI / 4),
            run_time=0.3
        )

        self.play(LaggedStart(*[FadeIn(t, scale=0.8) for t in tags], lag_ratio=0.05), run_time=0.8)
        self.wait(1)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.5)

    # ---- Slide 4: AI ----
    def slide_ai(self):
        title = Text("AI-Powered Design", font_size=56, font="Inter", weight=BOLD)
        title.set_color_by_gradient(CYAN, PRIMARY)
        title.to_edge(UP, buff=0.8)

        sub = Text("Ollama (local & private) + OpenAI API", font_size=20, color=SLATE, font="Inter")
        sub.next_to(title, DOWN, buff=0.3)

        features = [
            ("Text → UI", "Describe UI, get\nanimated components"),
            ("Screenshot → UI", "Upload screenshot,\nextract components"),
            ("AI Design System", "Generate tokens\nfrom brand"),
            ("A11y Audit", "WCAG 2.1 AA\nwith fix suggestions"),
            ("Smart Layout", "AI-optimized\nper device"),
            ("Prototyping", "Gestures & state\nmachines"),
        ]

        cards = VGroup()
        for feat_title, feat_desc in features:
            card = VGroup()
            bg = RoundedRectangle(
                width=2.8, height=1.6, corner_radius=0.15,
                fill_color="#0f2744", fill_opacity=0.8,
                stroke_color=PRIMARY, stroke_width=0.5
            )
            t = Text(feat_title, font_size=16, color=WHITE, font="Inter", weight=BOLD)
            d = Text(feat_desc, font_size=11, color=SLATE, font="Inter", line_spacing=0.8)
            t.move_to(bg.get_top() + DOWN * 0.4)
            d.move_to(bg.get_center() + DOWN * 0.2)
            card.add(bg, t, d)
            cards.add(card)

        row1 = VGroup(*cards[:3]).arrange(RIGHT, buff=0.2)
        row2 = VGroup(*cards[3:]).arrange(RIGHT, buff=0.2)
        grid = VGroup(row1, row2).arrange(DOWN, buff=0.2)
        grid.next_to(sub, DOWN, buff=0.5)

        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=0.5)
        self.play(LaggedStart(*[FadeIn(c, scale=0.8) for c in cards], lag_ratio=0.12), run_time=1)
        self.wait(1.5)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.5)

    # ---- Slide 5: CTA ----
    def slide_cta(self):
        title = Text("Design Everything.", font_size=72, font="Inter", weight=BOLD)
        title.set_color_by_gradient(PRIMARY, SECONDARY, ACCENT, AMBER)

        sub = Text("Open Source · MIT License · Free Forever", font_size=28, color=SLATE, font="Inter")
        sub.next_to(title, DOWN, buff=0.3)

        url_bg = RoundedRectangle(
            width=8, height=0.8, corner_radius=0.15,
            fill_opacity=0.9, stroke_width=0
        )
        url_bg.set_color_by_gradient(PRIMARY, SECONDARY)
        url_text = Text("github.com/embeddedos-org/EoStudio", font_size=22, color=WHITE, font="Inter", weight=BOLD)
        url_text.move_to(url_bg)
        url_group = VGroup(url_bg, url_text).next_to(sub, DOWN, buff=0.5)

        # Stats
        stats = VGroup()
        for num, label in [("13", "Editors"), ("33+", "Frameworks"), ("25", "Animations"), ("200+", "Tests")]:
            stat = VGroup()
            n = Text(num, font_size=48, color=PRIMARY, font="Inter", weight=BOLD)
            l = Text(label, font_size=16, color=DARK_SLATE, font="Inter")
            l.next_to(n, DOWN, buff=0.1)
            stat.add(n, l)
            stats.add(stat)
        stats.arrange(RIGHT, buff=1)
        stats.next_to(url_group, DOWN, buff=0.7)

        self.play(Write(title), run_time=0.8)
        self.play(FadeIn(sub, shift=UP * 0.2), run_time=0.4)
        self.play(FadeIn(url_group, scale=0.9), run_time=0.5)
        self.play(LaggedStart(*[FadeIn(s, shift=UP * 0.3) for s in stats], lag_ratio=0.15), run_time=0.6)
        self.wait(2)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.8)
