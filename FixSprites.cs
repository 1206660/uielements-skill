using UnityEditor;
using UnityEngine;

/// <summary>
/// Unity Editor工具:批量修复UI Sprites的导入设置
/// 
/// 使用方法:
/// 1. 将此文件放到Unity项目的 Assets/Editor/ 目录下
/// 2. 在Unity菜单栏点击 Tools > Fix UI Sprites
/// 3. 脚本会自动将 Assets/UI/Sprites/ 下所有PNG配置为 Sprite (2D and UI) 类型
/// </summary>
public class FixSprites
{
    [MenuItem("Tools/Fix UI Sprites")]
    static void FixAllSprites()
    {
        // 搜索 Assets/UI/Sprites 目录下的所有PNG文件
        string[] guids = AssetDatabase.FindAssets("t:Texture2D", new[] { "Assets/UI/Sprites" });
        
        int fixedCount = 0;
        int totalCount = guids.Length;

        for (int i = 0; i < guids.Length; i++)
        {
            string path = AssetDatabase.GUIDToAssetPath(guids[i]);
            
            // 显示进度条
            EditorUtility.DisplayProgressBar(
                "配置UI Sprites", 
                $"处理中: {path}", 
                (float)i / totalCount
            );

            TextureImporter importer = AssetImporter.GetAtPath(path) as TextureImporter;
            
            if (importer != null)
            {
                // 检查是否需要修改
                bool needsUpdate = false;
                
                if (importer.textureType != TextureImporterType.Sprite)
                {
                    importer.textureType = TextureImporterType.Sprite;
                    needsUpdate = true;
                }
                
                if (importer.spriteImportMode != SpriteImportMode.Single)
                {
                    importer.spriteImportMode = SpriteImportMode.Single;
                    needsUpdate = true;
                }
                
                if (importer.alphaIsTransparency != true)
                {
                    importer.alphaIsTransparency = true;
                    needsUpdate = true;
                }
                
                if (needsUpdate)
                {
                    // 保存并重新导入
                    importer.SaveAndReimport();
                    fixedCount++;
                    Debug.Log($"✅ 已修复: {path}");
                }
            }
        }
        
        EditorUtility.ClearProgressBar();
        
        // 显示完成消息
        EditorUtility.DisplayDialog(
            "配置完成", 
            $"共扫描 {totalCount} 个文件\n已修复 {fixedCount} 个文件\n\n所有图片已配置为 Sprite (2D and UI) 类型!",
            "确定"
        );
        
        Debug.Log($"🎉 Sprite配置完成! 共处理 {totalCount} 个文件,修复了 {fixedCount} 个文件");
    }
}
