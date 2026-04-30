"""Security analysis tools for EoStudio devtools."""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional


class Severity(Enum):
    """Severity levels for vulnerabilities."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class VulnerabilityType(Enum):
    """Types of vulnerabilities."""

    DEPENDENCY = "dependency"
    CODE_PATTERN = "code_pattern"
    SECRET_LEAK = "secret_leak"
    LICENSE = "license"
    CONFIGURATION = "configuration"


@dataclass
class Vulnerability:
    """Represents a single vulnerability finding."""

    id: str
    type: VulnerabilityType
    severity: Severity
    title: str
    description: str
    file: str
    line: int
    cwe: Optional[str] = None
    fix_suggestion: str = ""
    references: List[str] = field(default_factory=list)


@dataclass
class ScanResult:
    """Result of a security scan."""

    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    scanned_files: int = 0
    scan_duration_ms: int = 0
    timestamp: str = ""


@dataclass
class LicenseInfo:
    """License information for a dependency."""

    name: str
    spdx_id: str
    compatible: bool
    file: str


# Regex patterns for code scanning (OWASP Top 10)
_SQL_INJECTION_PATTERNS = [
    re.compile(r"""(?:execute|cursor\.execute)\s*\(\s*(?:f['"]|['"].*%s|['"].*\.format)""", re.IGNORECASE),
    re.compile(r"""(?:query|sql)\s*=\s*(?:f['"]|['"].*%s|['"].*\.format|['"].*\+)""", re.IGNORECASE),
]

_XSS_PATTERNS = [
    re.compile(r"""\.innerHTML\s*="""),
    re.compile(r"""dangerouslySetInnerHTML"""),
    re.compile(r"""document\.write\s*\("""),
]

_COMMAND_INJECTION_PATTERNS = [
    re.compile(r"""os\.system\s*\("""),
    re.compile(r"""subprocess\.\w+\s*\(.*shell\s*=\s*True""", re.DOTALL),
    re.compile(r"""os\.popen\s*\("""),
]

_PATH_TRAVERSAL_PATTERNS = [
    re.compile(r"""open\s*\(.*\+.*\)"""),
    re.compile(r"""os\.path\.join\s*\(.*request""", re.IGNORECASE),
    re.compile(r"""\.\.\/"""),
]

_HARDCODED_CREDS_PATTERNS = [
    re.compile(r"""(?:password|passwd|pwd)\s*=\s*['"][^'"]+['"]""", re.IGNORECASE),
    re.compile(r"""(?:secret|api_key|apikey|access_key)\s*=\s*['"][^'"]+['"]""", re.IGNORECASE),
    re.compile(r"""(?:token|auth_token)\s*=\s*['"][A-Za-z0-9+/=_-]{16,}['"]""", re.IGNORECASE),
]

_INSECURE_DESERIALIZATION_PATTERNS = [
    re.compile(r"""pickle\.loads?\s*\("""),
    re.compile(r"""yaml\.load\s*\((?!.*Loader\s*=\s*yaml\.SafeLoader)"""),
    re.compile(r"""marshal\.loads?\s*\("""),
]

_SSRF_PATTERNS = [
    re.compile(r"""requests\.(?:get|post|put|delete|patch)\s*\(.*(?:request\.|user_input|params)""", re.IGNORECASE),
    re.compile(r"""urllib\.request\.urlopen\s*\(.*(?:request\.|user_input)""", re.IGNORECASE),
]

_WEAK_CRYPTO_PATTERNS = [
    re.compile(r"""hashlib\.(?:md5|sha1)\s*\("""),
    re.compile(r"""MD5\s*\("""),
    re.compile(r"""SHA1\s*\("""),
]

# Secret detection patterns
_SECRET_PATTERNS = [
    (re.compile(r"""AKIA[0-9A-Z]{16}"""), "AWS Access Key", Severity.CRITICAL),
    (re.compile(r"""ghp_[A-Za-z0-9_]{36}"""), "GitHub Personal Access Token", Severity.CRITICAL),
    (re.compile(r"""gho_[A-Za-z0-9_]{36}"""), "GitHub OAuth Token", Severity.CRITICAL),
    (re.compile(r"""ghu_[A-Za-z0-9_]{36}"""), "GitHub User Token", Severity.CRITICAL),
    (re.compile(r"""ghs_[A-Za-z0-9_]{36}"""), "GitHub Server Token", Severity.CRITICAL),
    (re.compile(r"""ghr_[A-Za-z0-9_]{36}"""), "GitHub Refresh Token", Severity.CRITICAL),
    (re.compile(r"""xoxb-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24}"""), "Slack Bot Token", Severity.CRITICAL),
    (re.compile(r"""xoxp-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24}"""), "Slack User Token", Severity.CRITICAL),
    (re.compile(r"""sk-[A-Za-z0-9]{48}"""), "OpenAI API Key", Severity.CRITICAL),
    (re.compile(r"""-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----"""), "Private Key", Severity.CRITICAL),
    (re.compile(r"""(?:api[_-]?key|apikey)\s*[:=]\s*['"]?[A-Za-z0-9_\-]{20,}""", re.IGNORECASE), "Generic API Key", Severity.HIGH),
    (re.compile(r"""(?:password|passwd|pwd)\s*[:=]\s*['"]?[^\s'"]{8,}""", re.IGNORECASE), "Hardcoded Password", Severity.HIGH),
]

_SCANNABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
    ".rb", ".php", ".c", ".cpp", ".h", ".hpp", ".cs", ".swift",
    ".kt", ".scala", ".sh", ".bash", ".yaml", ".yml", ".toml",
    ".json", ".xml", ".env", ".cfg", ".ini", ".conf",
}

_INCOMPATIBLE_LICENSES = {
    "AGPL-3.0-only", "AGPL-3.0-or-later", "GPL-3.0-only",
    "GPL-3.0-or-later", "SSPL-1.0", "EUPL-1.2",
}


class SecurityScanner:
    """Security scanner for detecting vulnerabilities in projects."""

    def __init__(self, workspace_path: str = ".") -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self._vuln_counter = 0

    def _next_id(self) -> str:
        self._vuln_counter += 1
        return f"VULN-{self._vuln_counter:04d}"

    def _iter_source_files(self):
        """Yield source files in the workspace."""
        for root, dirs, files in os.walk(self.workspace_path):
            dirs[:] = [
                d for d in dirs
                if d not in {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".tox"}
            ]
            for fname in files:
                fpath = Path(root) / fname
                if fpath.suffix in _SCANNABLE_EXTENSIONS:
                    yield fpath

    def _run_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.workspace_path),
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="command not found or timed out")

    def scan_dependencies(self) -> ScanResult:
        """Scan dependencies for known vulnerabilities using package audit tools."""
        start = time.monotonic_ns()
        vulns: List[Vulnerability] = []
        scanned = 0

        # pip audit
        if (self.workspace_path / "requirements.txt").exists() or (self.workspace_path / "setup.py").exists():
            scanned += 1
            result = self._run_command(["pip", "audit", "--format", "json"])
            if result.returncode != 0 and result.stdout:
                try:
                    data = json.loads(result.stdout)
                    for entry in data.get("vulnerabilities", []):
                        vulns.append(Vulnerability(
                            id=self._next_id(),
                            type=VulnerabilityType.DEPENDENCY,
                            severity=Severity.HIGH,
                            title=f"Vulnerable dependency: {entry.get('name', 'unknown')}",
                            description=entry.get("description", ""),
                            file="requirements.txt",
                            line=0,
                            cwe=entry.get("aliases", [None])[0] if entry.get("aliases") else None,
                            fix_suggestion=f"Upgrade {entry.get('name')} to {entry.get('fix_versions', ['latest'])[0]}",
                            references=entry.get("references", []),
                        ))
                except (json.JSONDecodeError, KeyError):
                    pass

        # npm audit
        if (self.workspace_path / "package.json").exists():
            scanned += 1
            result = self._run_command(["npm", "audit", "--json"])
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    for name, advisory in data.get("vulnerabilities", {}).items():
                        severity_map = {"critical": Severity.CRITICAL, "high": Severity.HIGH, "moderate": Severity.MEDIUM, "low": Severity.LOW}
                        vulns.append(Vulnerability(
                            id=self._next_id(),
                            type=VulnerabilityType.DEPENDENCY,
                            severity=severity_map.get(advisory.get("severity", "high"), Severity.HIGH),
                            title=f"Vulnerable dependency: {name}",
                            description=advisory.get("title", ""),
                            file="package.json",
                            line=0,
                            fix_suggestion=advisory.get("fixAvailable", {}).get("name", "Update dependency"),
                            references=[advisory.get("url", "")],
                        ))
                except (json.JSONDecodeError, KeyError):
                    pass

        # cargo audit
        if (self.workspace_path / "Cargo.toml").exists():
            scanned += 1
            result = self._run_command(["cargo", "audit", "--json"])
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    for vuln_entry in data.get("vulnerabilities", {}).get("list", []):
                        advisory = vuln_entry.get("advisory", {})
                        vulns.append(Vulnerability(
                            id=self._next_id(),
                            type=VulnerabilityType.DEPENDENCY,
                            severity=Severity.HIGH,
                            title=f"Vulnerable crate: {advisory.get('package', 'unknown')}",
                            description=advisory.get("title", ""),
                            file="Cargo.toml",
                            line=0,
                            cwe=advisory.get("id"),
                            fix_suggestion=f"Update {advisory.get('package', '')} to a patched version",
                            references=[advisory.get("url", "")],
                        ))
                except (json.JSONDecodeError, KeyError):
                    pass

        elapsed = (time.monotonic_ns() - start) // 1_000_000
        return ScanResult(
            vulnerabilities=vulns,
            scanned_files=scanned,
            scan_duration_ms=elapsed,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

    def scan_code(self) -> ScanResult:
        """Regex-based SAST scan for OWASP Top 10 patterns."""
        start = time.monotonic_ns()
        vulns: List[Vulnerability] = []
        scanned = 0

        patterns_map = [
            (_SQL_INJECTION_PATTERNS, "SQL Injection", "Potential SQL injection via string formatting",
             "CWE-89", "Use parameterized queries instead of string formatting"),
            (_XSS_PATTERNS, "Cross-Site Scripting (XSS)", "Potential XSS via unsafe DOM manipulation",
             "CWE-79", "Use safe rendering methods; sanitize user input before inserting into DOM"),
            (_COMMAND_INJECTION_PATTERNS, "Command Injection", "Potential command injection via shell execution",
             "CWE-78", "Use subprocess with a list of arguments instead of shell=True; avoid os.system"),
            (_PATH_TRAVERSAL_PATTERNS, "Path Traversal", "Potential path traversal vulnerability",
             "CWE-22", "Validate and sanitize file paths; use os.path.realpath and check against allowed directories"),
            (_HARDCODED_CREDS_PATTERNS, "Hardcoded Credentials", "Hardcoded credentials detected in source code",
             "CWE-798", "Move credentials to environment variables or a secrets manager"),
            (_INSECURE_DESERIALIZATION_PATTERNS, "Insecure Deserialization", "Unsafe deserialization detected",
             "CWE-502", "Use safe deserialization methods (e.g., yaml.safe_load, json.loads)"),
            (_SSRF_PATTERNS, "Server-Side Request Forgery (SSRF)", "Potential SSRF via user-controlled URL",
             "CWE-918", "Validate and whitelist URLs before making server-side requests"),
            (_WEAK_CRYPTO_PATTERNS, "Weak Cryptography", "Weak hash algorithm used (MD5/SHA1)",
             "CWE-327", "Use SHA-256 or stronger hashing; for passwords use bcrypt, scrypt, or argon2"),
        ]

        for fpath in self._iter_source_files():
            scanned += 1
            try:
                content = fpath.read_text(errors="replace")
            except OSError:
                continue

            rel_path = str(fpath.relative_to(self.workspace_path))
            lines = content.splitlines()

            for line_num, line in enumerate(lines, start=1):
                for regexes, title, desc, cwe, fix in patterns_map:
                    for regex in regexes:
                        if regex.search(line):
                            vulns.append(Vulnerability(
                                id=self._next_id(),
                                type=VulnerabilityType.CODE_PATTERN,
                                severity=Severity.HIGH if "injection" in title.lower() or "XSS" in title else Severity.MEDIUM,
                                title=title,
                                description=desc,
                                file=rel_path,
                                line=line_num,
                                cwe=cwe,
                                fix_suggestion=fix,
                            ))
                            break  # one match per pattern group per line

        elapsed = (time.monotonic_ns() - start) // 1_000_000
        return ScanResult(
            vulnerabilities=vulns,
            scanned_files=scanned,
            scan_duration_ms=elapsed,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

    def scan_secrets(self) -> ScanResult:
        """Detect leaked secrets in source code and config files."""
        start = time.monotonic_ns()
        vulns: List[Vulnerability] = []
        scanned = 0

        for fpath in self._iter_source_files():
            scanned += 1
            try:
                content = fpath.read_text(errors="replace")
            except OSError:
                continue

            rel_path = str(fpath.relative_to(self.workspace_path))
            lines = content.splitlines()

            for line_num, line in enumerate(lines, start=1):
                for regex, secret_type, severity in _SECRET_PATTERNS:
                    if regex.search(line):
                        vulns.append(Vulnerability(
                            id=self._next_id(),
                            type=VulnerabilityType.SECRET_LEAK,
                            severity=severity,
                            title=f"Leaked secret: {secret_type}",
                            description=f"{secret_type} detected in source code",
                            file=rel_path,
                            line=line_num,
                            cwe="CWE-798",
                            fix_suggestion="Remove the secret from source code and rotate it immediately. Use environment variables or a secrets manager.",
                        ))

        elapsed = (time.monotonic_ns() - start) // 1_000_000
        return ScanResult(
            vulnerabilities=vulns,
            scanned_files=scanned,
            scan_duration_ms=elapsed,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

    def check_licenses(self) -> List[LicenseInfo]:
        """Check dependency licenses for compatibility."""
        licenses: List[LicenseInfo] = []

        # Check Python packages
        result = self._run_command(["pip", "list", "--format", "json"])
        if result.returncode == 0 and result.stdout:
            try:
                packages = json.loads(result.stdout)
                for pkg in packages:
                    name = pkg.get("name", "")
                    meta_result = self._run_command(["pip", "show", name])
                    if meta_result.returncode == 0:
                        license_name = ""
                        for meta_line in meta_result.stdout.splitlines():
                            if meta_line.startswith("License:"):
                                license_name = meta_line.split(":", 1)[1].strip()
                                break
                        spdx = license_name if license_name else "UNKNOWN"
                        licenses.append(LicenseInfo(
                            name=name,
                            spdx_id=spdx,
                            compatible=spdx not in _INCOMPATIBLE_LICENSES,
                            file="requirements.txt",
                        ))
            except (json.JSONDecodeError, KeyError):
                pass

        # Check package.json licenses
        pkg_json_path = self.workspace_path / "package.json"
        if pkg_json_path.exists():
            node_modules = self.workspace_path / "node_modules"
            if node_modules.exists():
                for pkg_dir in node_modules.iterdir():
                    if pkg_dir.is_dir() and not pkg_dir.name.startswith("."):
                        pkg_file = pkg_dir / "package.json"
                        if pkg_file.exists():
                            try:
                                data = json.loads(pkg_file.read_text(errors="replace"))
                                spdx = data.get("license", "UNKNOWN")
                                licenses.append(LicenseInfo(
                                    name=data.get("name", pkg_dir.name),
                                    spdx_id=spdx if isinstance(spdx, str) else "UNKNOWN",
                                    compatible=spdx not in _INCOMPATIBLE_LICENSES if isinstance(spdx, str) else True,
                                    file=str(pkg_file.relative_to(self.workspace_path)),
                                ))
                            except (json.JSONDecodeError, OSError):
                                pass

        return licenses

    def generate_sbom(self) -> Dict:
        """Generate a Software Bill of Materials in CycloneDX format."""
        components: List[Dict] = []

        # Python dependencies
        result = self._run_command(["pip", "list", "--format", "json"])
        if result.returncode == 0 and result.stdout:
            try:
                for pkg in json.loads(result.stdout):
                    components.append({
                        "type": "library",
                        "name": pkg.get("name", ""),
                        "version": pkg.get("version", ""),
                        "purl": f"pkg:pypi/{pkg.get('name', '')}@{pkg.get('version', '')}",
                    })
            except json.JSONDecodeError:
                pass

        # Node dependencies
        pkg_json_path = self.workspace_path / "package.json"
        if pkg_json_path.exists():
            try:
                data = json.loads(pkg_json_path.read_text(errors="replace"))
                for dep, version in {**data.get("dependencies", {}), **data.get("devDependencies", {})}.items():
                    clean_version = version.lstrip("^~>=<")
                    components.append({
                        "type": "library",
                        "name": dep,
                        "version": clean_version,
                        "purl": f"pkg:npm/{dep}@{clean_version}",
                    })
            except (json.JSONDecodeError, OSError):
                pass

        # Rust dependencies
        cargo_lock = self.workspace_path / "Cargo.lock"
        if cargo_lock.exists():
            try:
                content = cargo_lock.read_text(errors="replace")
                current_pkg: Dict = {}
                for raw_line in content.splitlines():
                    stripped = raw_line.strip()
                    if stripped == "[[package]]":
                        if current_pkg.get("name"):
                            components.append({
                                "type": "library",
                                "name": current_pkg["name"],
                                "version": current_pkg.get("version", ""),
                                "purl": f"pkg:cargo/{current_pkg['name']}@{current_pkg.get('version', '')}",
                            })
                        current_pkg = {}
                    elif stripped.startswith("name = "):
                        current_pkg["name"] = stripped.split('"')[1]
                    elif stripped.startswith("version = "):
                        current_pkg["version"] = stripped.split('"')[1]
                if current_pkg.get("name"):
                    components.append({
                        "type": "library",
                        "name": current_pkg["name"],
                        "version": current_pkg.get("version", ""),
                        "purl": f"pkg:cargo/{current_pkg['name']}@{current_pkg.get('version', '')}",
                    })
            except OSError:
                pass

        return {
            "bomFormat": "CycloneDX",
            "specVersion": "1.5",
            "version": 1,
            "metadata": {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "tools": [{"vendor": "EoStudio", "name": "security-scanner", "version": "1.0.0"}],
            },
            "components": components,
        }

    def generate_report(self, result: ScanResult, format: str = "json") -> str:
        """Generate a report from scan results in the specified format."""
        vulns_data = [
            {
                "id": v.id,
                "type": v.type.value,
                "severity": v.severity.value,
                "title": v.title,
                "description": v.description,
                "file": v.file,
                "line": v.line,
                "cwe": v.cwe,
                "fix_suggestion": v.fix_suggestion,
                "references": v.references,
            }
            for v in result.vulnerabilities
        ]

        report_data = {
            "summary": {
                "total_vulnerabilities": len(result.vulnerabilities),
                "critical": sum(1 for v in result.vulnerabilities if v.severity == Severity.CRITICAL),
                "high": sum(1 for v in result.vulnerabilities if v.severity == Severity.HIGH),
                "medium": sum(1 for v in result.vulnerabilities if v.severity == Severity.MEDIUM),
                "low": sum(1 for v in result.vulnerabilities if v.severity == Severity.LOW),
                "info": sum(1 for v in result.vulnerabilities if v.severity == Severity.INFO),
                "scanned_files": result.scanned_files,
                "scan_duration_ms": result.scan_duration_ms,
                "timestamp": result.timestamp,
            },
            "vulnerabilities": vulns_data,
        }

        if format == "json":
            return json.dumps(report_data, indent=2)

        if format == "markdown":
            lines = [
                "# Security Scan Report",
                "",
                f"**Timestamp:** {result.timestamp}",
                f"**Files scanned:** {result.scanned_files}",
                f"**Duration:** {result.scan_duration_ms}ms",
                "",
                "## Summary",
                "",
                "| Severity | Count |",
                "|----------|-------|",
                f"| Critical | {report_data['summary']['critical']} |",
                f"| High     | {report_data['summary']['high']} |",
                f"| Medium   | {report_data['summary']['medium']} |",
                f"| Low      | {report_data['summary']['low']} |",
                f"| Info     | {report_data['summary']['info']} |",
                "",
                "## Vulnerabilities",
                "",
            ]
            for v in result.vulnerabilities:
                lines.append(f"### [{v.severity.value.upper()}] {v.title}")
                lines.append(f"- **ID:** {v.id}")
                lines.append(f"- **File:** `{v.file}:{v.line}`")
                lines.append(f"- **Type:** {v.type.value}")
                if v.cwe:
                    lines.append(f"- **CWE:** {v.cwe}")
                lines.append(f"- **Description:** {v.description}")
                if v.fix_suggestion:
                    lines.append(f"- **Fix:** {v.fix_suggestion}")
                lines.append("")
            return "\n".join(lines)

        if format == "html":
            rows = ""
            for v in result.vulnerabilities:
                color = {"critical": "#dc3545", "high": "#fd7e14", "medium": "#ffc107", "low": "#28a745", "info": "#17a2b8"}
                badge_color = color.get(v.severity.value, "#6c757d")
                rows += (
                    f"<tr>"
                    f"<td>{v.id}</td>"
                    f"<td><span style='color:{badge_color};font-weight:bold'>{v.severity.value.upper()}</span></td>"
                    f"<td>{v.title}</td>"
                    f"<td><code>{v.file}:{v.line}</code></td>"
                    f"<td>{v.description}</td>"
                    f"<td>{v.fix_suggestion}</td>"
                    f"</tr>"
                )
            return (
                "<!DOCTYPE html><html><head><title>Security Report</title>"
                "<style>body{font-family:sans-serif;margin:20px}table{border-collapse:collapse;width:100%}"
                "th,td{border:1px solid #ddd;padding:8px;text-align:left}th{background:#f4f4f4}</style></head>"
                f"<body><h1>Security Scan Report</h1>"
                f"<p>Timestamp: {result.timestamp} | Files: {result.scanned_files} | Duration: {result.scan_duration_ms}ms</p>"
                f"<table><tr><th>ID</th><th>Severity</th><th>Title</th><th>Location</th><th>Description</th><th>Fix</th></tr>"
                f"{rows}</table></body></html>"
            )

        return json.dumps(report_data, indent=2)

    def scan_all(self) -> ScanResult:
        """Run all scans and merge results."""
        start = time.monotonic_ns()
        all_vulns: List[Vulnerability] = []
        total_files = 0

        for scan_fn in (self.scan_dependencies, self.scan_code, self.scan_secrets):
            result = scan_fn()
            all_vulns.extend(result.vulnerabilities)
            total_files += result.scanned_files

        elapsed = (time.monotonic_ns() - start) // 1_000_000
        return ScanResult(
            vulnerabilities=all_vulns,
            scanned_files=total_files,
            scan_duration_ms=elapsed,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

    def get_fix_suggestions(self, vuln: Vulnerability) -> List[str]:
        """Get fix suggestions for a vulnerability."""
        suggestions: List[str] = []

        if vuln.fix_suggestion:
            suggestions.append(vuln.fix_suggestion)

        fix_map = {
            "CWE-89": [
                "Use parameterized queries (e.g., cursor.execute('SELECT * FROM t WHERE id = ?', (id,)))",
                "Use an ORM like SQLAlchemy or Django ORM to avoid raw SQL",
            ],
            "CWE-79": [
                "Use textContent instead of innerHTML for plain text",
                "Sanitize HTML with a library like DOMPurify before insertion",
                "Use a templating engine with auto-escaping",
            ],
            "CWE-78": [
                "Use subprocess.run() with a list of arguments: subprocess.run(['cmd', 'arg1', 'arg2'])",
                "Avoid os.system() entirely; use subprocess with shell=False",
                "Use shlex.quote() if shell execution is unavoidable",
            ],
            "CWE-22": [
                "Use os.path.realpath() and verify the resolved path is within the allowed directory",
                "Reject paths containing '..' segments",
                "Use pathlib.Path.resolve() and check with is_relative_to()",
            ],
            "CWE-798": [
                "Move secrets to environment variables: os.environ.get('SECRET_KEY')",
                "Use a secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)",
                "Use a .env file (excluded from version control) with python-dotenv",
            ],
            "CWE-502": [
                "Use json.loads() instead of pickle.loads() when possible",
                "Use yaml.safe_load() instead of yaml.load()",
                "Validate and sanitize data before deserialization",
            ],
            "CWE-918": [
                "Validate URLs against an allowlist of permitted domains",
                "Block requests to internal/private IP ranges (10.x, 172.16.x, 192.168.x, 127.x)",
                "Use a URL parser to validate the scheme and host before making requests",
            ],
            "CWE-327": [
                "Use hashlib.sha256() or hashlib.sha3_256() for general hashing",
                "For passwords, use bcrypt, scrypt, or argon2",
                "Never use MD5 or SHA1 for security-sensitive operations",
            ],
        }

        if vuln.cwe and vuln.cwe in fix_map:
            suggestions.extend(fix_map[vuln.cwe])

        if vuln.type == VulnerabilityType.SECRET_LEAK:
            suggestions.extend([
                "Rotate the compromised secret immediately",
                "Add the file to .gitignore if it contains secrets",
                "Use git-filter-branch or BFG to remove secrets from git history",
                "Set up pre-commit hooks to prevent future secret leaks",
            ])

        if vuln.type == VulnerabilityType.DEPENDENCY:
            suggestions.extend([
                "Run dependency update commands (pip install --upgrade, npm update)",
                "Pin dependencies to specific versions in your lock file",
                "Set up automated dependency update tools (Dependabot, Renovate)",
            ])

        return suggestions
