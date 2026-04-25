"""Tests for the animation engine — keyframes, timeline, spring physics, presets."""

import math
import pytest

from eostudio.core.animation.keyframe import (
    Keyframe,
    KeyframeTrack,
    EasingFunction,
    EASING_FUNCTIONS,
    interpolate,
    cubic_bezier,
)
from eostudio.core.animation.timeline import (
    AnimationClip,
    AnimationTimeline,
    PlayState,
    FillMode,
    Direction,
)
from eostudio.core.animation.spring import SpringSimulator, SpringConfig, MultiSpringSimulator
from eostudio.core.animation.presets import (
    AnimationPreset,
    PRESETS,
    get_preset,
    list_presets,
    preset_categories,
)


# -----------------------------------------------------------------------
# Keyframe & Interpolation
# -----------------------------------------------------------------------

class TestInterpolation:
    def test_scalar_interpolation(self):
        assert interpolate(0.0, 10.0, 0.5) == 5.0
        assert interpolate(0.0, 10.0, 0.0) == 0.0
        assert interpolate(0.0, 10.0, 1.0) == 10.0

    def test_tuple_interpolation(self):
        result = interpolate((0.0, 0.0), (10.0, 20.0), 0.5)
        assert result == (5.0, 10.0)

    def test_list_interpolation(self):
        result = interpolate([0.0, 100.0], [100.0, 0.0], 0.25)
        assert result == [25.0, 75.0]

    def test_mismatched_length(self):
        result = interpolate((0.0,), (10.0, 20.0), 0.5)
        assert len(result) == 2
        assert result[0] == 5.0
        assert result[1] == 10.0  # 0 interpolated to 20


class TestEasingFunctions:
    def test_linear(self):
        fn = EASING_FUNCTIONS[EasingFunction.LINEAR]
        assert fn(0.0) == 0.0
        assert fn(0.5) == 0.5
        assert fn(1.0) == 1.0

    def test_ease_in_starts_slow(self):
        fn = EASING_FUNCTIONS[EasingFunction.EASE_IN]
        assert fn(0.1) < 0.1  # starts slower than linear

    def test_ease_out_starts_fast(self):
        fn = EASING_FUNCTIONS[EasingFunction.EASE_OUT]
        assert fn(0.1) > 0.1  # starts faster than linear

    def test_all_easings_have_endpoints(self):
        for easing, fn in EASING_FUNCTIONS.items():
            assert abs(fn(0.0)) < 0.01 or easing == EasingFunction.EASE_IN_BACK
            assert abs(fn(1.0) - 1.0) < 0.01

    def test_bounce_out(self):
        fn = EASING_FUNCTIONS[EasingFunction.EASE_OUT_BOUNCE]
        assert fn(0.0) == 0.0
        assert abs(fn(1.0) - 1.0) < 0.01

    def test_cubic_bezier(self):
        fn = cubic_bezier(0.25, 0.1, 0.25, 1.0)
        assert abs(fn(0.0)) < 0.01
        assert abs(fn(1.0) - 1.0) < 0.05


class TestKeyframe:
    def test_create(self):
        kf = Keyframe(time=0.5, value=100.0, easing=EasingFunction.EASE_OUT)
        assert kf.time == 0.5
        assert kf.value == 100.0

    def test_easing_fn(self):
        kf = Keyframe(time=0, value=0, easing=EasingFunction.LINEAR)
        fn = kf.get_easing_fn()
        assert fn(0.5) == 0.5

    def test_cubic_bezier_easing(self):
        kf = Keyframe(time=0, value=0, easing=EasingFunction.CUBIC_BEZIER,
                      bezier_points=(0.25, 0.1, 0.25, 1.0))
        fn = kf.get_easing_fn()
        assert callable(fn)


