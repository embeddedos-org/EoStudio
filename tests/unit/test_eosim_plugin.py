from eostudio.plugins.eosim_plugin import EoSimPlugin


def test_eosim_build_command():
    plugin = EoSimPlugin()
    result = plugin._on_build({"platform": "stm32f4"})
    assert result["success"] is False
    assert result["command"] == "ebuild configure --board stm32f4 && ebuild build"
