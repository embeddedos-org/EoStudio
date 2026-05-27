"""Tests for prototyping engine — interactions, transitions, gestures, state machine, player."""

import pytest

from eostudio.core.prototyping.interactions import (
    Interaction,
    InteractionTrigger,
    InteractionAction,
    InteractionManager,
)
from eostudio.core.prototyping.transitions import (
    ScreenTransition,
    TransitionType,
    TransitionDirection,
)
from eostudio.core.prototyping.gestures import (
    GestureRecognizer,
    GestureType,
    GestureConfig,
)
from eostudio.core.prototyping.state_machine import (
    PrototypeState,
    StateTransition,
    StateMachine,
    PrototypeVariable,
    VariableType,
)
from eostudio.core.prototyping.player import PrototypePlayer, PrototypeScreen


# -----------------------------------------------------------------------
# Interactions
# -----------------------------------------------------------------------

class TestInteractions:
    def test_create_interaction(self):
        i = Interaction(id="i1", source_id="btn", trigger=InteractionTrigger.CLICK,
                        action=InteractionAction.NAVIGATE, target_id="screen2")
        assert i.trigger == InteractionTrigger.CLICK

    def test_manager_add_and_dispatch(self):
        mgr = InteractionManager()
        mgr.add_interaction(Interaction(
            id="i1", source_id="btn1", trigger=InteractionTrigger.CLICK,
            action=InteractionAction.NAVIGATE, target_id="home",
        ))
        results = mgr.dispatch("btn1", InteractionTrigger.CLICK)
        assert len(results) == 1
        assert results[0]["action"] == "navigate"

    def test_dispatch_no_match(self):
        mgr = InteractionManager()
        results = mgr.dispatch("unknown", InteractionTrigger.CLICK)
        assert results == []

    def test_set_variable_action(self):
        mgr = InteractionManager()
        mgr.add_interaction(Interaction(
            id="i1", source_id="toggle", trigger=InteractionTrigger.CLICK,
            action=InteractionAction.SET_VARIABLE,
            parameters={"variable": "darkMode", "value": True},
        ))
        mgr.dispatch("toggle", InteractionTrigger.CLICK)
        assert mgr.get_variable("darkMode") is True

    def test_toggle_variable(self):
        mgr = InteractionManager()
        mgr.set_variable("active", False)
        mgr.add_interaction(Interaction(
            id="i1", source_id="btn", trigger=InteractionTrigger.CLICK,
            action=InteractionAction.TOGGLE_VARIABLE,
            parameters={"variable": "active"},
        ))
        mgr.dispatch("btn", InteractionTrigger.CLICK)
        assert mgr.get_variable("active") is True

    def test_condition(self):
        mgr = InteractionManager()
        mgr.set_variable("loggedIn", "true")
        mgr.add_interaction(Interaction(
            id="i1", source_id="btn", trigger=InteractionTrigger.CLICK,
            action=InteractionAction.NAVIGATE, target_id="dashboard",
            condition="loggedIn == true",
        ))
        results = mgr.dispatch("btn", InteractionTrigger.CLICK)
        assert len(results) == 1

    def test_condition_fails(self):
        mgr = InteractionManager()
        mgr.set_variable("loggedIn", "false")
        mgr.add_interaction(Interaction(
            id="i1", source_id="btn", trigger=InteractionTrigger.CLICK,
            action=InteractionAction.NAVIGATE, condition="loggedIn == true",
        ))
        results = mgr.dispatch("btn", InteractionTrigger.CLICK)
        assert len(results) == 0

    def test_serialization(self):
        mgr = InteractionManager()
        mgr.add_interaction(Interaction(
            id="i1", source_id="btn", trigger=InteractionTrigger.CLICK,
            action=InteractionAction.NAVIGATE,
        ))
        data = mgr.to_dict()
        restored = InteractionManager.from_dict(data)
        assert len(restored._interactions) == 1

    def test_remove_interaction(self):
        mgr = InteractionManager()
        mgr.add_interaction(Interaction(
            id="i1", source_id="btn", trigger=InteractionTrigger.CLICK,
            action=InteractionAction.NAVIGATE,
        ))
        mgr.remove_interaction("i1")
        assert len(mgr._interactions) == 0


# -----------------------------------------------------------------------
# Transitions
# -----------------------------------------------------------------------

class TestTransitions:
    def test_create(self):
        t = ScreenTransition("home", "detail", TransitionType.SLIDE_LEFT)
        assert t.from_screen == "home"
        assert t.transition_type == TransitionType.SLIDE_LEFT

    def test_css_animation(self):
        t = ScreenTransition("a", "b", TransitionType.FADE, duration=0.5)
        css = t.get_css_animation()
        assert "css_enter" in css

    def test_framer_motion_props(self):
        t = ScreenTransition("a", "b", TransitionType.SLIDE_UP)
        props = t.generate_framer_motion_props()
        assert "initial" in props
        assert "animate" in props
        assert props["initial"]["y"] == "100%"

    def test_serialization(self):
        t = ScreenTransition("a", "b", TransitionType.SCALE, duration=0.4)
        data = t.to_dict()
        restored = ScreenTransition.from_dict(data)
        assert restored.transition_type == TransitionType.SCALE
        assert restored.duration == 0.4


# -----------------------------------------------------------------------
# Gestures
# -----------------------------------------------------------------------

