using UnityEngine;
using UnityEditor;
using System.IO;
using System.Text.RegularExpressions;

/// <summary>
/// UXML路径批量修复工具
/// 修复 UI Toolkit 中图片路径引用问题
/// 
/// 使用方法:
/// 1. 确保PNG已放在 Assets/Resources/UI/Sprites/ 下
/// 2. 菜单栏 Tools > Fix UXML Sprite Paths
/// 3. 选择要修复的UXML文件
/// </summary>
public class FixUXMLPaths : EditorWindow
{
    private string uxmlPath = "Assets/UI/TeamScreen/TeamScreen.uxml";
    private PathFormat targetFormat = PathFormat.Resource;

    private enum PathFormat
    {
        Resource,      // resource://UI/Sprites/xxx
        Relative,      // ../Sprites/xxx.png
        AssetPath      // Assets/UI/Sprites/xxx.png
    }

    [MenuItem("Tools/Fix UXML Sprite Paths")]
    public static void ShowWindow()
    {
        GetWindow<FixUXMLPaths>("UXML路径修复");
    }

    private void OnGUI()
    {
        GUILayout.Label("UXML Sprite Path Fixer", EditorStyles.boldLabel);
        EditorGUILayout.Space();

        uxmlPath = EditorGUILayout.TextField("UXML文件路径:", uxmlPath);
        
        if (GUILayout.Button("选择UXML文件"))
        {
            string selected = EditorUtility.OpenFilePanel("选择UXML文件", "Assets/UI", "uxml");
            if (!string.IsNullOrEmpty(selected))
            {
                // 转换为相对路径
                if (selected.StartsWith(Application.dataPath))
                {
                    uxmlPath = "Assets" + selected.Substring(Application.dataPath.Length);
                }
            }
        }

        EditorGUILayout.Space();
        GUILayout.Label("目标路径格式:", EditorStyles.boldLabel);
        targetFormat = (PathFormat)EditorGUILayout.EnumPopup("格式:", targetFormat);

        EditorGUILayout.HelpBox(GetFormatDescription(), MessageType.Info);

        EditorGUILayout.Space();

        if (GUILayout.Button("执行修复", GUILayout.Height(40)))
        {
            FixPaths();
        }

        EditorGUILayout.Space();
        if (GUILayout.Button("预览修复结果"))
        {
            PreviewFix();
        }
    }

    private string GetFormatDescription()
    {
        switch (targetFormat)
        {
            case PathFormat.Resource:
                return "resource://UI/Sprites/xxx\n需要PNG在 Assets/Resources/UI/Sprites/ 下\n推荐用于Runtime加载";
            case PathFormat.Relative:
                return "../Sprites/xxx.png\n相对于UXML文件的路径\n适用于同项目内的资源";
            case PathFormat.AssetPath:
                return "Assets/UI/Sprites/xxx.png\n完整Asset路径\nEditor专用,Runtime可能不可用";
            default:
                return "";
        }
    }

    private void FixPaths()
    {
        if (!File.Exists(uxmlPath))
        {
            EditorUtility.DisplayDialog("错误", $"文件不存在:\n{uxmlPath}", "确定");
            return;
        }

        string content = File.ReadAllText(uxmlPath);
        string originalContent = content;

        // 匹配 url('project://database/Assets/UI/Sprites/xxx.png')
        string pattern = @"url\('project://database/Assets/UI/Sprites/([^']+)'\)";
        
        content = Regex.Replace(content, pattern, match =>
        {
            string fileName = match.Groups[1].Value; // 例如: 001_图层_8314.png
            string newPath = "";

            switch (targetFormat)
            {
                case PathFormat.Resource:
                    // 移除扩展名
                    string nameWithoutExt = Path.GetFileNameWithoutExtension(fileName);
                    newPath = $"url('resource://UI/Sprites/{nameWithoutExt}')";
                    break;
                case PathFormat.Relative:
                    newPath = $"url('../Sprites/{fileName}')";
                    break;
                case PathFormat.AssetPath:
                    newPath = $"url('Assets/UI/Sprites/{fileName}')";
                    break;
            }

            return newPath;
        });

        if (content != originalContent)
        {
            // 创建备份
            string backupPath = uxmlPath + ".backup";
            File.Copy(uxmlPath, backupPath, true);

            // 写入修复后的内容
            File.WriteAllText(uxmlPath, content);

            AssetDatabase.Refresh();

            int count = Regex.Matches(originalContent, pattern).Count;
            EditorUtility.DisplayDialog("修复完成", 
                $"✅ 修复完成!\n\n修改了 {count} 个路径引用\n备份文件: {backupPath}\n\n请在UI Builder中验证效果!", 
                "确定");
        }
        else
        {
            EditorUtility.DisplayDialog("提示", "未发现需要修复的路径", "确定");
        }
    }

