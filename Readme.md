# Unity UI Builder Skill

从设计稿（PSD 或切图+CSV）程序化生成 Unity UI Toolkit 界面代码的自动化工具。

## 快速开始

### 安装依赖

```bash
pip install psd-tools Pillow
```

### 方式1：从 PSD 文件生成

```bash
# 步骤1：导出 PSD → 切图 + manifest.csv
python scripts/psd_export.py --psd design.psd --out ./export

# 步骤2：生成 Unity 代码
python scripts/csv_to_uxml.py \
  --csv ./export/manifest.csv \
  --assets ./export \
  --out ./output \
  --screen MainUI
```

### 方式2：从切图 + CSV 生成

```bash
python scripts/csv_to_uxml.py \
  --csv manifest.csv \
  --assets ./cuts \
  --out ./output \
  --screen TeamScreen
```

### 预览布局（可选）

```bash
python scripts/preview_layout.py \
  --csv manifest.csv \
  --assets ./cuts \
  --out preview.html
```

在浏览器中打开 `preview.html` 查看切图叠加效果。

## 输出文件

生成完整的 Unity UI Toolkit 资产：

```
output/
├── TeamScreen.uxml              # UXML 布局文件
├── TeamScreen.uss               # USS 样式文件
├── TeamScreenController.cs      # C# 控制器脚本
└── sprites/                     # 整理后的切图
    ├── bg_main.png
    ├── btn_confirm.png
    └── ...
```

## Unity 项目集成

### 方法1：手动导入

1. 复制 `output/sprites/` → `Assets/UI/Sprites/`
2. 复制 `.uxml` 和 `.uss` → `Assets/UI/Documents/`
3. 复制 `Controller.cs` → `Assets/Scripts/UI/`
4. 场景中创建空 GameObject
5. 添加 `UIDocument` 组件，拖入 UXML
6. 添加 Controller 脚本，运行测试

### 方法2：编辑器集成（推荐）

将 `scripts/Editor/UIBuilderImporter.cs` 复制到 Unity 项目的 `Assets/Editor/` 目录。

使用菜单：**Tools > UI Builder > Import from CSV**

## 核心特性

### 智能类型推断

根据图层名称自动识别 UI 元素类型：

| 图层名包含              | 生成类型         |
|------------------------|-----------------|
| `btn`, `按钮`, `icon_`  | Button          |
| `文本`, `text`, `label` | Label           |
| `输入`, `input`         | TextField       |
| `滚动`, `scroll`        | ScrollView      |

### 字段名自动去重

相同前缀的按钮自动添加序号：

```csharp
// 图层名: icon_更换, icon_更换_拷贝, icon_筛选, icon_筛选_拷贝
private Button _btnIcon;      // icon_更换
private Button _btnIcon2;     // icon_更换_拷贝
private Button _btnIcon3;     // icon_筛选
private Button _btnIcon4;     // icon_筛选_拷贝
```

### 回调方法合并

相同类型按钮自动共享回调方法，减少重复代码：

```csharp
// 4个icon按钮共享1个回调
private void OnIconClicked() 
{
    Debug.Log("Icon clicked");
}
```

## manifest.csv 格式

CSV 文件必须包含以下列：

| 列名   | 类型   | 说明                       |
|--------|--------|----------------------------|
| index  | int    | 图层序号                   |
| name   | string | 图层名称（用于类型推断）   |
| x1,y1  | int    | 左上角坐标（像素）         |
| x2,y2  | int    | 右下角坐标                 |
| width  | int    | 宽度                       |
| height | int    | 高度                       |
| file   | string | 对应的切图文件名           |

示例：

```csv
index,name,x1,y1,x2,y2,width,height,file
0,bg_main,0,0,1242,2688,1242,2688,bg_main.png
1,icon_更换,50,100,150,200,100,100,icon_change.png
2,btn_confirm,50,300,250,400,200,100,btn_confirm.png
3,text_title,50,50,300,90,250,40,empty.png
```

## 高级用法

### 自定义类型映射

创建 `type_overrides.json` 覆盖默认推断规则：

```json
{
  "icon_更换": { 
    "type": "Button", 
    "callback": "OnSwapClicked" 
  },
  "图层_8277": { 
    "type": "ScrollView" 
  }
}
```

使用覆盖配置：

```bash
python scripts/csv_to_uxml.py \
  --csv manifest.csv \
  --assets ./cuts \
  --out ./output \
  --screen TeamScreen \
  --overrides type_overrides.json
```

### 分辨率适配

自动缩放到目标分辨率：

```bash
python scripts/csv_to_uxml.py \
  --csv manifest.csv \
  --assets ./cuts \
  --out ./output \
  --screen TeamScreen \
  --canvas 1242x2688 \
  --target 1080x1920
```

## 脚本说明

### psd_export.py

从 PSD 文件导出切图和坐标清单。

**参数**:
- `--psd`: PSD 文件路径
- `--out`: 输出目录
- `--dpi`: DPI（默认72）

### csv_to_uxml.py

主生成脚本，从 CSV + 切图生成 Unity 代码。

**参数**:
- `--csv`: manifest.csv 路径（必需）
- `--assets`: 切图目录（必需）
- `--out`: 输出目录（必需）
- `--screen`: 界面名称（默认 GeneratedScreen）
- `--overrides`: type_overrides.json 路径
- `--canvas`: 画布尺寸（如 1242x2688）
- `--target`: 目标分辨率（如 1080x1920）
- `--sprite-folder`: Unity Sprite 目录路径

### preview_layout.py

生成 HTML 预览页面。

**参数**:
- `--csv`: manifest.csv 路径（必需）
- `--assets`: 切图目录（必需）
- `--out`: 输出 HTML 文件路径
- `--scale`: 缩放比例（默认0.5）
- `--embed`: 嵌入切图为 base64（默认开启）

## 注意事项

- Unity 2021.3 LTS Runtime 不支持所有 USS 属性
- 大尺寸 PSD（>100MB）建议提前导出切图
- 生成的 UXML 使用绝对定位，如需响应式布局需手动调整
- 中文图层名会被清洗为合法的 CSS class 名称

## 版本历史

### v1.0.1 (2026-04-01)
- 修复 C# 字段名去重逻辑（用 index 区分相同前缀）
- 修复回调方法合并（相同回调只生成一个方法体）
- 完善测试用例和文档

### v1.0.0 (Initial Release)
- PSD 切图导出
- CSV to UXML/USS/C# 生成
- HTML 布局预览
- Unity Editor 集成

## License

MIT License
