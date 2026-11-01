"""Tiles renders/knives/*.png into renders/knives_sheet.png with labels."""
import os, sys
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "renders", "knives")
dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "renders", "knives_sheet.png")
import ast
names = {}
tree = ast.parse(open(os.path.join(HERE, "knives.py")).read())
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Subscript) and isinstance(node.value, ast.Call):
        k = node.targets[0].slice.value if isinstance(node.targets[0].slice, ast.Constant) else None
        for kw in node.value.keywords:
            if k and kw.arg == "name": names[k] = kw.value.value
keys = [k for k in names if os.path.exists(os.path.join(src, k + ".png"))]
cols, tile = 4, 420; rows = (len(keys) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tile, rows * tile), (12, 15, 18)); d = ImageDraw.Draw(sheet)
try: font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
except OSError: font = ImageFont.load_default()
for i, k in enumerate(keys):
    im = Image.open(os.path.join(src, k + ".png")).convert("RGB").resize((tile, tile))
    x, y = (i % cols) * tile, (i // cols) * tile; sheet.paste(im, (x, y))
    d.text((x + 14, y + 10), "★ " + names[k], fill=(228, 174, 57), font=font)
sheet.save(dst); print("sheet", dst, len(keys))
