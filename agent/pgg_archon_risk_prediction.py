"""
PGG Archon — RiskPredictionSurface/v1

Source: APEX-AGI omega_pipeline/super_agi_predictor.py
Absorbed: 2026-05-28

Purpose: Pre-execution safety pre-check before core modification,
         external code absorption, or auto-fix. Scans file content
         for vulnerability patterns and produces a structured risk report.

NOT:
  - Running background monitoring/daemons
  - Claiming "0 vulnerabilities" or "totally safe"
  - Autonomously blocking execution (output is advisory)
"""

from __future__ import annotations
import re
import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime
from enum import Enum


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class VulnerabilityType(Enum):
    SQL_INJECTION = "SQL Injection"
    COMMAND_INJECTION = "Command Injection"
    PATH_TRAVERSAL = "Path Traversal"
    HARDCODED_SECRETS = "Hardcoded Secrets"
    XSS = "Cross-Site Scripting"
    INSECURE_DESERIALIZATION = "Insecure Deserialization"
    SSRF = "Server-Side Request Forgery"
    RCE = "Remote Code Execution"


@dataclass
class RiskPrediction:
    """Single vulnerability prediction."""
    file_path: str
    line_number: int
    column: int
    vulnerability_type: str
    severity: str
    confidence: float
    description: str
    suggested_fix: str
    cwe_id: str
    cvss_score: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RiskReport:
    """Pre-execution risk assessment result."""
    scan_time: str
    files_scanned: int
    vulnerabilities: List[RiskPrediction]
    risk_score: float

    def to_dict(self) -> dict:
        return {
            "scan_time": self.scan_time,
            "files_scanned": self.files_scanned,
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
            "risk_score": self.risk_score,
            "summary": self._summary(),
        }

    def _summary(self) -> dict:
        sev = {}
        for v in self.vulnerabilities:
            sev[v.severity] = sev.get(v.severity, 0) + 1
        total = len(self.vulnerabilities)
        return {
            "total": total,
            "by_severity": sev,
            "safe": total == 0 or all(
                v.severity not in ("critical", "high") for v in self.vulnerabilities
            ),
        }


# ── pattern library (adapted from super_agi_predictor, dropped "0漏洞" framing) ──

