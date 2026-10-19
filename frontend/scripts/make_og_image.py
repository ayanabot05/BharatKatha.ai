"""Generate the social share card (1200x630) for BharatKatha.

The card is referenced by og:image, twitter:image and the sitemap image entry,
but did not exist - so every share and every AI-engine preview had no image.

Palette follows the app: warm apricot ground, maroon accent, deep-sage ink,
muted gold. No black, no white, no dark fills.

Run:  backend\\venv\\Scripts\\python.exe frontend\\scripts\\make_og_image.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
CREAM = (247, 224, 207)
CREAM_HI = (253, 238, 225)
MAROON = (163, 61, 82)
INK = (38, 59, 54)
GOLD = (222, 160, 92)

OUT = Path(__file__).resolve().parents[1] / "public" / "og-image.jpg"
FONTS = Path("C:/Windows/Fonts")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    for candidate in (name, "segoeuib.ttf", "segoeui.ttf", "arialbd.ttf", "arial.ttf"):
        path = FONTS / candidate
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()


def main() -> None:
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)

    # Vertical warm gradient (no white, no dark).
    for y in range(H):
        t = y / (H - 1)
        r = int(CREAM_HI[0] + (CREAM[0] - CREAM_HI[0]) * t)
        g = int(CREAM_HI[1] + (CREAM[1] - CREAM_HI[1]) * t)
        b = int(CREAM_HI[2] + (CREAM[2] - CREAM_HI[2]) * t)
        d.line([(0, y), (W, y)], fill=(r, g, b))

    # Reel sprocket rails along the top and bottom edges.
    dot = 4
    for x in range(24, W, 32):
        for cy in (22, H - 22):
            d.ellipse([x - dot, cy - dot, x + dot, cy + dot], fill=MAROON)

    # A strip of story frames along the bottom - the "film floor" motif.
    top, fh = H - 168, 104
    fw = 132
    for i, x in enumerate(range(40, W - 40, fw + 12)):
        d.rounded_rectangle([x, top, x + fw, top + fh], radius=10, outline=MAROON, width=3)
        d.rounded_rectangle(
            [x + 10, top + 26, x + fw - 10, top + fh - 12],
            radius=6,
            fill=CREAM_HI if i % 2 else (243, 208, 186),
        )

    # Wordmark.
    d.text((72, 96), "BharatKatha", font=font("segoeuib.ttf", 84), fill=MAROON)
    d.text((76, 196), ".ai", font=font("segoeuib.ttf", 40), fill=GOLD)

    # Headline + proof line.
    d.text(
        (72, 258),
        "One idea in.",
        font=font("segoeuib.ttf", 58),
        fill=INK,
    )
    d.text(
        (72, 324),
        "A narrated video out.",
        font=font("segoeuib.ttf", 58),
        fill=INK,
    )
    d.text(
        (72, 404),
        "AI illustrations, captions and voice in 11 Indian languages.",
        font=font("segoeui.ttf", 28),
        fill=(96, 114, 105),
    )

    img.save(OUT, "JPEG", quality=88, optimize=True, progressive=True)
    print(f"wrote {OUT}  {img.size[0]}x{img.size[1]}  {OUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
