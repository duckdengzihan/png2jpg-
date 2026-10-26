# -*- coding: utf-8 -*-
"""自测：验证 convert_one 核心逻辑（透明填白、质量参数、RGB 输出）。"""
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, r"E:\png转jpg应用")
from png2jpg import convert_one  # noqa: E402

tmp = Path(tempfile.mkdtemp())

# 1) 带透明通道的 PNG：透明区域应变成白色，不透明区域保留颜色
im = Image.new("RGBA", (300, 200), (0, 0, 0, 0))
dr = ImageDraw.Draw(im)
dr.rectangle([50, 50, 250, 150], fill=(30, 144, 255, 255))
src = tmp / "透明测试.png"
im.save(src)

dst = tmp / "透明测试.jpg"
convert_one(src, dst, 60)
assert dst.exists(), "输出文件不存在"
out = Image.open(dst)
assert out.format == "JPEG" and out.mode == "RGB" and out.size == (300, 200)
px_transparent = out.getpixel((5, 5))
assert px_transparent == (255, 255, 255), f"透明区域未填白: {px_transparent}"
px_color = out.getpixel((150, 100))
assert abs(px_color[0] - 30) < 12 and abs(px_color[1] - 144) < 12, f"颜色丢失: {px_color}"

# 2) 不同质量应产生不同大小的文件
d_low = tmp / "低质量.jpg"
d_high = tmp / "高质量.jpg"
big = Image.new("RGB", (2000, 2000))
dbig = ImageDraw.Draw(big)
for x in range(0, 2000, 40):
    dbig.line([(x, 0), (x, 2000)], fill=(x % 256, 60, 200), width=20)
big.save(tmp / "复杂图.png")
convert_one(tmp / "复杂图.png", d_low, 20)
convert_one(tmp / "复杂图.png", d_high, 95)
s_low, s_high = d_low.stat().st_size, d_high.stat().st_size
assert s_high > s_low, f"质量参数未生效: low={s_low} high={s_high}"

print(f"SELFTEST OK  透明填白=通过  质量20={s_low}B 质量95={s_high}B")