PATTERNS: dict = {
    VulnerabilityType.SQL_INJECTION: [
        (r'execute\s*\(\s*f["\']', "f-string in SQL execute", Severity.CRITICAL, 0.95),
        (r'execute\s*\(\s*["\'].*%s', "String formatting in SQL", Severity.CRITICAL, 0.90),
        (r'execute\s*\(\s*["\'].*\+', "String concatenation in SQL", Severity.HIGH, 0.85),
    ],
    VulnerabilityType.COMMAND_INJECTION: [
        (r'os\.system\s*\(.*\+', "String concat in os.system", Severity.CRITICAL, 0.95),
        (r'subprocess\.(call|run|Popen)\s*\(.*\+', "String concat in subprocess", Severity.CRITICAL, 0.90),
        (r'eval\s*\(.*\+', "Dynamic content in eval", Severity.CRITICAL, 0.95),
        (r'exec\s*\(.*\+', "String concat in exec", Severity.CRITICAL, 0.95),
    ],
    VulnerabilityType.PATH_TRAVERSAL: [
        (r'open\s*\(.*\+', "String concat in open()", Severity.HIGH, 0.85),
        (r'open\s*\(f["\']', "f-string in open()", Severity.HIGH, 0.90),
    ],
    VulnerabilityType.HARDCODED_SECRETS: [
        (r'api_key\s*=\s*["\'][^"\']{10,}["\']', "Hardcoded API key", Severity.CRITICAL, 0.95),
        (r'password\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded password", Severity.CRITICAL, 0.95),
        (r'secret\s*=\s*["\'][^"\']{10,}["\']', "Hardcoded secret", Severity.CRITICAL, 0.90),
        (r'token\s*=\s*["\'][^"\']{10,}["\']', "Hardcoded token", Severity.CRITICAL, 0.90),
        (r'private_key\s*=\s*["\'][^"\']{20,}["\']', "Hardcoded private key", Severity.CRITICAL, 0.98),
    ],
    VulnerabilityType.XSS: [
        (r'innerHTML\s*=\s*.*\+', "Dynamic content in innerHTML", Severity.HIGH, 0.85),
        (r'document\.write\s*\(.*\+', "Dynamic content in document.write", Severity.HIGH, 0.85),
    ],
    VulnerabilityType.INSECURE_DESERIALIZATION: [
        (r'pickle\.loads?\s*\(', "Insecure pickle usage", Severity.HIGH, 0.80),
        (r'yaml\.load\s*\([^,]', "Unsafe yaml.load (no Loader)", Severity.HIGH, 0.85),
    ],
    VulnerabilityType.SSRF: [
        (r'requests\.get\s*\(.*\+', "Dynamic URL in requests", Severity.MEDIUM, 0.75),
        (r'urllib\.request\.urlopen\s*\(.*\+', "Dynamic URL in urllib", Severity.MEDIUM, 0.75),
    ],
}

CWE_MAP: dict = {
    VulnerabilityType.SQL_INJECTION: "CWE-89",
    VulnerabilityType.COMMAND_INJECTION: "CWE-78",
    VulnerabilityType.PATH_TRAVERSAL: "CWE-22",
    VulnerabilityType.HARDCODED_SECRETS: "CWE-798",
    VulnerabilityType.XSS: "CWE-79",
    VulnerabilityType.INSECURE_DESERIALIZATION: "CWE-502",
    VulnerabilityType.SSRF: "CWE-918",
    VulnerabilityType.RCE: "CWE-94",
}

CVSS_MAP: dict = {
    Severity.CRITICAL: 9.5,
    Severity.HIGH: 7.5,
    Severity.MEDIUM: 5.0,
    Severity.LOW: 2.5,
    Severity.INFO: 0.0,
}

FIX_SUGGESTIONS: dict = {
    VulnerabilityType.SQL_INJECTION:
        "Use parameterized query: cursor.execute('SELECT * FROM users WHERE id = ?', (uid,))",
    VulnerabilityType.COMMAND_INJECTION:
        "Use arg list: subprocess.run(['ls', path], check=True)",
    VulnerabilityType.PATH_TRAVERSAL:
        "Use pathlib: Path(base) / filename; assert resolved.startswith(base)",
    VulnerabilityType.HARDCODED_SECRETS:
        "Use env var: os.environ.get('API_KEY')",
    VulnerabilityType.XSS:
        "Use template engine auto-escaping",
    VulnerabilityType.INSECURE_DESERIALIZATION:
        "Use json.loads() instead of pickle; yaml.safe_load() instead of yaml.load()",
    VulnerabilityType.SSRF:
        "Validate URL: use allowlist, block internal IPs",
}


def severity_order(s: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(s, 5)


def scan_content(content: str, file_path: str = "<inline>") -> RiskReport:
    """
    Scan a string of source code for vulnerability patterns.
    Returns a RiskReport with all findings.
    """
    predictions: List[RiskPrediction] = []
    lines = content.split("\n")

    for vuln_type, pattern_list in PATTERNS.items():
        cwe = CWE_MAP.get(vuln_type, "CWE-Unknown")
        fix = FIX_SUGGESTIONS.get(vuln_type, "Review security best practices")
        cvss = 5.0

        for pattern_str, desc, sev, conf in pattern_list:
            regex = re.compile(pattern_str, re.IGNORECASE)
            for line_num, line in enumerate(lines, 1):
                for match in regex.finditer(line):
                    cvss = CVSS_MAP.get(sev, 5.0)
                    predictions.append(
                        RiskPrediction(
                            file_path=file_path,
                            line_number=line_num,
                            column=match.start() + 1,
                            vulnerability_type=vuln_type.value,
                            severity=sev.value,
                            confidence=conf,
                            description=desc,
                            suggested_fix=fix,
                            cwe_id=cwe,
                            cvss_score=cvss,
                        )
                    )

    # deduplicate (same file, same line, same type)
    seen: set = set()
    unique: List[RiskPrediction] = []
    for p in predictions:
        key = (p.file_path, p.line_number, p.vulnerability_type)
        if key not in seen:
            seen.add(key)
            unique.append(p)

    unique.sort(key=lambda x: (severity_order(x.severity), -x.confidence))
    risk_score = _calculate_risk_score(unique)

    return RiskReport(
        scan_time=datetime.utcnow().isoformat(),
        files_scanned=1 if file_path != "<inline>" or content else 0,
        vulnerabilities=unique,
        risk_score=risk_score,
    )


def scan_file(file_path: str) -> RiskReport:
    """Scan a single file on disk."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    return scan_content(content, file_path=file_path)


def _calculate_risk_score(vulns: List[RiskPrediction]) -> float:
    """Calculate overall risk score 0-100."""
    if not vulns:
        return 0.0
    weights = {"critical": 10, "high": 5, "medium": 2, "low": 0.5, "info": 0.1}
    total = sum(weights.get(v.severity, 1) * v.confidence for v in vulns)
    return min(100.0, total * 10)


SURFACE_VERSION = "PGGArchonRiskPredictionSurface/v1"
SURFACE_SOURCE = "APEX-AGI omega_pipeline/super_agi_predictor.py"
SURFACE_ABSORBED = "2026-05-28"
