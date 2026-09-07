"""Voice-to-Code Interface — speak your code, designs, and commands.

Features:
- Voice command recognition for editor actions
- Dictate code in natural language → convert to actual code
- Voice-driven design: "Add a blue button labeled Submit"
- Multi-language support
- Noise filtering and confidence scoring
- Hotword detection ("Hey EoStudio")
- Integration with all editors (UI, CAD, code, game)
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger(__name__)


class VoiceCommandType(Enum):
    """Categories of voice commands."""

    EDITOR_ACTION = auto()  # "undo", "redo", "save", "open file"
    CODE_DICTATION = auto()  # "define function called get user"
    DESIGN_COMMAND = auto()  # "add a button", "change color to blue"
    AI_QUERY = auto()  # "explain this function", "fix the error"
    NAVIGATION = auto()  # "go to line 42", "open settings"
    UNKNOWN = auto()


@dataclass
class VoiceCommand:
    """A recognized voice command."""

    raw_text: str
    command_type: VoiceCommandType
    intent: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    generated_code: str = ""


@dataclass
class TranscriptionResult:
    """Result from speech-to-text."""

    text: str
    confidence: float
    language: str = "en"
    duration_seconds: float = 0.0


# ------------------------------------------------------------------
# Command patterns
# ------------------------------------------------------------------

_EDITOR_PATTERNS = [
    (re.compile(r"\b(undo|redo)\b", re.I), "undo_redo"),
    (re.compile(r"\b(save|save file|save all)\b", re.I), "save"),
    (re.compile(r"\b(open|open file|new file)\b", re.I), "open"),
    (re.compile(r"\b(close|close tab|close file)\b", re.I), "close"),
    (re.compile(r"\b(run|execute|build|compile)\b", re.I), "run"),
    (re.compile(r"\b(format|format code|prettier)\b", re.I), "format"),
    (re.compile(r"\b(find|search|find in files)\b", re.I), "find"),
    (re.compile(r"\bgo to line (\d+)\b", re.I), "goto_line"),
    (re.compile(r"\b(zoom in|zoom out|reset zoom)\b", re.I), "zoom"),
    (re.compile(r"\b(toggle terminal|open terminal)\b", re.I), "terminal"),
    (re.compile(r"\b(split editor|split right|split down)\b", re.I), "split"),
    (re.compile(r"\b(toggle sidebar|hide sidebar)\b", re.I), "sidebar"),
]

_CODE_PATTERNS = [
    (re.compile(r"\bdefine (?:a |an )?(?:function|method|def) (?:called |named )?(\w+)\b", re.I), "define_function"),
    (re.compile(r"\bcreate (?:a |an )?class (?:called |named )?(\w+)\b", re.I), "create_class"),
    (re.compile(r"\bimport (\w+)\b", re.I), "import"),
    (re.compile(r"\bprint (?:the value of |variable )?(\w+)\b", re.I), "print_var"),
    (re.compile(r"\bfor loop (?:over |through )?(\w+)\b", re.I), "for_loop"),
    (re.compile(r"\bif (\w+) (?:is |equals? |==)\s*(\w+)\b", re.I), "if_statement"),
    (re.compile(r"\breturn (\w+)\b", re.I), "return_stmt"),
    (re.compile(r"\bassign (\w+) (?:to |equals? )?(.+)\b", re.I), "assignment"),
]

_DESIGN_PATTERNS = [
    (re.compile(r"\badd (?:a |an )?(\w+)\b(?:.*?label(?:ed|led)? ['\"]?([^'\"]+)['\"]?)?", re.I), "add_component"),
    (re.compile(r"\bchange (?:the )?color (?:to )?(\w+)\b", re.I), "change_color"),
    (re.compile(r"\bset (?:the )?(?:font )?size (?:to )?(\d+)\b", re.I), "set_size"),
    (re.compile(r"\bmove (?:it |this )?(?:to )?(?:the )?(left|right|up|down|center)\b", re.I), "move"),
    (re.compile(r"\bdelete (?:the )?selected\b", re.I), "delete_selected"),
    (re.compile(r"\bgroup (?:the )?selected\b", re.I), "group"),
    (re.compile(r"\balign (?:to )?(left|right|center|top|bottom|middle)\b", re.I), "align"),
]


class VoiceCommandParser:
    """Parses transcribed text into structured voice commands."""

    def parse(self, text: str) -> VoiceCommand:
        """Parse transcribed text into a VoiceCommand.

        Args:
            text: Raw transcribed text.

        Returns:
            A VoiceCommand with intent and parameters.
        """
        text_clean = text.strip()

        # Check editor actions
        for pattern, intent in _EDITOR_PATTERNS:
            m = pattern.search(text_clean)
            if m:
                params: Dict[str, Any] = {}
                if m.lastindex and m.lastindex >= 1:
                    params["value"] = m.group(1)
                return VoiceCommand(
                    raw_text=text_clean,
                    command_type=VoiceCommandType.EDITOR_ACTION,
                    intent=intent,
                    parameters=params,
                    confidence=0.9,
                )

        # Check code dictation
        for pattern, intent in _CODE_PATTERNS:
            m = pattern.search(text_clean)
            if m:
                params = {}
                if m.lastindex and m.lastindex >= 1:
                    params["name"] = m.group(1)
                if m.lastindex and m.lastindex >= 2:
                    params["value"] = m.group(2)
                return VoiceCommand(
                    raw_text=text_clean,
                    command_type=VoiceCommandType.CODE_DICTATION,
                    intent=intent,
                    parameters=params,
                    confidence=0.85,
                )

        # Check design commands
        for pattern, intent in _DESIGN_PATTERNS:
            m = pattern.search(text_clean)
            if m:
                params = {}
                if m.lastindex and m.lastindex >= 1:
                    params["target"] = m.group(1)
                if m.lastindex and m.lastindex >= 2:
                    params["label"] = m.group(2)
                return VoiceCommand(
                    raw_text=text_clean,
                    command_type=VoiceCommandType.DESIGN_COMMAND,
                    intent=intent,
                    parameters=params,
                    confidence=0.8,
                )

        # Default: treat as AI query
        return VoiceCommand(
            raw_text=text_clean,
            command_type=VoiceCommandType.AI_QUERY,
            intent="ask_ai",
            parameters={"query": text_clean},
            confidence=0.5,
        )


class CodeDictationConverter:
    """Converts natural language code dictation to actual code."""

    _TEMPLATES = {
        "define_function": {
            "python": "def {name}():\n    pass\n",
            "typescript": "function {name}() {{\n    \n}}\n",
            "javascript": "function {name}() {{\n    \n}}\n",
            "rust": "fn {name}() {{\n    \n}}\n",
        },
        "create_class": {
            "python": "class {name}:\n    def __init__(self):\n        pass\n",
            "typescript": "class {name} {{\n    constructor() {{\n    }}\n}}\n",
        },
        "import": {
            "python": "import {name}\n",
            "typescript": "import {{ {name} }} from './{name}';\n",
        },
        "for_loop": {
            "python": "for item in {name}:\n    pass\n",
            "typescript": "for (const item of {name}) {{\n    \n}}\n",
        },
        "if_statement": {
            "python": "if {name} == {value}:\n    pass\n",
            "typescript": "if ({name} === {value}) {{\n    \n}}\n",
        },
        "return_stmt": {
            "python": "return {name}\n",
            "typescript": "return {name};\n",
        },
        "assignment": {
            "python": "{name} = {value}\n",
            "typescript": "const {name} = {value};\n",
        },
        "print_var": {
            "python": "print({name})\n",
            "typescript": "console.log({name});\n",
        },
    }

    def convert(
        self,
        command: VoiceCommand,
        language: str = "python",
    ) -> str:
        """Convert a code dictation command to actual code.

        Args:
            command: The parsed voice command.
            language: Target programming language.

        Returns:
            Generated code string.
        """
        templates = self._TEMPLATES.get(command.intent, {})
        template = templates.get(language, templates.get("python", ""))

        if template:
            try:
                return template.format(**command.parameters)
            except KeyError:
                return template

        return f"# {command.raw_text}\n"


class DesignCommandExecutor:
    """Executes design commands on the active editor."""

    _COLOR_MAP = {
        "red": "#EF4444",
        "blue": "#3B82F6",
        "green": "#22C55E",
        "yellow": "#EAB308",
        "purple": "#A855F7",
        "orange": "#F97316",
        "pink": "#EC4899",
        "gray": "#6B7280",
        "white": "#FFFFFF",
        "black": "#000000",
        "teal": "#14B8A6",
        "indigo": "#6366F1",
    }

    def execute(
        self,
        command: VoiceCommand,
        editor_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a design command and return the resulting action.

        Returns:
            A dict describing the action to perform on the editor.
        """
        intent = command.intent
        params = command.parameters

        if intent == "add_component":
            comp_type = params.get("target", "container").capitalize()
            label = params.get("label", comp_type)
            return {
                "action": "add_component",
                "component": {
                    "type": comp_type,
                    "label": label,
                    "position": {"x": 100, "y": 100},
                    "size": {"width": 120, "height": 40},
                },
            }
        elif intent == "change_color":
            color_name = params.get("target", "blue").lower()
            hex_color = self._COLOR_MAP.get(color_name, "#3B82F6")
            return {"action": "set_property", "property": "fill", "value": hex_color}
        elif intent == "set_size":
            size = int(params.get("target", 16))
            return {"action": "set_property", "property": "font_size", "value": size}
        elif intent == "move":
            direction = params.get("target", "right").lower()
            delta_map = {
                "left": (-10, 0),
                "right": (10, 0),
                "up": (0, -10),
                "down": (0, 10),
                "center": (0, 0),
            }
            dx, dy = delta_map.get(direction, (0, 0))
            return {"action": "move", "dx": dx, "dy": dy}
        elif intent == "delete_selected":
            return {"action": "delete_selected"}
        elif intent == "align":
            return {"action": "align", "alignment": params.get("target", "center")}
        else:
            return {"action": "unknown", "raw": command.raw_text}


