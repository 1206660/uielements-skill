using System.IO;
using UnityEditor;
using UnityEngine;

/// <summary>
/// Unity Editor 菜单集成 - UI Builder 一键导入
/// 将生成的 UXML/USS/C#/Sprites 导入到 Unity 工程对应目录
/// 
/// 使用: Unity 菜单 > Tools > UI Builder > Import Generated UI
/// </summary>
public class UIBuilderImporter : EditorWindow
{
    private string _sourceDir = "";
    private string _spriteTargetDir = "Assets/UI/Sprites";
    private string _documentTargetDir = "Assets/UI/Documents";
    private string _scriptTargetDir = "Assets/Scripts/UI";
    private bool _overwriteExisting = false;
    private Vector2 _scrollPos;

    [MenuItem("Tools/UI Builder/Import Generated UI")]
    public static void ShowWindow()
    {
        var window = GetWindow<UIBuilderImporter>("UI Builder Importer");
        window.minSize = new Vector2(450, 350);
    }

    private void OnGUI()
    {
        _scrollPos = EditorGUILayout.BeginScrollView(_scrollPos);

        EditorGUILayout.LabelField("UI Builder - 导入生成的界面", EditorStyles.boldLabel);
        EditorGUILayout.Space(8);

        // 源目录
        EditorGUILayout.LabelField("生成输出目录", EditorStyles.miniLabel);
        EditorGUILayout.BeginHorizontal();
        _sourceDir = EditorGUILayout.TextField(_sourceDir);
        if (GUILayout.Button("浏览", GUILayout.Width(60)))
        {
            var path = EditorUtility.OpenFolderPanel("选择生成输出目录", _sourceDir, "");
            if (!string.IsNullOrEmpty(path))
                _sourceDir = path;
        }
        EditorGUILayout.EndHorizontal();

        EditorGUILayout.Space(12);
        EditorGUILayout.LabelField("目标路径配置", EditorStyles.boldLabel);

        _spriteTargetDir = EditorGUILayout.TextField("Sprites 目录", _spriteTargetDir);
        _documentTargetDir = EditorGUILayout.TextField("UXML/USS 目录", _documentTargetDir);
        _scriptTargetDir = EditorGUILayout.TextField("C# 脚本目录", _scriptTargetDir);

        EditorGUILayout.Space(8);
        _overwriteExisting = EditorGUILayout.Toggle("覆盖已有文件", _overwriteExisting);

        EditorGUILayout.Space(16);

        // 预览
        if (!string.IsNullOrEmpty(_sourceDir) && Directory.Exists(_sourceDir))
        {
            EditorGUILayout.LabelField("预览", EditorStyles.boldLabel);
            var files = Directory.GetFiles(_sourceDir, "*", SearchOption.TopDirectoryOnly);
            int uxmlCount = 0, ussCount = 0, csCount = 0;
            foreach (var f in files)
            {
                var ext = Path.GetExtension(f).ToLower();
                if (ext == ".uxml") uxmlCount++;
                else if (ext == ".uss") ussCount++;
                else if (ext == ".cs") csCount++;
            }

            string spritesDir = Path.Combine(_sourceDir, "sprites");
            int spriteCount = Directory.Exists(spritesDir)
                ? Directory.GetFiles(spritesDir, "*.png").Length
                : 0;

            EditorGUILayout.HelpBox(
                $"UXML: {uxmlCount} 个\n" +
                $"USS:  {ussCount} 个\n" +
                $"C#:   {csCount} 个\n" +
                $"Sprites: {spriteCount} 个",
                MessageType.Info
            );
        }

        EditorGUILayout.Space(8);

        GUI.enabled = !string.IsNullOrEmpty(_sourceDir) && Directory.Exists(_sourceDir);
        if (GUILayout.Button("导入到 Unity 工程", GUILayout.Height(36)))
        {
            DoImport();
        }
        GUI.enabled = true;

        EditorGUILayout.EndScrollView();
    }

    private void DoImport()
    {
        int copied = 0;

        // 确保目标目录存在
        EnsureDirectory(_spriteTargetDir);
        EnsureDirectory(_documentTargetDir);
        EnsureDirectory(_scriptTargetDir);

        // 复制 Sprites
        string spritesDir = Path.Combine(_sourceDir, "sprites");
        if (Directory.Exists(spritesDir))
        {
            foreach (var file in Directory.GetFiles(spritesDir, "*.png"))
            {
                string dest = Path.Combine(_spriteTargetDir, Path.GetFileName(file));
                if (CopyFile(file, dest)) copied++;
            }
        }

        // 复制 UXML/USS
        foreach (var file in Directory.GetFiles(_sourceDir))
        {
            string ext = Path.GetExtension(file).ToLower();
            if (ext == ".uxml" || ext == ".uss")
            {
                string dest = Path.Combine(_documentTargetDir, Path.GetFileName(file));
                if (CopyFile(file, dest)) copied++;
            }
            else if (ext == ".cs")
            {
                string dest = Path.Combine(_scriptTargetDir, Path.GetFileName(file));
                if (CopyFile(file, dest)) copied++;
            }
        }

        AssetDatabase.Refresh();

        // 配置 Sprite 导入设置
        ConfigureSpriteImports();

        EditorUtility.DisplayDialog(
            "UI Builder Import",
            $"导入完成！共复制 {copied} 个文件。\n\n" +
            $"Sprites: {_spriteTargetDir}\n" +
            $"Documents: {_documentTargetDir}\n" +
            $"Scripts: {_scriptTargetDir}",
            "OK"
        );
    }

    private bool CopyFile(string src, string dest)
    {
        if (File.Exists(dest) && !_overwriteExisting)
        {
            Debug.LogWarning($"[UIBuilder] 跳过已存在: {dest}");
            return false;
        }

        File.Copy(src, dest, true);
        Debug.Log($"[UIBuilder] 复制: {Path.GetFileName(src)} -> {dest}");
        return true;
    }

    private void EnsureDirectory(string path)
    {
        if (!Directory.Exists(path))
        {
            Directory.CreateDirectory(path);
            Debug.Log($"[UIBuilder] 创建目录: {path}");
        }
    }

    /// <summary>
    /// 自动配置 Sprite 导入设置 (UI 用途)
    /// </summary>
    private void ConfigureSpriteImports()
    {
        string[] guids = AssetDatabase.FindAssets("t:Texture2D", new[] { _spriteTargetDir });
        int configured = 0;

        foreach (string guid in guids)
        {
            string assetPath = AssetDatabase.GUIDToAssetPath(guid);
            var importer = AssetImporter.GetAtPath(assetPath) as TextureImporter;

            if (importer != null)
            {
                bool changed = false;

                if (importer.textureType != TextureImporterType.Sprite)
                {
                    importer.textureType = TextureImporterType.Sprite;
                    changed = true;
                }

                if (importer.spriteImportMode != SpriteImportMode.Single)
                {
                    importer.spriteImportMode = SpriteImportMode.Single;
                    changed = true;
                }

                // UI 用途不需要 mipmap
                if (importer.mipmapEnabled)
                {
                    importer.mipmapEnabled = false;
                    changed = true;
                }

                if (changed)
                {
                    importer.SaveAndReimport();
                    configured++;
                }
            }
        }

        if (configured > 0)
            Debug.Log($"[UIBuilder] 配置 {configured} 个 Sprite 导入设置");
    }
}