class TestGestures:
    def test_tap_detection(self):
        gr = GestureRecognizer()
        events = []
        gr.on_gesture(GestureType.TAP, lambda e: events.append(e))
        gr.on_touch_start(100, 100)
        gr.on_touch_end(100, 100)
        assert len(events) == 1
        assert events[0].gesture_type == GestureType.TAP

    def test_swipe_detection(self):
        gr = GestureRecognizer(GestureConfig(swipe_threshold=10, swipe_velocity=0))
        events = []
        gr.on_gesture(GestureType.SWIPE_RIGHT, lambda e: events.append(e))
        gr.on_touch_start(0, 100)
        import time
        time.sleep(0.01)  # small delay for velocity calc
        gr.on_touch_end(200, 100)
        assert len(events) == 1

    def test_js_handler(self):
        gr = GestureRecognizer()
        js = gr.generate_js_handler(GestureType.TAP, "console.log('tap')")
        assert "addEventListener" in js
        assert "click" in js


# -----------------------------------------------------------------------
# State Machine
# -----------------------------------------------------------------------

class TestStateMachine:
    def test_create_and_transition(self):
        sm = StateMachine()
        sm.add_state(PrototypeState(name="home", is_initial=True))
        sm.add_state(PrototypeState(name="detail"))
        sm.add_transition(StateTransition(from_state="home", to_state="detail",
                                           trigger="navigate"))
        assert sm.state_name == "home"
        assert sm.send_event("navigate")
        assert sm.state_name == "detail"

    def test_go_back(self):
        sm = StateMachine()
        sm.add_state(PrototypeState(name="a", is_initial=True))
        sm.add_state(PrototypeState(name="b"))
        sm.add_transition(StateTransition("a", "b", trigger="go"))
        sm.send_event("go")
        assert sm.state_name == "b"
        sm.go_back()
        assert sm.state_name == "a"

    def test_guard_condition(self):
        sm = StateMachine()
        sm.add_state(PrototypeState(name="login", is_initial=True))
        sm.add_state(PrototypeState(name="dashboard"))
        sm.add_transition(StateTransition("login", "dashboard", trigger="submit",
                                           guard="isValid == true"))
        sm.add_variable(PrototypeVariable("isValid", "false", VariableType.STRING))
        assert not sm.send_event("submit")
        sm.set_variable("isValid", "true")
        assert sm.send_event("submit")
        assert sm.state_name == "dashboard"

    def test_variables(self):
        sm = StateMachine()
        sm.add_variable(PrototypeVariable("count", 0, VariableType.NUMBER))
        assert sm.get_variable("count") == 0
        sm.set_variable("count", 5)
        assert sm.get_variable("count") == 5

    def test_serialization(self):
        sm = StateMachine(name="TestSM")
        sm.add_state(PrototypeState(name="s1", is_initial=True))
        sm.add_transition(StateTransition("s1", "s1", trigger="loop"))
        data = sm.to_dict()
        restored = StateMachine.from_dict(data)
        assert restored.name == "TestSM"

    def test_on_enter_exit_actions(self):
        sm = StateMachine()
        sm.add_variable(PrototypeVariable("entered", False))
        sm.add_state(PrototypeState(name="a", is_initial=True,
                                     on_exit_actions=[{"type": "set_variable", "variable": "entered", "value": True}]))
        sm.add_state(PrototypeState(name="b"))
        sm.add_transition(StateTransition("a", "b", trigger="go"))
        sm.send_event("go")
        assert sm.get_variable("entered") is True


# -----------------------------------------------------------------------
# Prototype Player
# -----------------------------------------------------------------------

class TestPrototypePlayer:
    def test_create_and_navigate(self):
        player = PrototypePlayer()
        player.add_screen(PrototypeScreen(id="home", name="Home"))
        player.add_screen(PrototypeScreen(id="detail", name="Detail"))
        assert player.current_screen.id == "home"
        player.navigate_to("detail")
        assert player.current_screen.id == "detail"

    def test_go_back(self):
        player = PrototypePlayer()
        player.add_screen(PrototypeScreen(id="a", name="A"))
        player.add_screen(PrototypeScreen(id="b", name="B"))
        player.navigate_to("b")
        player.go_back()
        assert player.current_screen.id == "a"

    def test_export_html(self):
        player = PrototypePlayer()
        player.add_screen(PrototypeScreen(id="home", name="Home",
                                          components=[{"type": "Button", "label": "Click"}]))
        html = player.export_html()
        assert "<!DOCTYPE html>" in html
        assert "EoStudio Prototype" in html
        assert "Click" in html

    def test_start(self):
        player = PrototypePlayer()
        player.add_screen(PrototypeScreen(id="s1", name="S1"))
        player.add_screen(PrototypeScreen(id="s2", name="S2"))
        player.navigate_to("s2")
        screen = player.start()
        assert screen.id == "s1"

    def test_device_frames(self):
        assert "iphone_14" in PrototypePlayer.DEVICE_FRAMES
        assert "desktop" in PrototypePlayer.DEVICE_FRAMES

    def test_serialization(self):
        player = PrototypePlayer()
        player.add_screen(PrototypeScreen(id="home", name="Home"))
        data = player.to_dict()
        restored = PrototypePlayer.from_dict(data)
        assert "home" in restored.screens
