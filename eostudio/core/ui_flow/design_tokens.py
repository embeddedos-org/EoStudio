"""Design tokens — colors, typography, spacing, shadows for consistent theming."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class DesignToken:
    """Base design token with name, value, and category."""
    name: str
    value: Any
    category: str = "general"
    description: str = ""
    alias_of: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"name": self.name, "value": self.value, "category": self.category}
        if self.description:
            d["description"] = self.description
        if self.alias_of:
            d["alias_of"] = self.alias_of
        return d

    def to_css_variable(self) -> str:
        css_name = self.name.replace(".", "-").replace("_", "-")
        return f"--{css_name}: {self.value};"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DesignToken":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ColorToken(DesignToken):
    """Color design token with hex value and opacity."""
    category: str = "color"
    opacity: float = 1.0

    @property
    def rgba(self) -> Tuple[int, int, int, float]:
        hex_val = self.value.lstrip("#")
        if len(hex_val) == 6:
            r, g, b = int(hex_val[0:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16)
        elif len(hex_val) == 3:
            r, g, b = int(hex_val[0] * 2, 16), int(hex_val[1] * 2, 16), int(hex_val[2] * 2, 16)
        else:
            r, g, b = 0, 0, 0
        return (r, g, b, self.opacity)

    def with_opacity(self, opacity: float) -> "ColorToken":
        return ColorToken(name=self.name, value=self.value, opacity=opacity,
                          description=self.description)


@dataclass
class TypographyToken(DesignToken):
    """Typography design token."""
    category: str = "typography"
    font_family: str = "Inter, system-ui, sans-serif"
    font_size: float = 16.0
    font_weight: int = 400
    line_height: float = 1.5
    letter_spacing: float = 0.0

    def to_css(self) -> str:
        return (f"font-family: {self.font_family}; "
                f"font-size: {self.font_size}px; "
                f"font-weight: {self.font_weight}; "
                f"line-height: {self.line_height}; "
                f"letter-spacing: {self.letter_spacing}em;")


@dataclass
class SpacingToken(DesignToken):
    """Spacing design token (px values)."""
    category: str = "spacing"

    def to_css(self) -> str:
        return f"{self.value}px"


@dataclass
class ShadowToken(DesignToken):
    """Shadow design token."""
    category: str = "shadow"
    offset_x: float = 0.0
    offset_y: float = 2.0
    blur: float = 8.0
    spread: float = 0.0
    color: str = "rgba(0,0,0,0.1)"

    def to_css(self) -> str:
        return f"{self.offset_x}px {self.offset_y}px {self.blur}px {self.spread}px {self.color}"


@dataclass
class DesignTokenSet:
    """A collection of design tokens forming a theme/design system."""
    name: str = "Default"
    description: str = ""
    tokens: List[DesignToken] = field(default_factory=list)

    def add(self, token: DesignToken) -> None:
        self.tokens.append(token)

    def get(self, name: str) -> Optional[DesignToken]:
        for t in self.tokens:
            if t.name == name:
                if t.alias_of:
                    return self.get(t.alias_of)
                return t
        return None

    def by_category(self, category: str) -> List[DesignToken]:
        return [t for t in self.tokens if t.category == category]

    def to_css_variables(self) -> str:
        lines = [":root {"]
        for token in self.tokens:
            if not token.alias_of:
                lines.append(f"  {token.to_css_variable()}")
        lines.append("}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "tokens": [t.to_dict() for t in self.tokens],
        }

    def to_style_dictionary(self) -> Dict[str, Any]:
        """Export in Style Dictionary format for integration with external tools."""
        result: Dict[str, Any] = {}
        for token in self.tokens:
            parts = token.name.split(".")
            current = result
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = {"value": token.value}
            if token.description:
                current[parts[-1]]["comment"] = token.description
        return result

    @classmethod
    def create_default_light(cls) -> "DesignTokenSet":
        ts = cls(name="Light Theme", description="Default light theme")
        # Colors
        ts.add(ColorToken("color.primary", "#2563eb", description="Primary brand color"))
        ts.add(ColorToken("color.primary.hover", "#1d4ed8"))
        ts.add(ColorToken("color.secondary", "#7c3aed"))
        ts.add(ColorToken("color.success", "#16a34a"))
        ts.add(ColorToken("color.warning", "#d97706"))
        ts.add(ColorToken("color.error", "#dc2626"))
        ts.add(ColorToken("color.bg", "#ffffff"))
        ts.add(ColorToken("color.bg.secondary", "#f5f5f5"))
        ts.add(ColorToken("color.text", "#1f2937"))
        ts.add(ColorToken("color.text.secondary", "#6b7280"))
        ts.add(ColorToken("color.border", "#e5e7eb"))
        # Typography
        ts.add(TypographyToken("type.h1", "H1", font_size=36, font_weight=700, line_height=1.2))
        ts.add(TypographyToken("type.h2", "H2", font_size=30, font_weight=600, line_height=1.3))
        ts.add(TypographyToken("type.h3", "H3", font_size=24, font_weight=600, line_height=1.4))
        ts.add(TypographyToken("type.body", "Body", font_size=16, font_weight=400, line_height=1.6))
        ts.add(TypographyToken("type.caption", "Caption", font_size=12, font_weight=400, line_height=1.4))
        # Spacing
        for name, val in [("xs", 4), ("sm", 8), ("md", 16), ("lg", 24), ("xl", 32), ("2xl", 48)]:
            ts.add(SpacingToken(f"spacing.{name}", val))
        # Shadows
        ts.add(ShadowToken("shadow.sm", "sm", offset_y=1, blur=2, color="rgba(0,0,0,0.05)"))
        ts.add(ShadowToken("shadow.md", "md", offset_y=4, blur=6, spread=-1, color="rgba(0,0,0,0.1)"))
        ts.add(ShadowToken("shadow.lg", "lg", offset_y=10, blur=15, spread=-3, color="rgba(0,0,0,0.1)"))
        ts.add(ShadowToken("shadow.xl", "xl", offset_y=20, blur=25, spread=-5, color="rgba(0,0,0,0.1)"))
        # Radius
        ts.add(DesignToken("radius.sm", "4px", "radius"))
        ts.add(DesignToken("radius.md", "8px", "radius"))
        ts.add(DesignToken("radius.lg", "12px", "radius"))
        ts.add(DesignToken("radius.full", "9999px", "radius"))
        return ts

    @classmethod
    def create_default_dark(cls) -> "DesignTokenSet":
        ts = cls(name="Dark Theme", description="Default dark theme")
        ts.add(ColorToken("color.primary", "#3b82f6"))
        ts.add(ColorToken("color.primary.hover", "#60a5fa"))
        ts.add(ColorToken("color.secondary", "#8b5cf6"))
        ts.add(ColorToken("color.success", "#22c55e"))
        ts.add(ColorToken("color.warning", "#f59e0b"))
        ts.add(ColorToken("color.error", "#ef4444"))
        ts.add(ColorToken("color.bg", "#0f172a"))
        ts.add(ColorToken("color.bg.secondary", "#1e293b"))
        ts.add(ColorToken("color.text", "#f1f5f9"))
        ts.add(ColorToken("color.text.secondary", "#94a3b8"))
        ts.add(ColorToken("color.border", "#334155"))
        ts.add(TypographyToken("type.h1", "H1", font_size=36, font_weight=700, line_height=1.2))
        ts.add(TypographyToken("type.h2", "H2", font_size=30, font_weight=600, line_height=1.3))
        ts.add(TypographyToken("type.h3", "H3", font_size=24, font_weight=600, line_height=1.4))
        ts.add(TypographyToken("type.body", "Body", font_size=16, font_weight=400, line_height=1.6))
        ts.add(TypographyToken("type.caption", "Caption", font_size=12, font_weight=400, line_height=1.4))
        for name, val in [("xs", 4), ("sm", 8), ("md", 16), ("lg", 24), ("xl", 32), ("2xl", 48)]:
            ts.add(SpacingToken(f"spacing.{name}", val))
        ts.add(ShadowToken("shadow.sm", "sm", offset_y=1, blur=2, color="rgba(0,0,0,0.3)"))
        ts.add(ShadowToken("shadow.md", "md", offset_y=4, blur=6, spread=-1, color="rgba(0,0,0,0.4)"))
        ts.add(ShadowToken("shadow.lg", "lg", offset_y=10, blur=15, spread=-3, color="rgba(0,0,0,0.4)"))
        ts.add(DesignToken("radius.sm", "4px", "radius"))
        ts.add(DesignToken("radius.md", "8px", "radius"))
        ts.add(DesignToken("radius.lg", "12px", "radius"))
        ts.add(DesignToken("radius.full", "9999px", "radius"))
        return ts
