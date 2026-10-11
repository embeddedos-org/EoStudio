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

import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from eostudio.core.devtools.build_system import (
    BuildConfig,
    BuildSystem,
    BuildSystemManager,
    _DEFAULT_CONFIGS,
)
from eostudio.core.devtools.ebuild_backend import EbuildBackend, EbuildBackendError


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


_STUB_RECORD_ENV = "EOSTUDIO_TEST_EBUILD_RECORD"


class TestEbuildBackendArgv(unittest.TestCase):
    """EbuildBackend translates BuildConfig into real ebuild argv.

    The argv is asserted exactly: executable, verb, then the flags ebuild
    really defines. A stub `ebuild` on PATH records what it was called with so
    the executed argv is asserted too, not just the constructed one.
    """

    def _config(self, **overrides):
        base = dict(
            system=BuildSystem.EBUILD,
            build_command="ebuild build",
            test_command="ebuild test",
            clean_command="ebuild clean",
            run_command="ebuild monitor",
        )
        base.update(overrides)
        return BuildConfig(**base)

    def _install_stub_ebuild(self, bindir: Path) -> Path:
        """Write a stub `ebuild` that records its argv as JSON lines."""
        record = bindir / "argv.jsonl"
        helper_src = (
            "import json, os, sys\n"
            f"open(os.environ[{_STUB_RECORD_ENV!r}], 'a')"
            ".write(json.dumps(sys.argv) + chr(10))\n"
            "print('stub ebuild ok')\n"
        )
        if os.name == "nt":
            helper = bindir / "_ebuild_stub.py"
            helper.write_text(helper_src, encoding="utf-8")
            (bindir / "ebuild.cmd").write_text(
                f'@echo off\npython "{helper}" %*\n', encoding="utf-8"
            )
        else:
            stub = bindir / "ebuild"
            stub.write_text("#!/usr/bin/env python3\n" + helper_src, encoding="utf-8")
            stub.chmod(0o755)
        return record

    def _with_stub_on_path(self, fn):
        with TemporaryDirectory() as tmp:
            tmpdir = Path(tmp).resolve()
            bindir = tmpdir / "bin"
            bindir.mkdir()
            record = self._install_stub_ebuild(bindir)
            old_path = os.environ.get("PATH", "")
            old_record = os.environ.get(_STUB_RECORD_ENV)
            os.environ["PATH"] = str(bindir) + os.pathsep + old_path
            os.environ[_STUB_RECORD_ENV] = str(record)
            try:
                fn(tmpdir, record)
            finally:
                os.environ["PATH"] = old_path
                if old_record is None:
                    os.environ.pop(_STUB_RECORD_ENV, None)
                else:
                    os.environ[_STUB_RECORD_ENV] = old_record

    def _recorded_argvs(self, record: Path):
        return [json.loads(line) for line in record.read_text(encoding="utf-8").splitlines()]

    def test_build_argv_is_exact(self):
        with TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            argv = EbuildBackend(ws).build_argv(self._config())
            self.assertEqual(
                argv,
                ["ebuild", "build",
                 "--config", str(ws / "build.yaml"),
                 "--build-dir", str(ws / "_build")],
            )

    def test_test_clean_and_run_argv_are_exact(self):
        with TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            backend = EbuildBackend(ws)
            config = self._config()
            self.assertEqual(
                backend.test_argv(config),
                ["ebuild", "test",
                 "--config", str(ws / "build.yaml"),
                 "--build-dir", str(ws / "_build")],
            )
            self.assertEqual(
                backend.clean_argv(config),
                ["ebuild", "clean", "--build-dir", str(ws / "_build")],
            )
            # clean takes no --config; monitor takes neither flag.
            self.assertEqual(backend.run_argv(config), ["ebuild", "monitor"])

    def test_build_runs_the_stub_with_the_exact_argv(self):
        def check(tmpdir, record):
            result = EbuildBackend(tmpdir).build(self._config())
            self.assertTrue(result.success, result.errors)
            recorded = self._recorded_argvs(record)
            self.assertEqual(len(recorded), 1)
            self.assertIn(os.path.basename(recorded[0][0]),
                          ("ebuild", "ebuild.exe", "_ebuild_stub.py"))
            self.assertEqual(
                recorded[0][1:],
                ["build",
                 "--config", str(tmpdir / "build.yaml"),
                 "--build-dir", str(tmpdir / "_build")],
            )

        self._with_stub_on_path(check)

    def test_board_and_jobs_become_real_flags(self):
        with TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            argv = EbuildBackend(ws).build_argv(self._config(), board="stm32f4", jobs=4)
            self.assertEqual(
                argv,
                ["ebuild", "build",
                 "--board", "stm32f4", "-j", "4",
                 "--config", str(ws / "build.yaml"),
                 "--build-dir", str(ws / "_build")],
            )

    def test_configure_argv_is_the_real_board_selection_step(self):
        with TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            self.assertEqual(
                EbuildBackend(ws).configure_argv("stm32f4"),
                ["ebuild", "configure", "--board", "stm32f4",
                 "--build-dir", str(ws / "_build")],
            )
            with self.assertRaises(EbuildBackendError):
                EbuildBackend(ws).configure_argv("")


