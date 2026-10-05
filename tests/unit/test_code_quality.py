# SPDX-License-Identifier: MIT
"""Unit tests for eostudio.core.ai.code_quality — the TS/React quality checker.

Pure-logic module (regex checks + auto-fixes); no fixtures needed.
Covers every check method, the auto-fixers, project aggregation, and summary.
Contributes to the #36 coverage ratchet.
"""

import pytest
from eostudio.core.ai.code_quality import CodeQualityChecker, QualityIssue


@pytest.fixture
def checker():
    return CodeQualityChecker()


class TestQualityIssue:
    def test_to_dict(self):
        issue = QualityIssue(
            file="a.ts",
            line=3,
            severity="warning",
            category="types",
            message="msg",
            auto_fixable=True,
        )
        assert issue.to_dict() == {
            "file": "a.ts",
            "line": 3,
            "severity": "warning",
            "category": "types",
            "message": "msg",
            "auto_fixable": True,
        }


class TestCheckFile:
    def test_non_ts_file_returns_empty(self, checker):
        assert checker.check_file("main.py", "import os\n") == []
        assert checker.check_file("style.css", "body {}") == []

    def test_jsx_and_js_also_checked(self, checker):
        issues = checker.check_file("a.js", "const x: any = 1;\n")
        assert any(i.category == "types" for i in issues)


class TestErrorHandling:
    def test_fetch_without_catch_warns(self, checker):
        code = "const r = await fetch('/api');\nconsole.log(r);\n"
        issues = checker.check_file("a.ts", code)
        assert any(
            i.message.startswith("API call without error handling") for i in issues
        )

    def test_fetch_with_catch_ok(self, checker):
        code = "try {\n  const r = await fetch('/api');\n} catch (e) {}\n"
        # empty catch still flags, but the API-call warning must be gone
        issues = checker.check_file("a.ts", code)
        assert not any("API call without error handling" in i.message for i in issues)

    def test_empty_catch_is_error_and_fixable(self, checker):
        issues = checker.check_file("a.ts", "try {\n x();\n} catch (e) {}\n")
        empty = [i for i in issues if "Empty catch block" in i.message]
        assert len(empty) == 1
        assert empty[0].severity == "error"
        assert empty[0].auto_fixable

    def test_async_without_try_warns(self, checker):
        issues = checker.check_file("a.ts", "async function load() {\n return 1;\n}\n")
        assert any("Async function without try-catch" in i.message for i in issues)

    def test_async_with_try_ok(self, checker):
        code = "async function load() {\n try {\n return 1;\n } catch (e) {}\n}\n"
        issues = checker.check_file("a.ts", code)
        assert not any("Async function without try-catch" in i.message for i in issues)


class TestTypescriptTypes:
    def test_explicit_any_warns(self, checker):
        issues = checker.check_file("a.ts", "const x: any = 1;\n")
        assert any(i.category == "types" and i.severity == "warning" for i in issues)

    def test_eslint_disable_suppresses(self, checker):
        issues = checker.check_file(
            "a.ts", "const x: any = 1; // eslint-disable-line\n"
        )
        assert not any(i.category == "types" for i in issues)

    def test_as_any_warns(self, checker):
        issues = checker.check_file("a.ts", "const y = x as any;\n")
        assert any("as any" in i.message for i in issues)


class TestAccessibility:
    def test_non_tsx_skipped(self, checker):
        assert checker._check_accessibility("a.ts", "<img src='x'>") == []

    def test_img_without_alt_errors(self, checker):
        issues = checker.check_file("a.tsx", "<img src='x' />\n")
        img = [i for i in issues if "alt attribute" in i.message]
        assert len(img) == 1 and img[0].severity == "error"
        assert img[0].auto_fixable

    def test_img_with_alt_ok(self, checker):
        assert checker.check_file("a.tsx", "<img src='x' alt='y' />\n") == []

    def test_onclick_div_without_role_warns(self, checker):
        issues = checker.check_file(
            "a.tsx", "<div className='b' onClick={go}>x</div>\n"
        )
        assert any("onClick on non-interactive" in i.message for i in issues)

    def test_onclick_div_with_role_ok(self, checker):
        issues = checker.check_file(
            "a.tsx", "<div role='button' onClick={go}>x</div>\n"
        )
        assert not any("onClick on non-interactive" in i.message for i in issues)

    def test_input_without_label_warns(self, checker):
        issues = checker.check_file("a.tsx", "<input type='text' />\n")
        assert any("without aria-label" in i.message for i in issues)

    def test_input_with_id_ok(self, checker):
        assert checker.check_file("a.tsx", "<input id='n' type='text' />\n") == []


