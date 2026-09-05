"""Check the source against the mechanical rules in design/brand.md.

Six brand regressions shipped before this existed, and every one of them is
mechanically detectable: a 34px emoji in the empty state, a 9px bold heading,
two Catppuccin hex literals left over from the palette the brand pass removed,
an em dash in a status message, and glyphs typed into strings that a dot widget
already draws.

The brand file's Verification section says a design pass reviewed only as a diff
is a design pass done blind. That is about looking at the render. This is the
other half: the rules a machine can check, checked every time.

Judgement calls are deliberately NOT here. Whether a layout is good is for
tools/ui_preview.py and a human.

The canonical design system lives in design/brand.md, which is not part of the
public mirror. The rules this file enforces are restated in it below, so it is
readable and runnable on its own.

    python tools/check_brand.py          # exit 1 on any violation
"""

from __future__ import annotations

import ast
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

# design/brand.md -> Type: "15 / 12 / 11 / 10 and nothing else."
TYPE_SCALE = {15, 12, 11, 10}

# theme.py is where colour is allowed to be a literal. Everywhere else it is a
# regression by the brand file's own first anti-pattern.
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")
COLOUR_OWNER = "theme.py"

# Only these draw UI. refiner.py, transcriber.py and window_detector.py speak to
# the log, and config.py holds LLM prompt templates: an em dash inside a prompt
# is not visible copy, and reporting it would train people to skim this output.
UI_FILES = {"ui.py", "tray.py", "icons.py", "main.py"}

# Box drawing is used for section rules in comments and is not UI furniture.
ALLOWED_NON_ASCII = set("─│┌┐└┘├┤┬┴┼"
                        "—→·éêèàüöäñ")


def docstring_nodes(tree):
    """Every string node that is a docstring, so prose is not mistaken for copy."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                out.add(id(body[0].value))
    return out


def log_argument_nodes(tree):
    """Strings handed to log.*(). A log line is not something a user reads."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            target = node.func.value
            if isinstance(target, ast.Name) and target.id in ("log", "logger", "logging"):
                for arg in list(node.args) + [k.value for k in node.keywords]:
                    for sub_node in ast.walk(arg):
                        out.add(id(sub_node))
    return out


def visible_strings(path: Path):
    """String literals that are not docstrings and not log arguments."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = docstring_nodes(tree) | log_argument_nodes(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
            yield node.lineno, node.value


def check_emoji(path: Path, fail):
    for lineno, text in visible_strings(path):
        for ch in text:
            if ord(ch) < 0x2100 or ch in ALLOWED_NON_ASCII:
                continue
            name = unicodedata.name(ch, "unnamed")
            fail(path, lineno, "glyph in visible copy: %s (U+%04X). Draw it in icons.py."
                 % (name, ord(ch)))


def check_em_dash(path: Path, fail):
    for lineno, text in visible_strings(path):
        if "—" in text:
            fail(path, lineno, "em dash in visible copy. Vault hard ban.")


def check_hex(path: Path, fail):
    if path.name == COLOUR_OWNER:
        return
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        code = line.split("#", 1)[0] if not HEX.search(line.split("#", 1)[0] or "") else line
        for match in HEX.finditer(line):
            # A hex inside a comment is documentation, not a value in use.
            if line.index(match.group()) < line.find("#") or "#" not in line[:line.index(match.group())]:
                fail(path, i, "colour literal %s outside theme.py" % match.group())
                break


def check_font_size(path: Path, fail):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "attr", getattr(node.func, "id", ""))
        if name != "CTkFont":
            continue
        for kw in node.keywords:
            if kw.arg == "size" and isinstance(kw.value, ast.Constant) \
                    and isinstance(kw.value.value, int) and kw.value.value not in TYPE_SCALE:
                fail(path, node.lineno,
                     "font size %d is off the 15/12/11/10 scale" % kw.value.value)


def main() -> int:
    problems = []

    def fail(path, lineno, message):
        problems.append("%s:%d  %s" % (path.relative_to(ROOT).as_posix(), lineno, message))

    for path in sorted(SRC.glob("*.py")):
        if path.name.endswith("_test.py"):
            continue
        if path.name in UI_FILES:
            check_emoji(path, fail)
            check_em_dash(path, fail)
        check_hex(path, fail)
        check_font_size(path, fail)

    if problems:
        print("Brand violations (design/brand.md):\n")
        for p in problems:
            print("  " + p)
        print("\n%d problem(s)." % len(problems))
        return 1

    print("No brand violations. Layout and taste are still ui_preview.py plus a human.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
