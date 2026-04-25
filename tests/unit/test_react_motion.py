"""Tests for React Motion codegen — Framer Motion, GSAP, and CSS animation generation."""

import json
import pytest

from eostudio.codegen.react_motion import ReactMotionGenerator
from eostudio.core.animation.timeline import AnimationTimeline, AnimationClip
from eostudio.core.animation.keyframe import KeyframeTrack, EasingFunction
from eostudio.core.animation.presets import get_preset


def _sample_timeline() -> AnimationTimeline:
    """Create a sample timeline for testing."""
    tl = AnimationTimeline(name="Test Timeline")
    clip = tl.create_clip("header", duration=0.5, delay=0)
    track = clip.add_track("opacity")
    track.add_keyframe(0.0, 0.0)
    track.add_keyframe(0.5, 1.0)
    track2 = clip.add_track("y")
    track2.add_keyframe(0.0, 30.0)
    track2.add_keyframe(0.5, 0.0)

    clip2 = tl.create_clip("button", duration=0.4, delay=0.2)
    track3 = clip2.add_track("scale")
    track3.add_keyframe(0.0, 0.0)
    track3.add_keyframe(0.4, 1.0)
    return tl


def _sample_components():
    return [
        {"type": "Text", "label": "Welcome", "id": "header"},
        {"type": "Button", "label": "Get Started", "id": "button"},
        {"type": "Input", "label": "Email", "id": "email_input"},
        {"type": "Card", "label": "Feature Card", "id": "card1"},
        {"type": "Image", "label": "Hero", "id": "hero_img", "src": "hero.png"},
    ]


def _sample_screens():
    return [
        {"name": "Home", "components": _sample_components()},
        {"name": "About", "components": [{"type": "Text", "label": "About Us", "id": "about_text"}]},
    ]


# -----------------------------------------------------------------------
# Framer Motion
# -----------------------------------------------------------------------

class TestFramerMotionGenerator:
    def test_generate_files(self):
        gen = ReactMotionGenerator(library="framer-motion")
        files = gen.generate(_sample_timeline(), _sample_components(), _sample_screens())
        assert "src/App.jsx" in files
        assert "src/index.jsx" in files
        assert "src/hooks/useAnimation.js" in files
        assert "src/hooks/useScrollAnimation.js" in files
        assert "src/components/AnimatedComponent.jsx" in files
        assert "src/components/PageTransition.jsx" in files
        assert "src/animations/presets.js" in files
        assert "src/animations/variants.js" in files
        assert "package.json" in files
        assert "src/screens/Home.jsx" in files
        assert "src/screens/About.jsx" in files

    def test_app_has_animate_presence(self):
        gen = ReactMotionGenerator(library="framer-motion")
        files = gen.generate(_sample_timeline(), _sample_components(), _sample_screens())
        app = files["src/App.jsx"]
        assert "AnimatePresence" in app
        assert "framer-motion" in app
        assert "PageTransition" in app

    def test_screen_has_motion_components(self):
        gen = ReactMotionGenerator(library="framer-motion")
        files = gen.generate(_sample_timeline(), _sample_components(), _sample_screens())
        home = files["src/screens/Home.jsx"]
        assert "motion" in home
        assert "AnimatedComponent" in home
        assert "staggerContainer" in home

    def test_button_has_hover_tap(self):
        gen = ReactMotionGenerator(library="framer-motion")
        files = gen.generate(_sample_timeline(), _sample_components())
        home = files["src/screens/Home.jsx"]
        assert "whileHover" in home
        assert "whileTap" in home

    def test_presets_file(self):
        gen = ReactMotionGenerator(library="framer-motion")
        files = gen.generate(_sample_timeline(), _sample_components())
        presets = files["src/animations/presets.js"]
        assert "fadeIn" in presets
        assert "fadeInUp" in presets
        assert "slideUp" in presets
        assert "scaleIn" in presets
        assert "springConfigs" in presets

    def test_variants_from_timeline(self):
        gen = ReactMotionGenerator(library="framer-motion")
        files = gen.generate(_sample_timeline(), _sample_components())
        variants = files["src/animations/variants.js"]
        assert "header" in variants
        assert "button" in variants
        assert "staggerContainer" in variants

    def test_package_json_deps(self):
        gen = ReactMotionGenerator(library="framer-motion")
        files = gen.generate(_sample_timeline(), _sample_components())
        pkg = json.loads(files["package.json"])
        assert "framer-motion" in pkg["dependencies"]
        assert "react" in pkg["dependencies"]
        assert "react-router-dom" in pkg["dependencies"]

    def test_animated_component(self):
        gen = ReactMotionGenerator(library="framer-motion")
        files = gen.generate(_sample_timeline(), _sample_components())
        comp = files["src/components/AnimatedComponent.jsx"]
        assert "preset" in comp
        assert "trigger" in comp
        assert "scroll" in comp
        assert "mount" in comp

    def test_scroll_hooks(self):
        gen = ReactMotionGenerator(library="framer-motion")
        files = gen.generate(_sample_timeline(), _sample_components())
        scroll = files["src/hooks/useScrollAnimation.js"]
        assert "useParallax" in scroll
        assert "useScrollProgress" in scroll

    def test_page_transition(self):
        gen = ReactMotionGenerator(library="framer-motion")
        files = gen.generate(_sample_timeline(), _sample_components())
        pt = files["src/components/PageTransition.jsx"]
        assert "pageVariants" in pt
        assert "initial" in pt
        assert "exit" in pt


