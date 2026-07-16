from PIL import Image, ImageDraw

SIZE = 256
BG0 = (13, 17, 23, 255)      # #0d1117
BG1 = (22, 27, 34, 255)      # #161b22
ACC = (233, 69, 96, 255)     # #e94560
ACC2 = (31, 111, 235, 255)   # #1f6feb
TEXT = (230, 237, 243, 255)  # #e6edf3


def rounded_rect_mask(size, radius):
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Rounded-square dark background, matching the dashboard's card look
bg = Image.new("RGBA", (SIZE, SIZE), BG0)
mask = rounded_rect_mask(SIZE, radius=52)
img.paste(bg, (0, 0), mask)

# Subtle inner card
inner_margin = 14
inner = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
idraw = ImageDraw.Draw(inner)
idraw.rounded_rectangle(
    [inner_margin, inner_margin, SIZE - inner_margin, SIZE - inner_margin],
    radius=40, outline=(48, 54, 61, 255), width=3
)
img.alpha_composite(inner)

# Shield outline (monitoring / protection)
cx = SIZE // 2
shield_top = 56
shield_w = 118
shield = [
    (cx - shield_w // 2, shield_top),
    (cx + shield_w // 2, shield_top),
    (cx + shield_w // 2, 128),
    (cx, 208),
    (cx - shield_w // 2, 128),
]
sdraw = ImageDraw.Draw(img)
sdraw.polygon(shield, outline=ACC, width=7)

# Eye (detection) inside the shield
eye_cy = 128
eye_w = 64
eye_h = 34
sdraw.ellipse(
    [cx - eye_w // 2, eye_cy - eye_h // 2, cx + eye_w // 2, eye_cy + eye_h // 2],
    outline=TEXT, width=6
)
pupil_r = 13
sdraw.ellipse(
    [cx - pupil_r, eye_cy - pupil_r, cx + pupil_r, eye_cy + pupil_r],
    fill=ACC2
)
sdraw.ellipse([cx - 4, eye_cy - 4, cx + 4, eye_cy + 4], fill=TEXT)

out_path = r"C:\Users\domin\Documents\AIcontrol\icon.ico"
img.save(out_path, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("saved", out_path)
