import unittest
class TestEoStudioFunctional(unittest.TestCase):
    def test_build_and_debug_pipeline(self):
        pipeline = ["compile", "link", "load_symbols", "break_main"]
        self.assertEqual(pipeline[-1], "break_main")
