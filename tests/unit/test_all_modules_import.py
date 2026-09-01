# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Every shipped module must import.

`eostudio/gui/widgets/viewport_3d.py` was an empty file while
`eostudio/gui/editors/cad_editor.py` did `from ... import Viewport3D`. Nothing
caught it: 88 of EoStudio's modules are referenced by no test at all, so a
module can stop importing entirely and the suite stays green.

This is the cheapest guard against that whole class of defect — an undeclared
dependency, a renamed symbol, a file left empty. It asserts nothing about
behaviour, only that the package is not shipping a module that cannot be
loaded.
"""

import importlib
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2] / "eostudio"


def _module_names():
    names = []
    for path in sorted(_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(_ROOT.parent).with_suffix("")
        name = ".".join(rel.parts)
        if name.endswith(".__init__"):
            name = name[: -len(".__init__")]
        names.append(name)
    return names


MODULES = _module_names()


def test_the_package_was_actually_found():
    """A glob that silently matches nothing would make every case below pass."""
    assert len(MODULES) > 100, f"only found {len(MODULES)} modules under {_ROOT}"


@pytest.mark.parametrize("module", MODULES)
def test_module_imports(module):
    try:
        importlib.import_module(module)
    except ImportError as exc:
        # GUI widgets raise ImportError by design when tkinter or a display is
        # missing; that is the documented headless contract, not a defect.
        if "tkinter" in str(exc) or "display" in str(exc):
            pytest.skip(f"{module} needs a display: {exc}")
        raise


def test_no_shipped_module_is_empty():
    """An empty module that something imports from is the exact shape of the
    viewport_3d defect: the file exists, so the import path looks right, and
    the symbol is simply absent."""
    empty = [
        p.relative_to(_ROOT.parent)
        for p in _ROOT.rglob("*.py")
        if "__pycache__" not in p.parts
        and p.name != "__init__.py"
        and p.stat().st_size == 0
    ]
    assert not empty, (
        "empty modules ship as importable but define nothing: "
        + ", ".join(str(p) for p in empty)
    )