    private void PreviewFix()
    {
        if (!File.Exists(uxmlPath))
        {
            EditorUtility.DisplayDialog("错误", $"文件不存在:\n{uxmlPath}", "确定");
            return;
        }

        string content = File.ReadAllText(uxmlPath);
        string pattern = @"url\('project://database/Assets/UI/Sprites/([^']+)'\)";
        
        var matches = Regex.Matches(content, pattern);
        if (matches.Count == 0)
        {
            Debug.Log("未发现需要修复的路径");
            return;
        }

        Debug.Log($"=== 预览修复结果 ({matches.Count} 个路径) ===");
        foreach (Match match in matches)
        {
            string fileName = match.Groups[1].Value;
            string oldPath = match.Value;
            string newPath = "";

            switch (targetFormat)
            {
                case PathFormat.Resource:
                    string nameWithoutExt = Path.GetFileNameWithoutExtension(fileName);
                    newPath = $"url('resource://UI/Sprites/{nameWithoutExt}')";
                    break;
                case PathFormat.Relative:
                    newPath = $"url('../Sprites/{fileName}')";
                    break;
                case PathFormat.AssetPath:
                    newPath = $"url('Assets/UI/Sprites/{fileName}')";
                    break;
            }

            Debug.Log($"原路径: {oldPath}\n新路径: {newPath}\n");
        }
    }
}

/// <summary>
/// 快速执行修复(无窗口)
/// 菜单栏 Tools > Quick Fix UXML Paths (Resource)
/// </summary>
public class QuickFixUXMLPaths
{
    [MenuItem("Tools/Quick Fix UXML Paths (Resource Format)")]
    public static void QuickFixToResource()
    {
        string uxmlPath = "Assets/UI/TeamScreen/TeamScreen.uxml";
        
        if (!File.Exists(uxmlPath))
        {
            EditorUtility.DisplayDialog("错误", "找不到 TeamScreen.uxml 文件", "确定");
            return;
        }

        string content = File.ReadAllText(uxmlPath);
        string originalContent = content;

        // 匹配并替换路径
        string pattern = @"url\('project://database/Assets/UI/Sprites/([^']+)'\)";
        content = Regex.Replace(content, pattern, match =>
        {
            string fileName = match.Groups[1].Value;
            string nameWithoutExt = Path.GetFileNameWithoutExtension(fileName);
            return $"url('resource://UI/Sprites/{nameWithoutExt}')";
        });

        if (content != originalContent)
        {
            // 备份
            File.Copy(uxmlPath, uxmlPath + ".backup", true);
            
            // 写入
            File.WriteAllText(uxmlPath, content);
            AssetDatabase.Refresh();

            int count = Regex.Matches(originalContent, pattern).Count;
            EditorUtility.DisplayDialog("修复完成", 
                $"✅ 快速修复完成!\n\n修改了 {count} 个路径为 resource:// 格式\n\n请确保PNG已在 Assets/Resources/UI/Sprites/ 下!", 
                "确定");
        }
    }
}
