"""EoStudio Animation Engine Deep Dive — showcasing keyframes, springs, presets, and codegen."""

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


class AnimationDeepDive(Scene):
    def construct(self):
        self.camera.background_color = BG
        self.slide_intro()
        self.slide_keyframes()
        self.slide_spring_physics()
        self.slide_presets_showcase()
        self.slide_codegen_output()
        self.slide_outro()

    def slide_intro(self):
        title = Text("Animation Engine", font_size=72, weight=BOLD)
        title.set_color_by_gradient(SECONDARY, ACCENT)
        sub = Text("Keyframes · Spring Physics · 25 Presets · React Codegen", font_size=24, color=SLATE)
        sub.next_to(title, DOWN, buff=0.4)
        badge = Text("EoStudio v1.0", font_size=18, color=PRIMARY)
        badge.next_to(sub, DOWN, buff=0.3)

        self.play(Write(title), run_time=0.7)
        self.play(FadeIn(sub, shift=UP * 0.3), run_time=0.4)
        self.play(FadeIn(badge), run_time=0.3)
        self.wait(1.5)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.4)

    def slide_keyframes(self):
        title = Text("Keyframe System", font_size=48, weight=BOLD, color=CYAN)
        title.to_edge(UP, buff=0.6)

        # Timeline visualization
        timeline_line = Line(LEFT * 5, RIGHT * 5, color=SLATE, stroke_width=2)
        timeline_line.shift(DOWN * 0.5)

        # Keyframe diamonds
        kf_positions = [-4, -2, 0, 2, 4]
        kf_labels = ["0.0s", "0.25s", "0.5s", "0.75s", "1.0s"]
        kf_values = ["0", "0.3", "0.7", "0.9", "1.0"]
        diamonds = VGroup()
        labels = VGroup()
        values = VGroup()

        for pos, label, val in zip(kf_positions, kf_labels, kf_values):
            d = Square(side_length=0.25, color=ACCENT, fill_opacity=1).rotate(PI/4)
            d.move_to(timeline_line.get_start() + RIGHT * (pos + 5))
            d.shift(UP * 0)

            l = Text(label, font_size=12, color=SLATE)
            l.next_to(d, DOWN, buff=0.2)

            v = Text(val, font_size=14, color=WHITE)
            v.next_to(d, UP, buff=0.2)

            diamonds.add(d)
            labels.add(l)
            values.add(v)

        # Easing curve
        ease_label = Text("24 Easing Functions", font_size=20, color=SECONDARY)
        ease_label.shift(DOWN * 2)

        easings = VGroup()
        easing_names = ["linear", "ease-in", "ease-out", "ease-in-out", "bounce", "elastic", "back"]
        for i, name in enumerate(easing_names):
            tag = VGroup()
            bg = RoundedRectangle(width=1.5, height=0.35, corner_radius=0.15,
                                  fill_color=CARD_BG, fill_opacity=0.8, stroke_color=SECONDARY, stroke_width=0.5)
            txt = Text(name, font_size=11, color="#c4b5fd")
            txt.move_to(bg)
            tag.add(bg, txt)
            easings.add(tag)
        easings.arrange_in_grid(rows=1, buff=0.15)
        easings.shift(DOWN * 3)

        self.play(Write(title), run_time=0.4)
        self.play(Create(timeline_line), run_time=0.3)
        for d, l, v in zip(diamonds, labels, values):
            self.play(FadeIn(d, scale=0.5), FadeIn(l), FadeIn(v), run_time=0.15)

        # Animate a dot along the curve
        dot = Dot(color=ACCENT, radius=0.15)
        dot.move_to(diamonds[0])
        self.play(FadeIn(dot), run_time=0.2)
        for d in diamonds[1:]:
            self.play(dot.animate.move_to(d), run_time=0.3, rate_func=smooth)

        self.play(FadeIn(ease_label, shift=UP * 0.2), run_time=0.3)
        self.play(LaggedStart(*[FadeIn(e, scale=0.8) for e in easings], lag_ratio=0.06), run_time=0.5)
        self.wait(1)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.4)

    def slide_spring_physics(self):
        title = Text("Spring Physics", font_size=48, weight=BOLD, color=GREEN)
        title.to_edge(UP, buff=0.6)

        sub = Text("Like Framer Motion — stiffness, damping, mass", font_size=20, color=SLATE)
        sub.next_to(title, DOWN, buff=0.3)

        # Spring presets
        presets = [
            ("Gentle", "#22c55e", 0.8),
            ("Default", PRIMARY, 1.0),
            ("Wobbly", AMBER, 1.3),
            ("Stiff", ACCENT, 0.5),
            ("Slow", CYAN, 1.5),
        ]

        boxes = VGroup()
        for name, color, _overshoot in presets:
            bg = RoundedRectangle(width=2, height=1.5, corner_radius=0.2,
                                  fill_color=color, fill_opacity=0.85, stroke_width=0)
            txt = Text(name, font_size=18, color=WHITE, weight=BOLD)
            txt.move_to(bg)
            boxes.add(VGroup(bg, txt))
        boxes.arrange(RIGHT, buff=0.3)
        boxes.shift(DOWN * 0.5)

        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=0.4)

        # Staggered spring entrance
        for i, box in enumerate(boxes):
            box.shift(DOWN * 3)
        self.add(*boxes)

        anims = []
        for i, (box, (_, _, overshoot)) in enumerate(zip(boxes, presets)):
            target = DOWN * 0.5 + RIGHT * (i - 2) * 2.3
            anims.append(box.animate.move_to(target))

        self.play(LaggedStart(*anims, lag_ratio=0.12), run_time=1.2, rate_func=smooth)

        # Wobble the wobbly one
        self.play(
            boxes[2].animate.shift(UP * 0.4), run_time=0.2,
        )
        self.play(
            boxes[2].animate.shift(DOWN * 0.5), run_time=0.15,
        )
        self.play(
            boxes[2].animate.shift(UP * 0.15), run_time=0.1,
        )
        self.play(
            boxes[2].animate.shift(DOWN * 0.05), run_time=0.1,
        )

        # Config display
        config_text = Text(
            "SpringConfig(stiffness=180, damping=12, mass=1)  # wobbly",
            font_size=14, color="#a6e3a1"
        )
        config_text.shift(DOWN * 2.5)
        self.play(FadeIn(config_text), run_time=0.3)
        self.wait(1)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.4)

    def slide_presets_showcase(self):
        title = Text("25 Animation Presets", font_size=48, weight=BOLD)
        title.set_color_by_gradient(AMBER, ACCENT)
        title.to_edge(UP, buff=0.6)

        categories = [
            ("Entrance", ["fadeIn", "fadeInUp", "slideUp", "scaleIn", "popIn", "bounceIn", "rotateIn"], GREEN),
            ("Attention", ["pulse", "shake", "wobble", "flash", "bounce"], AMBER),
            ("Exit", ["fadeOut", "scaleOut"], ACCENT),
            ("Scroll", ["revealUp", "revealScale"], CYAN),
            ("Transition", ["crossFade", "slideTransition"], SECONDARY),
        ]

        self.play(Write(title), run_time=0.4)

        y_offset = 0.8
        all_items = []
        for cat_name, preset_names, color in categories:
            cat_label = Text(cat_name, font_size=18, color=color, weight=BOLD)
            cat_label.shift(DOWN * y_offset + LEFT * 5.5)
            all_items.append(cat_label)

            tags = VGroup()
            for name in preset_names:
                bg = RoundedRectangle(
                    width=len(name) * 0.12 + 0.5, height=0.35, corner_radius=0.15,
                    fill_color=CARD_BG, fill_opacity=0.8, stroke_color=color, stroke_width=0.8)
                txt = Text(name, font_size=12, color=WHITE)
                txt.move_to(bg)
                tags.add(VGroup(bg, txt))
            tags.arrange(RIGHT, buff=0.1)
            tags.next_to(cat_label, RIGHT, buff=0.3)
            all_items.append(tags)
            y_offset += 0.7

        for item in all_items:
            self.play(FadeIn(item, shift=RIGHT * 0.3), run_time=0.2)

        # Animate demo boxes
        demo = Text("Live Demo:", font_size=16, color=SLATE)
        demo.shift(DOWN * 3 + LEFT * 4)
        self.play(FadeIn(demo), run_time=0.2)

        demo_box = RoundedRectangle(width=1.2, height=0.8, corner_radius=0.1,
                                     fill_color=PRIMARY, fill_opacity=0.9, stroke_width=0)
        demo_label = Text("Card", font_size=14, color=WHITE, weight=BOLD)
        demo_label.move_to(demo_box)
        demo_group = VGroup(demo_box, demo_label)
        demo_group.shift(DOWN * 3 + RIGHT * 1)

        # fadeInUp
        demo_group.set_opacity(0)
        demo_group.shift(DOWN * 0.5)
        self.play(demo_group.animate.set_opacity(1).shift(UP * 0.5), run_time=0.4)
        self.wait(0.3)
        # pulse
        self.play(demo_group.animate.scale(1.1), run_time=0.2)
        self.play(demo_group.animate.scale(1/1.1), run_time=0.2)
        # shake
        self.play(demo_group.animate.shift(RIGHT * 0.15), run_time=0.05)
        self.play(demo_group.animate.shift(LEFT * 0.3), run_time=0.05)
        self.play(demo_group.animate.shift(RIGHT * 0.15), run_time=0.05)

        self.wait(0.8)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.4)

    def slide_codegen_output(self):
        title = Text("React + Framer Motion Codegen", font_size=44, weight=BOLD)
        title.set_color_by_gradient(PRIMARY, CYAN)
        title.to_edge(UP, buff=0.6)

        sub = Text("Design animation in EoStudio. Export as React app.", font_size=20, color=SLATE)
        sub.next_to(title, DOWN, buff=0.3)

        # File list
        files_title = Text("Generated Files:", font_size=18, color=GREEN, weight=BOLD)
        files_title.shift(LEFT * 3 + UP * 0.5)

        file_list = VGroup()
        for name in ["src/App.jsx", "src/screens/Home.jsx", "src/animations/presets.js",
                      "src/animations/variants.js", "src/hooks/useAnimation.js",
                      "src/hooks/useScrollAnimation.js", "src/components/AnimatedComponent.jsx",
                      "src/components/PageTransition.jsx", "package.json"]:
            t = Text(name, font_size=13, color=CYAN)
            file_list.add(t)
        file_list.arrange(DOWN, buff=0.15, aligned_edge=LEFT)
        file_list.next_to(files_title, DOWN, buff=0.3)

        # Features
        feat_title = Text("What You Get:", font_size=18, color=AMBER, weight=BOLD)
        feat_title.shift(RIGHT * 2.5 + UP * 0.5)

        features = VGroup()
        for f in ["AnimatePresence page transitions", "Stagger container animations",
                   "whileHover + whileTap interactions", "useScrollAnimation hook",
                   "useParallax hook", "Spring physics configs", "25 animation presets"]:
            t = Text(f, font_size=13, color=SLATE)
            features.add(t)
        features.arrange(DOWN, buff=0.15, aligned_edge=LEFT)
        features.next_to(feat_title, DOWN, buff=0.3)

        # Frameworks
        fw_label = Text("Also supports: GSAP + CSS Animations", font_size=16, color=SECONDARY)
        fw_label.shift(DOWN * 3.2)

        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=0.4)
        self.play(FadeIn(files_title), run_time=0.2)
        self.play(LaggedStart(*[FadeIn(f, shift=RIGHT * 0.2) for f in file_list], lag_ratio=0.06), run_time=0.6)
        self.play(FadeIn(feat_title), run_time=0.2)
        self.play(LaggedStart(*[FadeIn(f, shift=RIGHT * 0.2) for f in features], lag_ratio=0.06), run_time=0.5)
        self.play(FadeIn(fw_label, shift=UP * 0.2), run_time=0.3)
        self.wait(1.5)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.4)

    def slide_outro(self):
        title = Text("Build Animated UIs", font_size=64, weight=BOLD)
        title.set_color_by_gradient(PRIMARY, SECONDARY, ACCENT)

        sub = Text("Design. Animate. Export. Ship.", font_size=28, color=SLATE)
        sub.next_to(title, DOWN, buff=0.4)

        url = Text("EoStudio v1.0 — Community Edition", font_size=22, color=PRIMARY)
        url.next_to(sub, DOWN, buff=0.5)

        self.play(Write(title), run_time=0.6)
        self.play(FadeIn(sub, shift=UP * 0.2), run_time=0.3)
        self.play(FadeIn(url), run_time=0.3)
        self.wait(2)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.6)
