#!/usr/bin/env python3
"""
csv_to_uxml.py - 从 manifest.csv + 切图目录生成 Unity UI Toolkit 代码

输出:
  - {ScreenName}.uxml    布局文件
  - {ScreenName}.uss     样式文件
  - {ScreenName}Controller.cs  C# 控制器
  - sprites/             整理后的切图副本

用法:
  python csv_to_uxml.py --csv manifest.csv --assets ./cuts/ --out ./output --screen TeamScreen
"""

import argparse
import csv
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class LayerInfo:
    index: int
    name: str
    x1: int
    y1: int
    x2: int
    y2: int
    width: int
    height: int
    file: str
    # 推断出的信息
    element_type: str = "VisualElement"
    sanitized_name: str = ""
    callback: str = ""
    role: str = ""
    css_class: str = ""


# ---------------------------------------------------------------------------
# 名称清洗
# ---------------------------------------------------------------------------

_RE_NON_ALNUM = re.compile(r"[^a-zA-Z0-9_\u4e00-\u9fff]")
_RE_MULTI_UNDERSCORE = re.compile(r"_{2,}")


def sanitize_name(raw: str) -> str:
    """将中文图层名转为合法的 UXML name (允许中文, 去除特殊字符)"""
    s = raw.strip()
    s = s.replace("::", "_").replace(" ", "_")
    s = _RE_NON_ALNUM.sub("_", s)
    s = _RE_MULTI_UNDERSCORE.sub("_", s)
    s = s.strip("_")
    return s or "unnamed"


def to_css_class(raw: str) -> str:
    """生成 CSS class 名称 (纯 ASCII)"""
    s = sanitize_name(raw)
    # 把中文字符转成拼音缩写或直接移除, 这里简单移除
    s = re.sub(r"[\u4e00-\u9fff]+", "", s)
    s = _RE_MULTI_UNDERSCORE.sub("_", s).strip("_")
    if not s or s[0].isdigit():
        s = "el_" + s
    return s.lower()


def strip_chinese(s: str) -> str:
    """移除中文字符，保留ASCII部分"""
    result = re.sub(r"[\u4e00-\u9fff]+", "", s)
    result = _RE_MULTI_UNDERSCORE.sub("_", result).strip("_")
    return result or "element"


def to_pascal_case(s: str) -> str:
    """snake_case -> PascalCase"""
    return "".join(word.capitalize() for word in s.split("_") if word)


def to_camel_case(s: str) -> str:
    """snake_case -> camelCase"""
    pascal = to_pascal_case(s)
    return pascal[0].lower() + pascal[1:] if pascal else ""


def to_cs_identifier(raw_name: str, index: int = 0) -> str:
    """将图层名转为合法C#标识符 (纯ASCII), 用index区分重名"""
    s = sanitize_name(raw_name)
    s = strip_chinese(s)
    # 如果去除中文后内容太短或为空, 附加索引号
    if not s or len(s) < 3:
        s = f"El{index}_{s}" if s else f"El{index}"
    # 确保以字母开头
    if s[0].isdigit():
        s = "El" + s
    return to_pascal_case(s) if s else "Element"


# ---------------------------------------------------------------------------
# 图层类型推断
# ---------------------------------------------------------------------------

# 关键词 -> (element_type, role)
TYPE_RULES: List[Tuple[List[str], str, str]] = [
    (["btn", "按钮", "button"],                   "Button",        "button"),
    (["icon_", "icon"],                            "Button",        "icon-button"),
    (["选中", "selected", "tab", "选项"],          "Button",        "tab"),
    (["text", "文本", "label", "标题"],            "Label",         "label"),
    (["input", "输入", "search", "搜索"],          "TextField",     "input"),
    (["scroll", "滚动", "列表"],                   "ScrollView",    "scroll"),
    (["toggle", "开关", "checkbox"],               "Toggle",        "toggle"),
    (["slider", "滑块", "进度"],                   "Slider",        "slider"),
]

# 文本图层 - 内容很小且名称像中文文字
TEXT_PATTERNS = re.compile(
    r"^(级|队|战力|编队|图鉴|阵容推荐|英雄|装备|宝物|副本|团队|领地|玩法|"
    r"篝火等级|遗迹新层数解锁|英雄降级|篝火英雄|集结英雄|"
    r"\d+K?|960K|645700|260)$"
)


