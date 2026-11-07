"""把带棋盘格背景的 JPG logo 抠成真正透明的 PNG，并导出 web/favicon 所需尺寸。

用户提供的素材是 1920x1920 JPG，透明棋盘格被烘焙成了灰白像素。
本脚本按「色度」(max-min) 分离：背景为低色度灰白，logo 为高饱和蓝紫青。
"""
from PIL import Image, ImageFilter
import numpy as np
import os

SRC = r'C:\Users\Administrator\.workbuddy\clipboard-images\clipboard-2026-11-07T03-43-32-737Z-216be909.jpg'
OUT_DIR = r'C:\Users\Administrator\WorkBuddy\2026-09-29-16-25-58\lx-music-web\web\assets'
os.makedirs(OUT_DIR, exist_ok=True)

im = Image.open(SRC).convert('RGB')
a = np.asarray(im).astype(np.float32)
mx = a.max(2)
mn = a.min(2)
chroma = mx - mn
lum = a.mean(2)

# 软 alpha：低色度=背景(0)，高色度=logo(1)；中间带做平滑过渡抗锯齿
lo, hi = 8.0, 38.0
alpha = np.clip((chroma - lo) / (hi - lo), 0, 1)
# 极亮的近白像素（棋盘格白块 + JPEG 噪点）强制透明
alpha *= np.clip((250 - lum) / 40, 0, 1)
alpha = (alpha * 255).astype(np.uint8)

# 颜色去污染：背景是灰白，logo 边缘像素混了灰白会发白；
# 按 alpha 反推原始饱和色，抑制白边
rgb = a.copy()
keep = alpha > 8
# 用色度方向把颜色往饱和方向推回（减去混入的白）
bg = 225.0
al = alpha.astype(np.float32) / 255.0
al_safe = np.maximum(al, 0.06)
rgb = np.clip((a - bg * (1 - al_safe[..., None])) / al_safe[..., None], 0, 255)
rgb = np.where(keep[..., None], rgb, a)

rgba = np.dstack([rgb.astype(np.uint8), alpha])
out = Image.fromarray(rgba, 'RGBA')

# 裁到内容边界（留 2% 内边距），保证 logo 居中不偏心
bbox = out.getchannel('A').point(lambda v: 255 if v > 12 else 0).getbbox()
pad = int(max(bbox[2] - bbox[0], bbox[3] - bbox[1]) * 0.02)
x0, y0, x1, y1 = bbox
x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
x1, y1 = min(out.width, x1 + pad), min(out.height, y1 + pad)
out = out.crop((x0, y0, x1, y1))

# 正方形画布居中，避免 favicon 被拉伸
side = max(out.size)
canvas = Image.new('RGBA', (side, side), (0, 0, 0, 0))
canvas.paste(out, ((side - out.width) // 2, (side - out.height) // 2))

# 主素材 1024px（资料库/项目通用）
base = canvas.resize((1024, 1024), Image.LANCZOS)
base.save(os.path.join(OUT_DIR, 'ly-logo.png'), optimize=True)

# 网页用 512 / 顶栏 64 / favicon 各尺寸
for size, name in [(512, 'ly-logo-512.png'), (192, 'ly-logo-192.png'),
                   (180, 'apple-touch-icon.png'), (64, 'ly-logo-64.png'),
                   (32, 'favicon-32.png')]:
    canvas.resize((size, size), Image.LANCZOS).save(os.path.join(OUT_DIR, name), optimize=True)

# ICO 多尺寸（传统 favicon.ico）
canvas.resize((64, 64), Image.LANCZOS).save(
    os.path.join(OUT_DIR, 'favicon.ico'),
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])

# 质量报告
al = np.asarray(base.getchannel('A'))
print('输出目录:', OUT_DIR)
print('裁切框:', bbox, '-> 画布', side)
print('透明像素占比: %.1f%%' % ((al < 8).mean() * 100))
print('半透明边缘占比: %.2f%%' % (((al >= 8) & (al < 247)).mean() * 100))
for f in sorted(os.listdir(OUT_DIR)):
    print(' ', f, os.path.getsize(os.path.join(OUT_DIR, f), ), 'bytes')
