# Unity 导入指南

## 问题说明

如果你在Unity中看到UXML布局但**看不到图片**,原因是:

1. **切图未导入** - 生成的UXML引用 `Assets/UI/Sprites/xxx.png`,但你的项目中没有这些图片
2. **路径不匹配** - UXML中的路径必须与Unity项目的实际Assets路径一致

## 正确的导入流程

### 第 1 步:准备Unity项目结构

在Unity项目中创建以下目录:

```
YourUnityProject/Assets/
├── UI/
│   ├── Sprites/          ← 切图放这里
│   ├── UXML/             ← UXML/USS文件放这里
│   └── Scripts/          ← C#控制器放这里
```

### 第 2 步:导入切图到Unity

1. **复制切图**:将生成的 `test_output/sprites/` 目录下的所有PNG文件复制到Unity项目的 `Assets/UI/Sprites/`

```bash
# 示例(根据你的实际路径调整)
cp D:\Code\uielements-skill\test_output\sprites\*.png YourUnityProject\Assets\UI\Sprites\
```

2. **配置切图为Sprite**:
   - 在Unity中选中所有导入的PNG文件
   - 在Inspector中设置:
     - Texture Type: **Sprite (2D and UI)**
     - Sprite Mode: **Single**
     - Pixels Per Unit: **100** (或根据你的UI设计调整)
     - Filter Mode: **Bilinear**
     - Compression: **None** (开发阶段)
   - 点击 **Apply**

### 第 3 步:导入UXML/USS文件

将生成的文件复制到Unity:

```bash
cp D:\Code\uielements-skill\test_output\TeamScreen.uxml YourUnityProject\Assets\UI\UXML\
cp D:\Code\uielements-skill\test_output\TeamScreen.uss YourUnityProject\Assets\UI\UXML\
```

### 第 4 步:导入C#控制器

```bash
cp D:\Code\uielements-skill\test_output\TeamScreenController.cs YourUnityProject\Assets\UI\Scripts\
```

### 第 5 步:修改UXML中的路径(如果需要)

如果你的Sprites目录不在 `Assets/UI/Sprites/`,需要修改UXML中的路径:

打开 `TeamScreen.uxml`,查找所有:
```xml
url('project://database/Assets/UI/Sprites/xxx.png')
```

替换为你的实际路径:
```xml
url('project://database/Assets/YourActualPath/xxx.png')
```

### 第 6 步:在Unity场景中使用

1. 创建空GameObject
2. 添加 `UIDocument` 组件
3. 将 `TeamScreen.uxml` 拖到 `Source Asset` 字段
4. 添加 `TeamScreenController` 脚本组件
5. 将 `UIDocument` 组件拖到控制器的 `_uiDocument` 字段

## 验证步骤

1. **检查Console**:看是否有资源加载错误
2. **UI Builder预览**:在Unity编辑器中打开UXML文件,用UI Builder查看
3. **运行场景**:点击播放按钮,检查UI是否正常显示

## 自动化路径配置(可选)

如果你希望修改默认路径,可以编辑 `csv_to_uxml.py`:

```python
# 第 448 行左右
sprite_uri = f"url('project://database/Assets/UI/Sprites/{sprite_filename}');"

# 修改为你的路径
sprite_uri = f"url('project://database/Assets/YourPath/{sprite_filename}');"
```

然后重新运行生成脚本。

## 常见问题

### Q: 我看到白色方块,没有图片
**A**: 切图未正确导入或Texture Type不是Sprite。检查Inspector设置。

### Q: Console报错 "Asset not found"
**A**: UXML中的路径与实际Assets路径不匹配。检查第5步的路径配置。

### Q: 按钮点击没反应
**A**: 检查C#控制器的 `_uiDocument` 字段是否已正确赋值。

### Q: 我想用不同的目录结构
**A**: 
1. 修改 `csv_to_uxml.py` 中的路径模板
2. 或者生成后手动替换UXML中的所有路径

## 完整示例

假设你的Unity项目在 `C:\MyGame\`:

```bash
# 1. 生成代码
cd D:\Code\uielements-skill\scripts
python csv_to_uxml.py --csv ../test_data/manifest.csv --assets ../test_data/cuts --out ../test_output --screen TeamScreen

# 2. 复制切图
xcopy /Y D:\Code\uielements-skill\test_output\sprites\*.png C:\MyGame\Assets\UI\Sprites\

# 3. 复制UXML/USS
copy D:\Code\uielements-skill\test_output\TeamScreen.uxml C:\MyGame\Assets\UI\UXML\
copy D:\Code\uielements-skill\test_output\TeamScreen.uss C:\MyGame\Assets\UI\UXML\

# 4. 复制C#
copy D:\Code\uielements-skill\test_output\TeamScreenController.cs C:\MyGame\Assets\UI\Scripts\

# 5. 在Unity中配置Sprite设置(手动在Inspector中操作)

# 6. 创建GameObject并添加UIDocument和Controller组件
```

完成后,你应该能在Unity中看到完整的UI界面了!
