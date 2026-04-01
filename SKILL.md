---
name: Unity UI Builder
description: |
  从 PSD 切图 + CSV manifest 或原始 PSD 文件，程序化生成 Unity UI Toolkit (UIElements) 界面代码。
  支持 Unity 2021.3 LTS。输出 UXML 布局、USS 样式、C# 控制器和 Sprite 导入配置。
version: 1.0.1
triggers:
  - unity ui
  - 生成界面
  - psd to unity
  - csv to uxml
  - ui toolkit
  - uielements
  - 切图生成
  - 游戏界面
---

# Unity UI Builder Skill

从设计稿（PSD 或切图+CSV）程序化生成 Unity UI Toolkit 界面代码，适用于 Unity 2021.3 LTS。

## 能力概览

本 Skill 提供两条输入管线和一条统一输出：

```
输入 A: PSD 文件
  └─ scripts/psd_export.py → 切图 PNG + manifest.csv

输入 B: 切图目录 + manifest.csv (已有切图)
  └─ 直接使用

统一处理:
  manifest.csv + 切图 PNG
  └─ scripts/csv_to_uxml.py
      ├─ output/{ScreenName}.uxml      (布局)
      ├─ output/{ScreenName}.uss       (样式)
      ├─ output/{ScreenName}Controller.cs (C# 控制器)
      └─ output/sprites/               (整理后的切图)
```

## 前置条件

- Python 3.8+
- `pip install psd-tools Pillow`（仅 PSD 管线需要 psd-tools）
- Unity 2021.3 LTS（目标运行时）

## 额外工具

### HTML 布局预览

在生成 Unity 代码前，可以用浏览器预览切图布局：

```bash
python scripts/preview_layout.py \
  --csv manifest.csv \
  --assets ./cuts \
  --out preview.html
```

打开 `preview.html` 即可查看所有切图的叠加效果和坐标标注。

## 快速开始

### 管线 A：从 PSD 文件生成

```bash
# 第 1 步：导出 PSD 为切图 + CSV
python scripts/psd_export.py --psd "path/to/design.psd" --out ./export

# 第 2 步：从 CSV 生成 Unity 代码
python scripts/csv_to_uxml.py --csv ./export/manifest.csv --assets ./export --out ./output --screen MainUI
```

### 管线 B：从已有切图 + CSV 生成

```bash
python scripts/csv_to_uxml.py \
  --csv "path/to/manifest.csv" \
  --assets "path/to/cut_images/" \
  --out ./output \
  --screen TeamScreen
```

## manifest.csv 格式规范

CSV 必须包含以下列（逗号分隔，第一行为表头）：

| 列名   | 类型   | 说明                          |
|--------|--------|-------------------------------|
| index  | int    | 图层序号（从 1 开始）         |
| name   | string | 图层名称（来自 PSD/Figma）    |
| x1     | int    | 左上角 X（像素，相对画布）    |
| y1     | int    | 左上角 Y                      |
| x2     | int    | 右下角 X                      |
| y2     | int    | 右下角 Y                      |
| width  | int    | 宽度（像素）                  |
| height | int    | 高度（像素）                  |
| file   | string | 对应切图文件名                |

示例：
```csv
index,name,x1,y1,x2,y2,width,height,file
1,图层 8314,862,892,1157,998,295,106,001_图层_8314.png
2,背景,0,0,1242,2688,1242,2688,bg_main.png
```

## 输出文件说明

### UXML 布局文件

生成的 UXML 使用绝对定位还原设计稿坐标：

```xml
<?xml version="1.0" encoding="utf-8"?>
<ui:UXML xmlns:ui="UnityEngine.UIElements"
         xmlns:uie="UnityEditor.UIElements">
  <ui:VisualElement name="root" class="screen-root">
    <!-- 背景层 -->
    <ui:VisualElement name="layer-bg" class="sprite-element"
      style="left:0px; top:0px; width:1242px; height:2688px;
             background-image: url('project://database/Assets/UI/Sprites/bg_main.png');" />
    <!-- 按钮 -->
    <ui:Button name="btn-confirm" class="sprite-button"
      style="left:862px; top:892px; width:295px; height:106px;">
      <ui:VisualElement class="sprite-element"
        style="background-image: url('project://database/Assets/UI/Sprites/001_图层_8314.png');" />
    </ui:Button>
  </ui:VisualElement>
</ui:UXML>
```

### USS 样式文件

```css
.screen-root {
    width: 1242px;
    height: 2688px;
    position: relative;
}

.sprite-element {
    position: absolute;
    background-size: contain;
}

.sprite-button {
    position: absolute;
    background-color: rgba(0,0,0,0);
    border-width: 0;
    padding: 0;
    margin: 0;
}
```

### C# 控制器

自动生成按钮绑定代码，支持多个相似图层名的去重处理：