class TestKeyframeTrack:
    def test_add_and_evaluate(self):
        track = KeyframeTrack(property_name="opacity")
        track.add_keyframe(0.0, 0.0, EasingFunction.LINEAR)
        track.add_keyframe(1.0, 1.0, EasingFunction.LINEAR)
        assert track.evaluate(0.0) == 0.0
        assert track.evaluate(1.0) == 1.0
        assert abs(track.evaluate(0.5) - 0.5) < 0.01

    def test_sorted_keyframes(self):
        track = KeyframeTrack(property_name="x")
        track.add_keyframe(1.0, 100)
        track.add_keyframe(0.0, 0)
        track.add_keyframe(0.5, 50)
        assert track.keyframes[0].time == 0.0
        assert track.keyframes[2].time == 1.0

    def test_duration(self):
        track = KeyframeTrack(property_name="y")
        track.add_keyframe(0.0, 0)
        track.add_keyframe(2.0, 200)
        assert track.duration == 2.0

    def test_empty_track(self):
        track = KeyframeTrack(property_name="z")
        assert track.evaluate(0.5) == 0.0
        assert track.duration == 0.0

    def test_before_first_keyframe(self):
        track = KeyframeTrack(property_name="x")
        track.add_keyframe(1.0, 100)
        track.add_keyframe(2.0, 200)
        assert track.evaluate(0.0) == 100

    def test_serialization(self):
        track = KeyframeTrack(property_name="scale")
        track.add_keyframe(0.0, 1.0)
        track.add_keyframe(0.5, 2.0)
        data = track.to_dict()
        restored = KeyframeTrack.from_dict(data)
        assert restored.property_name == "scale"
        assert len(restored.keyframes) == 2
        assert abs(restored.evaluate(0.25) - 1.5) < 0.2

    def test_remove_keyframe(self):
        track = KeyframeTrack(property_name="x")
        track.add_keyframe(0.0, 0)
        track.add_keyframe(1.0, 100)
        track.remove_keyframe(0)
        assert len(track.keyframes) == 1


# -----------------------------------------------------------------------
# Animation Timeline
# -----------------------------------------------------------------------

class TestAnimationClip:
    def test_create_and_evaluate(self):
        clip = AnimationClip(target_id="btn1", duration=1.0)
        track = clip.add_track("opacity")
        track.add_keyframe(0.0, 0.0)
        track.add_keyframe(1.0, 1.0)
        values = clip.evaluate(0.5)
        assert "opacity" in values

    def test_delay(self):
        clip = AnimationClip(target_id="x", duration=1.0, delay=0.5)
        track = clip.add_track("opacity")
        track.add_keyframe(0.0, 0.0)
        track.add_keyframe(1.0, 1.0)
        assert clip.evaluate(0.0) == {}  # before delay, no fill
        values = clip.evaluate(1.0)
        assert "opacity" in values

    def test_total_duration(self):
        clip = AnimationClip(target_id="x", duration=2.0, delay=1.0, iterations=3)
        assert clip.total_duration == 7.0

    def test_direction_reverse(self):
        clip = AnimationClip(target_id="x", duration=1.0, direction=Direction.REVERSE)
        track = clip.add_track("x")
        track.add_keyframe(0.0, 0.0)
        track.add_keyframe(1.0, 100.0)
        values = clip.evaluate(0.0)
        assert values["x"] == 100.0  # reversed, so at t=0 we get end value

    def test_serialization(self):
        clip = AnimationClip(target_id="card", duration=0.5, delay=0.1)
        track = clip.add_track("opacity")
        track.add_keyframe(0.0, 0.0)
        track.add_keyframe(0.5, 1.0)
        data = clip.to_dict()
        restored = AnimationClip.from_dict(data)
        assert restored.target_id == "card"
        assert len(restored.tracks) == 1

    def test_get_track(self):
        clip = AnimationClip(target_id="x", duration=1.0)
        clip.add_track("opacity")
        clip.add_track("scale")
        assert clip.get_track("opacity") is not None
        assert clip.get_track("nonexistent") is None


class TestAnimationTimeline:
    def test_create_and_tick(self):
        tl = AnimationTimeline(name="Test")
        clip = tl.create_clip("btn", duration=1.0)
        track = clip.add_track("opacity")
        track.add_keyframe(0.0, 0.0)
        track.add_keyframe(1.0, 1.0)
        tl.play()
        values = tl.tick(0.5)
        assert "btn" in values
        assert "opacity" in values["btn"]

    def test_duration(self):
        tl = AnimationTimeline()
        tl.create_clip("a", duration=2.0)
        tl.create_clip("b", duration=3.0, delay=1.0)
        assert tl.duration == 4.0  # b starts at 1.0 + 3.0 duration

    def test_seek(self):
        tl = AnimationTimeline()
        clip = tl.create_clip("x", duration=1.0)
        track = clip.add_track("y")
        track.add_keyframe(0.0, 0.0)
        track.add_keyframe(1.0, 100.0)
        values = tl.seek(0.5)
        assert "x" in values

    def test_stagger(self):
        tl = AnimationTimeline()
        clips = tl.stagger(
            ["a", "b", "c"],
            [{"property": "opacity", "from": 0, "to": 1}],
            stagger_delay=0.1,
        )
        assert len(clips) == 3
        assert clips[0].delay == 0.0
        assert clips[1].delay == 0.1
        assert clips[2].delay == 0.2

    def test_sequence(self):
        tl = AnimationTimeline()
        c1 = AnimationClip(target_id="a", duration=1.0)
        c2 = AnimationClip(target_id="b", duration=1.0)
        tl.sequence([c1, c2], gap=0.5)
        assert c1.delay == 0.0
        assert c2.delay == 1.5

    def test_play_pause_stop(self):
        tl = AnimationTimeline()
        assert tl.state == PlayState.IDLE
        tl.play()
        assert tl.state == PlayState.PLAYING
        tl.pause()
        assert tl.state == PlayState.PAUSED
        tl.resume()
        assert tl.state == PlayState.PLAYING
        tl.stop()
        assert tl.state == PlayState.IDLE

    def test_serialization(self):
        tl = AnimationTimeline(name="MyTL")
        clip = tl.create_clip("x", duration=1.0)
        clip.add_track("opacity")
        data = tl.to_dict()
        restored = AnimationTimeline.from_dict(data)
        assert restored.name == "MyTL"
        assert len(restored.clips) == 1

    def test_on_complete_callback(self):
        tl = AnimationTimeline()
        tl.create_clip("x", duration=0.1)
        completed = []
        tl.on_complete(lambda: completed.append(True))
        tl.play()
        tl.tick(0.2)
        assert len(completed) == 1


