"""Bounded release checks; not a guarantee that arbitrary secrets can be detected."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {".git", ".work", ".superpowers", ".venv", "__pycache__", ".pytest_cache", "node_modules"}


def public_files(root: Path):
    for directory, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORED]
        for name in sorted(files):
            yield Path(directory) / name


def scan(root: Path) -> tuple[list[str], int]:
    errors = []
    files = list(public_files(root))
    local_blocklist = root / ".work/source-identifiers.json"
    blocked = json.loads(local_blocklist.read_text()) if local_blocklist.exists() else []
    patterns = {
        "private absolute path": r"/" + r"Users/[^\s\"']+",
        "non-example Bitable table identifier": r"\btbl[A-Za-z0-9]{12,}\b",
        "credential-bearing URL": r"https?://[^\s/@]+:[^\s/@]+@",
        "private-key material": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        "GitHub access-token format": r"\bgh[pousr]_[A-Za-z0-9]{30,}\b|github_pat_[A-Za-z0-9_]{30,}",
        "OpenAI-style key format": r"\bsk-[A-Za-z0-9_-]{24,}\b",
    }
    for p in files:
        rel = p.relative_to(root).as_posix()
        if p.is_symlink():
            errors.append(f"{rel}: symbolic links are not permitted")
            continue
        if (p.name.startswith('.env') and p.name != '.env.example') or p.suffix in {'.db', '.sqlite', '.sqlite3', '.pyc'}:
            errors.append(f"{rel}: runtime/secret file")
        if p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.gif'}:
            continue  # Visual inspection is a separate release step.
        try:
            text = p.read_text(encoding='utf-8')
        except UnicodeError:
            errors.append(f"{rel}: unexpected binary file")
            continue
        for label, pattern in patterns.items():
            if re.search(pattern, text):
                errors.append(f"{rel}: {label}")
        if any(value in text for value in blocked):
            errors.append(f"{rel}: original environment identifier")
        if p.suffix == '.md':
            for target in re.findall(r'!?\[[^\]]*\]\(([^\s)]+)\)', text):
                if re.match(r'^[a-z]+:', target) or target.startswith('#'):
                    continue
                link = target.split('#', 1)[0]
                dest = (p.parent / link).resolve()
                if not dest.is_relative_to(root) or not dest.exists():
                    errors.append(f"{rel}: missing/outside relative link {target}")
        if p.suffix == '.json':
            try:
                data = json.loads(text)
            except ValueError:
                errors.append(f"{rel}: invalid JSON")
                continue
            if rel.startswith('n8n/workflows/'):
                if data.get('active') is not False or data.get('staticData') is not None or data.get('pinData') != {}:
                    errors.append(f"{rel}: activation or retained runtime data")
                for n in data.get('nodes', []):
                    for c in n.get('credentials', {}).values():
                        if not re.fullmatch(r'[A-Z_]+_CREDENTIAL_ID', c.get('id', '')):
                            errors.append(f"{rel}: credential reference is not a placeholder")
    return errors, len(files)


if __name__ == '__main__':
    errors, count = scan(ROOT)
    for error in errors:
        print('FAIL:', error)
    print(f'Public checks: {count} files inspected; {len(errors)} failures. Binary visuals require separate inspection.')
    sys.exit(bool(errors))