```csharp
using UnityEngine;
using UnityEngine.UIElements;

public class TeamScreenController : MonoBehaviour
{
    [SerializeField] private UIDocument _uiDocument;

    private VisualElement _root;
    
    // 自动去重：icon_更换、icon_更换_拷贝 → _btnIcon, _btnIcon2
    private Button _btnIcon;
    private Button _btnIcon2;
    private Button _btnIcon3;
    private Button _btnIcon4;

    private void OnEnable()
    {
        _root = _uiDocument.rootVisualElement;
        QueryElements();
        BindCallbacks();
    }
    
    private void QueryElements()
    {
        _btnIcon = _root.Q<Button>("icon_更换");
        _btnIcon2 = _root.Q<Button>("icon_更换_拷贝");
        _btnIcon3 = _root.Q<Button>("icon_筛选");
        _btnIcon4 = _root.Q<Button>("icon_筛选_拷贝");
    }

    private void BindCallbacks()
    {
        // 相同前缀的按钮自动共享回调方法
        _btnIcon?.RegisterCallback<ClickEvent>(evt => OnIconClicked());
        _btnIcon2?.RegisterCallback<ClickEvent>(evt => OnIconClicked());
        _btnIcon3?.RegisterCallback<ClickEvent>(evt => OnIconClicked());
        _btnIcon4?.RegisterCallback<ClickEvent>(evt => OnIconClicked());
    }
    
    private void UnbindCallbacks()
    {
        _btnIcon?.UnregisterCallback<ClickEvent>(evt => OnIconClicked());
        _btnIcon2?.UnregisterCallback<ClickEvent>(evt => OnIconClicked());
        _btnIcon3?.UnregisterCallback<ClickEvent>(evt => OnIconClicked());
        _btnIcon4?.UnregisterCallback<ClickEvent>(evt => OnIconClicked());
    }

    // 相同类型按钮只生成一个回调方法
    private void OnIconClicked()
    {
        Debug.Log("Icon clicked");
    }
}
```

## 图层名称 → 元素类型推断规则

脚本通过图层名称中的关键词自动推断 UI 元素类型：

| 关键词匹配            | 生成类型          | 说明                 |
|-----------------------|-------------------|----------------------|
| `btn`, `按钮`, `icon_` | `ui:Button`       | 可点击按钮           |
| `文本`, `text`, `label`| `ui:Label`        | 文本标签             |
| `输入`, `input`        | `ui:TextField`    | 输入框               |
| `滚动`, `scroll`       | `ui:ScrollView`   | 滚动容器             |
| `组`, `group`, `组_`   | `ui:VisualElement`| 分组容器（含子元素） |
| 其他                   | `ui:VisualElement`| 默认图片元素         |

## 高级用法

### 自定义类型映射

创建 `type_overrides.json` 覆盖默认推断：

```json
{
  "icon_更换": { "type": "Button", "callback": "OnSwapClicked" },
  "icon_筛选": { "type": "Button", "callback": "OnFilterClicked" },
  "图层_8277_拷贝_4": { "type": "ScrollView", "direction": "vertical" },
  "组_885": { "type": "VisualElement", "role": "tab-bar" }
}
```

```bash
python scripts/csv_to_uxml.py \
  --csv manifest.csv \
  --assets ./cuts/ \
  --out ./output \
  --screen TeamScreen \
  --overrides type_overrides.json
```

### 设计尺寸适配

默认画布为 1242×2688（iPhone 竖屏 @3x）。可指定目标分辨率自动缩放：

```bash
python scripts/csv_to_uxml.py \
  --csv manifest.csv \
  --assets ./cuts/ \
  --out ./output \
  --screen TeamScreen \
  --canvas 1242x2688 \
  --target 1080x1920
```

## Unity 集成步骤

1. 将 `output/sprites/` 复制到 `Assets/UI/Sprites/`
2. 将 `.uxml` 和 `.uss` 复制到 `Assets/UI/Documents/`
3. 将 `Controller.cs` 复制到 `Assets/Scripts/UI/`
4. 场景中创建空 GameObject → 添加 `UIDocument` 组件 → 拖入 UXML
5. 添加 Controller 脚本 → 运行

或使用 Unity Editor 集成脚本一键导入：

```bash
# 将 scripts/Editor/UIBuilderImporter.cs 放入 Assets/Editor/
# Unity 菜单: Tools > UI Builder > Import from CSV
```

## 注意事项

- Unity 2021.3 的 UI Toolkit Runtime 不支持所有 USS 属性，脚本会自动过滤不兼容的属性
- 大尺寸 PSD（>100MB）切图可能较慢，建议提前用设计工具导出切图+CSV
- 生成的 UXML 使用绝对定位还原设计稿，如需响应式布局需手动调整 Flex 模式
- 中文图层名会被清洗为合法的 USS class name（保留原名作为 name 属性）
