import unittest

class TestEoStudioUnit(unittest.TestCase):
    def test_code_editor_syntax_highlighter(self):
        # Simulate code editor syntax highlighter
        code = "void main() { int x = 10; }"
        tokens = []
        for word in code.split():
            if word in ["void", "int"]:
                tokens.append((word, "KEYWORD"))
            else:
                tokens.append((word, "TEXT"))
        assert tokens[0][1] == "KEYWORD"
        assert tokens[2][1] == "KEYWORD"
