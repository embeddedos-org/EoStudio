"""Design system — unified design tokens, component library, and theme management."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from eostudio.core.ui_flow.design_tokens import DesignTokenSet
from eostudio.core.ui_flow.variants import VariantSet
from eostudio.core.ui_flow.responsive import ResponsiveConfig, BREAKPOINTS


@dataclass
class DesignSystem:
    """Complete design system combining tokens, variants, and responsive config."""
    name: str = "EoStudio Design System"
    version: str = "1.0.0"
    description: str = ""
    light_theme: Optional[DesignTokenSet] = None
    dark_theme: Optional[DesignTokenSet] = None
    active_theme: str = "light"
    component_variants: Dict[str, VariantSet] = field(default_factory=dict)
    global_responsive: ResponsiveConfig = field(default_factory=ResponsiveConfig)
    custom_fonts: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.light_theme is None:
            self.light_theme = DesignTokenSet.create_default_light()
        if self.dark_theme is None:
            self.dark_theme = DesignTokenSet.create_default_dark()
        if not self.component_variants:
            self.component_variants["Button"] = VariantSet.create_button_variants()
            self.component_variants["Input"] = VariantSet.create_input_variants()

    @property
    def current_theme(self) -> DesignTokenSet:
        return self.dark_theme if self.active_theme == "dark" else self.light_theme

    def toggle_theme(self) -> str:
        self.active_theme = "dark" if self.active_theme == "light" else "light"
        return self.active_theme

    def get_token(self, name: str) -> Any:
        token = self.current_theme.get(name)
        return token.value if token else None

    def add_component_variants(self, variant_set: VariantSet) -> None:
        self.component_variants[variant_set.component_type] = variant_set

    def get_variant(self, component_type: str, variant_name: str) -> Optional[Any]:
        vs = self.component_variants.get(component_type)
        if vs:
            return vs.get_variant(variant_name)
        return None

    def export_css(self) -> str:
        """Export the entire design system as CSS."""
        lines = ["/* EoStudio Design System */\n"]

        # Light theme
        lines.append("/* Light Theme */")
        lines.append(self.light_theme.to_css_variables())
        lines.append("")

        # Dark theme
        lines.append("/* Dark Theme */")
        dark_css = self.dark_theme.to_css_variables().replace(":root", '[data-theme="dark"]')
        lines.append(dark_css)
        lines.append("")

        # Component styles
        for comp_type, vs in self.component_variants.items():
            lines.append(f"/* {comp_type} Variants */")
            for variant in vs.variants:
                class_name = f"{comp_type.lower()}--{variant.name}"
                lines.append(f".{class_name} {{")
                for prop, val in variant.properties.items():
                    css_prop = prop.replace("_", "-")
                    lines.append(f"  {css_prop}: {val};")
                lines.append("}")
                for state in variant.states:
                    selector = state.to_css_selector(f".{class_name}")
                    lines.append(f"{selector} {{")
                    for prop, val in state.properties.items():
                        css_prop = prop.replace("_", "-")
                        lines.append(f"  {css_prop}: {val};")
                    lines.append("}")
            lines.append("")

        return "\n".join(lines)

    def export_tailwind_config(self) -> Dict[str, Any]:
        """Export tokens as Tailwind CSS config extend section."""
        config: Dict[str, Any] = {"colors": {}, "spacing": {}, "fontSize": {},
                                   "borderRadius": {}, "boxShadow": {}}
        for token in self.current_theme.tokens:
            if token.category == "color":
                key = token.name.replace("color.", "").replace(".", "-")
                config["colors"][key] = token.value
            elif token.category == "spacing":
                key = token.name.replace("spacing.", "")
                config["spacing"][key] = f"{token.value}px"
            elif token.category == "radius":
                key = token.name.replace("radius.", "")
                config["borderRadius"][key] = token.value
        return {"theme": {"extend": config}}

    def export_style_dictionary(self) -> Dict[str, Any]:
        """Export in Style Dictionary format."""
        return self.current_theme.to_style_dictionary()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "active_theme": self.active_theme,
            "light_theme": self.light_theme.to_dict() if self.light_theme else None,
            "dark_theme": self.dark_theme.to_dict() if self.dark_theme else None,
            "component_variants": {k: v.to_dict() for k, v in self.component_variants.items()},
        }

    def save_json(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_json(cls, path: str) -> "DesignSystem":
        with open(path) as f:
            data = json.load(f)
        ds = cls(name=data.get("name", ""), version=data.get("version", "1.0.0"),
                 description=data.get("description", ""),
                 active_theme=data.get("active_theme", "light"))
        # Tokens would be loaded from dicts — simplified here
        return ds