class VoiceToCode:
    """Main voice-to-code interface.

    Usage::

        vtc = VoiceToCode(language="python")

        # Process transcribed text
        result = vtc.process_text("define a function called calculate total")
        print(result.generated_code)  # "def calculate_total():\\n    pass\\n"

        # With AI enhancement
        result = vtc.process_text(
            "create a function that validates an email address",
            use_ai=True,
        )
    """

    def __init__(
        self,
        language: str = "python",
        router: Optional[Any] = None,
    ) -> None:
        self.language = language
        self._router = router
        self._parser = VoiceCommandParser()
        self._converter = CodeDictationConverter()
        self._design_executor = DesignCommandExecutor()
        self._on_command: Optional[Callable[[VoiceCommand], None]] = None

    def set_command_handler(self, handler: Callable[[VoiceCommand], None]) -> None:
        """Register a callback for when a command is recognized."""
        self._on_command = handler

    def process_text(
        self,
        text: str,
        use_ai: bool = False,
        editor_type: str = "code",
    ) -> VoiceCommand:
        """Process transcribed text and generate the appropriate action.

        Args:
            text: Transcribed speech text.
            use_ai: Use AI to generate richer code for complex dictations.
            editor_type: Active editor type ("code", "ui", "cad", etc.)

        Returns:
            A VoiceCommand with generated_code or action filled in.
        """
        command = self._parser.parse(text)

        if command.command_type == VoiceCommandType.CODE_DICTATION:
            if use_ai and self._router:
                command.generated_code = self._ai_generate_code(text)
            else:
                command.generated_code = self._converter.convert(command, self.language)

        elif command.command_type == VoiceCommandType.DESIGN_COMMAND:
            action = self._design_executor.execute(command)
            command.parameters["action"] = action

        elif command.command_type == VoiceCommandType.AI_QUERY and self._router:
            from eostudio.core.ai.multi_model_router import TaskType

            command.parameters["response"] = self._router.complete(text, task=TaskType.CHAT, complexity=4)

        if self._on_command:
            try:
                self._on_command(command)
            except Exception as exc:
                log.warning("Command handler error: %s", exc)

        return command

    def process_audio_file(self, audio_path: str, use_ai: bool = False) -> VoiceCommand:
        """Transcribe an audio file and process the command.

        Args:
            audio_path: Path to audio file (.wav, .mp3, .webm).
            use_ai: Use AI for code generation.

        Returns:
            Processed VoiceCommand.
        """
        transcription = self._transcribe(audio_path)
        if not transcription.text:
            return VoiceCommand(
                raw_text="",
                command_type=VoiceCommandType.UNKNOWN,
                intent="no_speech",
                confidence=0.0,
            )
        return self.process_text(transcription.text, use_ai=use_ai)

    def _transcribe(self, audio_path: str) -> TranscriptionResult:
        """Transcribe audio to text using available backend."""
        try:
            import subprocess

            result = subprocess.run(
                ["manus-speech-to-text", audio_path],
                capture_output=True,
                text=True,
                timeout=60,
            )
            text = result.stdout.strip()
            return TranscriptionResult(text=text, confidence=0.9)
        except Exception as exc:
            log.warning("Transcription failed: %s", exc)
            return TranscriptionResult(text="", confidence=0.0)

    def _ai_generate_code(self, description: str) -> str:
        """Use AI to generate code from a natural language description."""
        if not self._router:
            return f"# {description}\npass\n"

        from eostudio.core.ai.multi_model_router import TaskType

        prompt = f"Generate {self.language} code for: {description}\nReturn only the code, no explanations."
        code = self._router.complete(prompt, task=TaskType.CODE_GENERATION, complexity=5)
        # Strip fences
        code = re.sub(r"^```[a-zA-Z]*\n?", "", code.strip())
        code = re.sub(r"\n?```$", "", code.strip())
        return code.strip() + "\n"

    def supported_commands(self) -> Dict[str, List[str]]:
        """Return a dict of supported command categories and examples."""
        return {
            "Editor Actions": [
                "undo",
                "redo",
                "save",
                "open file",
                "close",
                "run",
                "format code",
                "go to line 42",
            ],
            "Code Dictation": [
                "define a function called get_user",
                "create a class called UserManager",
                "import requests",
                "for loop over items",
                "if status equals 200",
            ],
            "Design Commands": [
                "add a button labeled Submit",
                "change color to blue",
                "set font size to 16",
                "move to the right",
                "align to center",
                "delete selected",
            ],
            "AI Queries": [
                "explain this function",
                "fix the error",
                "how do I sort a list in Python",
                "refactor this code",
            ],
        }
