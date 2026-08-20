"""
Generate assets/icon.ico for Clembot-dictate.
Run once before build.bat. Output: assets/icon.ico
Usage: python assets/make_icon.py
"""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).parent / "icon.ico"
SIZES = [16, 32, 48, 64, 128, 256]


def _draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = max(1, size // 32)
    draw.ellipse([pad, pad, size - pad, size - pad], fill=(60, 65, 80, 255))

    cx, cy = size // 2, size // 2
    r = max(2, size // 6)
    white = (255, 255, 255, 230)
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
    print(f"Icon saved → {OUT}")
