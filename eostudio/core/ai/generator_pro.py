"""Enhanced AI design generator — text-to-animated-UI, design system gen, screenshot-to-UI, accessibility."""

from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Optional

from eostudio.core.ai.llm_client import LLMClient, LLMConfig


class AIDesignGeneratorPro:
    """Enhanced AI-powered design generation with animation, design systems, and accessibility."""

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self._client = llm_client or LLMClient(LLMConfig())

    # ------------------------------------------------------------------
    # Text-to-Animated-UI
    # ------------------------------------------------------------------

    def text_to_animated_ui(self, prompt: str,
                            style: str = "modern") -> Dict[str, Any]:
        """Generate a complete UI with animation data from a text prompt.

        Returns a dict with components, layout, and animation_timeline.
        """
        messages = [{"role": "user", "content": (
            f"Generate an animated UI design as JSON with these keys:\n"
            f"- name: screen name\n"
            f"- components: list of {{type, label, id, position, size, style}}\n"
            f"- layout: {{direction, gap, padding, alignment}}\n"
            f"- animations: list of {{target_id, preset, delay, duration, trigger}}\n"
            f"  preset options: fadeIn, fadeInUp, slideUp, scaleIn, bounceIn, popIn, revealUp\n"
            f"  trigger options: mount, scroll, hover, click\n"
            f"- transitions: list of {{from_screen, to_screen, animation, trigger}}\n"
            f"Style: {style}\n"
            f"Prompt: {prompt}"
        )}]
        raw = self._client.chat(messages)
        try:
            result = json.loads(raw)
            if "components" in result:
                return self._enrich_animated_ui(result)
        except (json.JSONDecodeError, TypeError):
            pass
        return self._fallback_animated_ui(prompt)

    def _enrich_animated_ui(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all required fields exist in the AI output."""
        data.setdefault("name", "Generated Screen")
        data.setdefault("layout", {"direction": "column", "gap": 16, "padding": 24})
        data.setdefault("animations", [])
        data.setdefault("transitions", [])
        data.setdefault("design_tokens", {
            "primary": "#2563eb",
            "background": "#ffffff",
            "text": "#1f2937",
            "border_radius": 8,
        })

        # Assign IDs if missing
        for i, comp in enumerate(data.get("components", [])):
            comp.setdefault("id", f"comp_{i}")
            comp.setdefault("position", {"x": 0, "y": i * 60})
            comp.setdefault("size", {"width": 200, "height": 48})

        # Auto-generate entrance animations if none provided
        if not data["animations"]:
            for i, comp in enumerate(data.get("components", [])):
                data["animations"].append({
                    "target_id": comp["id"],
                    "preset": "fadeInUp",
                    "delay": i * 0.1,
                    "duration": 0.5,
                    "trigger": "mount",
                })
        return data

    def _fallback_animated_ui(self, prompt: str) -> Dict[str, Any]:
        return {
            "name": "Generated Screen",
            "components": [
                {"type": "Container", "label": "Header", "id": "header",
                 "position": {"x": 0, "y": 0}, "size": {"width": 375, "height": 60}},
                {"type": "Text", "label": prompt[:30], "id": "title",
                 "position": {"x": 0, "y": 80}, "size": {"width": 375, "height": 40}},
                {"type": "Button", "label": "Get Started", "id": "cta",
                 "position": {"x": 0, "y": 140}, "size": {"width": 200, "height": 48}},
            ],
            "layout": {"direction": "column", "gap": 16, "padding": 24},
            "animations": [
                {"target_id": "header", "preset": "fadeIn", "delay": 0, "duration": 0.3, "trigger": "mount"},
                {"target_id": "title", "preset": "fadeInUp", "delay": 0.1, "duration": 0.5, "trigger": "mount"},
                {"target_id": "cta", "preset": "scaleIn", "delay": 0.3, "duration": 0.4, "trigger": "mount"},
            ],
            "transitions": [],
            "metadata": {"source": "fallback"},
        }

    # ------------------------------------------------------------------
    # Text-to-Design-System
    # ------------------------------------------------------------------

    def text_to_design_system(self, prompt: str) -> Dict[str, Any]:
        """Generate a complete design system from a brand description."""
        messages = [{"role": "user", "content": (
            f"Generate a design system as JSON with:\n"
            f"- name: design system name\n"
            f"- colors: {{primary, secondary, success, warning, error, bg, text, border}}\n"
            f"- typography: {{h1, h2, h3, body, caption}} each with "
            f"  {{font_family, font_size, font_weight, line_height}}\n"
            f"- spacing: {{xs, sm, md, lg, xl}} as px values\n"
            f"- border_radius: {{sm, md, lg, full}}\n"
            f"- shadows: {{sm, md, lg}} as CSS box-shadow values\n"
            f"- component_styles: {{button, input, card}} with variant styles\n"
            f"Brand description: {prompt}"
        )}]
        raw = self._client.chat(messages)
        try:
            result = json.loads(raw)
            if "colors" in result:
                return result
        except (json.JSONDecodeError, TypeError):
            pass
        return {
            "name": "Generated Design System",
            "colors": {"primary": "#2563eb", "secondary": "#7c3aed", "success": "#16a34a",
                       "warning": "#d97706", "error": "#dc2626", "bg": "#ffffff",
                       "text": "#1f2937", "border": "#e5e7eb"},
            "typography": {
                "h1": {"font_family": "Inter", "font_size": 36, "font_weight": 700, "line_height": 1.2},
                "body": {"font_family": "Inter", "font_size": 16, "font_weight": 400, "line_height": 1.6},
            },
            "spacing": {"xs": 4, "sm": 8, "md": 16, "lg": 24, "xl": 32},
            "border_radius": {"sm": "4px", "md": "8px", "lg": "12px", "full": "9999px"},
            "shadows": {"sm": "0 1px 2px rgba(0,0,0,0.05)", "md": "0 4px 6px rgba(0,0,0,0.1)"},
        }

    # ------------------------------------------------------------------
    # Screenshot-to-UI
    # ------------------------------------------------------------------

    def screenshot_to_ui(self, image_path: str) -> Dict[str, Any]:
        """Convert a screenshot/image to UI component structure.

        Uses vision-capable LLM to analyze the image and extract components.
        """
        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
        except (FileNotFoundError, IOError):
            return {"error": f"Could not read image: {image_path}", "components": []}

        messages = [{"role": "user", "content": [
            {"type": "text", "text": (
                "Analyze this UI screenshot and extract components as JSON:\n"
                "- components: list of {type, label, position: {x,y}, size: {width,height}, style}\n"
                "- layout: detected layout (flex direction, gap, padding)\n"
                "- colors: extracted color palette\n"
                "- typography: detected font styles\n"
                "Component types: Button, Text, Input, Image, Card, Container, AppBar, BottomNav, "
                "List, Toggle, Checkbox, Radio, Slider, Avatar, Badge, Chip, Dialog, Snackbar"
            )},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}},
        ]}]
        raw = self._client.chat(messages)
        try:
            result = json.loads(raw)
            if "components" in result:
                return result
        except (json.JSONDecodeError, TypeError):
            pass
        return {
            "components": [],
            "layout": {"direction": "column"},
            "colors": {},
            "metadata": {"source": "screenshot", "image": image_path},
        }

    # ------------------------------------------------------------------
    # Accessibility Audit
    # ------------------------------------------------------------------

    def accessibility_audit(self, components: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run an AI-powered accessibility audit on a component tree."""
        messages = [{"role": "user", "content": (
            f"Audit this UI for accessibility (WCAG 2.1 AA) and return JSON:\n"
            f"- score: 0-100\n"
            f"- issues: list of {{severity, component_id, rule, message, fix}}\n"
            f"  severity: error, warning, info\n"
            f"  rules: contrast, alt-text, focus-order, touch-target, aria-labels, "
            f"  color-only, keyboard-nav, heading-order, form-labels\n"
            f"- suggestions: list of improvement recommendations\n\n"
            f"Components:\n{json.dumps(components, indent=2)}"
        )}]
        raw = self._client.chat(messages)
        try:
            result = json.loads(raw)
            if "issues" in result or "score" in result:
                return result
        except (json.JSONDecodeError, TypeError):
            pass

        # Perform basic rule-based audit as fallback
        return self._rule_based_audit(components)

    def _rule_based_audit(self, components: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Basic rule-based accessibility audit."""
        issues: List[Dict[str, Any]] = []
        for comp in components:
            comp_id = comp.get("id", comp.get("label", "unknown"))
            comp_type = comp.get("type", "")

            if comp_type == "Image" and not comp.get("alt"):
                issues.append({
                    "severity": "error", "component_id": comp_id,
                    "rule": "alt-text",
                    "message": "Image missing alt text",
                    "fix": "Add descriptive alt text to the image",
                })

            if comp_type == "Button":
                size = comp.get("size", {})
                w = size.get("width", 48)
                h = size.get("height", 48)
                if w < 44 or h < 44:
                    issues.append({
                        "severity": "warning", "component_id": comp_id,
                        "rule": "touch-target",
                        "message": f"Touch target too small ({w}x{h}px, minimum 44x44px)",
                        "fix": "Increase button size to at least 44x44 pixels",
                    })

            if comp_type == "Input" and not comp.get("label") and not comp.get("aria_label"):
                issues.append({
                    "severity": "error", "component_id": comp_id,
                    "rule": "form-labels",
                    "message": "Input field missing label",
                    "fix": "Add a visible label or aria-label to the input",
                })

        score = max(0, 100 - len(issues) * 10)
        return {
            "score": score,
            "issues": issues,
            "suggestions": [
                "Ensure all interactive elements are keyboard accessible",
                "Test with screen reader (VoiceOver / TalkBack)",
                "Verify color contrast ratios meet WCAG AA (4.5:1 for text)",
            ],
        }

    # ------------------------------------------------------------------
    # Smart Layout Suggestions
    # ------------------------------------------------------------------

    def suggest_layout(self, components: List[Dict[str, Any]],
                       target_device: str = "mobile") -> Dict[str, Any]:
        """Suggest optimal layout for given components and target device."""
        messages = [{"role": "user", "content": (
            f"Suggest the best layout for these UI components on {target_device}:\n"
            f"{json.dumps(components, indent=2)}\n\n"
            f"Return JSON with:\n"
            f"- layout: {{direction, gap, padding, alignment, distribution}}\n"
            f"- component_order: reordered component IDs for best UX\n"
            f"- responsive_hints: suggestions for other breakpoints\n"
            f"- reasoning: brief explanation"
        )}]
        raw = self._client.chat(messages)
        try:
            result = json.loads(raw)
            if "layout" in result:
                return result
        except (json.JSONDecodeError, TypeError):
            pass
        return {
            "layout": {"direction": "column", "gap": 16, "padding": 24,
                       "alignment": "stretch", "distribution": "start"},
            "component_order": [c.get("id", f"comp_{i}") for i, c in enumerate(components)],
            "responsive_hints": {
                "tablet": "Consider 2-column grid layout",
                "desktop": "Use 3-column layout with sidebar",
            },
        }

    # ------------------------------------------------------------------
    # Color Palette Generation
    # ------------------------------------------------------------------

    def generate_palette(self, brand_color: str,
                         style: str = "modern") -> Dict[str, Any]:
        """Generate a full color palette from a single brand color."""
        messages = [{"role": "user", "content": (
            f"Generate a complete UI color palette from brand color {brand_color}.\n"
            f"Style: {style}\n"
            f"Return JSON with:\n"
            f"- primary: {{50-900 shades}}\n"
            f"- secondary: complementary color with shades\n"
            f"- neutral: gray scale shades\n"
            f"- semantic: {{success, warning, error, info}} colors\n"
            f"- surfaces: {{bg, card, elevated, overlay}}\n"
            f"- dark_mode: inverted palette for dark theme"
        )}]
        raw = self._client.chat(messages)
        try:
            result = json.loads(raw)
            if "primary" in result:
                return result
        except (json.JSONDecodeError, TypeError):
            pass
        # Generate basic palette from the color
        return self._generate_basic_palette(brand_color)

    def _generate_basic_palette(self, hex_color: str) -> Dict[str, Any]:
        """Generate a basic palette algorithmically."""
        hex_val = hex_color.lstrip("#")
        r, g, b = int(hex_val[0:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16)

        def shade(factor: float) -> str:
            nr = min(255, int(r + (255 - r) * factor)) if factor > 0 else max(0, int(r * (1 + factor)))
            ng = min(255, int(g + (255 - g) * factor)) if factor > 0 else max(0, int(g * (1 + factor)))
            nb = min(255, int(b + (255 - b) * factor)) if factor > 0 else max(0, int(b * (1 + factor)))
            return f"#{nr:02x}{ng:02x}{nb:02x}"

        return {
            "primary": {
                "50": shade(0.9), "100": shade(0.8), "200": shade(0.6),
                "300": shade(0.4), "400": shade(0.2), "500": hex_color,
                "600": shade(-0.15), "700": shade(-0.3), "800": shade(-0.45),
                "900": shade(-0.6),
            },
            "neutral": {
                "50": "#f9fafb", "100": "#f3f4f6", "200": "#e5e7eb",
                "300": "#d1d5db", "400": "#9ca3af", "500": "#6b7280",
                "600": "#4b5563", "700": "#374151", "800": "#1f2937", "900": "#111827",
            },
            "semantic": {
                "success": "#16a34a", "warning": "#d97706",
                "error": "#dc2626", "info": "#0284c7",
            },
            "surfaces": {
                "bg": "#ffffff", "card": "#ffffff",
                "elevated": "#f9fafb", "overlay": "rgba(0,0,0,0.5)",
            },
        }
