"""Tests for design system — tokens, auto-layout, variants, responsive, design system."""

import pytest

from eostudio.core.ui_flow.design_tokens import (
    DesignToken,
    DesignTokenSet,
    ColorToken,
    TypographyToken,
    SpacingToken,
    ShadowToken,
)
from eostudio.core.ui_flow.auto_layout import (
    AutoLayout,
    LayoutDirection,
    LayoutAlignment,
    LayoutDistribution,
    LayoutConstraints,
)
from eostudio.core.ui_flow.variants import (
    ComponentVariant,
    ComponentState,
    VariantSet,
    StateOverride,
)
from eostudio.core.ui_flow.responsive import (
    Breakpoint,
    ResponsiveConfig,
    BREAKPOINTS,
    ResponsiveOverride,
)
from eostudio.core.ui_flow.design_system import DesignSystem


# -----------------------------------------------------------------------
# Design Tokens
# -----------------------------------------------------------------------

class TestDesignTokens:
    def test_basic_token(self):
        token = DesignToken("test", "#ff0000", "color")
        assert token.name == "test"
        assert token.value == "#ff0000"

    def test_css_variable(self):
        token = DesignToken("color.primary", "#2563eb", "color")
        css = token.to_css_variable()
        assert "--color-primary: #2563eb;" in css

    def test_color_token_rgba(self):
        token = ColorToken("primary", "#ff8800")
        r, g, b, a = token.rgba
        assert r == 255
        assert g == 136
        assert b == 0
        assert a == 1.0

    def test_color_with_opacity(self):
        token = ColorToken("primary", "#ff0000")
        semi = token.with_opacity(0.5)
        assert semi.opacity == 0.5

    def test_typography_token(self):
        token = TypographyToken("h1", "H1", font_size=36, font_weight=700)
        css = token.to_css()
        assert "36px" in css
        assert "700" in css

    def test_spacing_token(self):
        token = SpacingToken("spacing.md", 16)
        assert token.to_css() == "16px"

    def test_shadow_token(self):
        token = ShadowToken("shadow.md", "md", offset_y=4, blur=6)
        css = token.to_css()
        assert "4px" in css
        assert "6px" in css

    def test_serialization(self):
        token = DesignToken("test", "value", "cat", "desc")
        data = token.to_dict()
        restored = DesignToken.from_dict(data)
        assert restored.name == "test"
        assert restored.value == "value"


class TestDesignTokenSet:
    def test_create_default_light(self):
        ts = DesignTokenSet.create_default_light()
        assert ts.name == "Light Theme"
        assert len(ts.tokens) > 10

    def test_create_default_dark(self):
        ts = DesignTokenSet.create_default_dark()
        assert ts.name == "Dark Theme"

    def test_get_token(self):
        ts = DesignTokenSet.create_default_light()
        token = ts.get("color.primary")
        assert token is not None
        assert token.value == "#2563eb"

    def test_by_category(self):
        ts = DesignTokenSet.create_default_light()
        colors = ts.by_category("color")
        assert len(colors) >= 5

    def test_css_variables(self):
        ts = DesignTokenSet.create_default_light()
        css = ts.to_css_variables()
        assert ":root {" in css
        assert "--color-primary" in css

    def test_style_dictionary_export(self):
        ts = DesignTokenSet.create_default_light()
        sd = ts.to_style_dictionary()
        assert "color" in sd

    def test_add_and_get(self):
        ts = DesignTokenSet(name="test")
        ts.add(DesignToken("x", "y"))
        assert ts.get("x").value == "y"
        assert ts.get("missing") is None


# -----------------------------------------------------------------------
# Auto Layout
# -----------------------------------------------------------------------

class TestAutoLayout:
    def test_column_layout(self):
        layout = AutoLayout(direction=LayoutDirection.COLUMN, gap=10)
        positions = layout.compute_layout(300, 500, [(100, 40), (100, 40), (100, 40)])
        assert len(positions) == 3
        assert positions[0][1] < positions[1][1] < positions[2][1]  # y increases

    def test_row_layout(self):
        layout = AutoLayout(direction=LayoutDirection.ROW, gap=10)
        positions = layout.compute_layout(500, 300, [(100, 40), (100, 40)])
        assert positions[0][0] < positions[1][0]  # x increases

    def test_center_distribution(self):
        layout = AutoLayout(direction=LayoutDirection.ROW,
                           distribution=LayoutDistribution.CENTER)
        positions = layout.compute_layout(400, 100, [(50, 30)])
        assert positions[0][0] > 100  # centered, not at 0

    def test_space_between(self):
        layout = AutoLayout(direction=LayoutDirection.ROW,
                           distribution=LayoutDistribution.SPACE_BETWEEN)
        positions = layout.compute_layout(300, 100, [(50, 30), (50, 30)])
        assert positions[0][0] == 0
        assert positions[1][0] == 250  # pushed to end

    def test_padding(self):
        layout = AutoLayout(padding_top=20, padding_left=20)
        positions = layout.compute_layout(300, 300, [(100, 40)])
        assert positions[0][0] >= 20
        assert positions[0][1] >= 20

    def test_to_css(self):
        layout = AutoLayout(direction=LayoutDirection.ROW, gap=16)
        css = layout.to_css()
        assert css["display"] == "flex"
        assert css["flex-direction"] == "row"
        assert css["gap"] == "16px"

    def test_serialization(self):
        layout = AutoLayout(direction=LayoutDirection.ROW, gap=20)
        data = layout.to_dict()
        restored = AutoLayout.from_dict(data)
        assert restored.direction == LayoutDirection.ROW
        assert restored.gap == 20

    def test_constraints_fill_width(self):
        c = LayoutConstraints(fill_width=True)
        css = c.to_css()
        assert css["width"] == "100%"


