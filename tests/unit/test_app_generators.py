# SPDX-License-Identifier: MIT
"""Unit tests for the full-project generators in eostudio.codegen:
WebAppGenerator (webapp.py), DesktopAppGenerator (desktop.py) and
MobileAppGenerator (mobile.py).

Every target is generated from the same screens; the tests check that the
Python and JSON files parse, that screen content and model fields reach the
output, and two regressions: mojibake in desktop.py and the Swift @main file
name. Contributes to the #36 coverage ratchet.
"""

import ast
import itertools
import json

import pytest
from eostudio.codegen.desktop import DesktopAppGenerator
from eostudio.codegen.mobile import MobileAppGenerator
from eostudio.codegen.webapp import WebAppGenerator

COMPONENT_TYPES = [
    "Button",
    "Text",
    "Input",
    "Container",
    "Card",
    "AppBar",
    "BottomNav",
    "List",
    "Grid",
    "Image",
    "Dialog",
    "TabBar",
    "Unknown",
]

SCREENS = [
    {
        "name": "Home",
        "components": [{"type": "Button", "label": "Checkout"}, {"type": "Text", "text": "Welcome back"}]
        + [{"type": t, "label": f"{t} label"} for t in COMPONENT_TYPES],
    },
    {"name": "Order Details", "components": []},
]

MODELS = [
    {
        "name": "Order",
        "fields": [
            {"name": "title", "type": "str"},
            {"name": "qty", "type": "int"},
            {"name": "price", "type": "float"},
            {"name": "paid", "type": "bool"},
            {"name": "placed_at", "type": "datetime"},
        ],
    }
]

MOJIBAKE = ("â€", "Ã")


def assert_well_formed(files):
    assert files
    for path, source in files.items():
        assert isinstance(source, str) and source, path
        assert not any(m in source for m in MOJIBAKE), path
        if path.endswith(".py"):
            ast.parse(source, filename=path)
        if path.endswith(".json"):
            json.loads(source)


class TestWebAppGenerator:
    @pytest.mark.parametrize(
        "frontend,backend",
        sorted(itertools.product(WebAppGenerator.SUPPORTED_FRONTENDS, WebAppGenerator.SUPPORTED_BACKENDS)),
    )
    def test_every_combination_is_well_formed(self, frontend, backend):
        files = WebAppGenerator(frontend, backend).generate(SCREENS, "Shop App", MODELS)
        assert_well_formed(files)
        assert "docker-compose.yml" in files
        assert ".env.example" in files
        assert "frontend/package.json" in files

    @pytest.mark.parametrize("frontend", sorted(WebAppGenerator.SUPPORTED_FRONTENDS))
    def test_screen_content_reaches_the_frontend(self, frontend):
        files = WebAppGenerator(frontend, "fastapi").generate(SCREENS, "Shop App", MODELS)
        frontend_src = "\n".join(v for k, v in files.items() if k.startswith("frontend/"))
        assert "Checkout" in frontend_src
        assert "Welcome back" in frontend_src
        assert "<button" in frontend_src

    @pytest.mark.parametrize("backend", ["fastapi", "flask", "django"])
    def test_model_fields_reach_the_backend(self, backend):
        files = WebAppGenerator("react", backend).generate(SCREENS, "Shop App", MODELS)
        backend_src = "\n".join(v for k, v in files.items() if k.startswith("backend/"))
        for field in ("title", "qty", "price", "paid", "placed_at"):
            assert field in backend_src

    def test_models_default_to_none(self):
        files = WebAppGenerator("react", "fastapi").generate(SCREENS, "Shop App")
        assert_well_formed(files)

    def test_react_writes_one_screen_file_per_screen(self):
        files = WebAppGenerator("react", "fastapi").generate(SCREENS, "Shop App", MODELS)
        assert "frontend/src/screens/HomeScreen.tsx" in files
        assert "frontend/src/screens/OrderDetailsScreen.tsx" in files

    @pytest.mark.parametrize("kwargs", [{"frontend": "ember"}, {"backend": "rails"}])
    def test_unsupported_framework_is_rejected(self, kwargs):
        with pytest.raises(ValueError, match="Unsupported"):
            WebAppGenerator(**kwargs)


class TestDesktopAppGenerator:
    @pytest.mark.parametrize("target", DesktopAppGenerator.SUPPORTED_TARGETS)
    def test_every_target_is_well_formed(self, target):
        files = DesktopAppGenerator(target).generate(SCREENS, "Shop App")
        assert_well_formed(files)
        source = "\n".join(files.values())
        assert "Checkout" in source
        assert "Welcome back" in source
        assert "Shop App" in source

    def test_electron_description_uses_a_real_em_dash(self):
        files = DesktopAppGenerator("electron").generate(SCREENS, "Shop App")
        assert json.loads(files["package.json"])["description"] == "Shop App — built with EoStudio"

    @pytest.mark.parametrize("target,path,kind", [("tkinter", "app.py", "tkinter"), ("qt", "main.py", "Qt")])
    def test_python_targets_have_a_clean_module_docstring(self, target, path, kind):
        files = DesktopAppGenerator(target).generate(SCREENS, "Shop App")
        docstring = ast.get_docstring(ast.parse(files[path]))
        assert docstring == f"Shop App — {kind} desktop application."

    def test_unknown_target_is_rejected(self):
        with pytest.raises(ValueError, match="Unknown target"):
            DesktopAppGenerator("winforms")


class TestMobileAppGenerator:
    @pytest.mark.parametrize("target", MobileAppGenerator.SUPPORTED_TARGETS)
    def test_every_target_is_well_formed(self, target):
        files = MobileAppGenerator(target).generate(SCREENS, "Shop App")
        assert_well_formed(files)
        source = "\n".join(files.values())
        assert "Checkout" in source
        assert "Welcome back" in source
        assert "OrderDetails" in source

    def test_swift_main_file_is_named_after_its_struct(self):
        files = MobileAppGenerator("swift").generate(SCREENS, "Shop App")
        assert "ShopAppApp.swift" in files
        assert "Shop AppApp.swift" not in files
        assert "struct ShopAppApp: App" in files["ShopAppApp.swift"]

    def test_kotlin_files_follow_the_package_name(self):
        files = MobileAppGenerator("kotlin").generate(SCREENS, "Shop App", package_name="org.shop.app")
        assert "app/src/main/java/org/shop/app/MainActivity.kt" in files
        assert "package org.shop.app" in files["app/src/main/java/org/shop/app/MainActivity.kt"]

    def test_no_screens_falls_back_to_a_home_screen(self):
        files = MobileAppGenerator("flutter").generate([], "Shop App")
        assert "lib/screens/home_screen.dart" in files

    def test_unsupported_target_is_rejected(self):
        with pytest.raises(ValueError, match="Unsupported target"):
            MobileAppGenerator("xamarin")