def infer_element_type(layer: LayerInfo, overrides: Optional[Dict] = None) -> None:
    """根据图层名推断元素类型, 填充 layer 的 element_type / role / callback"""

    name_lower = layer.name.lower().replace(" ", "_")

    # 优先使用覆盖配置
    if overrides and layer.name in overrides:
        ov = overrides[layer.name]
        layer.element_type = ov.get("type", "VisualElement")
        layer.callback = ov.get("callback", "")
        layer.role = ov.get("role", "")
        return

    # 文本推断: 小尺寸 + 名称是纯文字/数字
    if TEXT_PATTERNS.match(layer.name.strip()):
        layer.element_type = "Label"
        layer.role = "text"
        return

    # 关键词匹配
    for keywords, elem_type, role in TYPE_RULES:
        for kw in keywords:
            if kw in name_lower:
                layer.element_type = elem_type
                layer.role = role
                if elem_type == "Button":
                    cb_name = to_cs_identifier(layer.name, layer.index)
                    layer.callback = f"On{cb_name}Clicked"
                return

    # 默认: 图片元素
    layer.element_type = "VisualElement"
    layer.role = "sprite"


# ---------------------------------------------------------------------------
# CSV 解析
# ---------------------------------------------------------------------------

def parse_csv(csv_path: str) -> List[LayerInfo]:
    """解析 manifest.csv"""
    layers = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                layer = LayerInfo(
                    index=int(row["index"]),
                    name=row["name"].strip(),
                    x1=int(row["x1"]),
                    y1=int(row["y1"]),
                    x2=int(row["x2"]),
                    y2=int(row["y2"]),
                    width=int(row["width"]),
                    height=int(row["height"]),
                    file=row["file"].strip(),
                )
                layer.sanitized_name = sanitize_name(layer.name)
                layer.css_class = to_css_class(layer.name)
                layers.append(layer)
            except (ValueError, KeyError) as e:
                print(f"[WARN] 跳过行: {row} - {e}", file=sys.stderr)
    return layers


# ---------------------------------------------------------------------------
# Z-Order 排序 & 去重
# ---------------------------------------------------------------------------

def sort_layers(layers: List[LayerInfo]) -> List[LayerInfo]:
    """按面积降序 (大的在底层) + index 升序"""
    return sorted(layers, key=lambda l: (-l.width * l.height, l.index))


# ---------------------------------------------------------------------------
# UXML 生成
# ---------------------------------------------------------------------------

UXML_HEADER = """<?xml version="1.0" encoding="utf-8"?>
<ui:UXML xmlns:ui="UnityEngine.UIElements"
         xmlns:uie="UnityEditor.UIElements"
         xsi="http://www.w3.org/2001/XMLSchema-instance"
         engine="UnityEngine.UIElements"
         noNamespaceSchemaLocation="../../UIElementsSchema/UIElements.xsd">
  <ui:Style src="{uss_path}" />
  <ui:VisualElement name="{screen_name}-root" class="screen-root">
"""

UXML_FOOTER = """  </ui:VisualElement>
</ui:UXML>
"""


def _sprite_path(file: str, sprite_folder: str) -> str:
    """Unity 资产路径"""
    return f"url('project://database/{sprite_folder}/{file}')"