# -----------------------------------------------------------------------
# Variants
# -----------------------------------------------------------------------

class TestVariants:
    def test_create_variant(self):
        v = ComponentVariant(name="primary", properties={"bg": "#2563eb"})
        assert v.name == "primary"

    def test_add_state(self):
        v = ComponentVariant(name="primary", properties={"bg": "#2563eb"})
        v.add_state(ComponentState.HOVER, bg="#1d4ed8")
        state = v.get_state(ComponentState.HOVER)
        assert state is not None
        assert state.properties["bg"] == "#1d4ed8"

    def test_resolve_properties(self):
        v = ComponentVariant(name="primary", properties={"bg": "#2563eb", "color": "#fff"})
        v.add_state(ComponentState.HOVER, bg="#1d4ed8")
        resolved = v.resolve_properties(ComponentState.HOVER)
        assert resolved["bg"] == "#1d4ed8"
        assert resolved["color"] == "#fff"  # inherited

    def test_resolve_default_state(self):
        v = ComponentVariant(name="x", properties={"bg": "red"})
        resolved = v.resolve_properties(ComponentState.DEFAULT)
        assert resolved["bg"] == "red"

    def test_variant_set(self):
        vs = VariantSet.create_button_variants()
        assert len(vs.variants) >= 3
        assert vs.default_variant == "primary"
        primary = vs.get_variant("primary")
        assert primary is not None

    def test_variant_names(self):
        vs = VariantSet.create_button_variants()
        names = vs.variant_names()
        assert "primary" in names
        assert "secondary" in names
        assert "ghost" in names

    def test_serialization(self):
        vs = VariantSet.create_button_variants()
        data = vs.to_dict()
        restored = VariantSet.from_dict(data)
        assert len(restored.variants) == len(vs.variants)

    def test_state_css_selector(self):
        override = StateOverride(state=ComponentState.HOVER, properties={"bg": "red"})
        selector = override.to_css_selector(".btn")
        assert ":hover" in selector


# -----------------------------------------------------------------------
# Responsive
# -----------------------------------------------------------------------

class TestResponsive:
    def test_breakpoints_defined(self):
        assert "mobile" in BREAKPOINTS
        assert "tablet" in BREAKPOINTS
        assert "desktop" in BREAKPOINTS

    def test_breakpoint_media_query(self):
        bp = BREAKPOINTS["tablet"]
        mq = bp.media_query
        assert "768px" in mq

    def test_responsive_config(self):
        cfg = ResponsiveConfig()
        cfg.add_override("mobile", font_size="14px", padding="8px")
        override = cfg.get_override("mobile")
        assert override is not None
        assert override.properties["font_size"] == "14px"

    def test_generate_media_queries(self):
        cfg = ResponsiveConfig()
        cfg.add_override("mobile", font_size="14px")
        css = cfg.generate_media_queries("card", {"font-size": "16px"})
        assert "@media" in css
        assert ".card" in css

    def test_serialization(self):
        cfg = ResponsiveConfig()
        cfg.add_override("tablet", columns="2")
        data = cfg.to_dict()
        restored = ResponsiveConfig.from_dict(data)
        assert len(restored.overrides) == 1


# -----------------------------------------------------------------------
# Design System
# -----------------------------------------------------------------------

class TestDesignSystem:
    def test_create_default(self):
        ds = DesignSystem()
        assert ds.light_theme is not None
        assert ds.dark_theme is not None
        assert "Button" in ds.component_variants

    def test_toggle_theme(self):
        ds = DesignSystem()
        assert ds.active_theme == "light"
        ds.toggle_theme()
        assert ds.active_theme == "dark"
        ds.toggle_theme()
        assert ds.active_theme == "light"

    def test_get_token(self):
        ds = DesignSystem()
        val = ds.get_token("color.primary")
        assert val is not None

    def test_export_css(self):
        ds = DesignSystem()
        css = ds.export_css()
        assert ":root {" in css
        assert "button--primary" in css

    def test_export_tailwind(self):
        ds = DesignSystem()
        config = ds.export_tailwind_config()
        assert "theme" in config
        assert "extend" in config["theme"]

    def test_export_style_dictionary(self):
        ds = DesignSystem()
        sd = ds.export_style_dictionary()
        assert isinstance(sd, dict)

    def test_to_dict(self):
        ds = DesignSystem()
        data = ds.to_dict()
        assert data["name"] == "EoStudio Design System"
        assert "light_theme" in data
        assert "component_variants" in data

    def test_get_variant(self):
        ds = DesignSystem()
        v = ds.get_variant("Button", "primary")
        assert v is not None
        v = ds.get_variant("NonExistent", "x")
        assert v is None
