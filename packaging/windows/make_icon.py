"""Small original code-drawn icon; no network or generated bitmap dependency."""

from pathlib import Path

from PIL import Image, ImageDraw

image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((1, 1, 62, 62), radius=12, fill="#254e3c")
draw.polygon([(12, 14), (23, 14), (32, 43), (41, 14), (52, 14),
              (38, 52), (26, 52)], fill="#ecf4e8")
image.save(Path(__file__).with_name("victus.ico"), sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
