"""Regression tests for the security hardening scanner."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

from eostudio.core.security.hardening import SecurityScanner


def test_pip_audit_findings_are_reported_on_nonzero_exit(tmp_path):
    """pip-audit exits nonzero when it reports vulnerabilities."""
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("demo==1.0\n", encoding="utf-8")
    output = {
        "dependencies": [
            {
                "name": "demo",
                "version": "1.0",
                "vulns": [
                    {
                        "id": "CVE-2026-1234",
                        "description": "A known vulnerability.",
                        "fix_versions": ["1.1"],
                    }
                ],
            }
        ]
    }
    completed = subprocess.CompletedProcess(
        args=["pip-audit"],
        returncode=1,
        stdout=json.dumps(output),
        stderr="Found 1 known vulnerability",
    )

    with patch("eostudio.core.security.hardening.subprocess.run", return_value=completed):
        vulnerabilities = SecurityScanner().scan_dependencies(str(tmp_path))

    assert len(vulnerabilities) == 1
    assert vulnerabilities[0].id == "CVE-2026-1234"
    assert vulnerabilities[0].recommendation == "Upgrade to 1.1"


def test_pip_audit_empty_fix_versions_falls_back_to_latest(tmp_path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("demo==1.0\n", encoding="utf-8")
    output = {
        "dependencies": [
            {
                "name": "demo",
                "version": "1.0",
                "vulns": [{"id": "CVE-2026-1234", "fix_versions": []}],
            }
        ]
    }
    completed = subprocess.CompletedProcess(
        args=["pip-audit"],
        returncode=1,
        stdout=json.dumps(output),
        stderr="Found 1 known vulnerability",
    )

    with patch("eostudio.core.security.hardening.subprocess.run", return_value=completed):
        vulnerabilities = SecurityScanner().scan_dependencies(str(tmp_path))

    assert vulnerabilities[0].recommendation == "Upgrade to latest"