class TestEbuildBackendFailsClosed(unittest.TestCase):
    """Invalid configs raise; nothing is executed, substituted, or shelled out."""

    def _config(self, **overrides):
        base = dict(
            system=BuildSystem.EBUILD,
            build_command="ebuild build",
            test_command="ebuild test",
            clean_command="ebuild clean",
            run_command="ebuild monitor",
        )
        base.update(overrides)
        return BuildConfig(**base)

    def test_the_old_invalid_invocation_is_rejected(self):
        # The string this whole change exists to kill: ebuild never had a
        # top-level --platform flag.
        bad = self._config(build_command="ebuild --platform stm32f4")
        with TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            with self.assertRaises(EbuildBackendError):
                EbuildBackend(ws).build_argv(bad)

    def test_rejected_build_is_never_executed(self):
        bad = self._config(build_command="ebuild --platform stm32f4")

        def check(tmpdir, record):
            with self.assertRaises(EbuildBackendError):
                EbuildBackend(tmpdir).build(bad)
            self.assertFalse(record.exists())

        # Reuse the stub installer from the argv tests.
        TestEbuildBackendArgv()._with_stub_on_path(check)

    def test_unknown_flags_are_rejected(self):
        bad = self._config(build_command="ebuild build --frobnicate")
        with TemporaryDirectory() as tmp:
            with self.assertRaises(EbuildBackendError) as ctx:
                EbuildBackend(tmp).build_argv(bad)
            self.assertIn("--frobnicate", str(ctx.exception))

    def test_a_non_ebuild_config_is_rejected(self):
        other = BuildConfig(
            system=BuildSystem.MAKE,
            build_command="make",
            test_command="make test",
            clean_command="make clean",
            run_command="make run",
        )
        with TemporaryDirectory() as tmp:
            with self.assertRaises(EbuildBackendError):
                EbuildBackend(tmp).build(other)

    def test_a_build_target_is_rejected(self):
        # `ebuild build` takes no positional target; appending one would be an
        # invalid invocation, so fail closed instead of running it.
        with TemporaryDirectory() as tmp:
            with self.assertRaises(EbuildBackendError):
                EbuildBackend(tmp).build(self._config(), target="release")

    def test_execute_rejects_non_lifecycle_commands(self):
        with TemporaryDirectory() as tmp:
            backend = EbuildBackend(tmp)
            config = self._config()
            with self.assertRaises(EbuildBackendError):
                backend.execute("ebuild frobnicate", config)
            with self.assertRaises(EbuildBackendError):
                backend.execute("make", config)

    def test_manager_routes_ebuild_builds_through_the_backend(self):
        def check(tmpdir, record):
            (tmpdir / "build.yaml").write_text("project:\n  name: x\n", encoding="utf-8")
            result = BuildSystemManager(str(tmpdir)).build()
            self.assertTrue(result.success, result.errors)
            recorded = [json.loads(line)
                        for line in record.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(recorded), 1)
            self.assertEqual(
                recorded[0][1:],
                ["build",
                 "--config", str(tmpdir / "build.yaml"),
                 "--build-dir", str(tmpdir / "_build")],
            )

        TestEbuildBackendArgv()._with_stub_on_path(check)

    def test_manager_with_invalid_ebuild_config_fails_closed(self):
        bad = self._config(build_command="ebuild --platform stm32f4")

        def check(tmpdir, record):
            (tmpdir / "build.yaml").write_text("project:\n  name: x\n", encoding="utf-8")
            with mock.patch.dict(_DEFAULT_CONFIGS, {BuildSystem.EBUILD: bad}):
                with self.assertRaises(EbuildBackendError):
                    BuildSystemManager(str(tmpdir)).build()
            # No silent fallback: the stub was never executed.
            self.assertFalse(record.exists())

        TestEbuildBackendArgv()._with_stub_on_path(check)

    def test_manager_execute_dispatches_lifecycle_strings(self):
        def check(tmpdir, record):
            (tmpdir / "build.yaml").write_text("project:\n  name: x\n", encoding="utf-8")
            backend = EbuildBackend(tmpdir)
            result = backend.execute("ebuild clean", self._config())
            self.assertTrue(result.success, result.errors)
            recorded = [json.loads(line)
                        for line in record.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(recorded[0][1:],
                             ["clean", "--build-dir", str(tmpdir / "_build")])

        TestEbuildBackendArgv()._with_stub_on_path(check)


if __name__ == "__main__":
    unittest.main()