# -----------------------------------------------------------------------
# GSAP
# -----------------------------------------------------------------------

class TestGSAPGenerator:
    def test_generate_files(self):
        gen = ReactMotionGenerator(library="gsap")
        files = gen.generate(_sample_timeline(), _sample_components(), _sample_screens())
        assert "src/animations/gsapTimeline.js" in files
        assert "src/hooks/useGSAP.js" in files
        assert "src/hooks/useScrollTrigger.js" in files
        assert "package.json" in files

    def test_gsap_timeline(self):
        gen = ReactMotionGenerator(library="gsap")
        files = gen.generate(_sample_timeline(), _sample_components())
        tl = files["src/animations/gsapTimeline.js"]
        assert "gsap" in tl
        assert "ScrollTrigger" in tl
        assert "createTimeline" in tl
        assert "createScrollAnimations" in tl

    def test_gsap_screen(self):
        gen = ReactMotionGenerator(library="gsap")
        files = gen.generate(_sample_timeline(), _sample_components(), _sample_screens())
        home = files["src/screens/Home.jsx"]
        assert "gsap" in home
        assert "useRef" in home
        assert "animated-item" in home

    def test_package_json_gsap(self):
        gen = ReactMotionGenerator(library="gsap")
        files = gen.generate(_sample_timeline(), _sample_components())
        pkg = json.loads(files["package.json"])
        assert "gsap" in pkg["dependencies"]

    def test_use_gsap_hook(self):
        gen = ReactMotionGenerator(library="gsap")
        files = gen.generate(_sample_timeline(), _sample_components())
        hook = files["src/hooks/useGSAP.js"]
        assert "gsap.context" in hook

    def test_scroll_trigger_hook(self):
        gen = ReactMotionGenerator(library="gsap")
        files = gen.generate(_sample_timeline(), _sample_components())
        st = files["src/hooks/useScrollTrigger.js"]
        assert "ScrollTrigger" in st


# -----------------------------------------------------------------------
# CSS Animations
# -----------------------------------------------------------------------

class TestCSSGenerator:
    def test_generate_files(self):
        gen = ReactMotionGenerator(library="css")
        files = gen.generate(_sample_timeline(), _sample_components())
        assert "src/animations/keyframes.css" in files
        assert "src/animations/animations.css" in files

    def test_keyframes(self):
        gen = ReactMotionGenerator(library="css")
        files = gen.generate(_sample_timeline(), _sample_components())
        css = files["src/animations/keyframes.css"]
        assert "@keyframes" in css

    def test_animation_classes(self):
        gen = ReactMotionGenerator(library="css")
        files = gen.generate(_sample_timeline(), _sample_components())
        css = files["src/animations/animations.css"]
        assert ".animate-fadeIn" in css
        assert ".animate-fadeInUp" in css
        assert ".animate-bounce" in css


# -----------------------------------------------------------------------
# With Presets
# -----------------------------------------------------------------------

class TestWithPresets:
    def test_preset_applied_to_timeline(self):
        tl = AnimationTimeline()
        preset = get_preset("fadeInUp")
        clip = preset.apply("card", delay=0.2)
        tl.add_clip(clip)

        gen = ReactMotionGenerator(library="framer-motion")
        files = gen.generate(tl, [{"type": "Card", "label": "Test", "id": "card"}])
        variants = files["src/animations/variants.js"]
        assert "card" in variants

    def test_empty_timeline(self):
        gen = ReactMotionGenerator(library="framer-motion")
        files = gen.generate(AnimationTimeline(), _sample_components())
        assert "src/App.jsx" in files
        # Should still generate valid files with empty timeline