def generate_uxml(
    layers: List[LayerInfo],
    screen_name: str,
    sprite_folder: str = "Assets/UI/Sprites",
) -> str:
    """生成 UXML 字符串"""

    uss_path = f"{screen_name}.uss"
    lines = [UXML_HEADER.format(uss_path=uss_path, screen_name=screen_name)]

    for layer in layers:
        indent = "    "
        name_attr = f'name="{layer.sanitized_name}"'
        style_pos = (
            f"left:{layer.x1}px; top:{layer.y1}px; "
            f"width:{layer.width}px; height:{layer.height}px;"
        )
        sprite_url = _sprite_path(layer.file, sprite_folder)

        if layer.element_type == "Button":
            lines.append(
                f'{indent}<ui:Button {name_attr} class="sprite-button {layer.css_class}"\n'
                f'{indent}  style="{style_pos}">\n'
                f'{indent}  <ui:VisualElement class="sprite-bg"\n'
                f'{indent}    style="background-image: {sprite_url}; '
                f'width:100%; height:100%;" />\n'
                f'{indent}</ui:Button>\n'
            )

        elif layer.element_type == "Label":
            text_content = layer.name if layer.role == "text" else ""
            lines.append(
                f'{indent}<ui:Label {name_attr} text="{text_content}" '
                f'class="text-label {layer.css_class}"\n'
                f'{indent}  style="{style_pos}" />\n'
            )

        elif layer.element_type == "ScrollView":
            lines.append(
                f'{indent}<ui:ScrollView {name_attr} class="scroll-view {layer.css_class}"\n'
                f'{indent}  style="{style_pos}">\n'
                f'{indent}  <!-- 子元素在此处填充 -->\n'
                f'{indent}</ui:ScrollView>\n'
            )

        elif layer.element_type == "TextField":
            lines.append(
                f'{indent}<ui:TextField {name_attr} class="text-field {layer.css_class}"\n'
                f'{indent}  style="{style_pos}" />\n'
            )

        else:
            # VisualElement (sprite)
            lines.append(
                f'{indent}<ui:VisualElement {name_attr} class="sprite-element {layer.css_class}"\n'
                f'{indent}  style="{style_pos} '
                f'background-image: {sprite_url};" />\n'
            )

    lines.append(UXML_FOOTER)
    return "".join(lines)


# ---------------------------------------------------------------------------
# USS 生成
# ---------------------------------------------------------------------------

def generate_uss(layers: List[LayerInfo], canvas_w: int, canvas_h: int) -> str:
    """生成 USS 样式文件"""
    lines = [
        f"/* Auto-generated USS - Canvas: {canvas_w}x{canvas_h} */\n\n",
        ".screen-root {\n",
        f"    width: {canvas_w}px;\n",
        f"    height: {canvas_h}px;\n",
        "    position: relative;\n",
        "    overflow: hidden;\n",
        "}\n\n",
        ".sprite-element {\n",
        "    position: absolute;\n",
        "    -unity-background-scale-mode: scale-to-fit;\n",
        "}\n\n",
        ".sprite-button {\n",
        "    position: absolute;\n",
        "    background-color: rgba(0, 0, 0, 0);\n",
        "    border-width: 0;\n",
        "    padding: 0;\n",
        "    margin: 0;\n",
        "}\n\n",
        ".sprite-button:hover {\n",
        "    opacity: 0.85;\n",
        "}\n\n",
        ".sprite-button:active {\n",
        "    opacity: 0.7;\n",
        "}\n\n",
        ".sprite-bg {\n",
        "    -unity-background-scale-mode: scale-to-fit;\n",
        "}\n\n",
        ".text-label {\n",
        "    position: absolute;\n",
        "    -unity-text-align: middle-center;\n",
        "    color: rgb(255, 255, 255);\n",
        "    -unity-font-style: bold;\n",
        "    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);\n",
        "}\n\n",
        ".scroll-view {\n",
        "    position: absolute;\n",
        "}\n\n",
        ".text-field {\n",
        "    position: absolute;\n",
        "}\n\n",
    ]

    # 按元素类型生成特定样式
    buttons = [l for l in layers if l.element_type == "Button"]
    labels = [l for l in layers if l.element_type == "Label"]

    if labels:
        lines.append("/* --- 文本标签尺寸样式 --- */\n")
        for label in labels:
            font_size = max(10, int(label.height * 0.65))
            lines.append(
                f".{label.css_class} {{\n"
                f"    font-size: {font_size}px;\n"
                f"}}\n\n"
            )

    return "".join(lines)


# ---------------------------------------------------------------------------
# C# Controller 生成
# ---------------------------------------------------------------------------

