"""Export the publishable subset of this project to the public mirror.

The source of truth is here, inside a private vault. `clemenswan/clembot-dictate`
is a curated export of it, not a remote of it. Nothing publishes itself.

What must never leave, and why:

  history.json   real dictation transcripts. The single most sensitive file here
  CLAUDE.md      vault operating instructions, references other projects
  prd/roadmap/lineage/POW/wiki.md   internal planning and decision history
  distribution/CHECKLIST.md, RELEASE.md   name internal hosts and repositories
  dist/, build/  build output, hundreds of MB
  .claude/       agent configuration

The allowlist below is deliberately explicit. A denylist would silently publish
whatever a future session adds; this refuses to publish anything nobody named.

    python tools/export_public.py <path-to-clembot-dictate-checkout>
    python tools/export_public.py <path> --check     # report drift, copy nothing

The public tree also carries four files that exist only there, and this never
touches them: README.md, LICENSE, CHANGELOG.md, .gitignore, and docs/ (the public
docs are rewritten for an outside audience, not copied).
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Everything that may be published, named one by one.
ALLOWLIST = (
    "requirements.txt",
    "run.bat",
    "build.bat",
    "installer.iss",
    "voice-transcriber.spec",
    "distribution/version.json",
    "assets/make_icon.py",
    "assets/icon.ico",
    "tools/check_release.py",
    "tools/get_model_hash.py",
    "tools/export_public.py",
    "tools/ui_preview.py",
    "tools/check_brand.py",

    # Vendored MIT text engine used by src/normalizer.py. Named explicitly
    # because ALLOWED_DIRS globs src/*.py NON-recursively: without these three
    # lines the public build ships normalizer.py with no engine behind it, and
    # its import guard turns the feature into a silent no-op.
    "src/vendor/__init__.py",
    "src/vendor/text_unicode.py",
    "src/vendor/LICENSE-watermarks-remover",
    "src/vendor/ATTRIBUTION.md",
)
ALLOWED_DIRS = ("src",)              # every *.py inside, no subdirectories
NEVER = ("history.json", "CLAUDE.md", "prd.md", "roadmap.md", "lineage.md",
         "POW.md", "wiki.md", "distribution/CHECKLIST.md", "distribution/RELEASE.md")


def publishable() -> list[str]:
    files = list(ALLOWLIST)
    for name in ALLOWED_DIRS:
        files += sorted(f"{name}/{p.name}" for p in (ROOT / name).glob("*.py"))
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="path to the public repository checkout")
    parser.add_argument("--check", action="store_true",
                        help="report what differs and copy nothing")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.is_dir():
        print(f"not a directory: {target}")
        return 1
    if target == ROOT:
        print("refusing to export onto the source tree")
        return 1

    changed, missing, copied = [], [], 0
    for rel in publishable():
        source = ROOT / rel
        if not source.is_file():
            missing.append(rel)
            continue
        destination = target / rel
        same = destination.is_file() and filecmp.cmp(source, destination, shallow=False)
        if same:
            continue
        changed.append(rel)
        if not args.check:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied += 1

    # The point of the exercise: prove the sensitive files are not over there.
    leaked = [name for name in NEVER if (target / name).exists()]

    for rel in changed:
        print(f"{'differs' if args.check else 'copied '}  {rel}")
    for rel in missing:
        print(f"MISSING  {rel} (in the allowlist, not in this tree)")
    for name in leaked:
        print(f"LEAK     {name} is present in the public checkout and must not be")

    if not changed and not missing and not leaked:
        print("public mirror matches this tree, nothing sensitive present")
    elif not args.check:
        print(f"\n{copied} file(s) copied. Review the diff over there before committing; "
              "the public README, LICENSE, CHANGELOG and docs/ are maintained separately "
              "and are never touched by this script.")

    return 1 if (leaked or missing) else 0


if __name__ == "__main__":
    sys.exit(main())
