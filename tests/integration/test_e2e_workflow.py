"""End-to-end integration tests — full workflows from design to code generation."""

import json
import pytest

from eostudio.core.animation.timeline import AnimationTimeline
from eostudio.core.animation.presets import get_preset, PRESETS
from eostudio.core.ui_flow.design_system import DesignSystem
from eostudio.core.ui_flow.auto_layout import AutoLayout, LayoutDirection
from eostudio.core.ui_flow.responsive import ResponsiveConfig, BREAKPOINTS
from eostudio.core.prototyping.player import PrototypePlayer, PrototypeScreen
from eostudio.core.prototyping.interactions import InteractionManager, Interaction, InteractionTrigger, InteractionAction
from eostudio.core.prototyping.transitions import ScreenTransition, TransitionType
from eostudio.core.prototyping.state_machine import StateMachine, PrototypeState, StateTransition, PrototypeVariable
from eostudio.core.video.compositor import VideoCompositor, LayerType
from eostudio.core.video.promo_templates import get_template
from eostudio.codegen.react_motion import ReactMotionGenerator


class TestDesignToCodeWorkflow:
    """Full workflow: design components → add animations → generate React + Framer Motion."""

    def test_full_react_framer_motion_pipeline(self):
        # 1. Define components
        components = [
            {"type": "Container", "label": "Header", "id": "header"},
            {"type": "Text", "label": "Welcome to MyApp", "id": "title"},
            {"type": "Input", "label": "Email", "id": "email"},
            {"type": "Button", "label": "Sign Up", "id": "signup_btn"},
            {"type": "Card", "label": "Feature 1", "id": "card1"},
            {"type": "Card", "label": "Feature 2", "id": "card2"},
        ]

        screens = [
            {"name": "Home", "components": components[:4]},
            {"name": "Features", "components": components[4:]},
        ]

        # 2. Create animation timeline with presets
        timeline = AnimationTimeline(name="App Animations")

        header_clip = get_preset("fadeIn").apply("header", delay=0)
        timeline.add_clip(header_clip)

        title_clip = get_preset("fadeInUp").apply("title", delay=0.1)
        timeline.add_clip(title_clip)

        email_clip = get_preset("fadeInUp").apply("email", delay=0.2)
        timeline.add_clip(email_clip)

        btn_clip = get_preset("scaleIn").apply("signup_btn", delay=0.3)
        timeline.add_clip(btn_clip)

        # Stagger cards
        timeline.stagger(
            ["card1", "card2"],
            [{"property": "opacity", "from": 0, "to": 1},
             {"property": "y", "from": 40, "to": 0}],
            stagger_delay=0.15,
        )

        # 3. Generate React + Framer Motion code
        gen = ReactMotionGenerator(library="framer-motion")
        files = gen.generate(timeline, components, screens)

        # 4. Verify output
        assert len(files) >= 10

        # App.jsx has routing and AnimatePresence
        app = files["src/App.jsx"]
        assert "AnimatePresence" in app
        assert "Home" in app
        assert "Features" in app

        # Screens have animated components
        home = files["src/screens/Home.jsx"]
        assert "AnimatedComponent" in home
        assert "whileHover" in home  # button interaction

        # Presets file has all needed presets
        presets = files["src/animations/presets.js"]
        assert "fadeIn" in presets
        assert "fadeInUp" in presets
        assert "scaleIn" in presets

        # Variants reference our timeline clips
        variants = files["src/animations/variants.js"]
        assert "header" in variants
        assert "title" in variants

        # Package.json has correct deps
        pkg = json.loads(files["package.json"])
        assert "framer-motion" in pkg["dependencies"]
        assert "react-router-dom" in pkg["dependencies"]

    def test_full_gsap_pipeline(self):
        components = [{"type": "Text", "label": "Hello", "id": "t1"}]
        timeline = AnimationTimeline()
        clip = get_preset("slideUp").apply("t1")
        timeline.add_clip(clip)

        gen = ReactMotionGenerator(library="gsap")
        files = gen.generate(timeline, components)

        assert "src/animations/gsapTimeline.js" in files
        pkg = json.loads(files["package.json"])
        assert "gsap" in pkg["dependencies"]


class TestDesignSystemToCodeWorkflow:
    """Full workflow: create design system → export CSS → apply to React."""

    def test_design_system_css_export(self):
        ds = DesignSystem(name="MyBrand")
        css = ds.export_css()

        assert ":root {" in css
        assert "--color-primary" in css
        assert "button--primary" in css
        assert "button--secondary" in css
        assert ":hover" in css
        assert ":disabled" in css

    def test_design_system_tailwind_export(self):
        ds = DesignSystem()
        config = ds.export_tailwind_config()
        assert "theme" in config
        colors = config["theme"]["extend"]["colors"]
        assert "primary" in colors

    def test_theme_switching(self):
        ds = DesignSystem()
        light_primary = ds.get_token("color.primary")
        ds.toggle_theme()
        dark_primary = ds.get_token("color.primary")
        assert light_primary != dark_primary  # different themes have different values


