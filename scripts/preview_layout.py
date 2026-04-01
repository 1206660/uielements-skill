#!/usr/bin/env python3
"""
preview_layout.py - 将 manifest.csv + 切图合成为 HTML 预览页面

在浏览器中预览切图叠加效果，方便在生成 Unity 代码前确认布局。

用法:
  python preview_layout.py --csv manifest.csv --assets ./cuts/ --out preview.html
"""

import argparse
import base64
import csv
import os
import sys
from pathlib import Path


def image_to_data_uri(filepath: str) -> str:
    """将图片转为 base64 data URI (嵌入HTML)"""
    if not os.path.exists(filepath):
        return ""
    with open(filepath, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{data}"


def parse_csv(csv_path: str):
    """解析 manifest.csv"""
    layers = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                layers.append({
                    "index": int(row["index"]),
                    "name": row["name"].strip(),
                    "x1": int(row["x1"]),
                    "y1": int(row["y1"]),
                    "x2": int(row["x2"]),
                    "y2": int(row["y2"]),
                    "width": int(row["width"]),
                    "height": int(row["height"]),
                    "file": row["file"].strip(),
                })
            except (ValueError, KeyError):
                pass
    return layers


def generate_html(layers, assets_dir, canvas_w, canvas_h, embed_images=False, scale=0.5):
    """生成 HTML 预览页面"""

    # 按面积降序排列 (大的在底层)
    sorted_layers = sorted(layers, key=lambda l: -(l["width"] * l["height"]))

    sw = int(canvas_w * scale)
    sh = int(canvas_h * scale)

    elements = []
    sidebar_items = []

    for i, layer in enumerate(sorted_layers):
        x = int(layer["x1"] * scale)
        y = int(layer["y1"] * scale)
        w = int(layer["width"] * scale)
        h = int(layer["height"] * scale)

        if embed_images:
            src = image_to_data_uri(os.path.join(assets_dir, layer["file"]))
        else:
            src = os.path.join(assets_dir, layer["file"]).replace("\\", "/")

        idx = layer["index"]
        elements.append(
            f'    <img class="layer" data-idx="{idx}" '
            f'src="{src}" '
            f'alt="{layer["name"]}" '
            f'title="[{idx}] {layer["name"]} ({layer["width"]}x{layer["height"]})" '
            f'style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;z-index:{i};" />'
        )

        sidebar_items.append(
            f'    <label class="layer-toggle" data-idx="{idx}">'
            f'<input type="checkbox" checked data-idx="{idx}"> '
            f'<span class="idx">{idx:03d}</span> {layer["name"]}'
            f'<span class="size">{layer["width"]}x{layer["height"]}</span>'
            f'</label>'
        )

    sidebar_html = "\n".join(sidebar_items)
    elements_html = "\n".join(elements)
    layer_count = len(layers)

    html = (
        '<!DOCTYPE html>\n'
        '<html lang="zh-CN">\n'
        '<head>\n'
        '<meta charset="UTF-8">\n'
        '<title>UI Layout Preview</title>\n'
        '<style>\n'
        '* { margin:0; padding:0; box-sizing:border-box; }\n'
        'body { background:#1a1a2e; color:#eee; font-family:system-ui,-apple-system,sans-serif; display:flex; }\n'
        '#sidebar {\n'
        '  width:320px; height:100vh; overflow-y:auto; background:#16213e;\n'
        '  padding:12px; flex-shrink:0; border-right:1px solid #333;\n'
        '}\n'
        '#sidebar h2 { font-size:14px; margin-bottom:8px; color:#e94560; }\n'
        '.layer-toggle {\n'
        '  display:flex; align-items:center; gap:6px; padding:3px 4px;\n'
        '  font-size:12px; cursor:pointer; border-radius:3px;\n'
        '}\n'
        '.layer-toggle:hover { background:#1a1a40; }\n'
        '.layer-toggle .idx { color:#0f3460; font-family:monospace; }\n'
        '.layer-toggle .size { margin-left:auto; color:#666; font-size:10px; }\n'
        '#canvas-wrap {\n'
        '  flex:1; overflow:auto; padding:20px; display:flex;\n'
        '  align-items:flex-start; justify-content:center;\n'
        '}\n'
        '#canvas {\n'
        '  position:relative; width:' + str(sw) + 'px; height:' + str(sh) + 'px;\n'
        '  background:#222; border:1px solid #444; flex-shrink:0;\n'
        '}\n'
        '.layer {\n'
        '  position:absolute; image-rendering:auto;\n'
        '  transition: opacity 0.15s;\n'
        '}\n'
        '.layer.highlight {\n'
        '  outline:2px solid #e94560; outline-offset:1px;\n'
        '}\n'
        '.layer.hidden { display:none; }\n'
        '#controls {\n'
        '  position:fixed; bottom:12px; right:12px; display:flex; gap:8px;\n'
        '}\n'
        '#controls button {\n'
        '  padding:6px 14px; background:#0f3460; color:#fff; border:none;\n'
        '  border-radius:4px; cursor:pointer; font-size:12px;\n'
        '}\n'
        '#controls button:hover { background:#e94560; }\n'
        '</style>\n'
        '</head>\n'
        '<body>\n'
        '<div id="sidebar">\n'
        '  <h2>图层列表 (' + str(layer_count) + ' 层)</h2>\n'
        '  <div>\n'
        + sidebar_html + '\n'
        '  </div>\n'
        '</div>\n'
        '<div id="canvas-wrap">\n'
        '  <div id="canvas">\n'
        + elements_html + '\n'
        '  </div>\n'
        '</div>\n'
        '<div id="controls">\n'
        '  <button onclick="toggleAll(true)">全部显示</button>\n'
        '  <button onclick="toggleAll(false)">全部隐藏</button>\n'
        '</div>\n'
        '<script>\n'
        "document.querySelectorAll('.layer-toggle input').forEach(cb => {\n"
        "  cb.addEventListener('change', () => {\n"
        '    const idx = cb.dataset.idx;\n'
        "    const img = document.querySelector('.layer[data-idx=\"' + idx + '\"]');\n"
        "    if (img) img.classList.toggle('hidden', !cb.checked);\n"
        '  });\n'
        '});\n'
        "document.querySelectorAll('.layer-toggle').forEach(label => {\n"
        "  label.addEventListener('mouseenter', () => {\n"
        '    const idx = label.dataset.idx;\n'
        "    const img = document.querySelector('.layer[data-idx=\"' + idx + '\"]');\n"
        "    if (img) img.classList.add('highlight');\n"
        '  });\n'
        "  label.addEventListener('mouseleave', () => {\n"
        '    const idx = label.dataset.idx;\n'
        "    const img = document.querySelector('.layer[data-idx=\"' + idx + '\"]');\n"
        "    if (img) img.classList.remove('highlight');\n"
        '  });\n'
        '});\n'
        'function toggleAll(show) {\n'
        "  document.querySelectorAll('.layer-toggle input').forEach(cb => {\n"
        '    cb.checked = show;\n'
        "    cb.dispatchEvent(new Event('change'));\n"
        '  });\n'
        '}\n'
        '</script>\n'
        '</body>\n'
        '</html>'
    )

    return html


def main():
    parser = argparse.ArgumentParser(description="生成 HTML 预览页面")
    parser.add_argument("--csv", required=True, help="manifest.csv 路径")
    parser.add_argument("--assets", required=True, help="切图目录路径")
    parser.add_argument("--out", default="preview.html", help="输出 HTML 路径")
    parser.add_argument("--scale", type=float, default=0.5, help="缩放比例 (默认 0.5)")
    parser.add_argument("--embed", action="store_true", help="将图片嵌入 HTML (base64)")
    args = parser.parse_args()

    layers = parse_csv(args.csv)
    if not layers:
        print("[ERROR] CSV 中无有效图层", file=sys.stderr)
        sys.exit(1)

    max_x = max(l["x2"] for l in layers)
    max_y = max(l["y2"] for l in layers)

    html = generate_html(layers, args.assets, max_x, max_y, args.embed, args.scale)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[OK] 预览页面: {args.out}")
    print(f"[OK] 画布: {max_x}x{max_y} (缩放 {args.scale}x)")
    print(f"[OK] 图层: {len(layers)} 个")


if __name__ == "__main__":
    main()
