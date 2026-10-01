"""Simulation editor console expression evaluator (replaces eval, bandit B307)."""

import math
import unittest

try:
    from eostudio.gui.editors.simulation_editor import _safe_eval
except ImportError:
    _safe_eval = None


@unittest.skipIf(_safe_eval is None, "simulation_editor stubbed (tkinter unavailable)")
class TestConsoleSafeEval(unittest.TestCase):
    def test_supported_expressions(self):
        cases = {
            "2*3+1": 7,
            "-2**2": -4,
            "7 // 2 + 7 % 2": 4,
            "sin(pi/2)": 1.0,
            "sqrt(16) + abs(-1)": 5.0,
            "round(3.14159, 2)": 3.14,
            "round(3.14159, ndigits=1)": 3.1,
            "max(1, 5, 3)": 5,
            "sum(range(5))": 10,
            "list(range(3))": [0, 1, 2],
            "len([1, 2, 3])": 3,
            "math.floor(2.7)": 2,
            "exp(0) + log(e)": 2.0,
        }
        for expr, expected in cases.items():
            self.assertEqual(_safe_eval(expr), expected, expr)
        self.assertAlmostEqual(_safe_eval("cos(pi)"), -1.0)
        self.assertEqual(_safe_eval("math.pi"), math.pi)

    def test_rejects_escapes(self):
        for expr in (
            "__import__('os')",
            "().__class__.__base__.__subclasses__()",
            "open('/etc/passwd')",
            "math.__loader__",
            "undefined_name",
            "[x for x in range(3)]",
            "lambda: 1",
            "max(**{'a': 1})",
        ):
            with self.assertRaises(ValueError, msg=expr):
                _safe_eval(expr)


if __name__ == "__main__":
    unittest.main()