class TestPrototypeWorkflow:
    """Full workflow: create prototype → add interactions → export HTML."""

    def test_prototype_full_workflow(self):
        # 1. Create player with screens
        player = PrototypePlayer()
        player.add_screen(PrototypeScreen(
            id="login", name="Login",
            components=[
                {"type": "Input", "label": "Email", "id": "email"},
                {"type": "Input", "label": "Password", "id": "password"},
                {"type": "Button", "label": "Sign In", "id": "signin_btn"},
            ],
        ))
        player.add_screen(PrototypeScreen(
            id="dashboard", name="Dashboard",
            components=[
                {"type": "Text", "label": "Welcome!", "id": "welcome"},
                {"type": "Card", "label": "Stats", "id": "stats_card"},
            ],
        ))

        # 2. Add transition
        player.add_transition(ScreenTransition(
            from_screen="login", to_screen="dashboard",
            transition_type=TransitionType.SLIDE_LEFT,
            duration=0.3,
        ))

        # 3. Add interactions
        player.interactions.add_interaction(Interaction(
            id="i1", source_id="signin_btn",
            trigger=InteractionTrigger.CLICK,
            action=InteractionAction.NAVIGATE,
            target_id="dashboard",
        ))

        # 4. Setup state machine
        player.state_machine.add_variable(PrototypeVariable("isLoggedIn", False))

        # 5. Navigate
        assert player.current_screen.id == "login"
        player.navigate_to("dashboard")
        assert player.current_screen.id == "dashboard"
        player.go_back()
        assert player.current_screen.id == "login"

        # 6. Export HTML
        html = player.export_html()
        assert "<!DOCTYPE html>" in html
        assert "EoStudio Prototype" in html
        assert "Login" in html or "login" in html
        assert "Dashboard" in html or "dashboard" in html

        # 7. Serialize/deserialize
        data = player.to_dict()
        restored = PrototypePlayer.from_dict(data)
        assert len(restored.screens) == 2
        assert len(restored.transitions) == 1


class TestVideoPromoWorkflow:
    """Full workflow: select template → customize → render frames."""

    def test_promo_template_workflow(self):
        # 1. Get template
        tmpl = get_template("social_square")
        assert tmpl is not None

        # 2. Create compositor with custom values
        comp = tmpl.create_compositor(
            product_name="EoStudio",
            tagline="Design Everything",
            cta="Download Now",
            product="EoStudio",
        )

        assert comp.width == 1080
        assert comp.height == 1080
        assert len(comp.layers) > 0

        # 3. Add custom layers
        comp.add_text_layer("Community Edition", x=540, y=900,
                           font_size=24, color="#94a3b8",
                           start=2, end=5)

        # 4. Render frames
        frames = comp.render_all_frames()
        assert len(frames) > 0
        assert frames[0]["width"] == 1080

        # 5. Verify ffmpeg command
        cmd = comp.generate_ffmpeg_command("promo.mp4")
        assert "ffmpeg" in cmd
        assert "1080x1080" in cmd

    def test_product_launch_video(self):
        tmpl = get_template("product_launch")
        comp = tmpl.create_compositor(
            product_name="EoStudio 1.0",
            tagline="Design meets AI",
            feature_1="Animation Engine",
            feature_2="AI UI Generation",
            feature_3="Interactive Prototyping",
            url="eostudio.dev",
        )

        assert comp.duration == 15.0

        # Check frames at different times
        intro = comp.render_frame(2.0)
        assert len(intro["layers"]) > 0

        feat = comp.render_frame(5.0)
        assert len(feat["layers"]) > 0

        end = comp.render_frame(14.0)
        assert len(end["layers"]) > 0


class TestAnimationDesignSystemIntegration:
    """Verify animation engine works with design system tokens."""

    def test_animated_components_with_design_tokens(self):
        ds = DesignSystem()
        primary = ds.get_token("color.primary")

        timeline = AnimationTimeline()
        preset = get_preset("fadeInUp")
        clip = preset.apply("button", delay=0.2)
        timeline.add_clip(clip)

        # Evaluate at midpoint
        values = timeline.evaluate(0.5)
        assert "button" in values

        # Generate code with both
        gen = ReactMotionGenerator(library="framer-motion")
        files = gen.generate(timeline,
                            [{"type": "Button", "label": "CTA", "id": "button"}])

        css = files.get("src/screens/Home.module.css", "")
        assert "button" in css.lower()


class TestResponsiveAnimationWorkflow:
    """Responsive design with animations across breakpoints."""

    def test_responsive_with_layout(self):
        layout = AutoLayout(direction=LayoutDirection.COLUMN, gap=16)
        positions = layout.compute_layout(375, 812,
                                          [(375, 50), (375, 40), (200, 48)])
        assert len(positions) == 3

        # Tablet layout
        layout.direction = LayoutDirection.ROW
        tablet_pos = layout.compute_layout(768, 1024,
                                           [(200, 50), (200, 50), (200, 50)])
        assert tablet_pos[0][0] < tablet_pos[1][0]  # side by side

    def test_breakpoint_overrides(self):
        cfg = ResponsiveConfig()
        cfg.add_override("mobile", padding="8px", font_size="14px")
        cfg.add_override("desktop", padding="24px", font_size="18px")

        mobile_props = cfg.resolve_properties("mobile", {"padding": "16px"})
        assert mobile_props["padding"] == "8px"
