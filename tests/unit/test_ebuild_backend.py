"""EoStudio must drive ebuild, not reimplement it.

§14 names what EoStudio must not become — "Second build system" — and §15 says
it "invokes eBuild APIs/CLI; it does not duplicate build logic".

Two concrete failures motivated these tests. `ebuild` was absent from
BuildSystem while Buck and Bazel were present, so an ebuild project fell
through every detection marker to the MAKE fallback and would have run `make`
in a directory with no Makefile. And the one place the repository named the
tool, it named an invocation that does not exist.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from eostudio.core.devtools.build_system import (
    BuildSystem,
    BuildSystemManager,
    _DEFAULT_CONFIGS,
)


class TestEbuildIsAKnownBuildSystem(unittest.TestCase):
    def test_ebuild_is_in_the_enum(self):
        self.assertEqual(BuildSystem.EBUILD.value, "ebuild")

    def test_ebuild_has_a_default_config(self):
        self.assertIn(BuildSystem.EBUILD, _DEFAULT_CONFIGS)

    def test_the_commands_are_ebuilds_real_verbs(self):
        # Checked against `ebuild --help`. The build and the board selection
        # are separate steps; there is no top-level --platform or --config.
        cfg = _DEFAULT_CONFIGS[BuildSystem.EBUILD]
        self.assertEqual(cfg.build_command, "ebuild build")
        self.assertEqual(cfg.test_command, "ebuild test")
        self.assertEqual(cfg.clean_command, "ebuild clean")
        self.assertEqual(cfg.run_command, "ebuild monitor")

    def test_no_command_uses_a_flag_ebuild_does_not_have(self):
        cfg = _DEFAULT_CONFIGS[BuildSystem.EBUILD]
        for command in (cfg.build_command, cfg.test_command,
                        cfg.clean_command, cfg.run_command):
            self.assertNotIn("--platform", command)
            self.assertNotIn("--config", command)


class TestEbuildProjectDetection(unittest.TestCase):
    def test_a_build_yaml_identifies_an_ebuild_project(self):
        with TemporaryDirectory() as d:
            (Path(d) / "build.yaml").write_text("project:\n  name: x\n",
                                                encoding="utf-8")
            self.assertEqual(BuildSystemManager(d).detect(), BuildSystem.EBUILD)

    def test_it_does_not_fall_through_to_make(self):
        # The regression this exists for: with no marker matching, detect()
        # returns MAKE, and EoStudio would run `make` in a directory that has
        # no Makefile.
        with TemporaryDirectory() as d:
            (Path(d) / "build.yaml").write_text("project:\n  name: x\n",
                                                encoding="utf-8")
            manager = BuildSystemManager(d)
            self.assertNotEqual(manager.detect(), BuildSystem.MAKE)
            self.assertEqual(manager.get_config().build_command, "ebuild build")

    def test_ebuild_wins_over_a_generated_cmakelists(self):
        # ebuild generates build files, so a project that has been configured
        # once carries both. Matching CMake first would hand the project to a
        # backend that bypasses the toolchain owning it.
        with TemporaryDirectory() as d:
            (Path(d) / "build.yaml").write_text("project:\n  name: x\n",
                                                encoding="utf-8")
            (Path(d) / "CMakeLists.txt").write_text("", encoding="utf-8")
            self.assertEqual(BuildSystemManager(d).detect(), BuildSystem.EBUILD)

    def test_a_plain_cmake_project_is_unaffected(self):
        with TemporaryDirectory() as d:
            (Path(d) / "CMakeLists.txt").write_text("", encoding="utf-8")
            self.assertEqual(BuildSystemManager(d).detect(), BuildSystem.CMAKE)

    def test_a_node_project_is_unaffected(self):
        with TemporaryDirectory() as d:
            (Path(d) / "package.json").write_text("{}", encoding="utf-8")
            self.assertEqual(BuildSystemManager(d).detect(), BuildSystem.NPM)


class TestManualBuildFallbackIsRunnable(unittest.TestCase):
    """The fallback tells a developer what to run, so it must be runnable."""

    def test_it_no_longer_emits_flags_ebuild_rejects(self):
        from eostudio.plugins.eosim_plugin import EoSimPlugin

        plugin = EoSimPlugin()
        plugin._bridge = None
        result = plugin._on_build({"platform": "stm32f4", "source_dir": "/tmp/p"})

        self.assertFalse(result["success"])
        self.assertNotIn("--platform", result["command"])
        self.assertNotIn("--config board.yaml", result["command"])

    def test_it_configures_the_board_before_building(self):
        from eostudio.plugins.eosim_plugin import EoSimPlugin

        plugin = EoSimPlugin()
        plugin._bridge = None
        result = plugin._on_build({"platform": "stm32f4", "source_dir": "/tmp/p"})

        self.assertEqual(result["commands"],
                         ["ebuild configure --board stm32f4", "ebuild build"])


if __name__ == "__main__":
    unittest.main()
