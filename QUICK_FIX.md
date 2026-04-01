# 快速修复:Unity中看不到图片

## 问题诊断

你生成的UXML文件路径是 `project://database/Assets/UI/Sprites/xxx.png`,但Unity项目中:
1. 这个路径不存在
2. 切图没有导入到Unity

## 🚀 最快解决方案(2分钟)

### 方案A:重新生成时指定自定义路径

如果你的Unity项目中切图在其他位置,重新生成时指定正确路径:

```bash
cd D:\Code\uielements-skill\scripts

# 假设你的切图在 Assets/MyUI/Images/ 下
python csv_to_uxml.py \
  --csv ../test_data/manifest.csv \
  --assets ../test_data/cuts \
  --out ../test_output \
  --screen TeamScreen \
  --sprite-folder "Assets/MyUI/Images"
```

### 方案B:手动替换UXML中的路径(1分钟)

如果已经生成了文件,直接修改UXML:

```bash
# 打开 TeamScreen.uxml 文件
# 查找所有:  Assets/UI/Sprites
# 替换为:    Assets/你的实际路径
```

用VSCode或任何编辑器全局替换即可。

### 方案C:按照标准路径导入切图(推荐)

1. **在Unity项目中创建目录**:
   ```
   Assets/
   └── UI/
       └── Sprites/
   ```

2. **复制切图到Unity**:
   ```bash
   # 将生成的切图复制到Unity项目
   copy D:\Code\uielements-skill\test_output\sprites\*.png YourUnityProject\Assets\UI\Sprites\
   ```

3. **在Unity中配置Sprite**:
   - 选中所有导入的PNG
   - Inspector → Texture Type: **Sprite (2D and UI)**
   - 点击Apply

4. **导入UXML/USS**:
   ```bash
   copy D:\Code\uielements-skill\test_output\TeamScreen.uxml YourUnityProject\Assets\UI\
   copy D:\Code\uielements-skill\test_output\TeamScreen.uss YourUnityProject\Assets\UI\
   ```

5. **在Unity场景中使用**:
   - 创建GameObject
   - 添加UIDocument组件
   - 拖入TeamScreen.uxml到Source Asset字段

## ⚠️ 当前测试数据的问题

你使用的 `test_data/cuts/` 目录中的切图是**空文件**,只用于测试脚本逻辑:

```bash
$ ls -lh test_data/cuts/
# 所有PNG都是0字节或几字节的占位符
```

**如果要看到真实UI**:
- 用真实的PSD文件运行 `psd_export.py` 导出切图
- 或者手动准备真实的PNG切图

## 🔍 验证步骤

1. **检查Unity Console**:看是否有 "Asset not found" 错误
2. **UI Builder预览**:直接在Unity Editor中打开UXML看是否能看到
3. **检查Sprite配置**:确保PNG的Texture Type是Sprite

## 完整示例:从零开始

假设你的Unity项目在 `C:\MyGame\`:

```bash
# 1. 创建Unity目录结构
mkdir C:\MyGame\Assets\UI\Sprites

# 2. 使用真实PSD(或准备真实切图)
cd D:\Code\uielements-skill\scripts
python psd_export.py --psd path/to/real_design.psd --out ../export

# 3. 生成Unity代码
python csv_to_uxml.py \
  --csv ../export/manifest.csv \
  --assets ../export \
  --out ../output \
  --screen TeamScreen \
  --sprite-folder "Assets/UI/Sprites"

# 4. 复制文件到Unity
copy ..\output\sprites\*.png C:\MyGame\Assets\UI\Sprites\
copy ..\output\TeamScreen.uxml C:\MyGame\Assets\UI\
copy ..\output\TeamScreen.uss C:\MyGame\Assets\UI\
copy ..\output\TeamScreenController.cs C:\MyGame\Assets\UI\Scripts\

# 5. 在Unity中:
# - 选中所有PNG → Inspector → Texture Type: Sprite (2D and UI) → Apply
# - 创建GameObject → 添加UIDocument → 拖入TeamScreen.uxml
# - 添加TeamScreenController脚本 → 拖入UIDocument组件引用
```

完成!

## 详细指南

需要更多细节?查看:
- `UNITY_IMPORT_GUIDE.md` - 完整的Unity导入指南
- `README.md` - 项目使用说明
- `SKILL.md` - 技能文档
