#!/usr/bin/env python3
"""
psd_export.py - 将 PSD 文件的顶层图层导出为 PNG 切图 + manifest.csv

依赖:
  pip install psd-tools Pillow

用法:
  python psd_export.py --psd "design.psd" --out ./export
  python psd_export.py --psd "design.psd" --out ./export --min-size 10 --skip-hidden
"""

import argparse
import csv
import os
import re
import sys

try:
    from psd_tools import PSDImage
    from psd_tools.constants import BlendMode
except ImportError:
    print("[ERROR] 需要安装 psd-tools: pip install psd-tools Pillow", file=sys.stderr)
    sys.exit(1)

from PIL import Image


# ---------------------------------------------------------------------------
# 文件名清洗
# ---------------------------------------------------------------------------

_RE_INVALID_CHAR = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RE_MULTI_UNDERSCORE = re.compile(r"_{2,}")


def safe_filename(name: str, index: int) -> str:
    """将图层名转为安全文件名"""
    s = name.strip()
    s = s.replace("::", "_").replace(" ", "_")
    s = _RE_INVALID_CHAR.sub("_", s)
    s = _RE_MULTI_UNDERSCORE.sub("_", s).strip("_")
    if not s:
        s = "unnamed"
    return f"{index:03d}_{s}.png"


# ---------------------------------------------------------------------------
# 图层遍历
# ---------------------------------------------------------------------------

def collect_top_layers(psd, skip_hidden=True, min_size=4):
    """
    收集 PSD 顶层可见图层。

    参数:
      psd:         PSDImage 对象
      skip_hidden: 是否跳过不可见图层
      min_size:    忽略宽或高小于此值的图层

    返回:
      list of dict: [{ name, bbox, layer }, ...]
    """
    results = []
    for layer in psd:
        if skip_hidden and not layer.is_visible():
            continue

        bbox = layer.bbox
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        if w < min_size or h < min_size:
            continue

        results.append({
            "name": layer.name,
            "bbox": bbox,  # (x1, y1, x2, y2)
            "width": w,
            "height": h,
            "layer": layer,
        })

    return results


def collect_all_layers(psd, skip_hidden=True, min_size=4, max_depth=None):
    """
    递归收集所有叶子图层 (包括组内子图层)。

    参数:
      max_depth: 最大递归深度 (None=无限)
    """
    results = []

    def _walk(layer, depth=0):
        if max_depth is not None and depth > max_depth:
            return
        if skip_hidden and not layer.is_visible():
            return

        if layer.is_group():
            for child in layer:
                _walk(child, depth + 1)
        else:
            bbox = layer.bbox
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            if w >= min_size and h >= min_size:
                results.append({
                    "name": layer.name,
                    "bbox": bbox,
                    "width": w,
                    "height": h,
                    "layer": layer,
                })

    for layer in psd:
        _walk(layer)

    return results


# ---------------------------------------------------------------------------
# 导出
# ---------------------------------------------------------------------------

def export_layers(layers_info, out_dir, canvas_size):
    """
    将图层导出为 PNG + manifest.csv。

    参数:
      layers_info: collect_top_layers 或 collect_all_layers 的结果
      out_dir:     输出目录
      canvas_size: (width, height) PSD 画布尺寸
    """
    os.makedirs(out_dir, exist_ok=True)

    manifest_rows = []

    for idx, info in enumerate(layers_info, start=1):
        filename = safe_filename(info["name"], idx)
        filepath = os.path.join(out_dir, filename)

        # 导出 PNG
        try:
            layer_image = info["layer"].composite()
            if layer_image is not None:
                layer_image.save(filepath)
            else:
                # 回退: 尝试 topdown composite
                print(f"[WARN] 图层 {info['name']} composite 返回 None, 尝试 topdown",
                      file=sys.stderr)
                layer_image = info["layer"].composite(viewport=info["bbox"])
                if layer_image is not None:
                    layer_image.save(filepath)
                else:
                    print(f"[WARN] 跳过无法渲染的图层: {info['name']}", file=sys.stderr)
                    continue
        except Exception as e:
            print(f"[WARN] 导出失败 {info['name']}: {e}", file=sys.stderr)
            continue

        bbox = info["bbox"]
        manifest_rows.append({
            "index": idx,
            "name": info["name"],
            "x1": bbox[0],
            "y1": bbox[1],
            "x2": bbox[2],
            "y2": bbox[3],
            "width": info["width"],
            "height": info["height"],
            "file": filename,
        })

        print(f"  [{idx:3d}] {info['name']:30s}  {info['width']:4d}x{info['height']:<4d}  -> {filename}")

    # 写入 manifest.csv
    csv_path = os.path.join(out_dir, "manifest.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "index", "name", "x1", "y1", "x2", "y2", "width", "height", "file"
        ])
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"\n[OK] 导出 {len(manifest_rows)} 个图层到 {out_dir}")
    print(f"[OK] manifest: {csv_path}")
    print(f"[OK] 画布尺寸: {canvas_size[0]}x{canvas_size[1]}")

    return manifest_rows


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="从 PSD 文件导出图层切图 + manifest.csv"
    )
    parser.add_argument("--psd", required=True, help="PSD 文件路径")
    parser.add_argument("--out", required=True, help="输出目录")
    parser.add_argument(
        "--mode",
        choices=["top", "all"],
        default="top",
        help="导出模式: top=仅顶层, all=所有叶子图层 (默认: top)",
    )
    parser.add_argument("--min-size", type=int, default=4, help="忽略宽或高小于此值的图层")
    parser.add_argument("--skip-hidden", action="store_true", default=True, help="跳过隐藏图层")
    parser.add_argument("--max-depth", type=int, default=None, help="最大递归深度 (仅 all 模式)")
    args = parser.parse_args()

    psd_path = args.psd
    if not os.path.exists(psd_path):
        print(f"[ERROR] PSD 文件不存在: {psd_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] 加载 PSD: {psd_path}")
    psd = PSDImage.open(psd_path)
    canvas_size = (psd.width, psd.height)
    print(f"[INFO] 画布尺寸: {canvas_size[0]}x{canvas_size[1]}")
    print(f"[INFO] 图层数量: {len(list(psd.descendants()))}")

    # 收集图层
    if args.mode == "top":
        print(f"[INFO] 模式: 顶层图层")
        layers_info = collect_top_layers(psd, args.skip_hidden, args.min_size)
    else:
        print(f"[INFO] 模式: 所有叶子图层 (max_depth={args.max_depth})")
        layers_info = collect_all_layers(psd, args.skip_hidden, args.min_size, args.max_depth)

    print(f"[INFO] 有效图层: {len(layers_info)}")

    if not layers_info:
        print("[WARN] 未找到有效图层", file=sys.stderr)
        sys.exit(0)

    # 导出
    export_layers(layers_info, args.out, canvas_size)


if __name__ == "__main__":
    main()
