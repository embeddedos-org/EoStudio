"""EoStudio vs The Competition — visual comparison video."""

from manim import *

BG = "#0a0a1a"
PRIMARY = "#3b82f6"
SECONDARY = "#8b5cf6"
ACCENT = "#ec4899"
CYAN = "#22d3ee"
GREEN = "#22c55e"
AMBER = "#f59e0b"
RED = "#ef4444"
SLATE = "#94a3b8"
CARD_BG = "#1e1e2e"


class EoStudioVsCompetition(Scene):
    def construct(self):
        self.camera.background_color = BG
        self.slide_intro()
        self.slide_comparison_table()
        self.slide_what_others_need()
        self.slide_eostudio_does_all()
        self.slide_outro()

    def slide_intro(self):
        title = Text("One Tool to Rule Them All", font_size=56, weight=BOLD)
        title.set_color_by_gradient(AMBER, ACCENT)
        sub = Text("EoStudio vs Figma vs Framer vs v0 vs Runway", font_size=22, color=SLATE)
        sub.next_to(title, DOWN, buff=0.4)
        self.play(Write(title), run_time=0.6)
        self.play(FadeIn(sub, shift=UP * 0.2), run_time=0.4)
        self.wait(1.5)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.4)

    def slide_comparison_table(self):
        title = Text("Feature Comparison", font_size=44, weight=BOLD, color=CYAN)
        title.to_edge(UP, buff=0.5)

        # Headers
        headers = ["Feature", "Figma", "Framer", "v0", "EoStudio"]
        header_colors = [SLATE, AMBER, ACCENT, CYAN, GREEN]
        header_row = VGroup()
        for h, c in zip(headers, header_colors):
            t = Text(h, font_size=14, color=c, weight=BOLD)
            header_row.add(t)
        header_row.arrange(RIGHT, buff=1.2)
        header_row.shift(UP * 1.8)

        # Rows
        rows_data = [
            ["UI Design", GREEN, GREEN, RED, GREEN],
            ["Animation Engine", RED, GREEN, RED, GREEN],
            ["Code Generation", RED, AMBER, GREEN, GREEN],
            ["Prototyping", GREEN, GREEN, RED, GREEN],
            ["3D / CAD / Game", RED, RED, RED, GREEN],
            ["AI Generation", AMBER, RED, GREEN, GREEN],
            ["Video/Promo", RED, RED, RED, GREEN],
            ["Design System", GREEN, AMBER, RED, GREEN],
            ["Open Source", RED, RED, RED, GREEN],
            ["Offline / Local AI", RED, RED, RED, GREEN],
        ]

        all_rows = VGroup()
        for i, (feature, *statuses) in enumerate(rows_data):
            row = VGroup()
            feat_text = Text(feature, font_size=12, color=WHITE)
            row.add(feat_text)
            for status_color in statuses:
                if status_color == GREEN:
                    dot = Text("Yes", font_size=11, color=GREEN, weight=BOLD)
                elif status_color == AMBER:
                    dot = Text("Partial", font_size=11, color=AMBER)
                else:
                    dot = Text("No", font_size=11, color="#4b5563")
                row.add(dot)
            row.arrange(RIGHT, buff=1.2)
            all_rows.add(row)

        all_rows.arrange(DOWN, buff=0.22)
        all_rows.shift(DOWN * 0.5)

        # Align columns
        for row in all_rows:
            for j, item in enumerate(row):
                item.align_to(header_row[j], LEFT)
        for j, h in enumerate(header_row):
            h.align_to(all_rows[0][j], LEFT)

        self.play(Write(title), run_time=0.4)
        self.play(FadeIn(header_row), run_time=0.3)
        for row in all_rows:
            self.play(FadeIn(row, shift=RIGHT * 0.2), run_time=0.15)
        self.wait(2)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.4)

    def slide_what_others_need(self):
        title = Text("What Others Require", font_size=44, weight=BOLD, color=AMBER)
        title.to_edge(UP, buff=0.6)

        sub = Text("To match EoStudio, you need ALL of these:", font_size=18, color=SLATE)
        sub.next_to(title, DOWN, buff=0.3)

        tools = [
            ("Figma", "$15/mo", "UI Design"),
            ("Framer", "$25/mo", "Prototyping + Motion"),
            ("v0", "AI credits", "AI UI Generation"),
            ("Runway", "$15/mo", "Video Generation"),
            ("Blender", "Free", "3D Modeling"),
            ("KiCad", "Free", "PCB Design"),
        ]

        cards = VGroup()
        for name, price, purpose in tools:
            card = VGroup()
            bg = RoundedRectangle(width=3.2, height=1.2, corner_radius=0.15,
                                  fill_color=CARD_BG, fill_opacity=0.8,
                                  stroke_color="#30363d", stroke_width=0.5)
            n = Text(name, font_size=16, color=WHITE, weight=BOLD)
            p = Text(price, font_size=12, color=AMBER)
            d = Text(purpose, font_size=11, color=SLATE)
            n.move_to(bg.get_top() + DOWN * 0.25)
            p.next_to(n, DOWN, buff=0.1)
            d.next_to(p, DOWN, buff=0.1)
            card.add(bg, n, p, d)
            cards.add(card)

        row1 = VGroup(*cards[:3]).arrange(RIGHT, buff=0.2)
        row2 = VGroup(*cards[3:]).arrange(RIGHT, buff=0.2)
        grid = VGroup(row1, row2).arrange(DOWN, buff=0.2)
        grid.shift(DOWN * 0.8)

        total = Text("Total: $55+/mo + 6 separate tools", font_size=18, color=RED, weight=BOLD)
        total.shift(DOWN * 3.2)

        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=0.4)
        self.play(LaggedStart(*[FadeIn(c, scale=0.9) for c in cards], lag_ratio=0.12), run_time=0.8)
        self.play(FadeIn(total, shift=UP * 0.2), run_time=0.4)
        self.wait(1.5)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.4)

    def slide_eostudio_does_all(self):
        title = Text("EoStudio Does It All", font_size=56, weight=BOLD)
        title.set_color_by_gradient(PRIMARY, GREEN)
        title.to_edge(UP, buff=0.6)

        # Single box
        eo_bg = RoundedRectangle(width=10, height=4, corner_radius=0.3,
                                  fill_color=PRIMARY, fill_opacity=0.9, stroke_width=0)
        eo_bg.shift(DOWN * 0.5)

        eo_title = Text("EoStudio v1.0", font_size=36, color=WHITE, weight=BOLD)
        eo_title.move_to(eo_bg.get_top() + DOWN * 0.6)

        features = VGroup()
        for feat in ["13 Editors", "33+ Codegen", "AI-Powered", "Animation", "Prototyping", "Video/Promo", "Design System", "Open Source"]:
            bg = RoundedRectangle(width=len(feat) * 0.12 + 0.5, height=0.35, corner_radius=0.15,
                                  fill_color=WHITE, fill_opacity=0.15, stroke_width=0)
            txt = Text(feat, font_size=12, color=WHITE, weight=BOLD)
            txt.move_to(bg)
            features.add(VGroup(bg, txt))
        features.arrange_in_grid(rows=2, buff=0.12)
        features.move_to(eo_bg.get_center() + DOWN * 0.3)

        price = Text("Free & Open Source — MIT License", font_size=22, color=GREEN, weight=BOLD)
        price.shift(DOWN * 3.2)

        self.play(Write(title), run_time=0.4)
        self.play(FadeIn(eo_bg, scale=0.95), run_time=0.4)
        self.play(Write(eo_title), run_time=0.3)
        self.play(LaggedStart(*[FadeIn(f, scale=0.8) for f in features], lag_ratio=0.08), run_time=0.6)
        self.play(FadeIn(price, shift=UP * 0.2), run_time=0.4)
        self.wait(1.5)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.4)

    def slide_outro(self):
        title = Text("Stop Paying. Start Building.", font_size=56, weight=BOLD)
        title.set_color_by_gradient(GREEN, CYAN)
        url_bg = RoundedRectangle(width=8, height=0.7, corner_radius=0.15,
                                  fill_color=PRIMARY, fill_opacity=0.9, stroke_width=0)
        url_text = Text("github.com/embeddedos-org/EoStudio", font_size=20, color=WHITE, weight=BOLD)
        url_text.move_to(url_bg)
        url_group = VGroup(url_bg, url_text).next_to(title, DOWN, buff=0.5)

        self.play(Write(title), run_time=0.6)
        self.play(FadeIn(url_group, scale=0.9), run_time=0.4)
        self.wait(2)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.6)
