"""EoStudio AI & Prototyping — showcasing AI generation, prototyping, and design system."""

from manim import *

BG = "#0a0a1a"
PRIMARY = "#3b82f6"
SECONDARY = "#8b5cf6"
ACCENT = "#ec4899"
CYAN = "#22d3ee"
GREEN = "#22c55e"
AMBER = "#f59e0b"
SLATE = "#94a3b8"
CARD_BG = "#1e1e2e"


class AIPrototypingVideo(Scene):
    def construct(self):
        self.camera.background_color = BG
        self.slide_intro()
        self.slide_text_to_ui()
        self.slide_design_system()
        self.slide_prototyping()
        self.slide_accessibility()
        self.slide_outro()

    def slide_intro(self):
        title = Text("AI + Prototyping", font_size=72, weight=BOLD)
        title.set_color_by_gradient(CYAN, PRIMARY)
        sub = Text("Generate. Prototype. Audit. Ship.", font_size=28, color=SLATE)
        sub.next_to(title, DOWN, buff=0.4)
        badge = Text("EoStudio v1.0", font_size=18, color=PRIMARY)
        badge.next_to(sub, DOWN, buff=0.3)

        self.play(Write(title), run_time=0.6)
        self.play(FadeIn(sub, shift=UP * 0.3), run_time=0.4)
        self.play(FadeIn(badge), run_time=0.3)
        self.wait(1.5)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.4)

    def slide_text_to_ui(self):
        title = Text("Text to Animated UI", font_size=48, weight=BOLD, color=CYAN)
        title.to_edge(UP, buff=0.6)

        # Prompt
        prompt_bg = RoundedRectangle(width=10, height=1, corner_radius=0.15,
                                      fill_color="#0d1117", fill_opacity=0.95,
                                      stroke_color=PRIMARY, stroke_width=1)
        prompt_bg.shift(UP * 1.5)
        prompt_text = Text('"Design a dashboard with charts and sidebar"',
                          font_size=16, color=GREEN, font="Monospace")
        prompt_text.move_to(prompt_bg)

        # Arrow
        arrow = Arrow(start=UP * 0.8, end=DOWN * 0.2, color=ACCENT, stroke_width=3)

        # Generated UI mockup
        ui_bg = RoundedRectangle(width=8, height=3.5, corner_radius=0.2,
                                  fill_color=CARD_BG, fill_opacity=0.9,
                                  stroke_color="#45475a", stroke_width=1)
        ui_bg.shift(DOWN * 1.8)

        # Sidebar
        sidebar = Rectangle(width=1.5, height=3.3, fill_color="#181825", fill_opacity=1, stroke_width=0)
        sidebar.align_to(ui_bg, LEFT).shift(RIGHT * 0.1)
        sidebar.align_to(ui_bg, UP).shift(DOWN * 0.1)

        # Nav items
        nav_items = VGroup()
        for i, label in enumerate(["Dashboard", "Analytics", "Users", "Settings"]):
            item_bg = Rectangle(width=1.3, height=0.3, fill_color=PRIMARY if i == 0 else "#0d1117",
                               fill_opacity=0.8 if i == 0 else 0.3, stroke_width=0)
            item_text = Text(label, font_size=9, color=WHITE)
            item_text.move_to(item_bg)
            nav_items.add(VGroup(item_bg, item_text))
        nav_items.arrange(DOWN, buff=0.08)
        nav_items.move_to(sidebar).shift(DOWN * 0.3)

        # Chart placeholders
        charts = VGroup()
        for i in range(3):
            chart = RoundedRectangle(width=1.8, height=1.2, corner_radius=0.1,
                                      fill_color="#181825", fill_opacity=0.8,
                                      stroke_color="#30363d", stroke_width=0.5)
            charts.add(chart)
        charts.arrange(RIGHT, buff=0.2)
        charts.shift(DOWN * 1.3 + RIGHT * 1)

        # Animation badges
        anim_badges = VGroup()
        for label in ["fadeInUp", "scaleIn", "stagger: 0.1s"]:
            bg = RoundedRectangle(width=len(label) * 0.11 + 0.4, height=0.3, corner_radius=0.12,
                                  fill_color=SECONDARY, fill_opacity=0.3,
                                  stroke_color=SECONDARY, stroke_width=0.5)
            txt = Text(label, font_size=10, color="#c4b5fd")
            txt.move_to(bg)
            anim_badges.add(VGroup(bg, txt))
        anim_badges.arrange(RIGHT, buff=0.1)
        anim_badges.shift(DOWN * 3.5)

        self.play(Write(title), run_time=0.4)
        self.play(FadeIn(prompt_bg), Write(prompt_text), run_time=0.5)
        self.play(GrowArrow(arrow), run_time=0.3)
        self.play(FadeIn(ui_bg), run_time=0.3)
        self.play(FadeIn(sidebar), LaggedStart(*[FadeIn(n, shift=RIGHT * 0.2) for n in nav_items], lag_ratio=0.1), run_time=0.5)
        self.play(LaggedStart(*[FadeIn(c, scale=0.8) for c in charts], lag_ratio=0.15), run_time=0.5)
        self.play(LaggedStart(*[FadeIn(b, shift=UP * 0.2) for b in anim_badges], lag_ratio=0.1), run_time=0.4)
        self.wait(1)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.4)

    def slide_design_system(self):
        title = Text("AI Design System", font_size=48, weight=BOLD, color=AMBER)
        title.to_edge(UP, buff=0.6)

        sub = Text("Generate tokens, palette, typography from a brand description", font_size=18, color=SLATE)
        sub.next_to(title, DOWN, buff=0.3)

        # Color palette
        palette_label = Text("Colors", font_size=16, color=WHITE, weight=BOLD)
        palette_label.shift(UP * 0.5 + LEFT * 4)

        colors = ["#2563eb", "#3b82f6", "#60a5fa", "#93c5fd", "#dbeafe"]
        swatches = VGroup()
        for c in colors:
            s = Square(side_length=0.6, fill_color=c, fill_opacity=1, stroke_width=0)
            swatches.add(s)
        swatches.arrange(RIGHT, buff=0.05)
        swatches.next_to(palette_label, DOWN, buff=0.2)

        # Typography
        type_label = Text("Typography", font_size=16, color=WHITE, weight=BOLD)
        type_label.shift(UP * 0.5 + RIGHT * 2)

        type_items = VGroup()
        for name, size in [("H1 — 36px Bold", 16), ("H2 — 30px Semi", 14), ("Body — 16px Regular", 12), ("Caption — 12px", 10)]:
            t = Text(name, font_size=size, color=SLATE)
            type_items.add(t)
        type_items.arrange(DOWN, buff=0.15, aligned_edge=LEFT)
        type_items.next_to(type_label, DOWN, buff=0.2)

        # Export options
        exports = VGroup()
        for label, color in [("CSS Variables", PRIMARY), ("Tailwind Config", CYAN), ("Style Dictionary", GREEN)]:
            bg = RoundedRectangle(width=2.5, height=0.45, corner_radius=0.2,
                                  fill_color=color, fill_opacity=0.85, stroke_width=0)
            txt = Text(label, font_size=14, color=WHITE, weight=BOLD)
            txt.move_to(bg)
            exports.add(VGroup(bg, txt))
        exports.arrange(RIGHT, buff=0.2)
        exports.shift(DOWN * 2)

        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=0.4)
        self.play(FadeIn(palette_label), run_time=0.2)
        self.play(LaggedStart(*[FadeIn(s, scale=0.5) for s in swatches], lag_ratio=0.08), run_time=0.4)
        self.play(FadeIn(type_label), run_time=0.2)
        self.play(LaggedStart(*[FadeIn(t, shift=RIGHT * 0.2) for t in type_items], lag_ratio=0.1), run_time=0.4)
        self.play(LaggedStart(*[FadeIn(e, scale=0.9) for e in exports], lag_ratio=0.1), run_time=0.5)
        self.wait(1)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.4)

    def slide_prototyping(self):
        title = Text("Interactive Prototyping", font_size=48, weight=BOLD, color=GREEN)
        title.to_edge(UP, buff=0.6)

        # Device frame
        device = RoundedRectangle(width=3, height=5.5, corner_radius=0.3,
                                   fill_color="#181825", fill_opacity=0.95,
                                   stroke_color="#45475a", stroke_width=2)
        device.shift(LEFT * 3)

        screen_label = Text("iPhone 14", font_size=12, color=SLATE)
        screen_label.next_to(device, UP, buff=0.15)

        # Screen content
        header = Rectangle(width=2.8, height=0.4, fill_color=PRIMARY, fill_opacity=0.8, stroke_width=0)
        header.align_to(device, UP).shift(DOWN * 0.3)
        header_txt = Text("My App", font_size=11, color=WHITE, weight=BOLD)
        header_txt.move_to(header)

        # Buttons
        btns = VGroup()
        for label in ["Login", "Sign Up", "Browse"]:
            bg = RoundedRectangle(width=2.4, height=0.4, corner_radius=0.1,
                                  fill_color="#313244", fill_opacity=0.8, stroke_width=0)
            txt = Text(label, font_size=11, color=WHITE)
            txt.move_to(bg)
            btns.add(VGroup(bg, txt))
        btns.arrange(DOWN, buff=0.15)
        btns.move_to(device).shift(DOWN * 0.5)

        # Interactions list
        inter_title = Text("Interactions", font_size=18, color=AMBER, weight=BOLD)
        inter_title.shift(RIGHT * 2.5 + UP * 1.5)

        interactions = VGroup()
        for txt in ["Click Login -> Navigate to /login", "Hover Sign Up -> Pulse animation",
                     "Swipe Left -> Slide transition", "Long Press -> Show context menu"]:
            item = Text(txt, font_size=12, color=SLATE)
            interactions.add(item)
        interactions.arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        interactions.next_to(inter_title, DOWN, buff=0.3)

        # Gestures
        gest_title = Text("Gesture Support", font_size=16, color=CYAN, weight=BOLD)
        gest_title.next_to(interactions, DOWN, buff=0.4)

        gestures = VGroup()
        for g in ["Tap", "Swipe", "Pinch", "Long Press"]:
            bg = RoundedRectangle(width=1.3, height=0.35, corner_radius=0.15,
                                  fill_color=CARD_BG, fill_opacity=0.8, stroke_color=CYAN, stroke_width=0.5)
            txt = Text(g, font_size=11, color=CYAN)
            txt.move_to(bg)
            gestures.add(VGroup(bg, txt))
        gestures.arrange(RIGHT, buff=0.1)
        gestures.next_to(gest_title, DOWN, buff=0.2)

        self.play(Write(title), run_time=0.4)
        self.play(FadeIn(device), FadeIn(screen_label), run_time=0.3)
        self.play(FadeIn(header), FadeIn(header_txt), run_time=0.2)
        self.play(LaggedStart(*[FadeIn(b, shift=UP * 0.2) for b in btns], lag_ratio=0.1), run_time=0.4)

        # Simulate click
        self.play(btns[0][0].animate.set_fill(PRIMARY, opacity=1), run_time=0.15)
        self.play(btns[0][0].animate.set_fill("#313244", opacity=0.8), run_time=0.15)

        self.play(FadeIn(inter_title), run_time=0.2)
        self.play(LaggedStart(*[FadeIn(i, shift=RIGHT * 0.2) for i in interactions], lag_ratio=0.1), run_time=0.5)
        self.play(FadeIn(gest_title), run_time=0.2)
        self.play(LaggedStart(*[FadeIn(g, scale=0.8) for g in gestures], lag_ratio=0.08), run_time=0.4)
        self.wait(1)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.4)

    def slide_accessibility(self):
        title = Text("AI Accessibility Audit", font_size=48, weight=BOLD, color=ACCENT)
        title.to_edge(UP, buff=0.6)

        sub = Text("WCAG 2.1 AA compliance with auto-fix suggestions", font_size=18, color=SLATE)
        sub.next_to(title, DOWN, buff=0.3)

        # Score
        score_num = Text("87", font_size=96, color=GREEN, weight=BOLD)
        score_label = Text("/ 100", font_size=28, color=SLATE)
        score_label.next_to(score_num, RIGHT, buff=0.1).shift(DOWN * 0.3)
        score_desc = Text("A11y Score", font_size=16, color=SLATE)
        score_desc.next_to(score_num, DOWN, buff=0.2)
        score_group = VGroup(score_num, score_label, score_desc).shift(LEFT * 3 + DOWN * 0.5)

        # Issues
        issues_title = Text("Issues Found", font_size=18, color=AMBER, weight=BOLD)
        issues_title.shift(RIGHT * 2 + UP * 0.5)

        issues = VGroup()
        issue_data = [
            ("Image missing alt text", ACCENT),
            ("Button too small (32x32)", AMBER),
            ("Input missing label", ACCENT),
            ("Low contrast ratio (3.2:1)", AMBER),
        ]
        for text, color in issue_data:
            dot = Dot(radius=0.06, color=color)
            txt = Text(text, font_size=13, color=SLATE)
            txt.next_to(dot, RIGHT, buff=0.15)
            issues.add(VGroup(dot, txt))
        issues.arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        issues.next_to(issues_title, DOWN, buff=0.3)

        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=0.4)
        self.play(Write(score_num), FadeIn(score_label), FadeIn(score_desc), run_time=0.5)
        self.play(FadeIn(issues_title), run_time=0.2)
        self.play(LaggedStart(*[FadeIn(i, shift=RIGHT * 0.2) for i in issues], lag_ratio=0.12), run_time=0.5)
        self.wait(1)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.4)

    def slide_outro(self):
        title = Text("AI Meets Design", font_size=64, weight=BOLD)
        title.set_color_by_gradient(CYAN, PRIMARY, SECONDARY)
        sub = Text("Generate. Prototype. Audit. Ship.", font_size=28, color=SLATE)
        sub.next_to(title, DOWN, buff=0.4)
        url = Text("github.com/embeddedos-org/EoStudio", font_size=20, color=PRIMARY)
        url.next_to(sub, DOWN, buff=0.5)

        self.play(Write(title), run_time=0.6)
        self.play(FadeIn(sub, shift=UP * 0.2), run_time=0.3)
        self.play(FadeIn(url), run_time=0.3)
        self.wait(2)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.6)
