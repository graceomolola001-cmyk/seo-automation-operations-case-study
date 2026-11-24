"""Simple disclosure guard for this *public* sample, in addition to human review.

Avoid searching source with real secret values. Heuristics cover URLs, API tokens,
email addresses, account IDs, and private infrastructure markers.
"""
from pathlib import Path
import re
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
EXCLUDED = {"security_scan.py", "LICENSE"}
SUSPICIOUS = [
    ("embedded email address", re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)),
    ("hardcoded Google Chat space", re.compile(r"spaces/[A-Za-z0-9_\-]{9,}")),
    ("Google tracking tag", re.compile(r"(?:GTM|G)-[A-Z0-9]{8,}")),
    ("private site URL", re.compile("ecampus" + r"\.ui\.edu\.ng", re.I)),
    ("internal n8n host", re.compile("hostinger" + r"site\.com", re.I)),
    ("organization identifier", re.compile("astria" + "learning", re.I)),
    ("private workbook ID", re.compile(r"1rm34F[a-zA-Z0-9_\-]{25,}")),
    ("GitHub PAT", re.compile(r"gh[pousr]_[A-Za-z0-9_]{25,}")),
    ("generic API token assignment", re.compile(r"(?i)(api[_-]?key|secret|access[_-]?token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{25,}['\"]")),
]
violations=[]
files=0
for path in ROOT.rglob("*"):
    if not path.is_file() or path.name in EXCLUDED or ".git" in path.parts or "__pycache__" in path.parts:
        continue
    if path.suffix.lower() not in {".py", ".js", ".json", ".md", ".yml", ".yaml", ".txt", ".gitignore"} and path.name not in {".gitignore"}:
        continue
    files += 1
    text = path.read_text(encoding="utf-8")
    for label, expr in SUSPICIOUS:
        m=expr.search(text)
        if m:
            violations.append(f"{path.relative_to(ROOT)}: {label} (line {text[:m.start()].count(chr(10))+1})")
if violations:
    print("PUBLIC-SAFETY SCAN FAILED:\n" + "\n".join(violations))
    raise SystemExit(1)
print(f"PUBLIC-SAFETY SCAN PASSED: {files} text files, no flagged sensitive markers")
