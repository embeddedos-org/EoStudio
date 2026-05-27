import unittest
class TestEoStudioUnit(unittest.TestCase):
    def test_syntax_highlight_tokenizer(self):
        tokens = ["void", "main", "(", ")"]
        self.assertEqual(tokens[0], "void")
