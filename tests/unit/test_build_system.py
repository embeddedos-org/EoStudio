from eostudio.core.devtools.build_system import (
    _DEFAULT_CONFIGS,
    BuildSystem,
    BuildSystemManager,
)


def test_ebuild_backend_command():
    config = _DEFAULT_CONFIGS.get(BuildSystem.EBUILD)
    assert config is not None
    assert config.build_command == "ebuild configure --board default && ebuild build"
    assert config.test_command == "ebuild test"

def test_detect_ebuild_project(tmp_path):
    (tmp_path / "board.yaml").touch()
    manager = BuildSystemManager(str(tmp_path))
    assert manager.detect() == BuildSystem.EBUILD
