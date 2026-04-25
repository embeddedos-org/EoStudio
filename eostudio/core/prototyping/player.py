"""Prototype player — runs interactive prototypes with navigation and interaction."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from eostudio.core.prototyping.interactions import InteractionManager, InteractionAction
from eostudio.core.prototyping.transitions import ScreenTransition, TransitionType
from eostudio.core.prototyping.gestures import GestureRecognizer, GestureType
from eostudio.core.prototyping.state_machine import StateMachine, PrototypeState, PrototypeVariable


@dataclass
class PrototypeScreen:
    """A screen in the prototype with components and interactions."""
    id: str
    name: str
    components: List[Dict[str, Any]] = field(default_factory=list)
    background: str = "#ffffff"
    device_frame: str = "iphone_14"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "components": self.components,
            "background": self.background,
            "device_frame": self.device_frame,
        }


class PrototypePlayer:
    """Runs an interactive prototype with navigation, interactions, and state management."""

    DEVICE_FRAMES = {
        "iphone_14": {"width": 390, "height": 844, "label": "iPhone 14"},
        "iphone_15_pro": {"width": 393, "height": 852, "label": "iPhone 15 Pro"},
        "iphone_se": {"width": 375, "height": 667, "label": "iPhone SE"},
        "pixel_8": {"width": 412, "height": 915, "label": "Pixel 8"},
        "galaxy_s24": {"width": 360, "height": 780, "label": "Galaxy S24"},
        "ipad_pro": {"width": 1024, "height": 1366, "label": "iPad Pro"},
        "desktop": {"width": 1440, "height": 900, "label": "Desktop"},
        "macbook": {"width": 1512, "height": 982, "label": "MacBook Pro"},
    }

    def __init__(self) -> None:
        self.screens: Dict[str, PrototypeScreen] = {}
        self.transitions: List[ScreenTransition] = []
        self.interactions = InteractionManager()
        self.gestures = GestureRecognizer()
        self.state_machine = StateMachine()
        self._current_screen: Optional[str] = None
        self._history: List[str] = []
        self._recording: List[Dict[str, Any]] = []
        self._is_recording = False

    @property
    def current_screen(self) -> Optional[PrototypeScreen]:
        if self._current_screen:
            return self.screens.get(self._current_screen)
        return None

    def add_screen(self, screen: PrototypeScreen) -> None:
        self.screens[screen.id] = screen
        # Add state machine state for this screen
        self.state_machine.add_state(PrototypeState(
            name=screen.id,
            screen_id=screen.id,
            is_initial=len(self.screens) == 1,
        ))
        if not self._current_screen:
            self._current_screen = screen.id

    def add_transition(self, transition: ScreenTransition) -> None:
        self.transitions.append(transition)

    def navigate_to(self, screen_id: str,
                    transition_type: TransitionType = TransitionType.PUSH) -> bool:
        """Navigate to a specific screen."""
        if screen_id not in self.screens:
            return False

        old_screen = self._current_screen
        if old_screen:
            self._history.append(old_screen)

        self._current_screen = screen_id

        if self._is_recording and old_screen:
            self._recording.append({
                "type": "navigation",
                "from": old_screen,
                "to": screen_id,
                "transition": transition_type.value,
            })

        return True

    def go_back(self) -> bool:
        """Navigate back to previous screen."""
        if self._history:
            self._current_screen = self._history.pop()
            return True
        return False

    def start(self) -> Optional[PrototypeScreen]:
        """Start the prototype from the first screen."""
        if self.screens:
            self._current_screen = next(iter(self.screens))
            self._history.clear()
            self.state_machine.reset()
            return self.current_screen
        return None

    def start_recording(self) -> None:
        """Start recording user interactions for playback."""
        self._is_recording = True
        self._recording.clear()

    def stop_recording(self) -> List[Dict[str, Any]]:
        """Stop recording and return the recorded session."""
        self._is_recording = False
        return list(self._recording)

    def get_transition(self, from_screen: str, to_screen: str) -> Optional[ScreenTransition]:
        """Get the transition between two screens."""
        for t in self.transitions:
            if t.from_screen == from_screen and t.to_screen == to_screen:
                return t
        return None

    def export_html(self) -> str:
        """Export the prototype as a standalone HTML file for sharing."""
        screens_json = json.dumps({sid: s.to_dict() for sid, s in self.screens.items()})
        transitions_json = json.dumps([t.to_dict() for t in self.transitions])
        interactions_json = json.dumps(self.interactions.to_dict())

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EoStudio Prototype</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         display: flex; justify-content: center; align-items: center;
         min-height: 100vh; background: #1a1a2e; }}
  .device-frame {{ width: 390px; height: 844px; background: #fff;
                   border-radius: 44px; overflow: hidden; position: relative;
                   box-shadow: 0 25px 50px rgba(0,0,0,0.4); }}
  .screen {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%;
             transition: transform 0.3s ease, opacity 0.3s ease; }}
  .screen.entering {{ animation: slideIn 0.3s ease forwards; }}
  .screen.exiting {{ animation: slideOut 0.3s ease forwards; }}
  .component {{ position: absolute; cursor: pointer; }}
  .nav-dots {{ position: fixed; bottom: 20px; display: flex; gap: 8px; }}
  .nav-dot {{ width: 10px; height: 10px; border-radius: 50%; background: #444;
              cursor: pointer; transition: background 0.2s; }}
  .nav-dot.active {{ background: #3b82f6; }}
  @keyframes slideIn {{ from {{ transform: translateX(100%); }} to {{ transform: translateX(0); }} }}
  @keyframes slideOut {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-100%); }} }}
  @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
</style>
</head>
<body>
<div class="device-frame" id="device">
  <div id="screen-container"></div>
</div>
<div class="nav-dots" id="nav-dots"></div>
<script>
const screens = {screens_json};
const transitions = {transitions_json};
const interactions = {interactions_json};
let currentScreen = Object.keys(screens)[0];
let history = [];

function renderScreen(screenId) {{
  const container = document.getElementById('screen-container');
  const screen = screens[screenId];
  if (!screen) return;
  container.innerHTML = '';
  const div = document.createElement('div');
  div.className = 'screen entering';
  div.style.background = screen.background || '#ffffff';
  screen.components.forEach(comp => {{
    const el = document.createElement('div');
    el.className = 'component';
    el.textContent = comp.label || comp.type;
    const pos = comp.position || {{x: 0, y: 0}};
    const size = comp.size || {{width: 100, height: 40}};
    el.style.cssText = `left:${{pos.x}}px;top:${{pos.y}}px;width:${{size.width}}px;height:${{size.height}}px;
      display:flex;align-items:center;justify-content:center;
      background:#f0f0f0;border-radius:8px;font-size:14px;`;
    div.appendChild(el);
  }});
  container.appendChild(div);
  updateNavDots(screenId);
}}

function navigateTo(screenId) {{
  if (screens[screenId]) {{
    history.push(currentScreen);
    currentScreen = screenId;
    renderScreen(screenId);
  }}
}}

function updateNavDots(activeId) {{
  const dots = document.getElementById('nav-dots');
  dots.innerHTML = '';
  Object.keys(screens).forEach(id => {{
    const dot = document.createElement('div');
    dot.className = 'nav-dot' + (id === activeId ? ' active' : '');
    dot.onclick = () => navigateTo(id);
    dots.appendChild(dot);
  }});
}}

renderScreen(currentScreen);
</script>
</body>
</html>"""

    def export_gif_frames(self, fps: int = 15,
                          duration: float = 5.0) -> List[Dict[str, Any]]:
        """Generate frame data for GIF/video export of the prototype walkthrough."""
        frames = []
        total_frames = int(fps * duration)
        screens_list = list(self.screens.keys())
        frames_per_screen = total_frames // max(1, len(screens_list))

        for si, screen_id in enumerate(screens_list):
            screen = self.screens[screen_id]
            for fi in range(frames_per_screen):
                frames.append({
                    "frame": si * frames_per_screen + fi,
                    "screen_id": screen_id,
                    "screen_name": screen.name,
                    "components": screen.components,
                    "background": screen.background,
                    "is_transition": fi < 5 and si > 0,
                    "transition_progress": fi / 5 if fi < 5 and si > 0 else 1.0,
                })
        return frames

    def to_dict(self) -> Dict[str, Any]:
        return {
            "screens": {sid: s.to_dict() for sid, s in self.screens.items()},
            "transitions": [t.to_dict() for t in self.transitions],
            "interactions": self.interactions.to_dict(),
            "state_machine": self.state_machine.to_dict(),
            "current_screen": self._current_screen,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PrototypePlayer":
        player = cls()
        for s_data in data.get("screens", {}).values():
            player.add_screen(PrototypeScreen(
                id=s_data["id"], name=s_data["name"],
                components=s_data.get("components", []),
                background=s_data.get("background", "#ffffff"),
                device_frame=s_data.get("device_frame", "iphone_14"),
            ))
        for t_data in data.get("transitions", []):
            player.add_transition(ScreenTransition.from_dict(t_data))
        if "interactions" in data:
            player.interactions = InteractionManager.from_dict(data["interactions"])
        if "state_machine" in data:
            player.state_machine = StateMachine.from_dict(data["state_machine"])
        return player
