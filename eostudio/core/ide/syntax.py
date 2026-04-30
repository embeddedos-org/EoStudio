"""
EoStudio Syntax Highlighter
============================

Production-ready, token-based syntax highlighter supporting 30+ languages
and 12 built-in color themes. Uses only Python stdlib (re module).

Usage:
    highlighter = SyntaxHighlighter("python")
    tokens = highlighter.tokenize(source_code)
    ansi_output = highlighter.highlight(source_code)
    html_output = highlighter.highlight_html(source_code)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import ClassVar, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Token types
# ---------------------------------------------------------------------------

class TokenType(Enum):
    """Every lexical category the highlighter can emit."""
    KEYWORD = auto()
    STRING = auto()
    COMMENT = auto()
    NUMBER = auto()
    OPERATOR = auto()
    FUNCTION = auto()
    CLASS = auto()
    DECORATOR = auto()
    BUILTIN = auto()
    TYPE = auto()
    VARIABLE = auto()
    PUNCTUATION = auto()
    WHITESPACE = auto()
    NEWLINE = auto()
    IDENTIFIER = auto()
    PREPROCESSOR = auto()
    TAG = auto()
    ATTRIBUTE = auto()
    UNKNOWN = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Token:
    """A single highlighted token."""
    type: TokenType
    value: str
    start: int
    end: int


@dataclass
class LanguageDefinition:
    """Holds the name, file extensions, and ordered regex patterns for a language."""
    name: str
    extensions: List[str]
    patterns: List[Tuple[TokenType, str]]


@dataclass
class Theme:
    """Maps each TokenType to a hex colour string (e.g. ``#FF5555``)."""
    name: str
    colors: Dict[TokenType, str]
    background: str = "#282828"
    foreground: str = "#ebdbb2"


# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

def _hex_to_ansi(hex_color: str) -> str:
    """Convert ``#RRGGBB`` to a 24-bit ANSI escape sequence."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"\033[38;2;{r};{g};{b}m"


_ANSI_RESET = "\033[0m"


# ===================================================================
# Built-in themes (12)
# ===================================================================

def _make_theme(name: str, bg: str, fg: str, mapping: Dict[TokenType, str]) -> Theme:
    """Fill missing token types with the theme foreground colour."""
    full: Dict[TokenType, str] = {}
    for tt in TokenType:
        full[tt] = mapping.get(tt, fg)
    return Theme(name=name, colors=full, background=bg, foreground=fg)


BUILTIN_THEMES: Dict[str, Theme] = {}

# -- Monokai --
BUILTIN_THEMES["monokai"] = _make_theme("monokai", "#272822", "#F8F8F2", {
    TokenType.KEYWORD:      "#F92672",
    TokenType.STRING:       "#E6DB74",
    TokenType.COMMENT:      "#75715E",
    TokenType.NUMBER:       "#AE81FF",
    TokenType.OPERATOR:     "#F92672",
    TokenType.FUNCTION:     "#A6E22E",
    TokenType.CLASS:        "#A6E22E",
    TokenType.DECORATOR:    "#A6E22E",
    TokenType.BUILTIN:      "#66D9EF",
    TokenType.TYPE:         "#66D9EF",
    TokenType.VARIABLE:     "#F8F8F2",
    TokenType.PUNCTUATION:  "#F8F8F2",
    TokenType.PREPROCESSOR: "#F92672",
    TokenType.TAG:          "#F92672",
    TokenType.ATTRIBUTE:    "#A6E22E",
    TokenType.IDENTIFIER:   "#F8F8F2",
})

# -- One Dark --
BUILTIN_THEMES["one_dark"] = _make_theme("one_dark", "#282C34", "#ABB2BF", {
    TokenType.KEYWORD:      "#C678DD",
    TokenType.STRING:       "#98C379",
    TokenType.COMMENT:      "#5C6370",
    TokenType.NUMBER:       "#D19A66",
    TokenType.OPERATOR:     "#56B6C2",
    TokenType.FUNCTION:     "#61AFEF",
    TokenType.CLASS:        "#E5C07B",
    TokenType.DECORATOR:    "#C678DD",
    TokenType.BUILTIN:      "#E5C07B",
    TokenType.TYPE:         "#E5C07B",
    TokenType.VARIABLE:     "#E06C75",
    TokenType.PUNCTUATION:  "#ABB2BF",
    TokenType.PREPROCESSOR: "#C678DD",
    TokenType.TAG:          "#E06C75",
    TokenType.ATTRIBUTE:    "#D19A66",
    TokenType.IDENTIFIER:   "#ABB2BF",
})

# -- Solarized Dark --
BUILTIN_THEMES["solarized_dark"] = _make_theme("solarized_dark", "#002B36", "#839496", {
    TokenType.KEYWORD:      "#859900",
    TokenType.STRING:       "#2AA198",
    TokenType.COMMENT:      "#586E75",
    TokenType.NUMBER:       "#D33682",
    TokenType.OPERATOR:     "#859900",
    TokenType.FUNCTION:     "#268BD2",
    TokenType.CLASS:        "#B58900",
    TokenType.DECORATOR:    "#CB4B16",
    TokenType.BUILTIN:      "#B58900",
    TokenType.TYPE:         "#B58900",
    TokenType.VARIABLE:     "#268BD2",
    TokenType.PUNCTUATION:  "#839496",
    TokenType.PREPROCESSOR: "#CB4B16",
    TokenType.TAG:          "#268BD2",
    TokenType.ATTRIBUTE:    "#B58900",
    TokenType.IDENTIFIER:   "#839496",
})

# -- Solarized Light --
BUILTIN_THEMES["solarized_light"] = _make_theme("solarized_light", "#FDF6E3", "#657B83", {
    TokenType.KEYWORD:      "#859900",
    TokenType.STRING:       "#2AA198",
    TokenType.COMMENT:      "#93A1A1",
    TokenType.NUMBER:       "#D33682",
    TokenType.OPERATOR:     "#859900",
    TokenType.FUNCTION:     "#268BD2",
    TokenType.CLASS:        "#B58900",
    TokenType.DECORATOR:    "#CB4B16",
    TokenType.BUILTIN:      "#B58900",
    TokenType.TYPE:         "#B58900",
    TokenType.VARIABLE:     "#268BD2",
    TokenType.PUNCTUATION:  "#657B83",
    TokenType.PREPROCESSOR: "#CB4B16",
    TokenType.TAG:          "#268BD2",
    TokenType.ATTRIBUTE:    "#B58900",
    TokenType.IDENTIFIER:   "#657B83",
})

# -- Dracula --
BUILTIN_THEMES["dracula"] = _make_theme("dracula", "#282A36", "#F8F8F2", {
    TokenType.KEYWORD:      "#FF79C6",
    TokenType.STRING:       "#F1FA8C",
    TokenType.COMMENT:      "#6272A4",
    TokenType.NUMBER:       "#BD93F9",
    TokenType.OPERATOR:     "#FF79C6",
    TokenType.FUNCTION:     "#50FA7B",
    TokenType.CLASS:        "#8BE9FD",
    TokenType.DECORATOR:    "#50FA7B",
    TokenType.BUILTIN:      "#8BE9FD",
    TokenType.TYPE:         "#8BE9FD",
    TokenType.VARIABLE:     "#F8F8F2",
    TokenType.PUNCTUATION:  "#F8F8F2",
    TokenType.PREPROCESSOR: "#FF79C6",
    TokenType.TAG:          "#FF79C6",
    TokenType.ATTRIBUTE:    "#50FA7B",
    TokenType.IDENTIFIER:   "#F8F8F2",
})

# -- GitHub Light --
BUILTIN_THEMES["github_light"] = _make_theme("github_light", "#FFFFFF", "#24292E", {
    TokenType.KEYWORD:      "#D73A49",
    TokenType.STRING:       "#032F62",
    TokenType.COMMENT:      "#6A737D",
    TokenType.NUMBER:       "#005CC5",
    TokenType.OPERATOR:     "#D73A49",
    TokenType.FUNCTION:     "#6F42C1",
    TokenType.CLASS:        "#6F42C1",
    TokenType.DECORATOR:    "#6F42C1",
    TokenType.BUILTIN:      "#005CC5",
    TokenType.TYPE:         "#005CC5",
    TokenType.VARIABLE:     "#E36209",
    TokenType.PUNCTUATION:  "#24292E",
    TokenType.PREPROCESSOR: "#D73A49",
    TokenType.TAG:          "#22863A",
    TokenType.ATTRIBUTE:    "#6F42C1",
    TokenType.IDENTIFIER:   "#24292E",
})

# -- GitHub Dark --
BUILTIN_THEMES["github_dark"] = _make_theme("github_dark", "#0D1117", "#C9D1D9", {
    TokenType.KEYWORD:      "#FF7B72",
    TokenType.STRING:       "#A5D6FF",
    TokenType.COMMENT:      "#8B949E",
    TokenType.NUMBER:       "#79C0FF",
    TokenType.OPERATOR:     "#FF7B72",
    TokenType.FUNCTION:     "#D2A8FF",
    TokenType.CLASS:        "#FFA657",
    TokenType.DECORATOR:    "#D2A8FF",
    TokenType.BUILTIN:      "#79C0FF",
    TokenType.TYPE:         "#FFA657",
    TokenType.VARIABLE:     "#FFA657",
    TokenType.PUNCTUATION:  "#C9D1D9",
    TokenType.PREPROCESSOR: "#FF7B72",
    TokenType.TAG:          "#7EE787",
    TokenType.ATTRIBUTE:    "#D2A8FF",
    TokenType.IDENTIFIER:   "#C9D1D9",
})

# -- Nord --
BUILTIN_THEMES["nord"] = _make_theme("nord", "#2E3440", "#D8DEE9", {
    TokenType.KEYWORD:      "#81A1C1",
    TokenType.STRING:       "#A3BE8C",
    TokenType.COMMENT:      "#616E88",
    TokenType.NUMBER:       "#B48EAD",
    TokenType.OPERATOR:     "#81A1C1",
    TokenType.FUNCTION:     "#88C0D0",
    TokenType.CLASS:        "#8FBCBB",
    TokenType.DECORATOR:    "#D08770",
    TokenType.BUILTIN:      "#8FBCBB",
    TokenType.TYPE:         "#8FBCBB",
    TokenType.VARIABLE:     "#D8DEE9",
    TokenType.PUNCTUATION:  "#ECEFF4",
    TokenType.PREPROCESSOR: "#81A1C1",
    TokenType.TAG:          "#81A1C1",
    TokenType.ATTRIBUTE:    "#8FBCBB",
    TokenType.IDENTIFIER:   "#D8DEE9",
})

# -- Catppuccin (Mocha) --
BUILTIN_THEMES["catppuccin"] = _make_theme("catppuccin", "#1E1E2E", "#CDD6F4", {
    TokenType.KEYWORD:      "#CBA6F7",
    TokenType.STRING:       "#A6E3A1",
    TokenType.COMMENT:      "#585B70",
    TokenType.NUMBER:       "#FAB387",
    TokenType.OPERATOR:     "#89DCEB",
    TokenType.FUNCTION:     "#89B4FA",
    TokenType.CLASS:        "#F9E2AF",
    TokenType.DECORATOR:    "#CBA6F7",
    TokenType.BUILTIN:      "#F9E2AF",
    TokenType.TYPE:         "#F9E2AF",
    TokenType.VARIABLE:     "#CDD6F4",
    TokenType.PUNCTUATION:  "#BAC2DE",
    TokenType.PREPROCESSOR: "#CBA6F7",
    TokenType.TAG:          "#CBA6F7",
    TokenType.ATTRIBUTE:    "#89B4FA",
    TokenType.IDENTIFIER:   "#CDD6F4",
})

# -- Gruvbox --
BUILTIN_THEMES["gruvbox"] = _make_theme("gruvbox", "#282828", "#EBDBB2", {
    TokenType.KEYWORD:      "#FB4934",
    TokenType.STRING:       "#B8BB26",
    TokenType.COMMENT:      "#928374",
    TokenType.NUMBER:       "#D3869B",
    TokenType.OPERATOR:     "#FE8019",
    TokenType.FUNCTION:     "#FABD2F",
    TokenType.CLASS:        "#FABD2F",
    TokenType.DECORATOR:    "#8EC07C",
    TokenType.BUILTIN:      "#83A598",
    TokenType.TYPE:         "#83A598",
    TokenType.VARIABLE:     "#EBDBB2",
    TokenType.PUNCTUATION:  "#EBDBB2",
    TokenType.PREPROCESSOR: "#FB4934",
    TokenType.TAG:          "#FB4934",
    TokenType.ATTRIBUTE:    "#FABD2F",
    TokenType.IDENTIFIER:   "#EBDBB2",
})

# -- Tokyo Night --
BUILTIN_THEMES["tokyo_night"] = _make_theme("tokyo_night", "#1A1B26", "#A9B1D6", {
    TokenType.KEYWORD:      "#BB9AF7",
    TokenType.STRING:       "#9ECE6A",
    TokenType.COMMENT:      "#565F89",
    TokenType.NUMBER:       "#FF9E64",
    TokenType.OPERATOR:     "#89DDFF",
    TokenType.FUNCTION:     "#7AA2F7",
    TokenType.CLASS:        "#2AC3DE",
    TokenType.DECORATOR:    "#BB9AF7",
    TokenType.BUILTIN:      "#2AC3DE",
    TokenType.TYPE:         "#2AC3DE",
    TokenType.VARIABLE:     "#C0CAF5",
    TokenType.PUNCTUATION:  "#A9B1D6",
    TokenType.PREPROCESSOR: "#BB9AF7",
    TokenType.TAG:          "#F7768E",
    TokenType.ATTRIBUTE:    "#7AA2F7",
    TokenType.IDENTIFIER:   "#A9B1D6",
})

# -- Material Dark --
BUILTIN_THEMES["material_dark"] = _make_theme("material_dark", "#263238", "#EEFFFF", {
    TokenType.KEYWORD:      "#C792EA",
    TokenType.STRING:       "#C3E88D",
    TokenType.COMMENT:      "#546E7A",
    TokenType.NUMBER:       "#F78C6C",
    TokenType.OPERATOR:     "#89DDFF",
    TokenType.FUNCTION:     "#82AAFF",
    TokenType.CLASS:        "#FFCB6B",
    TokenType.DECORATOR:    "#C792EA",
    TokenType.BUILTIN:      "#FFCB6B",
    TokenType.TYPE:         "#FFCB6B",
    TokenType.VARIABLE:     "#EEFFFF",
    TokenType.PUNCTUATION:  "#89DDFF",
    TokenType.PREPROCESSOR: "#C792EA",
    TokenType.TAG:          "#F07178",
    TokenType.ATTRIBUTE:    "#FFCB6B",
    TokenType.IDENTIFIER:   "#EEFFFF",
})


# ===================================================================
# Language definitions (30+)
# ===================================================================
#
# Pattern order matters -- earlier patterns take priority.  Each language
# list is assembled with: comments first, then strings, decorators,
# numbers, keywords, builtins, types, operators, function/class names,
# punctuation, identifiers, whitespace/newlines.
# ===================================================================

def _kw(words: List[str]) -> str:
    """Build a regex alternation that matches whole words."""
    return r"\b(?:" + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) + r")\b"


# ---------------------------------------------------------------
# Python
# ---------------------------------------------------------------
_PYTHON_KEYWORDS = [
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
    "while", "with", "yield", "match", "case", "type",
]
_PYTHON_BUILTINS = [
    "abs", "all", "any", "ascii", "bin", "bool", "breakpoint", "bytearray",
    "bytes", "callable", "chr", "classmethod", "compile", "complex",
    "delattr", "dict", "dir", "divmod", "enumerate", "eval", "exec",
    "filter", "float", "format", "frozenset", "getattr", "globals",
    "hasattr", "hash", "help", "hex", "id", "input", "int", "isinstance",
    "issubclass", "iter", "len", "list", "locals", "map", "max",
    "memoryview", "min", "next", "object", "oct", "open", "ord", "pow",
    "print", "property", "range", "repr", "reversed", "round", "set",
    "setattr", "slice", "sorted", "staticmethod", "str", "sum", "super",
    "tuple", "type", "vars", "zip", "__import__",
]

_LANG_PYTHON = LanguageDefinition(
    name="python",
    extensions=[".py", ".pyw", ".pyi"],
    patterns=[
        # Comments
        (TokenType.COMMENT,     r"#[^\n]*"),
        # Triple-quoted strings (must come before single-quoted)
        (TokenType.STRING,      r'"""[\s\S]*?"""'),
        (TokenType.STRING,      r"'''[\s\S]*?'''"),
        # f-strings / b-strings / r-strings (simple handling)
        (TokenType.STRING,      r'[fFbBrRuU]{1,2}"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,      r"[fFbBrRuU]{1,2}'(?:[^'\\]|\\.)*'"),
        # Normal strings
        (TokenType.STRING,      r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,      r"'(?:[^'\\]|\\.)*'"),
        # Decorator
        (TokenType.DECORATOR,   r"@\w+(?:\.\w+)*"),
        # Numbers
        (TokenType.NUMBER,      r"0[xX][0-9a-fA-F_]+"),
        (TokenType.NUMBER,      r"0[oO][0-7_]+"),
        (TokenType.NUMBER,      r"0[bB][01_]+"),
        (TokenType.NUMBER,      r"\d[\d_]*\.[\d_]*(?:[eE][+-]?\d[\d_]*)?[jJ]?"),
        (TokenType.NUMBER,      r"\d[\d_]*[eE][+-]?\d[\d_]*[jJ]?"),
        (TokenType.NUMBER,      r"\d[\d_]*[jJ]?"),
        # Keywords
        (TokenType.KEYWORD,     _kw(_PYTHON_KEYWORDS)),
        # Builtins
        (TokenType.BUILTIN,     _kw(_PYTHON_BUILTINS)),
        # Function definition
        (TokenType.FUNCTION,    r"(?<=\bdef\s)\w+"),
        # Class definition
        (TokenType.CLASS,       r"(?<=\bclass\s)\w+"),
        # Operators
        (TokenType.OPERATOR,    r"->|:=|\*\*=?|//=?|<<=?|>>=?|[+\-*/%&|^~<>=!]=?|@=?"),
        # Punctuation
        (TokenType.PUNCTUATION, r"[(){}\[\]:;.,]"),
        # Identifiers
        (TokenType.IDENTIFIER,  r"[A-Za-z_]\w*"),
        # Whitespace / newlines
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# JavaScript
# ---------------------------------------------------------------
_JS_KEYWORDS = [
    "async", "await", "break", "case", "catch", "class", "const",
    "continue", "debugger", "default", "delete", "do", "else", "export",
    "extends", "finally", "for", "function", "if", "import", "in",
    "instanceof", "let", "new", "of", "return", "static", "super",
    "switch", "this", "throw", "try", "typeof", "var", "void", "while",
    "with", "yield", "from", "as",
]
_JS_BUILTINS = [
    "Array", "Boolean", "Date", "Error", "Function", "JSON", "Map",
    "Math", "Number", "Object", "Promise", "Proxy", "RegExp", "Set",
    "String", "Symbol", "WeakMap", "WeakSet", "console", "document",
    "globalThis", "undefined", "null", "true", "false", "NaN", "Infinity",
    "parseInt", "parseFloat", "isNaN", "isFinite", "setTimeout",
    "setInterval", "clearTimeout", "clearInterval", "fetch", "window",
]

_LANG_JAVASCRIPT = LanguageDefinition(
    name="javascript",
    extensions=[".js", ".jsx", ".mjs", ".cjs"],
    patterns=[
        (TokenType.COMMENT,     r"//[^\n]*"),
        (TokenType.COMMENT,     r"/\*[\s\S]*?\*/"),
        (TokenType.STRING,      r"`(?:[^`\\]|\\.|\$\{[^}]*\})*`"),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,      r"'(?:[^'\\]|\\.)*'"),
        (TokenType.NUMBER,      r"0[xX][0-9a-fA-F_]+n?"),
        (TokenType.NUMBER,      r"0[oO][0-7_]+n?"),
        (TokenType.NUMBER,      r"0[bB][01_]+n?"),
        (TokenType.NUMBER,      r"\d[\d_]*\.[\d_]*(?:[eE][+-]?\d[\d_]*)?n?"),
        (TokenType.NUMBER,      r"\d[\d_]*[eE][+-]?\d[\d_]*n?"),
        (TokenType.NUMBER,      r"\d[\d_]*n?"),
        (TokenType.KEYWORD,     _kw(_JS_KEYWORDS)),
        (TokenType.BUILTIN,     _kw(_JS_BUILTINS)),
        (TokenType.FUNCTION,    r"(?<=\bfunction\s)\w+"),
        (TokenType.FUNCTION,    r"\w+(?=\s*\()"),
        (TokenType.OPERATOR,    r">>>?=?|===?|!==?|\?\?=?|\?\.|&&=?|\|\|=?|=>|\*\*=?|<<=?|>>=?|[+\-*/%&|^~<>=!]=?|\.\.\."),
        (TokenType.PUNCTUATION, r"[(){}\[\]:;.,?]"),
        (TokenType.IDENTIFIER,  r"[A-Za-z_$]\w*"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# TypeScript
# ---------------------------------------------------------------
_TS_KEYWORDS = _JS_KEYWORDS + [
    "abstract", "as", "declare", "enum", "implements", "interface",
    "keyof", "module", "namespace", "never", "override", "private",
    "protected", "public", "readonly", "type", "unknown", "any",
    "is", "infer", "satisfies", "using",
]
_TS_TYPES = [
    "string", "number", "boolean", "void", "any", "never", "unknown",
    "object", "undefined", "null", "bigint", "symbol",
]

_LANG_TYPESCRIPT = LanguageDefinition(
    name="typescript",
    extensions=[".ts", ".tsx"],
    patterns=[
        (TokenType.COMMENT,     r"//[^\n]*"),
        (TokenType.COMMENT,     r"/\*[\s\S]*?\*/"),
        (TokenType.STRING,      r"`(?:[^`\\]|\\.|\$\{[^}]*\})*`"),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,      r"'(?:[^'\\]|\\.)*'"),
        (TokenType.NUMBER,      r"0[xX][0-9a-fA-F_]+n?"),
        (TokenType.NUMBER,      r"0[oO][0-7_]+n?"),
        (TokenType.NUMBER,      r"0[bB][01_]+n?"),
        (TokenType.NUMBER,      r"\d[\d_]*\.[\d_]*(?:[eE][+-]?\d[\d_]*)?n?"),
        (TokenType.NUMBER,      r"\d[\d_]*[eE][+-]?\d[\d_]*n?"),
        (TokenType.NUMBER,      r"\d[\d_]*n?"),
        (TokenType.KEYWORD,     _kw(_TS_KEYWORDS)),
        (TokenType.BUILTIN,     _kw(_JS_BUILTINS)),
        (TokenType.TYPE,        _kw(_TS_TYPES)),
        (TokenType.DECORATOR,   r"@\w+(?:\.\w+)*"),
        (TokenType.FUNCTION,    r"(?<=\bfunction\s)\w+"),
        (TokenType.FUNCTION,    r"\w+(?=\s*\()"),
        (TokenType.OPERATOR,    r">>>?=?|===?|!==?|\?\?=?|\?\.|&&=?|\|\|=?|=>|\*\*=?|<<=?|>>=?|[+\-*/%&|^~<>=!]=?|\.\.\."),
        (TokenType.PUNCTUATION, r"[(){}\[\]:;.,?<>]"),
        (TokenType.IDENTIFIER,  r"[A-Za-z_$]\w*"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# C
# ---------------------------------------------------------------
_C_KEYWORDS = [
    "auto", "break", "case", "char", "const", "continue", "default",
    "do", "double", "else", "enum", "extern", "float", "for", "goto",
    "if", "inline", "int", "long", "register", "restrict", "return",
    "short", "signed", "sizeof", "static", "struct", "switch", "typedef",
    "union", "unsigned", "void", "volatile", "while", "_Alignas",
    "_Alignof", "_Atomic", "_Bool", "_Complex", "_Generic", "_Imaginary",
    "_Noreturn", "_Static_assert", "_Thread_local",
]
_C_TYPES = [
    "int", "char", "float", "double", "long", "short", "unsigned",
    "signed", "void", "size_t", "ssize_t", "int8_t", "int16_t",
    "int32_t", "int64_t", "uint8_t", "uint16_t", "uint32_t", "uint64_t",
    "bool", "FILE", "ptrdiff_t", "intptr_t", "uintptr_t",
]

_LANG_C = LanguageDefinition(
    name="c",
    extensions=[".c", ".h"],
    patterns=[
        (TokenType.COMMENT,      r"//[^\n]*"),
        (TokenType.COMMENT,      r"/\*[\s\S]*?\*/"),
        (TokenType.PREPROCESSOR, r"#\s*(?:include|define|undef|if|ifdef|ifndef|elif|else|endif|pragma|error|warning|line)\b[^\n]*"),
        (TokenType.STRING,       r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,       r"'(?:[^'\\]|\\.)*'"),
        (TokenType.NUMBER,       r"0[xX][0-9a-fA-F]+[uUlL]*"),
        (TokenType.NUMBER,       r"0[bB][01]+[uUlL]*"),
        (TokenType.NUMBER,       r"\d+\.?\d*(?:[eE][+-]?\d+)?[fFlLuU]*"),
        (TokenType.KEYWORD,      _kw(_C_KEYWORDS)),
        (TokenType.TYPE,         _kw(_C_TYPES)),
        (TokenType.FUNCTION,     r"\w+(?=\s*\()"),
        (TokenType.OPERATOR,     r"->|<<|>>|\+\+|--|&&|\|\||[+\-*/%&|^~<>=!]=?"),
        (TokenType.PUNCTUATION,  r"[(){}\[\]:;.,?]"),
        (TokenType.IDENTIFIER,   r"[A-Za-z_]\w*"),
        (TokenType.NEWLINE,      r"\n"),
        (TokenType.WHITESPACE,   r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# C++
# ---------------------------------------------------------------
_CPP_KEYWORDS = _C_KEYWORDS + [
    "alignas", "alignof", "and", "and_eq", "asm", "bitand", "bitor",
    "bool", "catch", "char8_t", "char16_t", "char32_t", "class",
    "co_await", "co_return", "co_yield", "compl", "concept", "consteval",
    "constexpr", "constinit", "const_cast", "decltype", "delete",
    "dynamic_cast", "explicit", "export", "false", "friend", "module",
    "mutable", "namespace", "new", "noexcept", "not", "not_eq",
    "nullptr", "operator", "or", "or_eq", "private", "protected",
    "public", "reinterpret_cast", "requires", "static_assert",
    "static_cast", "template", "this", "throw", "true", "try",
    "typeid", "typename", "using", "virtual", "wchar_t", "xor", "xor_eq",
    "override", "final", "import",
]
_CPP_TYPES = _C_TYPES + [
    "string", "wstring", "vector", "map", "set", "unordered_map",
    "unordered_set", "array", "deque", "list", "pair", "tuple",
    "shared_ptr", "unique_ptr", "weak_ptr", "optional", "variant",
    "any", "string_view", "span",
]

_LANG_CPP = LanguageDefinition(
    name="cpp",
    extensions=[".cpp", ".cxx", ".cc", ".hpp", ".hxx", ".hh", ".h++"],
    patterns=[
        (TokenType.COMMENT,      r"//[^\n]*"),
        (TokenType.COMMENT,      r"/\*[\s\S]*?\*/"),
        (TokenType.PREPROCESSOR, r"#\s*(?:include|define|undef|if|ifdef|ifndef|elif|else|endif|pragma|error|warning|line)\b[^\n]*"),
        (TokenType.STRING,       r'R"([^(]*)\([\s\S]*?\)\1"'),
        (TokenType.STRING,       r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,       r"'(?:[^'\\]|\\.)*'"),
        (TokenType.NUMBER,       r"0[xX][0-9a-fA-F']+[uUlL]*"),
        (TokenType.NUMBER,       r"0[bB][01']+[uUlL]*"),
        (TokenType.NUMBER,       r"\d[\d']*\.[\d']*(?:[eE][+-]?\d[\d']*)?[fFlLuU]*"),
        (TokenType.NUMBER,       r"\d[\d']*[fFlLuU]*"),
        (TokenType.KEYWORD,      _kw(_CPP_KEYWORDS)),
        (TokenType.TYPE,         _kw(_CPP_TYPES)),
        (TokenType.FUNCTION,     r"\w+(?=\s*\()"),
        (TokenType.OPERATOR,     r"->|::|<<|>>|\+\+|--|&&|\|\||<=>|[+\-*/%&|^~<>=!]=?"),
        (TokenType.PUNCTUATION,  r"[(){}\[\]:;.,?<>]"),
        (TokenType.IDENTIFIER,   r"[A-Za-z_]\w*"),
        (TokenType.NEWLINE,      r"\n"),
        (TokenType.WHITESPACE,   r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# Java
# ---------------------------------------------------------------
_JAVA_KEYWORDS = [
    "abstract", "assert", "boolean", "break", "byte", "case", "catch",
    "char", "class", "const", "continue", "default", "do", "double",
    "else", "enum", "extends", "final", "finally", "float", "for",
    "goto", "if", "implements", "import", "instanceof", "int",
    "interface", "long", "native", "new", "package", "private",
    "protected", "public", "record", "return", "sealed", "short",
    "static", "strictfp", "super", "switch", "synchronized", "this",
    "throw", "throws", "transient", "try", "var", "void", "volatile",
    "while", "yield", "permits", "non-sealed",
]
_JAVA_BUILTINS = [
    "true", "false", "null", "System", "String", "Integer", "Double",
    "Float", "Long", "Boolean", "Character", "Byte", "Short",
    "Object", "Class", "Math", "Thread", "Runnable",
]

_LANG_JAVA = LanguageDefinition(
    name="java",
    extensions=[".java"],
    patterns=[
        (TokenType.COMMENT,      r"//[^\n]*"),
        (TokenType.COMMENT,      r"/\*[\s\S]*?\*/"),
        (TokenType.STRING,       r'"""[\s\S]*?"""'),
        (TokenType.STRING,       r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,       r"'(?:[^'\\]|\\.)*'"),
        (TokenType.DECORATOR,    r"@\w+(?:\.\w+)*"),
        (TokenType.NUMBER,       r"0[xX][0-9a-fA-F_]+[lL]?"),
        (TokenType.NUMBER,       r"0[bB][01_]+[lL]?"),
        (TokenType.NUMBER,       r"\d[\d_]*\.[\d_]*(?:[eE][+-]?\d[\d_]*)?[fFdD]?"),
        (TokenType.NUMBER,       r"\d[\d_]*[lLfFdD]?"),
        (TokenType.KEYWORD,      _kw(_JAVA_KEYWORDS)),
        (TokenType.BUILTIN,      _kw(_JAVA_BUILTINS)),
        (TokenType.FUNCTION,     r"\w+(?=\s*\()"),
        (TokenType.OPERATOR,     r">>>?=?|<<=?|>>=?|\+\+|--|&&|\|\||->|::|[+\-*/%&|^~<>=!]=?"),
        (TokenType.PUNCTUATION,  r"[(){}\[\]:;.,?<>]"),
        (TokenType.IDENTIFIER,   r"[A-Za-z_$]\w*"),
        (TokenType.NEWLINE,      r"\n"),
        (TokenType.WHITESPACE,   r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# Kotlin
# ---------------------------------------------------------------
_KOTLIN_KEYWORDS = [
    "abstract", "actual", "annotation", "as", "break", "by", "catch",
    "class", "companion", "const", "constructor", "continue", "crossinline",
    "data", "delegate", "do", "else", "enum", "expect", "external",
    "false", "final", "finally", "for", "fun", "get", "if", "import",
    "in", "infix", "init", "inline", "inner", "interface", "internal",
    "is", "lateinit", "noinline", "null", "object", "open", "operator",
    "out", "override", "package", "private", "protected", "public",
    "reified", "return", "sealed", "set", "super", "suspend", "tailrec",
    "this", "throw", "true", "try", "typealias", "typeof", "val", "var",
    "vararg", "when", "where", "while", "yield",
]

_LANG_KOTLIN = LanguageDefinition(
    name="kotlin",
    extensions=[".kt", ".kts"],
    patterns=[
        (TokenType.COMMENT,     r"//[^\n]*"),
        (TokenType.COMMENT,     r"/\*[\s\S]*?\*/"),
        (TokenType.STRING,      r'"""[\s\S]*?"""'),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.|\$\{[^}]*\}|\$\w+)*"'),
        (TokenType.STRING,      r"'(?:[^'\\]|\\.)*'"),
        (TokenType.DECORATOR,   r"@\w+(?:\.\w+)*"),
        (TokenType.NUMBER,      r"0[xX][0-9a-fA-F_]+[lL]?"),
        (TokenType.NUMBER,      r"0[bB][01_]+[lL]?"),
        (TokenType.NUMBER,      r"\d[\d_]*\.[\d_]*(?:[eE][+-]?\d[\d_]*)?[fF]?"),
        (TokenType.NUMBER,      r"\d[\d_]*[lLfF]?"),
        (TokenType.KEYWORD,     _kw(_KOTLIN_KEYWORDS)),
        (TokenType.FUNCTION,    r"(?<=\bfun\s)\w+"),
        (TokenType.FUNCTION,    r"\w+(?=\s*\()"),
        (TokenType.OPERATOR,    r"->|::|\.\.|\?\.|!!|\?:|[+\-*/%&|^~<>=!]=?|&&|\|\|"),
        (TokenType.PUNCTUATION, r"[(){}\[\]:;.,?<>]"),
        (TokenType.IDENTIFIER,  r"[A-Za-z_]\w*"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# Swift
# ---------------------------------------------------------------
_SWIFT_KEYWORDS = [
    "associatedtype", "async", "await", "break", "case", "catch", "class",
    "continue", "default", "defer", "deinit", "do", "else", "enum",
    "extension", "fallthrough", "false", "fileprivate", "final", "for",
    "func", "guard", "if", "import", "in", "init", "inout", "internal",
    "is", "lazy", "let", "mutating", "nil", "nonmutating", "open",
    "operator", "optional", "override", "private", "protocol", "public",
    "repeat", "required", "rethrows", "return", "self", "Self", "some",
    "static", "struct", "subscript", "super", "switch", "throw", "throws",
    "true", "try", "typealias", "unowned", "var", "weak", "where",
    "while", "willSet", "didSet", "get", "set", "any", "actor",
]
_SWIFT_TYPES = [
    "Int", "Int8", "Int16", "Int32", "Int64", "UInt", "UInt8", "UInt16",
    "UInt32", "UInt64", "Float", "Double", "Bool", "String", "Character",
    "Array", "Dictionary", "Set", "Optional", "Result", "Void", "Never",
    "Any", "AnyObject",
]

_LANG_SWIFT = LanguageDefinition(
    name="swift",
    extensions=[".swift"],
    patterns=[
        (TokenType.COMMENT,     r"//[^\n]*"),
        (TokenType.COMMENT,     r"/\*[\s\S]*?\*/"),
        (TokenType.STRING,      r'"""[\s\S]*?"""'),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.|\\\([^)]*\))*"'),
        (TokenType.NUMBER,      r"0[xX][0-9a-fA-F_]+"),
        (TokenType.NUMBER,      r"0[oO][0-7_]+"),
        (TokenType.NUMBER,      r"0[bB][01_]+"),
        (TokenType.NUMBER,      r"\d[\d_]*\.[\d_]*(?:[eE][+-]?\d[\d_]*)?"),
        (TokenType.NUMBER,      r"\d[\d_]*"),
        (TokenType.DECORATOR,   r"@\w+"),
        (TokenType.KEYWORD,     _kw(_SWIFT_KEYWORDS)),
        (TokenType.TYPE,        _kw(_SWIFT_TYPES)),
        (TokenType.FUNCTION,    r"(?<=\bfunc\s)\w+"),
        (TokenType.FUNCTION,    r"\w+(?=\s*\()"),
        (TokenType.OPERATOR,    r"->|\.\.\.|\.\.<|&&|\|\||[+\-*/%&|^~<>=!]=?"),
        (TokenType.PUNCTUATION, r"[(){}\[\]:;.,?<>]"),
        (TokenType.IDENTIFIER,  r"[A-Za-z_]\w*"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# Rust
# ---------------------------------------------------------------
_RUST_KEYWORDS = [
    "as", "async", "await", "break", "const", "continue", "crate",
    "dyn", "else", "enum", "extern", "false", "fn", "for", "if",
    "impl", "in", "let", "loop", "match", "mod", "move", "mut",
    "pub", "ref", "return", "self", "Self", "static", "struct",
    "super", "trait", "true", "type", "unsafe", "use", "where",
    "while", "yield", "abstract", "become", "box", "do", "final",
    "macro", "override", "priv", "try", "typeof", "unsized", "virtual",
]
_RUST_TYPES = [
    "i8", "i16", "i32", "i64", "i128", "isize", "u8", "u16", "u32",
    "u64", "u128", "usize", "f32", "f64", "bool", "char", "str",
    "String", "Vec", "Option", "Result", "Box", "Rc", "Arc", "Cell",
    "RefCell", "HashMap", "HashSet", "BTreeMap", "BTreeSet",
]
_RUST_BUILTINS = [
    "println", "print", "eprintln", "eprint", "format", "vec",
    "panic", "assert", "assert_eq", "assert_ne", "debug_assert",
    "todo", "unimplemented", "unreachable", "cfg", "include",
    "Some", "None", "Ok", "Err",
]

_LANG_RUST = LanguageDefinition(
    name="rust",
    extensions=[".rs"],
    patterns=[
        (TokenType.COMMENT,     r"//[^\n]*"),
        (TokenType.COMMENT,     r"/\*[\s\S]*?\*/"),
        (TokenType.STRING,      r'r#*"[\s\S]*?"#*'),
        (TokenType.STRING,      r'b?"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,      r"b?'(?:[^'\\]|\\.)*'"),
        (TokenType.DECORATOR,   r"#!\?\[[\s\S]*?\]"),
        (TokenType.DECORATOR,   r"#\[[\s\S]*?\]"),
        (TokenType.NUMBER,      r"0[xX][0-9a-fA-F_]+(?:i8|i16|i32|i64|i128|isize|u8|u16|u32|u64|u128|usize|f32|f64)?"),
        (TokenType.NUMBER,      r"0[oO][0-7_]+(?:i8|i16|i32|i64|i128|isize|u8|u16|u32|u64|u128|usize)?"),
        (TokenType.NUMBER,      r"0[bB][01_]+(?:i8|i16|i32|i64|i128|isize|u8|u16|u32|u64|u128|usize)?"),
        (TokenType.NUMBER,      r"\d[\d_]*\.[\d_]*(?:[eE][+-]?\d[\d_]*)?(?:f32|f64)?"),
        (TokenType.NUMBER,      r"\d[\d_]*(?:i8|i16|i32|i64|i128|isize|u8|u16|u32|u64|u128|usize|f32|f64)?"),
        (TokenType.KEYWORD,     _kw(_RUST_KEYWORDS)),
        (TokenType.TYPE,        _kw(_RUST_TYPES)),
        (TokenType.BUILTIN,     _kw(_RUST_BUILTINS)),
        (TokenType.FUNCTION,    r"(?<=\bfn\s)\w+"),
        (TokenType.FUNCTION,    r"\w+(?=\s*\()"),
        (TokenType.OPERATOR,    r"=>|->|::|\.\.=?|&&|\|\||<<=?|>>=?|[+\-*/%&|^~<>=!]=?"),
        (TokenType.PUNCTUATION, r"[(){}\[\]:;.,?<>]"),
        (TokenType.IDENTIFIER,  r"[A-Za-z_]\w*"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# Go
# ---------------------------------------------------------------
_GO_KEYWORDS = [
    "break", "case", "chan", "const", "continue", "default", "defer",
    "else", "fallthrough", "for", "func", "go", "goto", "if", "import",
    "interface", "map", "package", "range", "return", "select", "struct",
    "switch", "type", "var",
]
_GO_TYPES = [
    "bool", "byte", "complex64", "complex128", "error", "float32",
    "float64", "int", "int8", "int16", "int32", "int64", "rune",
    "string", "uint", "uint8", "uint16", "uint32", "uint64", "uintptr",
    "any",
]
_GO_BUILTINS = [
    "append", "cap", "close", "complex", "copy", "delete", "imag",
    "len", "make", "new", "panic", "print", "println", "real",
    "recover", "true", "false", "nil", "iota",
]

_LANG_GO = LanguageDefinition(
    name="go",
    extensions=[".go"],
    patterns=[
        (TokenType.COMMENT,     r"//[^\n]*"),
        (TokenType.COMMENT,     r"/\*[\s\S]*?\*/"),
        (TokenType.STRING,      r'`[^`]*`'),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,      r"'(?:[^'\\]|\\.)*'"),
        (TokenType.NUMBER,      r"0[xX][0-9a-fA-F_]+"),
        (TokenType.NUMBER,      r"0[oO][0-7_]+"),
        (TokenType.NUMBER,      r"0[bB][01_]+"),
        (TokenType.NUMBER,      r"\d[\d_]*\.[\d_]*(?:[eE][+-]?\d[\d_]*)?i?"),
        (TokenType.NUMBER,      r"\d[\d_]*i?"),
        (TokenType.KEYWORD,     _kw(_GO_KEYWORDS)),
        (TokenType.TYPE,        _kw(_GO_TYPES)),
        (TokenType.BUILTIN,     _kw(_GO_BUILTINS)),
        (TokenType.FUNCTION,    r"(?<=\bfunc\s)\w+"),
        (TokenType.FUNCTION,    r"\w+(?=\s*\()"),
        (TokenType.OPERATOR,    r":=|<-|&&|\|\||<<|>>|&\^|[+\-*/%&|^~<>=!]=?|\+\+|--"),
        (TokenType.PUNCTUATION, r"[(){}\[\]:;.,]"),
        (TokenType.IDENTIFIER,  r"[A-Za-z_]\w*"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# Ruby
# ---------------------------------------------------------------
_RUBY_KEYWORDS = [
    "BEGIN", "END", "alias", "and", "begin", "break", "case", "class",
    "def", "do", "else", "elsif", "end", "ensure", "false",
    "for", "if", "in", "module", "next", "nil", "not", "or", "redo",
    "rescue", "retry", "return", "self", "super", "then", "true",
    "undef", "unless", "until", "when", "while", "yield", "__FILE__",
    "__LINE__", "__ENCODING__", "raise", "require", "require_relative",
    "include", "extend", "prepend", "attr_accessor", "attr_reader",
    "attr_writer", "private", "protected", "public", "proc", "lambda",
]

_LANG_RUBY = LanguageDefinition(
    name="ruby",
    extensions=[".rb", ".gemspec", ".rake"],
    patterns=[
        (TokenType.COMMENT,     r"#[^\n]*"),
        (TokenType.COMMENT,     r"=begin[\s\S]*?=end"),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,      r"'(?:[^'\\]|\\.)*'"),
        (TokenType.STRING,      r"/(?:[^/\\]|\\.)*?/[imxouesn]*"),
        (TokenType.NUMBER,      r"0[xX][0-9a-fA-F_]+"),
        (TokenType.NUMBER,      r"0[bB][01_]+"),
        (TokenType.NUMBER,      r"0[oO]?[0-7_]+"),
        (TokenType.NUMBER,      r"\d[\d_]*\.[\d_]*(?:[eE][+-]?\d[\d_]*)?"),
        (TokenType.NUMBER,      r"\d[\d_]*"),
        (TokenType.VARIABLE,    r"@@?\w+"),
        (TokenType.VARIABLE,    r"\$[A-Za-z_]\w*"),
        (TokenType.KEYWORD,     _kw(_RUBY_KEYWORDS)),
        (TokenType.FUNCTION,    r"(?<=\bdef\s)\w+[?!]?"),
        (TokenType.OPERATOR,    r"<=>|<<|>>|&&|\|\||\.\.\.?|\*\*|[+\-*/%&|^~<>=!]=?"),
        (TokenType.PUNCTUATION, r"[(){}\[\]:;.,?]"),
        (TokenType.IDENTIFIER,  r":\w+"),
        (TokenType.IDENTIFIER,  r"[A-Za-z_]\w*[?!]?"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# PHP
# ---------------------------------------------------------------
_PHP_KEYWORDS = [
    "abstract", "and", "array", "as", "break", "callable", "case",
    "catch", "class", "clone", "const", "continue", "declare", "default",
    "die", "do", "echo", "else", "elseif", "empty", "enddeclare",
    "endfor", "endforeach", "endif", "endswitch", "endwhile", "enum",
    "eval", "exit", "extends", "false", "final", "finally", "fn", "for",
    "foreach", "function", "global", "goto", "if", "implements",
    "include", "include_once", "instanceof", "insteadof", "interface",
    "isset", "list", "match", "namespace", "new", "null", "or",
    "print", "private", "protected", "public", "readonly", "require",
    "require_once", "return", "static", "switch", "throw", "trait",
    "true", "try", "unset", "use", "var", "while", "xor", "yield",
]

_LANG_PHP = LanguageDefinition(
    name="php",
    extensions=[".php", ".phtml"],
    patterns=[
        (TokenType.COMMENT,     r"//[^\n]*"),
        (TokenType.COMMENT,     r"#[^\n]*"),
        (TokenType.COMMENT,     r"/\*[\s\S]*?\*/"),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.|\$\{[^}]*\}|\$\w+)*"'),
        (TokenType.STRING,      r"'(?:[^'\\]|\\.)*'"),
        (TokenType.VARIABLE,    r"\$[A-Za-z_]\w*"),
        (TokenType.NUMBER,      r"0[xX][0-9a-fA-F_]+"),
        (TokenType.NUMBER,      r"0[bB][01_]+"),
        (TokenType.NUMBER,      r"\d[\d_]*\.[\d_]*(?:[eE][+-]?\d[\d_]*)?"),
        (TokenType.NUMBER,      r"\d[\d_]*"),
        (TokenType.KEYWORD,     _kw(_PHP_KEYWORDS)),
        (TokenType.FUNCTION,    r"(?<=\bfunction\s)\w+"),
        (TokenType.FUNCTION,    r"\w+(?=\s*\()"),
        (TokenType.OPERATOR,    r"=>|->|::|<=>|\?\?=?|\?->|&&|\|\||\.=?|<<=?|>>=?|\*\*=?|[+\-*/%&|^~<>=!]=?|\+\+|--"),
        (TokenType.PUNCTUATION, r"[(){}\[\]:;.,?<>@]"),
        (TokenType.IDENTIFIER,  r"[A-Za-z_]\w*"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# C#
# ---------------------------------------------------------------
_CSHARP_KEYWORDS = [
    "abstract", "as", "base", "bool", "break", "byte", "case", "catch",
    "char", "checked", "class", "const", "continue", "decimal", "default",
    "delegate", "do", "double", "else", "enum", "event", "explicit",
    "extern", "false", "finally", "fixed", "float", "for", "foreach",
    "goto", "if", "implicit", "in", "int", "interface", "internal",
    "is", "lock", "long", "namespace", "new", "null", "object",
    "operator", "out", "override", "params", "private", "protected",
    "public", "readonly", "record", "ref", "return", "sbyte", "sealed",
    "short", "sizeof", "stackalloc", "static", "string", "struct",
    "switch", "this", "throw", "true", "try", "typeof", "uint",
    "ulong", "unchecked", "unsafe", "ushort", "using", "var", "virtual",
    "void", "volatile", "while", "async", "await", "dynamic", "global",
    "nameof", "notnull", "unmanaged", "value", "when", "where", "with",
    "yield", "init", "required", "file", "scoped",
]

_LANG_CSHARP = LanguageDefinition(
    name="csharp",
    extensions=[".cs"],
    patterns=[
        (TokenType.COMMENT,      r"//[^\n]*"),
        (TokenType.COMMENT,      r"/\*[\s\S]*?\*/"),
        (TokenType.PREPROCESSOR, r"#\s*(?:if|elif|else|endif|define|undef|warning|error|line|region|endregion|pragma|nullable)\b[^\n]*"),
        (TokenType.STRING,       r'@"(?:[^"]|"")*"'),
        (TokenType.STRING,       r'\$"(?:[^"\\]|\\.|\{[^}]*\})*"'),
        (TokenType.STRING,       r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,       r"'(?:[^'\\]|\\.)*'"),
        (TokenType.NUMBER,       r"0[xX][0-9a-fA-F_]+[uUlLmMfFdD]*"),
        (TokenType.NUMBER,       r"0[bB][01_]+[uUlL]*"),
        (TokenType.NUMBER,       r"\d[\d_]*\.[\d_]*(?:[eE][+-]?\d[\d_]*)?[fFdDmM]?"),
        (TokenType.NUMBER,       r"\d[\d_]*[uUlLfFdDmM]*"),
        (TokenType.KEYWORD,      _kw(_CSHARP_KEYWORDS)),
        (TokenType.FUNCTION,     r"\w+(?=\s*\()"),
        (TokenType.OPERATOR,     r"=>|\?\?=?|\?\.|\?\[|&&|\|\||<<=?|>>=?|\+\+|--|[+\-*/%&|^~<>=!]=?"),
        (TokenType.PUNCTUATION,  r"[(){}\[\]:;.,?<>]"),
        (TokenType.IDENTIFIER,   r"@?[A-Za-z_]\w*"),
        (TokenType.NEWLINE,      r"\n"),
        (TokenType.WHITESPACE,   r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# HTML
# ---------------------------------------------------------------
_LANG_HTML = LanguageDefinition(
    name="html",
    extensions=[".html", ".htm", ".xhtml"],
    patterns=[
        (TokenType.COMMENT,     r"<!--[\s\S]*?-->"),
        (TokenType.TAG,         r"<!DOCTYPE[^>]*>"),
        (TokenType.TAG,         r"</?\w[\w-]*"),
        (TokenType.TAG,         r"/?>"),
        (TokenType.ATTRIBUTE,   r'\w[\w-]*(?=\s*=)'),
        (TokenType.STRING,      r'"[^"]*"'),
        (TokenType.STRING,      r"'[^']*'"),
        (TokenType.OPERATOR,    r"="),
        (TokenType.IDENTIFIER,  r"[A-Za-z_][\w-]*"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# CSS
# ---------------------------------------------------------------
_CSS_KEYWORDS = [
    "important", "inherit", "initial", "unset", "revert", "none", "auto",
    "block", "inline", "flex", "grid", "absolute", "relative", "fixed",
    "sticky", "static",
]

_LANG_CSS = LanguageDefinition(
    name="css",
    extensions=[".css", ".scss", ".sass", ".less"],
    patterns=[
        (TokenType.COMMENT,     r"/\*[\s\S]*?\*/"),
        (TokenType.COMMENT,     r"//[^\n]*"),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,      r"'(?:[^'\\]|\\.)*'"),
        (TokenType.NUMBER,      r"-?\d+\.?\d*(?:px|em|rem|%|vh|vw|vmin|vmax|ch|ex|cm|mm|in|pt|pc|deg|rad|grad|turn|s|ms|Hz|kHz|dpi|dpcm|dppx|fr)?"),
        (TokenType.VARIABLE,    r"--[\w-]+"),
        (TokenType.VARIABLE,    r"\$[\w-]+"),
        (TokenType.FUNCTION,    r"\w[\w-]*(?=\s*\()"),
        (TokenType.TAG,         r"[.#][\w-]+"),
        (TokenType.TAG,         r"@[\w-]+"),
        (TokenType.ATTRIBUTE,   r"[\w-]+(?=\s*:)"),
        (TokenType.KEYWORD,     _kw(_CSS_KEYWORDS)),
        (TokenType.OPERATOR,    r"[>+~*=|^$]"),
        (TokenType.PUNCTUATION, r"[(){}\[\]:;.,!]"),
        (TokenType.IDENTIFIER,  r"[\w-]+"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# SQL
# ---------------------------------------------------------------
_SQL_KEYWORDS = [
    "SELECT", "FROM", "WHERE", "INSERT", "INTO", "UPDATE", "DELETE",
    "CREATE", "DROP", "ALTER", "TABLE", "INDEX", "VIEW", "DATABASE",
    "SCHEMA", "JOIN", "INNER", "LEFT", "RIGHT", "OUTER", "FULL",
    "CROSS", "ON", "AND", "OR", "NOT", "IN", "EXISTS", "BETWEEN",
    "LIKE", "IS", "NULL", "AS", "ORDER", "BY", "GROUP", "HAVING",
    "LIMIT", "OFFSET", "UNION", "ALL", "DISTINCT", "CASE", "WHEN",
    "THEN", "ELSE", "END", "SET", "VALUES", "BEGIN", "COMMIT",
    "ROLLBACK", "TRANSACTION", "GRANT", "REVOKE", "PRIMARY", "KEY",
    "FOREIGN", "REFERENCES", "CONSTRAINT", "CHECK", "DEFAULT", "UNIQUE",
    "ASC", "DESC", "CASCADE", "TRUNCATE", "IF", "REPLACE", "TEMP",
    "TEMPORARY", "WITH", "RECURSIVE", "RETURNING", "OVER", "PARTITION",
    "WINDOW", "ROWS", "RANGE", "PRECEDING", "FOLLOWING", "CURRENT",
    "ROW", "UNBOUNDED", "FETCH", "NEXT", "ONLY", "EXCEPT", "INTERSECT",
    "LATERAL", "NATURAL", "USING", "EXPLAIN", "ANALYZE",
    # Lowercase variants
    "select", "from", "where", "insert", "into", "update", "delete",
    "create", "drop", "alter", "table", "index", "view", "database",
    "schema", "join", "inner", "left", "right", "outer", "full",
    "cross", "on", "and", "or", "not", "in", "exists", "between",
    "like", "is", "null", "as", "order", "by", "group", "having",
    "limit", "offset", "union", "all", "distinct", "case", "when",
    "then", "else", "end", "set", "values", "begin", "commit",
    "rollback", "transaction", "grant", "revoke", "primary", "key",
    "foreign", "references", "constraint", "check", "default", "unique",
    "asc", "desc", "cascade", "truncate", "if", "replace",
    "with", "recursive", "returning",
]
_SQL_TYPES = [
    "INT", "INTEGER", "SMALLINT", "BIGINT", "SERIAL", "BIGSERIAL",
    "FLOAT", "REAL", "DOUBLE", "DECIMAL", "NUMERIC", "CHAR", "VARCHAR",
    "TEXT", "BLOB", "BOOLEAN", "DATE", "TIME", "TIMESTAMP", "DATETIME",
    "JSON", "JSONB", "UUID", "BYTEA", "ARRAY", "INTERVAL",
    "int", "integer", "smallint", "bigint", "serial", "bigserial",
    "float", "real", "double", "decimal", "numeric", "char", "varchar",
    "text", "blob", "boolean", "date", "time", "timestamp", "datetime",
    "json", "jsonb", "uuid", "bytea", "array", "interval",
]
_SQL_BUILTINS = [
    "COUNT", "SUM", "AVG", "MIN", "MAX", "COALESCE", "NULLIF",
    "CAST", "CONVERT", "IFNULL", "NVL", "ISNULL", "NOW", "CURRENT_DATE",
    "CURRENT_TIME", "CURRENT_TIMESTAMP", "EXTRACT", "SUBSTRING",
    "TRIM", "UPPER", "LOWER", "LENGTH", "CONCAT", "REPLACE", "ROUND",
    "FLOOR", "CEIL", "ABS", "MOD", "POWER", "SQRT",
    "ROW_NUMBER", "RANK", "DENSE_RANK", "NTILE", "LAG", "LEAD",
    "FIRST_VALUE", "LAST_VALUE",
    "count", "sum", "avg", "min", "max", "coalesce", "nullif",
    "cast", "convert", "now", "length", "concat", "replace", "round",
    "row_number", "rank", "dense_rank",
]

_LANG_SQL = LanguageDefinition(
    name="sql",
    extensions=[".sql"],
    patterns=[
        (TokenType.COMMENT,     r"--[^\n]*"),
        (TokenType.COMMENT,     r"/\*[\s\S]*?\*/"),
        (TokenType.STRING,      r"'(?:[^'\\]|''|\\.)*'"),
        (TokenType.STRING,      r'"(?:[^"\\]|""|\\.)*"'),
        (TokenType.NUMBER,      r"\d+\.?\d*(?:[eE][+-]?\d+)?"),
        (TokenType.KEYWORD,     _kw(_SQL_KEYWORDS)),
        (TokenType.TYPE,        _kw(_SQL_TYPES)),
        (TokenType.BUILTIN,     _kw(_SQL_BUILTINS)),
        (TokenType.FUNCTION,    r"\w+(?=\s*\()"),
        (TokenType.OPERATOR,    r"<>|!=|<=|>=|::|[+\-*/%<>=!]"),
        (TokenType.PUNCTUATION, r"[(){}\[\]:;.,?]"),
        (TokenType.VARIABLE,    r"@\w+"),
        (TokenType.IDENTIFIER,  r"[A-Za-z_]\w*"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# Shell / Bash
# ---------------------------------------------------------------
_SHELL_KEYWORDS = [
    "if", "then", "else", "elif", "fi", "case", "esac", "for", "while",
    "until", "do", "done", "in", "function", "select", "time", "coproc",
    "return", "exit", "break", "continue", "declare", "typeset",
    "local", "export", "readonly", "unset", "shift", "source", "eval",
    "exec", "trap", "set", "shopt",
]
_SHELL_BUILTINS = [
    "echo", "printf", "read", "cd", "pwd", "pushd", "popd", "dirs",
    "let", "test", "true", "false", "getopts", "hash", "type",
    "umask", "wait", "jobs", "fg", "bg", "kill", "alias", "unalias",
    "bind", "builtin", "caller", "command", "compgen", "complete",
    "enable", "help", "history", "logout", "mapfile", "readarray",
]

_LANG_SHELL = LanguageDefinition(
    name="shell",
    extensions=[".sh", ".bash", ".zsh", ".ksh"],
    patterns=[
        (TokenType.COMMENT,     r"#[^\n]*"),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.|\$\{[^}]*\}|\$\([^)]*\)|\$\w+)*"'),
        (TokenType.STRING,      r"'[^']*'"),
        (TokenType.VARIABLE,    r"\$\{[^}]*\}"),
        (TokenType.VARIABLE,    r"\$\([^)]*\)"),
        (TokenType.VARIABLE,    r"\$[A-Za-z_]\w*"),
        (TokenType.VARIABLE,    r"\$[0-9@#?$!*-]"),
        (TokenType.NUMBER,      r"\d+\.?\d*"),
        (TokenType.KEYWORD,     _kw(_SHELL_KEYWORDS)),
        (TokenType.BUILTIN,     _kw(_SHELL_BUILTINS)),
        (TokenType.FUNCTION,    r"\w+(?=\s*\(\))"),
        (TokenType.OPERATOR,    r"&&|\|\||;;|[|&;><]=?|<<-?|>>"),
        (TokenType.PUNCTUATION, r"[(){}\[\]]"),
        (TokenType.IDENTIFIER,  r"[A-Za-z_][\w.-]*"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# YAML
# ---------------------------------------------------------------
_LANG_YAML = LanguageDefinition(
    name="yaml",
    extensions=[".yml", ".yaml"],
    patterns=[
        (TokenType.COMMENT,     r"#[^\n]*"),
        (TokenType.TAG,         r"!!\w+"),
        (TokenType.TAG,         r"!\w+"),
        (TokenType.KEYWORD,     r"\b(?:true|false|yes|no|on|off|null|True|False|Yes|No|On|Off|Null|TRUE|FALSE|NULL)\b"),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,      r"'(?:[^'\\]|\\.)*'"),
        (TokenType.ATTRIBUTE,   r"[\w][\w ./-]*(?=\s*:)"),
        (TokenType.NUMBER,      r"-?\d+\.?\d*(?:[eE][+-]?\d+)?"),
        (TokenType.OPERATOR,    r"[|>][-+]?"),
        (TokenType.PUNCTUATION, r"[{}\[\]:,\-?&*]"),
        (TokenType.VARIABLE,    r"<<"),
        (TokenType.IDENTIFIER,  r"\S+"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# JSON
# ---------------------------------------------------------------
_LANG_JSON = LanguageDefinition(
    name="json",
    extensions=[".json", ".jsonc", ".json5"],
    patterns=[
        (TokenType.COMMENT,     r"//[^\n]*"),
        (TokenType.COMMENT,     r"/\*[\s\S]*?\*/"),
        (TokenType.ATTRIBUTE,   r'"(?:[^"\\]|\\.)*"(?=\s*:)'),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.)*"'),
        (TokenType.KEYWORD,     r"\b(?:true|false|null)\b"),
        (TokenType.NUMBER,      r"-?\d+\.?\d*(?:[eE][+-]?\d+)?"),
        (TokenType.PUNCTUATION, r"[{}\[\]:,]"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# TOML
# ---------------------------------------------------------------
_LANG_TOML = LanguageDefinition(
    name="toml",
    extensions=[".toml"],
    patterns=[
        (TokenType.COMMENT,     r"#[^\n]*"),
        (TokenType.TAG,         r"\[\[[\w.]+\]\]"),
        (TokenType.TAG,         r"\[[\w.]+\]"),
        (TokenType.STRING,      r'"""[\s\S]*?"""'),
        (TokenType.STRING,      r"'''[\s\S]*?'''"),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,      r"'[^']*'"),
        (TokenType.KEYWORD,     r"\b(?:true|false)\b"),
        (TokenType.NUMBER,      r"0[xX][0-9a-fA-F_]+"),
        (TokenType.NUMBER,      r"0[oO][0-7_]+"),
        (TokenType.NUMBER,      r"0[bB][01_]+"),
        (TokenType.NUMBER,      r"[+-]?\d[\d_]*\.[\d_]*(?:[eE][+-]?\d[\d_]*)?"),
        (TokenType.NUMBER,      r"[+-]?\d[\d_]*"),
        (TokenType.NUMBER,      r"[+-]?(?:inf|nan)"),
        (TokenType.ATTRIBUTE,   r"[\w-]+(?=\s*=)"),
        (TokenType.OPERATOR,    r"="),
        (TokenType.PUNCTUATION, r"[{}\[\]:.,]"),
        (TokenType.IDENTIFIER,  r"[\w-]+"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------
_LANG_MARKDOWN = LanguageDefinition(
    name="markdown",
    extensions=[".md", ".markdown", ".mkd"],
    patterns=[
        (TokenType.COMMENT,     r"<!--[\s\S]*?-->"),
        (TokenType.STRING,      r"`{3}[\s\S]*?`{3}"),
        (TokenType.STRING,      r"`[^`\n]+`"),
        (TokenType.TAG,         r"^#{1,6}\s+.*$"),
        (TokenType.OPERATOR,    r"^\s*[-*+]\s"),
        (TokenType.OPERATOR,    r"^\s*\d+\.\s"),
        (TokenType.ATTRIBUTE,   r"\[(?:[^\[\]\\]|\\.)*\]\([^)]*\)"),
        (TokenType.ATTRIBUTE,   r"!\[(?:[^\[\]\\]|\\.)*\]\([^)]*\)"),
        (TokenType.KEYWORD,     r"\*\*(?:[^*\\]|\\.)+\*\*"),
        (TokenType.KEYWORD,     r"__(?:[^_\\]|\\.)+__"),
        (TokenType.BUILTIN,     r"\*(?:[^*\\]|\\.)+\*"),
        (TokenType.BUILTIN,     r"_(?:[^_\\]|\\.)+_"),
        (TokenType.PUNCTUATION, r"^---+$"),
        (TokenType.PUNCTUATION, r"^===+$"),
        (TokenType.IDENTIFIER,  r"\S+"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# Dart
# ---------------------------------------------------------------
_DART_KEYWORDS = [
    "abstract", "as", "assert", "async", "await", "base", "break",
    "case", "catch", "class", "const", "continue", "covariant",
    "default", "deferred", "do", "dynamic", "else", "enum", "export",
    "extends", "extension", "external", "factory", "false", "final",
    "finally", "for", "Function", "get", "hide", "if", "implements",
    "import", "in", "interface", "is", "late", "library", "mixin",
    "new", "null", "on", "operator", "part", "required", "rethrow",
    "return", "sealed", "set", "show", "static", "super", "switch",
    "sync", "this", "throw", "true", "try", "typedef", "var", "void",
    "when", "while", "with", "yield",
]
_DART_TYPES = [
    "int", "double", "num", "String", "bool", "List", "Map", "Set",
    "Future", "Stream", "Iterable", "dynamic", "void", "Never", "Null",
    "Object", "Type",
]

_LANG_DART = LanguageDefinition(
    name="dart",
    extensions=[".dart"],
    patterns=[
        (TokenType.COMMENT,     r"//[^\n]*"),
        (TokenType.COMMENT,     r"/\*[\s\S]*?\*/"),
        (TokenType.STRING,      r'r"""[\s\S]*?"""'),
        (TokenType.STRING,      r"r'''[\s\S]*?'''"),
        (TokenType.STRING,      r'"""[\s\S]*?"""'),
        (TokenType.STRING,      r"'''[\s\S]*?'''"),
        (TokenType.STRING,      r'r"[^"]*"'),
        (TokenType.STRING,      r"r'[^']*'"),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.|\$\{[^}]*\}|\$\w+)*"'),
        (TokenType.STRING,      r"'(?:[^'\\]|\\.|\$\{[^}]*\}|\$\w+)*'"),
        (TokenType.DECORATOR,   r"@\w+(?:\.\w+)*"),
        (TokenType.NUMBER,      r"0[xX][0-9a-fA-F]+"),
        (TokenType.NUMBER,      r"\d+\.?\d*(?:[eE][+-]?\d+)?"),
        (TokenType.KEYWORD,     _kw(_DART_KEYWORDS)),
        (TokenType.TYPE,        _kw(_DART_TYPES)),
        (TokenType.FUNCTION,    r"\w+(?=\s*\()"),
        (TokenType.OPERATOR,    r"=>|\?\?=?|\?\.|\.\.|&&|\|\||<<=?|>>=?|>>>|[+\-*/%&|^~<>=!]=?|\+\+|--"),
        (TokenType.PUNCTUATION, r"[(){}\[\]:;.,?<>]"),
        (TokenType.IDENTIFIER,  r"[A-Za-z_$]\w*"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# Lua
# ---------------------------------------------------------------
_LUA_KEYWORDS = [
    "and", "break", "do", "else", "elseif", "end", "false", "for",
    "function", "goto", "if", "in", "local", "nil", "not", "or",
    "repeat", "return", "then", "true", "until", "while",
]
_LUA_BUILTINS = [
    "assert", "collectgarbage", "dofile", "error", "getmetatable",
    "ipairs", "load", "loadfile", "next", "pairs", "pcall", "print",
    "rawequal", "rawget", "rawlen", "rawset", "require", "select",
    "setmetatable", "tonumber", "tostring", "type", "unpack",
    "xpcall", "table", "string", "math", "io", "os", "coroutine",
    "debug", "package", "utf8",
]

_LANG_LUA = LanguageDefinition(
    name="lua",
    extensions=[".lua"],
    patterns=[
        (TokenType.COMMENT,     r"--\[\[[\s\S]*?\]\]"),
        (TokenType.COMMENT,     r"--[^\n]*"),
        (TokenType.STRING,      r"\[\[[\s\S]*?\]\]"),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,      r"'(?:[^'\\]|\\.)*'"),
        (TokenType.NUMBER,      r"0[xX][0-9a-fA-F]+(?:\.[0-9a-fA-F]+)?(?:[pP][+-]?\d+)?"),
        (TokenType.NUMBER,      r"\d+\.?\d*(?:[eE][+-]?\d+)?"),
        (TokenType.KEYWORD,     _kw(_LUA_KEYWORDS)),
        (TokenType.BUILTIN,     _kw(_LUA_BUILTINS)),
        (TokenType.FUNCTION,    r"(?<=\bfunction\s)\w+"),
        (TokenType.FUNCTION,    r"\w+(?=\s*\()"),
        (TokenType.OPERATOR,    r"\.\.\.?|~=|<=|>=|==|<<|>>|//|[+\-*/%^#<>=]"),
        (TokenType.PUNCTUATION, r"[(){}\[\]:;.,]"),
        (TokenType.IDENTIFIER,  r"[A-Za-z_]\w*"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# R
# ---------------------------------------------------------------
_R_KEYWORDS = [
    "if", "else", "repeat", "while", "function", "for", "in", "next",
    "break", "TRUE", "FALSE", "NULL", "Inf", "NaN", "NA", "NA_integer_",
    "NA_real_", "NA_complex_", "NA_character_", "return", "library",
    "require", "source",
]
_R_BUILTINS = [
    "c", "list", "matrix", "array", "factor", "vector",
    "print", "cat", "paste", "paste0", "sprintf", "length", "nchar",
    "substr", "grep", "grepl", "sub", "gsub", "which", "any", "all",
    "sum", "mean", "median", "sd", "var", "min", "max", "range",
    "seq", "rep", "rev", "sort", "order", "unique", "duplicated",
    "table", "apply", "sapply", "lapply", "tapply", "mapply",
    "class", "typeof", "str", "summary", "head", "tail", "names",
    "nrow", "ncol", "dim", "rbind", "cbind", "merge",
]

_LANG_R = LanguageDefinition(
    name="r",
    extensions=[".r", ".R", ".Rmd"],
    patterns=[
        (TokenType.COMMENT,     r"#[^\n]*"),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,      r"'(?:[^'\\]|\\.)*'"),
        (TokenType.NUMBER,      r"0[xX][0-9a-fA-F]+[Li]?"),
        (TokenType.NUMBER,      r"\d+\.?\d*(?:[eE][+-]?\d+)?[Li]?"),
        (TokenType.KEYWORD,     _kw(_R_KEYWORDS)),
        (TokenType.BUILTIN,     _kw(_R_BUILTINS)),
        (TokenType.FUNCTION,    r"\w+(?=\s*\()"),
        (TokenType.OPERATOR,    r"<-|->|<<-|->>|%%|%/%|%in%|\|>|&&|\|\||[+\-*/^<>=!&|~$@]=?"),
        (TokenType.PUNCTUATION, r"[(){}\[\]:;.,?]"),
        (TokenType.VARIABLE,    r"\.\w+"),
        (TokenType.IDENTIFIER,  r"[A-Za-z_][\w.]*"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# MATLAB
# ---------------------------------------------------------------
_MATLAB_KEYWORDS = [
    "break", "case", "catch", "classdef", "continue", "else", "elseif",
    "end", "for", "function", "global", "if", "methods", "otherwise",
    "parfor", "persistent", "properties", "return", "spmd", "switch",
    "try", "while", "events", "enumeration", "arguments",
]
_MATLAB_BUILTINS = [
    "abs", "acos", "asin", "atan", "atan2", "ceil", "cos", "exp",
    "floor", "log", "log2", "log10", "max", "min", "mod", "pow",
    "round", "sin", "sqrt", "tan", "zeros", "ones", "eye", "rand",
    "randn", "linspace", "logspace", "length", "size", "numel",
    "reshape", "repmat", "cat", "disp", "fprintf", "sprintf",
    "plot", "figure", "hold", "xlabel", "ylabel", "title", "legend",
    "subplot", "mesh", "surf", "contour", "imagesc", "colorbar",
    "true", "false", "pi", "inf", "nan", "eps", "realmin", "realmax",
]

_LANG_MATLAB = LanguageDefinition(
    name="matlab",
    extensions=[".m", ".mat"],
    patterns=[
        (TokenType.COMMENT,     r"%\{[\s\S]*?%\}"),
        (TokenType.COMMENT,     r"%[^\n]*"),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,      r"'(?:[^'\\]|'')*'"),
        (TokenType.NUMBER,      r"0[xX][0-9a-fA-F]+"),
        (TokenType.NUMBER,      r"\d+\.?\d*(?:[eE][+-]?\d+)?[ij]?"),
        (TokenType.KEYWORD,     _kw(_MATLAB_KEYWORDS)),
        (TokenType.BUILTIN,     _kw(_MATLAB_BUILTINS)),
        (TokenType.FUNCTION,    r"(?<=\bfunction\s)\w+"),
        (TokenType.FUNCTION,    r"\w+(?=\s*\()"),
        (TokenType.OPERATOR,    r"\.\*|\./|\.\^|\.\\|\.'" + r"|~=|<=|>=|==|&&|\|\||[+\-*/\\^<>=~&|:@]"),
        (TokenType.PUNCTUATION, r"[(){}\[\]:;.,?]"),
        (TokenType.IDENTIFIER,  r"[A-Za-z_]\w*"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# VHDL
# ---------------------------------------------------------------
_VHDL_KEYWORDS = [
    "abs", "access", "after", "alias", "all", "and", "architecture",
    "array", "assert", "attribute", "begin", "block", "body", "buffer",
    "bus", "case", "component", "configuration", "constant", "disconnect",
    "downto", "else", "elsif", "end", "entity", "exit", "file",
    "for", "function", "generate", "generic", "group", "guarded",
    "if", "impure", "in", "inertial", "inout", "is", "label",
    "library", "linkage", "literal", "loop", "map", "mod", "nand",
    "new", "next", "nor", "not", "null", "of", "on", "open", "or",
    "others", "out", "package", "port", "postponed", "procedure",
    "process", "pure", "range", "record", "register", "reject",
    "rem", "report", "return", "rol", "ror", "select", "severity",
    "signal", "shared", "sla", "sll", "sra", "srl", "subtype",
    "then", "to", "transport", "type", "unaffected", "units", "until",
    "use", "variable", "wait", "when", "while", "with", "xnor", "xor",
]
_VHDL_TYPES = [
    "bit", "bit_vector", "boolean", "character", "integer", "natural",
    "positive", "real", "string", "time", "std_logic", "std_logic_vector",
    "std_ulogic", "std_ulogic_vector", "signed", "unsigned",
]

_LANG_VHDL = LanguageDefinition(
    name="vhdl",
    extensions=[".vhd", ".vhdl"],
    patterns=[
        (TokenType.COMMENT,     r"--[^\n]*"),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,      r"'.'"),
        (TokenType.NUMBER,      r"16#[0-9a-fA-F_]+#"),
        (TokenType.NUMBER,      r"2#[01_]+#"),
        (TokenType.NUMBER,      r"8#[0-7_]+#"),
        (TokenType.NUMBER,      r"\d[\d_]*\.[\d_]*(?:[eE][+-]?\d[\d_]*)?"),
        (TokenType.NUMBER,      r"\d[\d_]*"),
        (TokenType.KEYWORD,     _kw(_VHDL_KEYWORDS)),
        (TokenType.TYPE,        _kw(_VHDL_TYPES)),
        (TokenType.FUNCTION,    r"\w+(?=\s*\()"),
        (TokenType.OPERATOR,    r"<=|=>|:=|/=|>=|<<|>>|\*\*|[+\-*/&<>=|]"),
        (TokenType.PUNCTUATION, r"[(){}\[\]:;.,']"),
        (TokenType.IDENTIFIER,  r"[A-Za-z_]\w*"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# Verilog
# ---------------------------------------------------------------
_VERILOG_KEYWORDS = [
    "always", "and", "assign", "automatic", "begin", "buf", "bufif0",
    "bufif1", "case", "casex", "casez", "cell", "cmos", "config",
    "deassign", "default", "defparam", "design", "disable", "edge",
    "else", "end", "endcase", "endconfig", "endfunction", "endgenerate",
    "endmodule", "endprimitive", "endspecify", "endtable", "endtask",
    "event", "for", "force", "forever", "fork", "function", "generate",
    "genvar", "highz0", "highz1", "if", "ifnone", "incdir", "include",
    "initial", "inout", "input", "instance", "integer", "join",
    "large", "liblist", "library", "localparam", "macromodule",
    "medium", "module", "nand", "negedge", "nmos", "nor", "not",
    "notif0", "notif1", "or", "output", "parameter", "pmos",
    "posedge", "primitive", "pull0", "pull1", "pulldown", "pullup",
    "rcmos", "real", "realtime", "reg", "release", "repeat", "rnmos",
    "rpmos", "rtran", "rtranif0", "rtranif1", "scalared", "signed",
    "small", "specify", "specparam", "strong0", "strong1", "supply0",
    "supply1", "table", "task", "time", "tran", "tranif0", "tranif1",
    "tri", "tri0", "tri1", "triand", "trior", "trireg", "unsigned",
    "use", "vectored", "wait", "wand", "weak0", "weak1", "while",
    "wire", "wor", "xnor", "xor",
]

_LANG_VERILOG = LanguageDefinition(
    name="verilog",
    extensions=[".v", ".sv", ".vh", ".svh"],
    patterns=[
        (TokenType.COMMENT,      r"//[^\n]*"),
        (TokenType.COMMENT,      r"/\*[\s\S]*?\*/"),
        (TokenType.PREPROCESSOR, r"`\w+"),
        (TokenType.STRING,       r'"(?:[^"\\]|\\.)*"'),
        (TokenType.NUMBER,       r"\d+'[bBhHoOdD][0-9a-fA-FxXzZ_]+"),
        (TokenType.NUMBER,       r"\d+\.?\d*(?:[eE][+-]?\d+)?"),
        (TokenType.KEYWORD,      _kw(_VERILOG_KEYWORDS)),
        (TokenType.VARIABLE,     r"\$\w+"),
        (TokenType.FUNCTION,     r"\w+(?=\s*\()"),
        (TokenType.OPERATOR,     r"<<<|>>>|===|!==|<=|>=|==|!=|&&|\|\||<<|>>|[+\-*/%&|^~<>=!?:]"),
        (TokenType.PUNCTUATION,  r"[(){}\[\];.,#@]"),
        (TokenType.IDENTIFIER,   r"[A-Za-z_]\w*"),
        (TokenType.NEWLINE,      r"\n"),
        (TokenType.WHITESPACE,   r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# Assembly (generic x86-style)
# ---------------------------------------------------------------
_ASM_KEYWORDS = [
    "mov", "add", "sub", "mul", "div", "and", "or", "xor", "not",
    "shl", "shr", "cmp", "jmp", "je", "jne", "jg", "jge", "jl",
    "jle", "ja", "jae", "jb", "jbe", "jz", "jnz", "call", "ret",
    "push", "pop", "lea", "nop", "int", "syscall", "enter", "leave",
    "inc", "dec", "neg", "test", "movzx", "movsx", "imul", "idiv",
    "cdq", "cbw", "cwde", "rep", "movsb", "stosb", "lodsb",
    "db", "dw", "dd", "dq", "resb", "resw", "resd", "resq",
    "equ", "times", "section", "segment", "global", "extern",
    "org", "bits",
]
_ASM_REGISTERS = [
    "eax", "ebx", "ecx", "edx", "esi", "edi", "esp", "ebp",
    "rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rsp", "rbp",
    "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15",
    "al", "bl", "cl", "dl", "ah", "bh", "ch", "dh",
    "ax", "bx", "cx", "dx", "si", "di", "sp", "bp",
    "cs", "ds", "es", "fs", "gs", "ss", "cr0", "cr2", "cr3", "cr4",
    "xmm0", "xmm1", "xmm2", "xmm3", "xmm4", "xmm5", "xmm6", "xmm7",
]

_LANG_ASSEMBLY = LanguageDefinition(
    name="assembly",
    extensions=[".asm", ".s", ".S"],
    patterns=[
        (TokenType.COMMENT,      r";[^\n]*"),
        (TokenType.COMMENT,      r"#[^\n]*"),
        (TokenType.PREPROCESSOR, r"%\w+"),
        (TokenType.PREPROCESSOR, r"\.\w+"),
        (TokenType.STRING,       r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,       r"'(?:[^'\\]|\\.)*'"),
        (TokenType.NUMBER,       r"0[xX][0-9a-fA-F]+[hH]?"),
        (TokenType.NUMBER,       r"0[bB][01]+"),
        (TokenType.NUMBER,       r"[0-9a-fA-F]+[hH]"),
        (TokenType.NUMBER,       r"\d+\.?\d*"),
        (TokenType.BUILTIN,      _kw(_ASM_REGISTERS)),
        (TokenType.KEYWORD,      _kw(_ASM_KEYWORDS)),
        (TokenType.TAG,          r"\w+:"),
        (TokenType.OPERATOR,     r"[+\-*/%,<>]"),
        (TokenType.PUNCTUATION,  r"[(){}\[\]:]"),
        (TokenType.IDENTIFIER,   r"[A-Za-z_.]\w*"),
        (TokenType.NEWLINE,      r"\n"),
        (TokenType.WHITESPACE,   r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# Dockerfile
# ---------------------------------------------------------------
_DOCKERFILE_KEYWORDS = [
    "FROM", "RUN", "CMD", "LABEL", "MAINTAINER", "EXPOSE", "ENV",
    "ADD", "COPY", "ENTRYPOINT", "VOLUME", "USER", "WORKDIR", "ARG",
    "ONBUILD", "STOPSIGNAL", "HEALTHCHECK", "SHELL",
]

_LANG_DOCKERFILE = LanguageDefinition(
    name="dockerfile",
    extensions=[],  # detected by filename
    patterns=[
        (TokenType.COMMENT,     r"#[^\n]*"),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,      r"'(?:[^'\\]|\\.)*'"),
        (TokenType.KEYWORD,     r"\b(?:" + "|".join(_DOCKERFILE_KEYWORDS) + r")\b"),
        (TokenType.VARIABLE,    r"\$\{[^}]*\}"),
        (TokenType.VARIABLE,    r"\$[A-Za-z_]\w*"),
        (TokenType.NUMBER,      r"\d+"),
        (TokenType.OPERATOR,    r"[=\\]"),
        (TokenType.PUNCTUATION, r"[(){}\[\]:;,]"),
        (TokenType.IDENTIFIER,  r"[A-Za-z_][\w./-]*"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# Makefile
# ---------------------------------------------------------------
_LANG_MAKEFILE = LanguageDefinition(
    name="makefile",
    extensions=[],  # detected by filename
    patterns=[
        (TokenType.COMMENT,     r"#[^\n]*"),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,      r"'(?:[^'\\]|\\.)*'"),
        (TokenType.KEYWORD,     r"\b(?:ifeq|ifneq|ifdef|ifndef|else|endif|include|sinclude|override|export|unexport|define|endef|vpath)\b"),
        (TokenType.BUILTIN,     r"\$\([^)]+\)"),
        (TokenType.BUILTIN,     r"\$\{[^}]+\}"),
        (TokenType.BUILTIN,     r"\$[@<^+?*%]"),
        (TokenType.VARIABLE,    r"\$[A-Za-z_]\w*"),
        (TokenType.TAG,         r"^[\w./%\-]+\s*:(?!=)"),
        (TokenType.OPERATOR,    r"[?+:]?=|&&|\|\|"),
        (TokenType.PUNCTUATION, r"[(){}\[\]:;,\\|]"),
        (TokenType.IDENTIFIER,  r"[A-Za-z_][\w.-]*"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# Haskell
# ---------------------------------------------------------------
_HASKELL_KEYWORDS = [
    "as", "case", "class", "data", "default", "deriving", "do", "else",
    "family", "forall", "foreign", "hiding", "if", "import", "in",
    "infix", "infixl", "infixr", "instance", "let", "mdo", "module",
    "newtype", "of", "proc", "qualified", "rec", "then", "type",
    "where", "pattern",
]
_HASKELL_BUILTINS = [
    "True", "False", "Nothing", "Just", "Left", "Right", "IO",
    "Maybe", "Either", "String", "Int", "Integer", "Float", "Double",
    "Char", "Bool", "Show", "Read", "Eq", "Ord", "Num", "Enum",
    "Bounded", "Integral", "Floating", "Monad", "Functor",
    "Applicative", "Foldable", "Traversable", "Semigroup", "Monoid",
    "map", "filter", "foldl", "foldr", "head", "tail", "init", "last",
    "length", "null", "reverse", "concat", "concatMap", "zip",
    "unzip", "take", "drop", "span", "elem", "notElem",
    "lookup", "print", "putStrLn", "putStr", "getLine", "readLn",
    "show", "read", "error", "undefined",
]

_LANG_HASKELL = LanguageDefinition(
    name="haskell",
    extensions=[".hs", ".lhs"],
    patterns=[
        (TokenType.COMMENT,     r"\{-[\s\S]*?-\}"),
        (TokenType.COMMENT,     r"--[^\n]*"),
        (TokenType.STRING,      r'"(?:[^"\\]|\\.)*"'),
        (TokenType.STRING,      r"'(?:[^'\\]|\\.)'"),
        (TokenType.NUMBER,      r"0[xX][0-9a-fA-F]+"),
        (TokenType.NUMBER,      r"0[oO][0-7]+"),
        (TokenType.NUMBER,      r"\d+\.?\d*(?:[eE][+-]?\d+)?"),
        (TokenType.KEYWORD,     _kw(_HASKELL_KEYWORDS)),
        (TokenType.BUILTIN,     _kw(_HASKELL_BUILTINS)),
        (TokenType.TYPE,        r"\b[A-Z]\w*"),
        (TokenType.OPERATOR,    r"=>|->|<-|\.\.|::|\\|[+\-*/%<>=!&|^~@.?$]+"),
        (TokenType.PUNCTUATION, r"[(){}\[\]:;,`]"),
        (TokenType.IDENTIFIER,  r"[a-z_]\w*'?"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)

# ---------------------------------------------------------------
# Plaintext (fallback)
# ---------------------------------------------------------------
_LANG_PLAINTEXT = LanguageDefinition(
    name="plaintext",
    extensions=[".txt", ".text", ".log"],
    patterns=[
        (TokenType.IDENTIFIER,  r"\S+"),
        (TokenType.NEWLINE,     r"\n"),
        (TokenType.WHITESPACE,  r"[ \t\r]+"),
    ],
)


# ===================================================================
# Language registry
# ===================================================================

_ALL_LANGUAGES: Dict[str, LanguageDefinition] = {}
_EXT_MAP: Dict[str, str] = {}


def _register(lang: LanguageDefinition) -> None:
    _ALL_LANGUAGES[lang.name] = lang
    for ext in lang.extensions:
        _EXT_MAP[ext.lower()] = lang.name


# Register every language
_register(_LANG_PYTHON)
_register(_LANG_JAVASCRIPT)
_register(_LANG_TYPESCRIPT)
_register(_LANG_C)
_register(_LANG_CPP)
_register(_LANG_JAVA)
_register(_LANG_KOTLIN)
_register(_LANG_SWIFT)
_register(_LANG_RUST)
_register(_LANG_GO)
_register(_LANG_RUBY)
_register(_LANG_PHP)
_register(_LANG_CSHARP)
_register(_LANG_HTML)
_register(_LANG_CSS)
_register(_LANG_SQL)
_register(_LANG_SHELL)
_register(_LANG_YAML)
_register(_LANG_JSON)
_register(_LANG_TOML)
_register(_LANG_MARKDOWN)
_register(_LANG_DART)
_register(_LANG_LUA)
_register(_LANG_R)
_register(_LANG_MATLAB)
_register(_LANG_VHDL)
_register(_LANG_VERILOG)
_register(_LANG_ASSEMBLY)
_register(_LANG_DOCKERFILE)
_register(_LANG_MAKEFILE)
_register(_LANG_HASKELL)
_register(_LANG_PLAINTEXT)

# Filename-only detection
_FILENAME_MAP: Dict[str, str] = {
    "Dockerfile":  "dockerfile",
    "dockerfile":  "dockerfile",
    "Makefile":    "makefile",
    "makefile":    "makefile",
    "GNUmakefile": "makefile",
    "Rakefile":    "ruby",
    "Gemfile":     "ruby",
    "CMakeLists.txt": "makefile",
    "Jenkinsfile": "shell",
    ".bashrc":     "shell",
    ".bash_profile": "shell",
    ".zshrc":      "shell",
    ".profile":    "shell",
}


# ===================================================================
# SyntaxHighlighter
# ===================================================================

class SyntaxHighlighter:
    """Token-based syntax highlighter with multi-language and theme support.

    Backward-compatible with the original stub API:
        ``__init__(language="python")``, ``highlight(source)``, ``set_language(language)``

    Parameters
    ----------
    language : str
        Language name (case-insensitive). Defaults to ``"python"``.
    theme : str
        Theme name. Defaults to ``"monokai"``.
    """

    # Class-level caches
    _compiled_patterns: ClassVar[Dict[str, List[Tuple[TokenType, re.Pattern]]]] = {}

    def __init__(self, language: str = "python", theme: str = "monokai") -> None:
        self._language_name: str = ""
        self._lang: LanguageDefinition = _LANG_PLAINTEXT
        self._theme: Theme = BUILTIN_THEMES.get("monokai", list(BUILTIN_THEMES.values())[0])
        self.set_language(language)
        self.set_theme(theme)

    # ------------------------------------------------------------------
    # Language / theme management
    # ------------------------------------------------------------------

    def set_language(self, language: str) -> None:
        """Switch the active language (case-insensitive)."""
        key = language.lower().replace("-", "").replace(" ", "")
        # Try common aliases
        alias: Dict[str, str] = {
            "c++": "cpp", "cplusplus": "cpp", "cxx": "cpp",
            "c#": "csharp", "cs": "csharp",
            "js": "javascript", "jsx": "javascript",
            "ts": "typescript", "tsx": "typescript",
            "py": "python", "python3": "python",
            "rb": "ruby",
            "sh": "shell", "bash": "shell", "zsh": "shell",
            "yml": "yaml",
            "md": "markdown",
            "asm": "assembly", "nasm": "assembly", "masm": "assembly",
            "docker": "dockerfile",
            "make": "makefile",
            "hs": "haskell",
            "objc": "c", "objectivec": "c",
            "golang": "go",
            "kt": "kotlin", "kts": "kotlin",
        }
        resolved = alias.get(key, key)
        if resolved in _ALL_LANGUAGES:
            self._language_name = resolved
            self._lang = _ALL_LANGUAGES[resolved]
        else:
            self._language_name = "plaintext"
            self._lang = _LANG_PLAINTEXT

    @property
    def language(self) -> str:
        return self._language_name

    def set_theme(self, theme: str) -> None:
        """Switch the active theme (case-insensitive, hyphens accepted)."""
        key = theme.lower().replace("-", "_").replace(" ", "_")
        if key in BUILTIN_THEMES:
            self._theme = BUILTIN_THEMES[key]

    @property
    def theme(self) -> str:
        return self._theme.name

    def load_custom_theme(self, path: str) -> None:
        """Load a theme from a JSON file.

        Expected JSON format::

            {
                "name": "my_theme",
                "background": "#1e1e1e",
                "foreground": "#d4d4d4",
                "colors": {
                    "KEYWORD": "#569cd6",
                    "STRING": "#ce9178",
                    ...
                }
            }
        """
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        mapping: Dict[TokenType, str] = {}
        for key, val in data.get("colors", {}).items():
            try:
                tt = TokenType[key.upper()]
                mapping[tt] = val
            except KeyError:
                pass
        self._theme = _make_theme(
            data.get("name", "custom"),
            data.get("background", "#1e1e1e"),
            data.get("foreground", "#d4d4d4"),
            mapping,
        )

    # ------------------------------------------------------------------
    # Class methods
    # ------------------------------------------------------------------

    @classmethod
    def get_supported_languages(cls) -> List[str]:
        """Return a sorted list of supported language names."""
        return sorted(_ALL_LANGUAGES.keys())

    @classmethod
    def get_supported_themes(cls) -> List[str]:
        """Return a sorted list of built-in theme names."""
        return sorted(BUILTIN_THEMES.keys())

    @staticmethod
    def detect_language(filename: str) -> str:
        """Detect a language from a file name or path.

        Returns the language name string, or ``"plaintext"`` if unknown.
        """
        basename = Path(filename).name
        # Check exact filename first
        if basename in _FILENAME_MAP:
            return _FILENAME_MAP[basename]
        # Check extension
        ext = Path(filename).suffix.lower()
        return _EXT_MAP.get(ext, "plaintext")

    # ------------------------------------------------------------------
    # Compilation (cached per language)
    # ------------------------------------------------------------------

    def _get_compiled(self) -> List[Tuple[TokenType, re.Pattern]]:
        name = self._lang.name
        if name not in self._compiled_patterns:
            compiled: List[Tuple[TokenType, re.Pattern]] = []
            for tt, pat in self._lang.patterns:
                try:
                    compiled.append((tt, re.compile(pat, re.MULTILINE)))
                except re.error:
                    # Skip invalid patterns gracefully
                    pass
            self._compiled_patterns[name] = compiled
        return self._compiled_patterns[name]

    # ------------------------------------------------------------------
    # Tokenisation
    # ------------------------------------------------------------------

    def tokenize(self, source: str) -> List[Token]:
        """Tokenize *source* into a list of :class:`Token` objects.

        Unrecognised characters are emitted as ``TokenType.UNKNOWN``.
        """
        compiled = self._get_compiled()
        tokens: List[Token] = []
        pos = 0
        length = len(source)

        while pos < length:
            best_match: Optional[re.Match] = None
            best_type: TokenType = TokenType.UNKNOWN

            for tt, rx in compiled:
                m = rx.match(source, pos)
                if m:
                    best_match = m
                    best_type = tt
                    break  # first-match wins (patterns are priority-ordered)

            if best_match:
                val = best_match.group()
                tokens.append(Token(type=best_type, value=val, start=pos, end=pos + len(val)))
                pos += len(val)
            else:
                # Single-character fallback
                tokens.append(Token(type=TokenType.UNKNOWN, value=source[pos], start=pos, end=pos + 1))
                pos += 1

        return tokens

    # ------------------------------------------------------------------
    # Highlight (ANSI terminal)
    # ------------------------------------------------------------------

    def highlight(self, source: str) -> str:
        """Return *source* highlighted with ANSI 24-bit colour codes.

        This is the original stub method, preserved for backward compatibility.
        """
        tokens = self.tokenize(source)
        parts: List[str] = []
        colors = self._theme.colors
        for tok in tokens:
            if tok.type in (TokenType.WHITESPACE, TokenType.NEWLINE):
                parts.append(tok.value)
            else:
                ansi = _hex_to_ansi(colors.get(tok.type, self._theme.foreground))
                parts.append(f"{ansi}{tok.value}{_ANSI_RESET}")
        return "".join(parts)

    # ------------------------------------------------------------------
    # Highlight (HTML)
    # ------------------------------------------------------------------

    @staticmethod
    def _html_escape(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    def highlight_html(self, source: str) -> str:
        """Return *source* as an HTML string with inline ``color`` styles.

        Each token is wrapped in ``<span style="color:#HEX">...</span>``.
        The result is wrapped in a ``<pre><code>`` block with the theme
        background/foreground applied.
        """
        tokens = self.tokenize(source)
        colors = self._theme.colors
        parts: List[str] = []
        parts.append(
            f'<pre style="background:{self._theme.background};color:{self._theme.foreground};'
            f'padding:1em;border-radius:4px;overflow-x:auto;font-family:monospace">'
            f"<code>"
        )
        for tok in tokens:
            escaped = self._html_escape(tok.value)
            if tok.type in (TokenType.WHITESPACE, TokenType.NEWLINE):
                parts.append(escaped)
            else:
                color = colors.get(tok.type, self._theme.foreground)
                css_class = tok.type.name.lower()
                parts.append(f'<span class="tok-{css_class}" style="color:{color}">{escaped}</span>')
        parts.append("</code></pre>")
        return "".join(parts)