# -----------------------------------------------------------------------
# Spring Physics
# -----------------------------------------------------------------------

class TestSpringSimulator:
    def test_reaches_target(self):
        sim = SpringSimulator(0.0, 100.0, SpringConfig.default())
        for _ in range(1000):
            sim.step(1.0 / 60)
        assert sim.at_rest
        assert abs(sim.position - 100.0) < 0.01

    def test_stiff_spring_faster(self):
        stiff = SpringSimulator(0.0, 100.0, SpringConfig.stiff())
        gentle = SpringSimulator(0.0, 100.0, SpringConfig.gentle())
        stiff_dur = stiff.estimated_duration()
        gentle_dur = gentle.estimated_duration()
        assert stiff_dur < gentle_dur

    def test_evaluate(self):
        sim = SpringSimulator(0.0, 100.0)
        val = sim.evaluate(2.0)
        assert 0 < val <= 110  # might overshoot slightly

    def test_sample(self):
        sim = SpringSimulator(0.0, 50.0)
        samples = sim.sample(3.0, fps=30)
        assert len(samples) > 0
        assert samples[0][1] == 0.0  # starts at 0

    def test_clamp(self):
        config = SpringConfig(stiffness=200, damping=5, mass=1, clamp=True)
        sim = SpringSimulator(0.0, 100.0, config)
        for _ in range(2000):
            sim.step(1.0 / 120)
        assert sim.position <= 100.0

    def test_presets(self):
        assert SpringConfig.wobbly().damping_ratio < 1.0  # underdamped
        assert SpringConfig.default().natural_frequency > 0

    def test_damping_ratio(self):
        config = SpringConfig(stiffness=100, damping=20, mass=1)
        assert config.damping_ratio == 1.0  # critically damped


class TestMultiSpringSimulator:
    def test_2d_spring(self):
        sim = MultiSpringSimulator((0, 0), (100, 200))
        for _ in range(1000):
            sim.step(1.0 / 60)
        assert sim.at_rest
        pos = sim.position
        assert abs(pos[0] - 100) < 0.1
        assert abs(pos[1] - 200) < 0.1


# -----------------------------------------------------------------------
# Presets
# -----------------------------------------------------------------------

class TestPresets:
    def test_presets_loaded(self):
        assert len(PRESETS) >= 20

    def test_get_preset(self):
        preset = get_preset("fadeIn")
        assert preset is not None
        assert preset.name == "fadeIn"

    def test_get_missing_preset(self):
        assert get_preset("nonexistent") is None

    def test_apply_preset(self):
        preset = get_preset("fadeInUp")
        clip = preset.apply("myComp", delay=0.5)
        assert clip.target_id == "myComp"
        assert clip.delay == 0.5
        assert len(clip.tracks) >= 2  # opacity + y

    def test_list_by_category(self):
        entrance = list_presets("entrance")
        assert len(entrance) >= 5
        for p in entrance:
            assert p.category == "entrance"

    def test_categories(self):
        cats = preset_categories()
        assert "entrance" in cats
        assert "exit" in cats
        assert "attention" in cats

    def test_preset_serialization(self):
        preset = get_preset("bounce")
        data = preset.to_dict()
        assert data["name"] == "bounce"
        assert data["category"] == "attention"
