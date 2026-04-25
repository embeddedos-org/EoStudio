"""Promo templates — app store previews, social media, product launch videos."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from eostudio.core.video.compositor import (
    VideoCompositor, Layer, LayerType, LayerTransform, BlendMode,
)


@dataclass
class PromoTemplate:
    """A reusable promotional video/image template."""
    name: str
    category: str
    width: int
    height: int
    duration: float
    description: str = ""
    layers_config: List[Dict[str, Any]] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)

    def create_compositor(self, **overrides: Any) -> VideoCompositor:
        """Create a VideoCompositor from this template with variable substitutions."""
        comp = VideoCompositor(
            width=self.width, height=self.height,
            fps=overrides.get("fps", 30), duration=self.duration,
        )
        comp.background_color = overrides.get("background", "#000000")

        merged_vars = {**self.variables, **overrides}

        for lc in self.layers_config:
            content = dict(lc.get("content", {}))
            # Substitute variables in text content
            if "text" in content:
                for var_name, var_value in merged_vars.items():
                    content["text"] = content["text"].replace(f"{{{var_name}}}", str(var_value))

            transform_data = lc.get("transform", {})
            transform = LayerTransform(
                x=transform_data.get("x", 0), y=transform_data.get("y", 0),
                width=transform_data.get("width", 100), height=transform_data.get("height", 100),
                opacity=transform_data.get("opacity", 1.0),
            )

            layer = Layer(
                id=lc.get("id", f"layer_{len(comp.layers)}"),
                name=lc.get("name", "Layer"),
                layer_type=LayerType(lc.get("type", "text")),
                transform=transform,
                content=content,
                start_time=lc.get("start", 0),
                end_time=lc.get("end", self.duration),
            )
            comp.add_layer(layer)
        return comp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "category": self.category,
            "width": self.width, "height": self.height,
            "duration": self.duration, "description": self.description,
            "layers": self.layers_config, "variables": self.variables,
        }


# ---------------------------------------------------------------------------
# Built-in promo templates
# ---------------------------------------------------------------------------

PROMO_TEMPLATES: Dict[str, PromoTemplate] = {}


def _register(template: PromoTemplate) -> PromoTemplate:
    PROMO_TEMPLATES[template.name] = template
    return template


# ---- App Store Preview ----
_register(PromoTemplate(
    name="app_store_preview",
    category="app_store",
    width=1290, height=2796,
    duration=8.0,
    description="iOS App Store preview with device mockup and feature highlights",
    variables={"app_name": "My App", "tagline": "Your tagline here",
               "feature_1": "Feature 1", "feature_2": "Feature 2", "feature_3": "Feature 3"},
    layers_config=[
        {"id": "bg", "name": "Background", "type": "gradient",
         "content": {"colors": ["#667eea", "#764ba2"], "direction": "135deg"},
         "transform": {"width": 1290, "height": 2796}},
        {"id": "title", "name": "App Name", "type": "text",
         "content": {"text": "{app_name}", "font_size": 72, "color": "#ffffff",
                     "font_weight": 800, "text_align": "center"},
         "transform": {"x": 645, "y": 200, "width": 1000}},
        {"id": "tagline", "name": "Tagline", "type": "text",
         "content": {"text": "{tagline}", "font_size": 36, "color": "rgba(255,255,255,0.8)",
                     "text_align": "center"},
         "transform": {"x": 645, "y": 300, "width": 1000}},
        {"id": "device", "name": "Device Mockup", "type": "device_frame",
         "content": {"device": "iphone_15_pro"},
         "transform": {"x": 645, "y": 1400, "scale_x": 0.9, "scale_y": 0.9}},
    ],
))

# ---- Social Media Square ----
_register(PromoTemplate(
    name="social_square",
    category="social",
    width=1080, height=1080,
    duration=5.0,
    description="Square social media post with product showcase",
    variables={"headline": "Introducing", "product_name": "Product",
               "cta": "Try it now"},
    layers_config=[
        {"id": "bg", "name": "Background", "type": "gradient",
         "content": {"colors": ["#0f172a", "#1e293b"], "direction": "180deg"},
         "transform": {"width": 1080, "height": 1080}},
        {"id": "headline", "name": "Headline", "type": "text",
         "content": {"text": "{headline}", "font_size": 32, "color": "#94a3b8",
                     "font_weight": 500},
         "transform": {"x": 540, "y": 120}},
        {"id": "product", "name": "Product Name", "type": "text",
         "content": {"text": "{product_name}", "font_size": 64, "color": "#f1f5f9",
                     "font_weight": 800},
         "transform": {"x": 540, "y": 200}},
        {"id": "device", "name": "Device", "type": "device_frame",
         "content": {"device": "iphone_14"},
         "transform": {"x": 540, "y": 580, "scale_x": 0.55, "scale_y": 0.55}},
        {"id": "cta", "name": "CTA", "type": "text",
         "content": {"text": "{cta}", "font_size": 28, "color": "#3b82f6",
                     "font_weight": 600},
         "transform": {"x": 540, "y": 1000}},
    ],
))

# ---- Product Launch Video ----
_register(PromoTemplate(
    name="product_launch",
    category="video",
    width=1920, height=1080,
    duration=15.0,
    description="Full product launch video with animated feature reveals",
    variables={"product_name": "Product", "tagline": "The next big thing",
               "feature_1": "Feature 1", "feature_2": "Feature 2",
               "feature_3": "Feature 3", "url": "product.com"},
    layers_config=[
        {"id": "bg", "name": "Background", "type": "gradient",
         "content": {"colors": ["#0c0a09", "#1c1917"], "direction": "180deg"},
         "transform": {"width": 1920, "height": 1080}},
        {"id": "logo_reveal", "name": "Product Name", "type": "text",
         "content": {"text": "{product_name}", "font_size": 96, "color": "#ffffff",
                     "font_weight": 800}, "start": 0, "end": 4,
         "transform": {"x": 960, "y": 540}},
        {"id": "tagline_text", "name": "Tagline", "type": "text",
         "content": {"text": "{tagline}", "font_size": 36, "color": "#a8a29e"},
         "start": 1.5, "end": 4,
         "transform": {"x": 960, "y": 640}},
        {"id": "feat1", "name": "Feature 1", "type": "text",
         "content": {"text": "{feature_1}", "font_size": 48, "color": "#ffffff"},
         "start": 4, "end": 7,
         "transform": {"x": 400, "y": 500}},
        {"id": "feat2", "name": "Feature 2", "type": "text",
         "content": {"text": "{feature_2}", "font_size": 48, "color": "#ffffff"},
         "start": 7, "end": 10,
         "transform": {"x": 400, "y": 500}},
        {"id": "feat3", "name": "Feature 3", "type": "text",
         "content": {"text": "{feature_3}", "font_size": 48, "color": "#ffffff"},
         "start": 10, "end": 13,
         "transform": {"x": 400, "y": 500}},
        {"id": "cta_final", "name": "CTA", "type": "text",
         "content": {"text": "{url}", "font_size": 42, "color": "#3b82f6",
                     "font_weight": 600}, "start": 13, "end": 15,
         "transform": {"x": 960, "y": 540}},
    ],
))

# ---- Twitter/X Card ----
_register(PromoTemplate(
    name="twitter_card",
    category="social",
    width=1200, height=675,
    duration=3.0,
    description="Twitter/X card image with clean layout",
    variables={"title": "Title", "subtitle": "Subtitle", "badge": "NEW"},
    layers_config=[
        {"id": "bg", "name": "Background", "type": "gradient",
         "content": {"colors": ["#1e3a5f", "#0f172a"], "direction": "135deg"},
         "transform": {"width": 1200, "height": 675}},
        {"id": "badge_text", "name": "Badge", "type": "text",
         "content": {"text": "{badge}", "font_size": 18, "color": "#3b82f6",
                     "font_weight": 700, "bg": "rgba(59,130,246,0.1)", "padding": "8px 16px",
                     "border_radius": "20px"},
         "transform": {"x": 120, "y": 200}},
        {"id": "title_text", "name": "Title", "type": "text",
         "content": {"text": "{title}", "font_size": 48, "color": "#f1f5f9",
                     "font_weight": 700},
         "transform": {"x": 120, "y": 280}},
        {"id": "sub_text", "name": "Subtitle", "type": "text",
         "content": {"text": "{subtitle}", "font_size": 24, "color": "#94a3b8"},
         "transform": {"x": 120, "y": 360}},
    ],
))

# ---- LinkedIn Post ----
_register(PromoTemplate(
    name="linkedin_post",
    category="social",
    width=1200, height=627,
    duration=3.0,
    description="LinkedIn post image with professional styling",
    variables={"headline": "Headline", "body": "Body text", "author": "Author Name"},
    layers_config=[
        {"id": "bg", "name": "Background", "type": "gradient",
         "content": {"colors": ["#ffffff", "#f8fafc"], "direction": "180deg"},
         "transform": {"width": 1200, "height": 627}},
        {"id": "accent", "name": "Accent Bar", "type": "shape",
         "content": {"type": "rectangle", "color": "#0077b5"},
         "transform": {"x": 0, "y": 0, "width": 8, "height": 627}},
        {"id": "head", "name": "Headline", "type": "text",
         "content": {"text": "{headline}", "font_size": 42, "color": "#1f2937",
                     "font_weight": 700},
         "transform": {"x": 80, "y": 200}},
        {"id": "body_text", "name": "Body", "type": "text",
         "content": {"text": "{body}", "font_size": 24, "color": "#4b5563"},
         "transform": {"x": 80, "y": 300}},
        {"id": "author_text", "name": "Author", "type": "text",
         "content": {"text": "{author}", "font_size": 18, "color": "#6b7280"},
         "transform": {"x": 80, "y": 550}},
    ],
))

# ---- Product Hunt ----
_register(PromoTemplate(
    name="product_hunt",
    category="social",
    width=1270, height=760,
    duration=5.0,
    description="Product Hunt featured image",
    variables={"product": "Product Name", "tagline": "One line description",
               "emoji": "rocket"},
    layers_config=[
        {"id": "bg", "name": "Background", "type": "gradient",
         "content": {"colors": ["#fef3c7", "#fde68a"], "direction": "135deg"},
         "transform": {"width": 1270, "height": 760}},
        {"id": "name", "name": "Product", "type": "text",
         "content": {"text": "{product}", "font_size": 56, "color": "#1f2937",
                     "font_weight": 800},
         "transform": {"x": 635, "y": 300}},
        {"id": "tag", "name": "Tagline", "type": "text",
         "content": {"text": "{tagline}", "font_size": 28, "color": "#92400e"},
         "transform": {"x": 635, "y": 400}},
    ],
))


def get_template(name: str) -> Optional[PromoTemplate]:
    return PROMO_TEMPLATES.get(name)


def list_templates(category: Optional[str] = None) -> List[PromoTemplate]:
    templates = list(PROMO_TEMPLATES.values())
    if category:
        templates = [t for t in templates if t.category == category]
    return templates


def template_categories() -> List[str]:
    return sorted(set(t.category for t in PROMO_TEMPLATES.values()))
