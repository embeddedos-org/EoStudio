import unittest

class TestEoStudioSimulation(unittest.TestCase):
    def test_debugger_breakpoint_hit_simulation(self):
        # Simulate GDB breakpoint hit
        debugger_state = "RUNNING"
        breakpoints = [0x08000120]
        current_pc = 0x08000110
        # Step CPU
        current_pc = 0x08000120
        if current_pc in breakpoints:
            debugger_state = "STOPPED"
        assert debugger_state == "STOPPED", "Debugger breakpoint hit simulation failed"