class TestHardcodedStrings:
    def test_hardcoded_url_info(self, checker):
        issues = checker.check_file("a.ts", "const u = 'https://api.x.com/v1';\n")
        url = [i for i in issues if "Hardcoded URL" in i.message]
        assert len(url) == 1 and url[0].severity == "info"

    def test_localhost_ok(self, checker):
        assert checker.check_file("a.ts", "const u = 'http://localhost:3000';\n") == []

    def test_comment_url_ok(self, checker):
        assert checker.check_file("a.ts", "// see https://docs.x.com\n") == []

    def test_hardcoded_secret_errors(self, checker):
        issues = checker.check_file("a.ts", "const api_key = 'sk-live-1234567890';\n")
        sec = [i for i in issues if "hardcoded secret" in i.message]
        assert len(sec) == 1 and sec[0].severity == "error"


class TestUnusedImports:
    def test_unused_import_warns(self, checker):
        code = "import { foo, bar } from './x';\nconsole.log(foo);\n"
        issues = checker.check_file("a.ts", code)
        unused = [i for i in issues if "Unused import: bar" in i.message]
        assert len(unused) == 1
        assert unused[0].auto_fixable

    def test_used_import_ok(self, checker):
        code = "import { foo } from './x';\nconsole.log(foo);\n"
        assert checker.check_file("a.ts", code) == []

    def test_react_import_skipped(self, checker):
        code = "import React from 'react';\nconst x = 1;\n"
        issues = checker.check_file("a.tsx", code)
        assert not any("Unused import: React" in i.message for i in issues)

    def test_empty_named_import_ok(self, checker):
        code = "import {} from './x';\nconst x = 1;\n"
        assert checker.check_file("a.ts", code) == []


class TestCheckProject:
    def test_only_files_with_issues_reported(self, checker):
        results = checker.check_project(
            {
                "clean.ts": "const x: number = 1;\n",
                "dirty.ts": "const y: any = 2;\n",
                "notes.md": "const z: any = 3;\n",
            }
        )
        assert set(results) == {"dirty.ts"}


class TestAutoFix:
    def test_console_log_removed_error_kept(self, checker):
        code = "console.log('debug');\nconsole.error('bad');\n"
        fixed = checker.auto_fix("a.ts", code)
        assert "console.log" not in fixed
        assert "console.error('bad');" in fixed

    def test_use_client_added_for_tsx_hooks(self, checker):
        code = "import { useState } from 'react';\nconst x = useState(0);\n"
        fixed = checker.auto_fix("a.tsx", code)
        assert fixed.startswith('"use client";')

    def test_use_client_not_added_when_present(self, checker):
        code = '"use client";\nconst x = useState(0);\n'
        assert checker.auto_fix("a.tsx", code) == code

    def test_use_client_not_added_for_ts(self, checker):
        code = "const x = useState(0);\n"
        assert checker.auto_fix("a.ts", code) == code

    def test_key_prop_added(self, checker):
        code = "items.map((item) => (<li >{item.name}</li>))\n"
        fixed = checker.auto_fix("a.tsx", code)
        assert "key={item.id}" in fixed

    def test_return_type_added(self, checker):
        code = "export function Card(props) {\n return null;\n}\n"
        fixed = checker.auto_fix("a.tsx", code)
        assert "): JSX.Element {" in fixed

    def test_existing_return_type_untouched(self, checker):
        code = "export function Card(props): JSX.Element {\n return null;\n}\n"
        assert checker.auto_fix("a.tsx", code) == code

    def test_non_ts_unchanged(self, checker):
        code = "console.log('x');\n"
        assert checker.auto_fix("a.py", code) == code


class TestSummary:
    def test_summary_math(self, checker):
        issues = {
            "a.ts": [
                QualityIssue("a.ts", 1, "error", "hardcoded", "m", True),
                QualityIssue("a.ts", 2, "warning", "types", "m", False),
            ],
            "b.ts": [
                QualityIssue("b.ts", 1, "warning", "unused", "m", True),
            ],
        }
        s = checker.summary(issues)
        assert s["total_issues"] == 3
        assert s["by_severity"] == {"error": 1, "warning": 2, "info": 0}
        assert s["by_category"] == {"hardcoded": 1, "types": 1, "unused": 1}
        assert s["auto_fixable"] == 2
        assert s["quality_score"] == 100 - 10 - 2 * 3
        assert s["files_with_issues"] == 2

    def test_empty_summary(self, checker):
        s = checker.summary({})
        assert s["total_issues"] == 0
        assert s["quality_score"] == 100
