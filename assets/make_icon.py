"""
Generate assets/icon.ico for Clembot-dictate.
Run once before build.bat. Output: assets/icon.ico
Usage: python assets/make_icon.py
"""
from pathlib import Path
from PIL import Image, ImageDraw

# Brand colours, mirrored from src/theme.py. Kept as literals because this script
# runs at build time with no src/ on the path: the tuple beside each name is the
# check that they have not drifted.
ACCENT    = (81, 175, 111, 255)     # theme.ACCENT    #51af6f
RECORDING = (231, 98, 80, 255)      # theme.RECORDING #e76250
INK       = (14, 12, 8, 255)        # theme.BG        #0e0c08

OUT = Path(__file__).parent / "icon.ico"
SIZES = [16, 32, 48, 64, 128, 256]


def _draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = max(1, size // 32)
    draw.ellipse([pad, pad, size - pad, size - pad], fill=ACCENT)

    cx, cy = size // 2, size // 2
    r = max(2, size // 6)
    white = INK
    offset = max(1, size // 16)
    lw = max(1, size // 32)

    # Mic capsule
    draw.ellipse([cx - r, cy - r - offset, cx + r, cy + r - offset], fill=white)

    # Mic stand
    draw.rectangle([cx - lw, cy + r - offset, cx + lw, cy + r + size // 8], fill=white)

    # Mic bracket
    bracket = max(2, size // 8)
    draw.arc(
        [cx - bracket, cy - offset, cx + bracket, cy + size // 7],
        start=0, end=180, fill=white, width=lw,
    )

    return img


if __name__ == "__main__":
    imgs = [_draw(s) for s in SIZES]
    # Pillow uses each image's natural size when sizes= is omitted
    imgs[0].save(OUT, format="ICO", append_images=imgs[1:])
    # ASCII only: build.bat treats a non-zero exit as icon failure and pauses, and a
    # non-UTF-8 console makes this print raise UnicodeEncodeError after the file is
    # already written. The build then blocks on a success.
    print(f"Icon saved -> {OUT}")
