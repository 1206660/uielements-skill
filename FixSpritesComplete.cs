using UnityEditor;
using UnityEngine;
using System.Linq;

/// <summary>
/// Unity UI Toolkit PNG配置完整修复工具
/// 修复项:
/// 1. textureType = Sprite (2D and UI)
/// 2. spriteMode = Multiple
/// 3. alphaIsTransparency = true  (关键修复)
/// 4. mipmapEnabled = false       (关键修复)
/// 5. wrapMode = Clamp
/// 6. filterMode = Bilinear
/// </summary>
public class FixSpritesComplete
{
    [MenuItem("Tools/Fix UI Sprites (Complete Fix)")]
    static void FixAllSprites()
    {
        // 查找Assets/UI/Sprites下的所有Texture2D
        string[] guids = AssetDatabase.FindAssets("t:Texture2D", new[] { "Assets/UI/Sprites" });
        
        if (guids.Length == 0)
        {
            EditorUtility.DisplayDialog("提示", "在 Assets/UI/Sprites/ 下没有找到PNG文件!", "确定");
            return;
        }
        
        int totalFiles = guids.Length;
        int fixedFiles = 0;
        int skippedFiles = 0;
        
        EditorUtility.DisplayProgressBar("修复PNG配置", "开始处理...", 0f);
        
        for (int i = 0; i < guids.Length; i++)
        {
            string guid = guids[i];
            string path = AssetDatabase.GUIDToAssetPath(guid);
            
            // 更新进度条
            float progress = (float)i / totalFiles;
            EditorUtility.DisplayProgressBar("修复PNG配置", $"处理中: {path}", progress);
            
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            
            if (importer == null)
            {
                skippedFiles++;
                continue;
            }
            
            bool changed = false;
            
            // 1. 确保是Sprite类型
            if (importer.textureType != TextureImporterType.Sprite)
            {
                importer.textureType = TextureImporterType.Sprite;
                changed = true;
                Debug.Log($"[修复] {path} - 改为Sprite类型");
            }
            
            // 2. 确保spriteMode是Multiple
            if (importer.spriteImportMode != SpriteImportMode.Multiple)
            {
                importer.spriteImportMode = SpriteImportMode.Multiple;
                changed = true;
                Debug.Log($"[修复] {path} - 改为Multiple模式");
            }
            
            // 🔥 3. 关键修复:启用Alpha透明度
            if (!importer.alphaIsTransparency)
            {
                importer.alphaIsTransparency = true;
                changed = true;
                Debug.Log($"[修复] {path} - 启用Alpha透明度 ✅");
            }
            
            // 🔥 4. 关键修复:关闭MipMap(UI不需要)
            if (importer.mipmapEnabled)
            {
                importer.mipmapEnabled = false;
                changed = true;
                Debug.Log($"[修复] {path} - 关闭MipMap ✅");
            }
            
            // 5. 确保Wrap Mode是Clamp
            if (importer.wrapMode != TextureWrapMode.Clamp)
            {
                importer.wrapMode = TextureWrapMode.Clamp;
                changed = true;
                Debug.Log($"[修复] {path} - 改为Clamp模式");
            }
            
            // 6. 确保Filter Mode是Bilinear
            if (importer.filterMode != FilterMode.Bilinear)
            {
                importer.filterMode = FilterMode.Bilinear;
                changed = true;
                Debug.Log($"[修复] {path} - 改为Bilinear过滤");
            }
            
            // 如果有修改,保存并重新导入
            if (changed)
            {
                importer.SaveAndReimport();
                fixedFiles++;
            }
            else
            {
                skippedFiles++;
            }
        }
        
        EditorUtility.ClearProgressBar();
        
        // 显示结果
        string message = $"处理完成!\n\n" +
                        $"总文件数: {totalFiles}\n" +
                        $"已修复: {fixedFiles}\n" +
                        $"已跳过(无需修复): {skippedFiles}\n\n" +
                        $"关键修复项:\n" +
                        $"✅ Alpha Is Transparency = true\n" +
                        $"✅ Generate Mip Maps = false\n\n" +
                        $"请运行游戏测试图片是否正常显示!";
        
        EditorUtility.DisplayDialog("✅ 修复完成", message, "确定");
        
        Debug.Log($"=== 修复完成 === 总:{totalFiles} 修复:{fixedFiles} 跳过:{skippedFiles}");
    }
    
    /// <summary>
    /// 检查当前选中PNG的配置
    /// </summary>
    [MenuItem("Tools/Check Selected PNG Config")]
    static void CheckSelectedPNG()
    {
        var selected = Selection.activeObject;
        if (selected == null)
        {
            EditorUtility.DisplayDialog("提示", "请先选中一个PNG文件!", "确定");
            return;
        }
        
        string path = AssetDatabase.GetAssetPath(selected);
        var importer = AssetImporter.GetAtPath(path) as TextureImporter;
        
        if (importer == null)
        {
            EditorUtility.DisplayDialog("错误", "选中的不是一个纹理文件!", "确定");
            return;
        }
        
        string report = $"文件: {path}\n\n" +
                       $"textureType: {importer.textureType} {(importer.textureType == TextureImporterType.Sprite ? "✅" : "❌")}\n" +
                       $"spriteMode: {importer.spriteImportMode} {(importer.spriteImportMode == SpriteImportMode.Multiple ? "✅" : "⚠️")}\n" +
                       $"alphaIsTransparency: {importer.alphaIsTransparency} {(importer.alphaIsTransparency ? "✅" : "❌")}\n" +
                       $"mipmapEnabled: {importer.mipmapEnabled} {(importer.mipmapEnabled ? "❌" : "✅")}\n" +
                       $"wrapMode: {importer.wrapMode} {(importer.wrapMode == TextureWrapMode.Clamp ? "✅" : "⚠️")}\n" +
                       $"filterMode: {importer.filterMode} {(importer.filterMode == FilterMode.Bilinear ? "✅" : "⚠️")}\n\n" +
                       $"✅ = 正确配置\n" +
                       $"❌ = 错误配置(需要修复)\n" +
                       $"⚠️ = 可选配置(不影响显示)";
        
        Debug.Log(report);
        EditorUtility.DisplayDialog("PNG配置检查", report, "确定");
    }
}
