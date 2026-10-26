# -*- coding: utf-8 -*-
"""生成应用图标 icon.ico（蓝色圆角底 + 白色山形照片图形）。"""
from PIL import Image, ImageDraw

img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([6, 6, 250, 250], radius=52, fill=(52, 120, 246, 255))
d.ellipse([168, 56, 212, 100], fill=(255, 213, 74, 255))
d.polygon([(38, 196), (124, 92), (166, 142), (196, 108), (224, 196)],
          fill=(255, 255, 255, 240))
img.save(r"E:\png转jpg应用\icon.ico",
         sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("ICON OK")
