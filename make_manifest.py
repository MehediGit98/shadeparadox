#!/usr/bin/env python3
"""Write or check MANIFEST_SHA256.json (flat {relative path: sha256}).

    python make_manifest.py --write    regenerate the manifest
    python make_manifest.py --check    verify every file against it (exit 1 on mismatch)
"""
import fnmatch, hashlib, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "MANIFEST_SHA256.json"
def ignored(relative, is_dir=False):
    """Apply the filename, directory and root patterns used in .gitignore.

    The release uses no Git dependency, so ZIP recipients can check integrity
    with Python alone. Local files excluded by these rules are never hashed.
    """
    parts = Path(relative).parts
    excluded = False
    for line in (ROOT/'.gitignore').read_text(encoding='utf-8').splitlines():
        pattern = line.strip()
        if not pattern or pattern.startswith('#'):
            continue
        negate = pattern.startswith('!')
        if negate:
            pattern = pattern[1:]
        directories_only = pattern.endswith('/')
        anchored = pattern.startswith('/')
        pattern = pattern.strip('/')
        candidates = parts if is_dir or not directories_only else parts[:-1]
        if anchored or '/' in pattern:
            candidates = ['/'.join(candidates[:i]) for i in range(1, len(candidates)+1)]
        if any(fnmatch.fnmatchcase(candidate, pattern) for candidate in candidates):
            excluded = not negate
    return excluded


def files():
    for base, dirs, names in os.walk(ROOT):
        base = Path(base)
        dirs[:] = sorted(d for d in dirs if not ignored((base/d).relative_to(ROOT), is_dir=True))
        for name in sorted(names):
            p = base/name
            if not p.is_file() or p == MANIFEST:
                continue
            rel = p.relative_to(ROOT)
            if not ignored(rel):
                yield rel.as_posix(), p


def digest(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def main(mode: str) -> int:
    current = {rel: digest(p) for rel, p in files()}
    if mode == "--write":
        MANIFEST.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
        print(f"wrote {len(current)} digests to {MANIFEST.name}")
        return 0
    recorded = json.loads(MANIFEST.read_text())
    missing = sorted(set(recorded) - set(current))
    extra = sorted(set(current) - set(recorded))
    changed = sorted(k for k in recorded if k in current and recorded[k] != current[k])
    for label, items in (("missing", missing), ("not in manifest", extra), ("changed", changed)):
        for k in items:
            print(f"{label}: {k}")
    ok = not (missing or extra or changed)
    print(f"{len(recorded)} files recorded; {'all match' if ok else 'MISMATCH'}")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("--write", "--check"):
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