CS_TEMPLATE = """using UnityEngine;
using UnityEngine.UIElements;

/// <summary>
/// Auto-generated UI Controller for {screen_name}
/// Generated from manifest.csv by Unity UI Builder Skill
/// </summary>
public class {screen_name}Controller : MonoBehaviour
{{
    [SerializeField] private UIDocument _uiDocument;

    private VisualElement _root;

    // --- 元素引用 ---
{field_declarations}

    private void OnEnable()
    {{
        _root = _uiDocument.rootVisualElement;
        QueryElements();
        BindCallbacks();
    }}

    private void OnDisable()
    {{
        UnbindCallbacks();
    }}

    /// <summary>
    /// 查询并缓存所有 UI 元素引用
    /// </summary>
    private void QueryElements()
    {{
{query_statements}
    }}

    /// <summary>
    /// 绑定按钮回调
    /// </summary>
    private void BindCallbacks()
    {{
{bind_statements}
    }}

    /// <summary>
    /// 解绑按钮回调
    /// </summary>
    private void UnbindCallbacks()
    {{
{unbind_statements}
    }}

    // --- 回调方法 (请在此实现业务逻辑) ---
{callback_methods}
}}
"""


def generate_controller(layers: List[LayerInfo], screen_name: str) -> str:
    """生成 C# 控制器"""

    buttons = [l for l in layers if l.element_type == "Button" and l.callback]
    labels = [l for l in layers if l.element_type == "Label"]

    # 生成唯一字段名：用 index 确保不重名
    seen_field_names = set()
    unique_buttons = []
    for b in buttons:
        field_name = "_btn" + to_cs_identifier(b.name, b.index)
        # 如果字段名仍然重复，追加 index
        if field_name in seen_field_names:
            field_name = "_btn" + to_cs_identifier(b.name, b.index) + str(b.index)
        seen_field_names.add(field_name)
        b._field_name = field_name  # 临时附加属性
        unique_buttons.append(b)

    # 字段声明
    field_lines = []
    for b in unique_buttons:
        field_lines.append(f"    private Button {b._field_name};")

    # Query 语句
    query_lines = []
    for b in unique_buttons:
        query_lines.append(
            f'        {b._field_name} = _root.Q<Button>("{b.sanitized_name}");'
        )

    # Bind 语句
    bind_lines = []
    for b in unique_buttons:
        bind_lines.append(
            f"        {b._field_name}?.RegisterCallback<ClickEvent>(evt => {b.callback}());"
        )

    # Unbind 语句
    unbind_lines = []
    for b in unique_buttons:
        unbind_lines.append(
            f"        {b._field_name}?.UnregisterCallback<ClickEvent>(evt => {b.callback}());"
        )

    # 回调方法 (按 callback 名去重, 同名回调只生成一个方法)
    callback_lines = []
    seen_cb_names = set()
    for b in unique_buttons:
        if b.callback not in seen_cb_names:
            seen_cb_names.add(b.callback)
            callback_lines.append(
                f"    private void {b.callback}()\n"
                f"    {{\n"
                f'        Debug.Log("{b.callback} triggered - {b.name}");\n'
                f"    }}\n"
            )

    return CS_TEMPLATE.format(
        screen_name=screen_name,
        field_declarations="\n".join(field_lines) if field_lines else "    // (无按钮元素)",
        query_statements="\n".join(query_lines) if query_lines else "        // (无需查询)",
        bind_statements="\n".join(bind_lines) if bind_lines else "        // (无需绑定)",
        unbind_statements="\n".join(unbind_lines) if unbind_lines else "        // (无需解绑)",
        callback_methods="\n".join(callback_lines) if callback_lines else "    // (无回调方法)",
    )


# ---------------------------------------------------------------------------
# 切图复制
# ---------------------------------------------------------------------------

def copy_sprites(layers: List[LayerInfo], assets_dir: str, out_dir: str) -> int:
    """复制切图到输出目录, 返回复制数量"""
    sprites_dir = os.path.join(out_dir, "sprites")
    os.makedirs(sprites_dir, exist_ok=True)

    copied = 0
    for layer in layers:
        src = os.path.join(assets_dir, layer.file)
        dst = os.path.join(sprites_dir, layer.file)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            copied += 1
        else:
            print(f"[WARN] 切图不存在: {src}", file=sys.stderr)
    return copied


# ---------------------------------------------------------------------------
# 画布尺寸推断
# ---------------------------------------------------------------------------

