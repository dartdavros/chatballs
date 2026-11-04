"""Index actual screenshots for human inspection. Does not alter the baseline."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parent.parent / "verification"
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
for prefix in ("S", "D", "P"):
    for variant in ("ru-light-1440", "en-dark-320"):
        paths = sorted(root.glob(f"{prefix}[0-9][0-9]-{variant}.png"))
        cols = 2 if prefix == "S" and variant.startswith("ru") else 4
        cell_width = 720 if cols == 2 else 420
        cell_height = 520 if cols == 2 else 1010 if prefix == "S" else 875
        page_size = cols * 2
        for offset in range(0, len(paths), page_size):
            batch = paths[offset : offset + page_size]
            rows = (len(batch) + cols - 1) // cols
            sheet = Image.new("RGB", (cols * cell_width, rows * cell_height), "#e6e9ed")
            draw = ImageDraw.Draw(sheet)
            for i, path in enumerate(batch):
                img = Image.open(path).convert("RGB")
                img.thumbnail((cell_width, cell_height - 30))
                x, y = (i % cols) * cell_width, (i // cols) * cell_height
                draw.text((x + 8, y + 4), path.stem, font=font, fill="black")
                sheet.paste(img, (x, y + 28))
            sheet.save(root / f"contact-{prefix}-{variant}-{offset // page_size + 1}.jpg", quality=90)
print("Contact sheets saved beside original screenshots.")
