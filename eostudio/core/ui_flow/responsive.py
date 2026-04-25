"""Responsive breakpoints and configuration for multi-device design."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Breakpoint:
    """A responsive breakpoint definition."""
    name: str
    min_width: int
    max_width: Optional[int] = None
    label: str = ""
    icon: str = ""
    device_frame: Optional[Tuple[int, int]] = None  # width, height for preview frame

    @property
    def media_query(self) -> str:
        parts = []
        parts.append(f"(min-width: {self.min_width}px)")
        if self.max_width:
            parts.append(f"(max-width: {self.max_width}px)")
        return " and ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"name": self.name, "min_width": self.min_width}
        if self.max_width:
            d["max_width"] = self.max_width
        if self.label:
            d["label"] = self.label
        if self.device_frame:
            d["device_frame"] = list(self.device_frame)
        return d


# Standard breakpoints
BREAKPOINTS: Dict[str, Breakpoint] = {
    "mobile_sm": Breakpoint("mobile_sm", 320, 374, "Small Phone", "phone",
                            device_frame=(320, 568)),
    "mobile": Breakpoint("mobile", 375, 767, "Phone", "phone",
                         device_frame=(375, 812)),
    "tablet": Breakpoint("tablet", 768, 1023, "Tablet", "tablet",
                         device_frame=(768, 1024)),
    "desktop": Breakpoint("desktop", 1024, 1439, "Desktop", "monitor",
                          device_frame=(1440, 900)),
    "desktop_lg": Breakpoint("desktop_lg", 1440, None, "Large Desktop", "monitor",
                             device_frame=(1920, 1080)),
}


@dataclass
class ResponsiveOverride:
    """Property overrides for a specific breakpoint."""
    breakpoint: str
    properties: Dict[str, Any] = field(default_factory=dict)
    layout_overrides: Dict[str, Any] = field(default_factory=dict)
    visibility: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "breakpoint": self.breakpoint,
            "properties": self.properties,
            "layout_overrides": self.layout_overrides,
            "visibility": self.visibility,
        }


@dataclass
class ResponsiveConfig:
    """Responsive configuration for a component with per-breakpoint overrides."""
    base_breakpoint: str = "desktop"
    overrides: List[ResponsiveOverride] = field(default_factory=list)
    fluid_scaling: bool = False
    min_font_scale: float = 0.875
    max_font_scale: float = 1.0

    def add_override(self, breakpoint: str, **props: Any) -> ResponsiveOverride:
        override = ResponsiveOverride(breakpoint=breakpoint, properties=props)
        self.overrides = [o for o in self.overrides if o.breakpoint != breakpoint]
        self.overrides.append(override)
        return override

    def get_override(self, breakpoint: str) -> Optional[ResponsiveOverride]:
        for o in self.overrides:
            if o.breakpoint == breakpoint:
                return o
        return None

    def resolve_properties(self, breakpoint: str,
                           base_props: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve properties for a given breakpoint by merging base + overrides."""
        result = dict(base_props)
        bp = BREAKPOINTS.get(breakpoint)
        if not bp:
            return result

        # Apply all overrides for breakpoints <= current
        bp_order = list(BREAKPOINTS.keys())
        try:
            current_idx = bp_order.index(breakpoint)
        except ValueError:
            return result

        for i in range(current_idx + 1):
            override = self.get_override(bp_order[i])
            if override:
                result.update(override.properties)
        return result

    def generate_media_queries(self, class_name: str,
                               base_css: Dict[str, str]) -> str:
        """Generate CSS with media queries for all breakpoints."""
        lines = []
        # Base styles
        lines.append(f".{class_name} {{")
        for prop, val in base_css.items():
            lines.append(f"  {prop}: {val};")
        lines.append("}")

        for override in sorted(self.overrides,
                                key=lambda o: BREAKPOINTS.get(o.breakpoint, Breakpoint("", 0)).min_width):
            bp = BREAKPOINTS.get(override.breakpoint)
            if not bp or not override.properties:
                continue
            lines.append(f"\n@media {bp.media_query} {{")
            lines.append(f"  .{class_name} {{")
            for prop, val in override.properties.items():
                css_prop = prop.replace("_", "-")
                lines.append(f"    {css_prop}: {val};")
            lines.append("  }")
            if not override.visibility:
                lines.append(f"  .{class_name} {{ display: none; }}")
            lines.append("}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_breakpoint": self.base_breakpoint,
            "overrides": [o.to_dict() for o in self.overrides],
            "fluid_scaling": self.fluid_scaling,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResponsiveConfig":
        cfg = cls(
            base_breakpoint=data.get("base_breakpoint", "desktop"),
            fluid_scaling=data.get("fluid_scaling", False),
        )
        for o_data in data.get("overrides", []):
            cfg.overrides.append(ResponsiveOverride(
                breakpoint=o_data["breakpoint"],
                properties=o_data.get("properties", {}),
                layout_overrides=o_data.get("layout_overrides", {}),
                visibility=o_data.get("visibility", True),
            ))
        return cfg