def infer_canvas_size(layers: List[LayerInfo]) -> Tuple[int, int]:
    """从图层坐标推断画布尺寸"""
    max_x = max(l.x2 for l in layers) if layers else 1242
    max_y = max(l.y2 for l in layers) if layers else 2688
    # 取到常见分辨率的上界
    return max_x, max_y


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="从 manifest.csv + 切图目录生成 Unity UI Toolkit 代码"
    )
    parser.add_argument("--csv", required=True, help="manifest.csv 路径")
    parser.add_argument("--assets", required=True, help="切图目录路径")
    parser.add_argument("--out", required=True, help="输出目录")
    parser.add_argument("--screen", default="GeneratedScreen", help="界面名称 (PascalCase)")
    parser.add_argument("--overrides", default=None, help="type_overrides.json 路径")
    parser.add_argument("--canvas", default=None, help="画布尺寸, 如 1242x2688")
    parser.add_argument("--target", default=None, help="目标分辨率, 如 1080x1920 (可选缩放)")
    parser.add_argument(
        "--sprite-folder",
        default="Assets/UI/Sprites",
        help="Unity 工程中的 Sprite 文件夹路径",
    )
    args = parser.parse_args()

    # 加载覆盖配置
    overrides = None
    if args.overrides and os.path.exists(args.overrides):
        with open(args.overrides, "r", encoding="utf-8") as f:
            overrides = json.load(f)
        print(f"[INFO] 加载覆盖配置: {len(overrides)} 条规则")

    # 解析 CSV
    print(f"[INFO] 解析 CSV: {args.csv}")
    layers = parse_csv(args.csv)
    print(f"[INFO] 解析到 {len(layers)} 个图层")

    if not layers:
        print("[ERROR] CSV 中无有效图层", file=sys.stderr)
        sys.exit(1)

    # 推断元素类型
    for layer in layers:
        infer_element_type(layer, overrides)

    # 排序 (大面积在底层)
    layers = sort_layers(layers)

    # 画布尺寸
    if args.canvas:
        cw, ch = map(int, args.canvas.split("x"))
    else:
        cw, ch = infer_canvas_size(layers)
    print(f"[INFO] 画布尺寸: {cw}x{ch}")

    # 目标缩放
    if args.target:
        tw, th = map(int, args.target.split("x"))
        sx, sy = tw / cw, th / ch
        scale = min(sx, sy)
        print(f"[INFO] 缩放到 {tw}x{th} (比例: {scale:.3f})")
        for layer in layers:
            layer.x1 = int(layer.x1 * scale)
            layer.y1 = int(layer.y1 * scale)
            layer.x2 = int(layer.x2 * scale)
            layer.y2 = int(layer.y2 * scale)
            layer.width = int(layer.width * scale)
            layer.height = int(layer.height * scale)
        cw, ch = tw, th

    # 创建输出目录
    os.makedirs(args.out, exist_ok=True)

    # 生成 UXML
    uxml = generate_uxml(layers, args.screen, args.sprite_folder)
    uxml_path = os.path.join(args.out, f"{args.screen}.uxml")
    with open(uxml_path, "w", encoding="utf-8") as f:
        f.write(uxml)
    print(f"[OK] UXML: {uxml_path}")

    # 生成 USS
    uss = generate_uss(layers, cw, ch)
    uss_path = os.path.join(args.out, f"{args.screen}.uss")
    with open(uss_path, "w", encoding="utf-8") as f:
        f.write(uss)
    print(f"[OK] USS:  {uss_path}")

    # 生成 C#
    cs = generate_controller(layers, args.screen)
    cs_path = os.path.join(args.out, f"{args.screen}Controller.cs")
    with open(cs_path, "w", encoding="utf-8") as f:
        f.write(cs)
    print(f"[OK] C#:   {cs_path}")

    # 复制切图
    copied = copy_sprites(layers, args.assets, args.out)
    print(f"[OK] Sprites: 复制 {copied}/{len(layers)} 个文件")

    # 统计
    buttons = [l for l in layers if l.element_type == "Button"]
    labels = [l for l in layers if l.element_type == "Label"]
    sprites = [l for l in layers if l.role == "sprite"]
    print(f"\n[统计]")
    print(f"  按钮: {len(buttons)}")
    print(f"  文本: {len(labels)}")
    print(f"  图片: {len(sprites)}")
    print(f"  总计: {len(layers)} 个元素")
    print(f"\n[完成] 输出目录: {args.out}")


if __name__ == "__main__":
    main()
