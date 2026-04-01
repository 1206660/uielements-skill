using UnityEngine;
using UnityEditor;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

/// <summary>
/// UI Toolkit 完整诊断工具
/// 检查PNG配置、路径、文件名等所有可能导致显示问题的因素
/// 
/// 使用方法:
/// 菜单栏 Tools > Diagnose UI Toolkit Issues
/// </summary>
public class DiagnoseUIToolkit
{
    [MenuItem("Tools/Diagnose UI Toolkit Issues")]
    public static void RunDiagnostics()
    {
        StringBuilder report = new StringBuilder();
        report.AppendLine("=== UI Toolkit 完整诊断报告 ===\n");

        // 1. 检查Sprites文件夹
        report.AppendLine("## 1. Sprites文件夹检查");
        string spritesPath = "Assets/UI/Sprites";
        
        if (!Directory.Exists(spritesPath))
        {
            report.AppendLine("❌ 错误:Sprites文件夹不存在!");
        }
        else
        {
            string[] pngFiles = Directory.GetFiles(spritesPath, "*.png");
            report.AppendLine($"✅ 找到 {pngFiles.Length} 个PNG文件");

            // 检查是否在Resources下
            bool inResources = spritesPath.Contains("/Resources/");
            if (inResources)
            {
                report.AppendLine($"✅ Sprites在Resources文件夹下,可使用 resource:// 路径");
            }
            else
            {
                report.AppendLine($"⚠️ Sprites不在Resources下,Runtime加载需要特殊处理");
                report.AppendLine($"   建议:移动到 Assets/Resources/UI/Sprites/");
            }
        }
        report.AppendLine();

        // 2. 检查PNG配置
        report.AppendLine("## 2. PNG配置检查");
        CheckPNGConfigurations(spritesPath, report);
        report.AppendLine();

        // 3. 检查UXML路径
        report.AppendLine("## 3. UXML路径检查");
        CheckUXMLPaths(report);
        report.AppendLine();

        // 4. 检查文件名
        report.AppendLine("## 4. 文件名检查");
        CheckFileNames(spritesPath, report);
        report.AppendLine();

        // 5. 生成修复建议
        report.AppendLine("## 5. 修复建议");
        GenerateRecommendations(report);

        // 输出报告
        Debug.Log(report.ToString());

        // 保存到文件
        string reportPath = "Assets/UI_Toolkit_Diagnosis_Report.txt";
        File.WriteAllText(reportPath, report.ToString());
        AssetDatabase.Refresh();

        EditorUtility.DisplayDialog("诊断完成", 
            $"诊断报告已生成!\n\n详细报告:\n{reportPath}\n\n请查看Console窗口查看完整内容", 
            "确定");
    }

    private static void CheckPNGConfigurations(string spritesPath, StringBuilder report)
    {
        if (!Directory.Exists(spritesPath)) return;

        string[] pngFiles = Directory.GetFiles(spritesPath, "*.png");
        int totalIssues = 0;

        // 检查前5个PNG的配置
        int checkCount = Mathf.Min(5, pngFiles.Length);
        report.AppendLine($"检查前 {checkCount} 个PNG的配置:\n");

        for (int i = 0; i < checkCount; i++)
        {
            string assetPath = pngFiles[i].Replace("\\", "/");
            assetPath = assetPath.Substring(assetPath.IndexOf("Assets/"));

            TextureImporter importer = AssetImporter.GetAtPath(assetPath) as TextureImporter;
            if (importer == null) continue;

            string fileName = Path.GetFileName(assetPath);
            report.AppendLine($"[{i+1}] {fileName}");

            // 检查各项配置
            bool hasIssue = false;

            if (importer.textureType != TextureImporterType.Sprite)
            {
                report.AppendLine($"  ❌ textureType = {importer.textureType} (应该是 Sprite)");
                hasIssue = true;
            }

            if (importer.spriteImportMode != SpriteImportMode.Multiple)
            {
                report.AppendLine($"  ⚠️ spriteMode = {importer.spriteImportMode} (建议 Multiple)");
            }

            if (!importer.alphaIsTransparency)
            {
                report.AppendLine($"  ❌ alphaIsTransparency = false (应该是 true)");
                hasIssue = true;
            }

            if (importer.mipmapEnabled)
            {
                report.AppendLine($"  ⚠️ mipmapEnabled = true (UI应该是 false)");
            }

            if (importer.wrapMode != TextureWrapMode.Clamp)
            {
                report.AppendLine($"  ⚠️ wrapMode = {importer.wrapMode} (建议 Clamp)");
            }

            if (!hasIssue)
            {
                report.AppendLine($"  ✅ 配置正确");
            }
            else
            {
                totalIssues++;
            }

            report.AppendLine();
        }

        if (totalIssues > 0)
        {
            report.AppendLine($"⚠️ 发现 {totalIssues} 个PNG配置问题");
            report.AppendLine($"   使用 Tools > Fix UI Sprites (Complete Fix) 自动修复");
        }
        else
        {
            report.AppendLine($"✅ PNG配置正确!");
        }
    }

    private static void CheckUXMLPaths(StringBuilder report)
    {
        string uxmlPath = "Assets/UI/TeamScreen/TeamScreen.uxml";
        
        if (!File.Exists(uxmlPath))
        {
            report.AppendLine("❌ 找不到 TeamScreen.uxml 文件");
            return;
        }

        string content = File.ReadAllText(uxmlPath);

        // 检查路径格式
        string[] patterns = new string[]
        {
            @"url\('project://database/",
            @"url\('resource://",
            @"url\('Assets/",
            @"url\('\.\./",
        };

        string[] formatNames = new string[]
        {
            "project:// (Editor专用)",
            "resource:// (需要Resources文件夹)",
            "Assets直接路径",
            "相对路径"
        };

        bool foundPaths = false;
        for (int i = 0; i < patterns.Length; i++)
        {
            var matches = Regex.Matches(content, patterns[i]);
            if (matches.Count > 0)
            {
                report.AppendLine($"找到 {matches.Count} 个 {formatNames[i]} 引用");
                foundPaths = true;

                if (i == 0) // project://
                {
                    report.AppendLine($"  ⚠️ project:// 路径在Runtime可能不工作");
                    report.AppendLine($"     建议:使用 Tools > Fix UXML Sprite Paths 转换");
                }
                else if (i == 1) // resource://
                {
                    report.AppendLine($"  ✅ resource:// 路径正确");
                    report.AppendLine($"     确保PNG在 Assets/Resources/UI/Sprites/ 下");
                }
            }
        }

        if (!foundPaths)
        {
            report.AppendLine("⚠️ 未找到background-image路径引用");
        }
    }

    private static void CheckFileNames(string spritesPath, StringBuilder report)
    {
        if (!Directory.Exists(spritesPath)) return;

        string[] pngFiles = Directory.GetFiles(spritesPath, "*.png");
        
        int chineseNameCount = 0;
        int spaceCount = 0;
        int specialCharCount = 0;

        foreach (string file in pngFiles)
        {
            string fileName = Path.GetFileName(file);
            
            // 检查中文字符
            if (Regex.IsMatch(fileName, @"[\u4e00-\u9fa5]"))
            {
                chineseNameCount++;
            }

            // 检查空格
            if (fileName.Contains(" "))
            {
                spaceCount++;
            }

            // 检查特殊字符
            if (Regex.IsMatch(fileName, @"[^\w\.\-_\u4e00-\u9fa5]"))
            {
                specialCharCount++;
            }
        }

        if (chineseNameCount > 0)
        {
            report.AppendLine($"⚠️ {chineseNameCount} 个文件名包含中文字符");
            report.AppendLine($"   可能导致跨平台兼容性问题");
            report.AppendLine($"   建议:测试改一个为英文名,验证是否解决问题");
        }

        if (spaceCount > 0)
        {
            report.AppendLine($"⚠️ {spaceCount} 个文件名包含空格");
        }

        if (specialCharCount > 0)
        {
            report.AppendLine($"⚠️ {specialCharCount} 个文件名包含特殊字符");
        }

        if (chineseNameCount == 0 && spaceCount == 0 && specialCharCount == 0)
        {
            report.AppendLine($"✅ 文件名格式正常");
        }
    }

    private static void GenerateRecommendations(StringBuilder report)
    {
        report.AppendLine("根据诊断结果,推荐的修复步骤:");
        report.AppendLine();
        report.AppendLine("1️⃣ **修复PNG配置** (必须!)");
        report.AppendLine("   菜单: Tools > Fix UI Sprites (Complete Fix)");
        report.AppendLine("   作用: 修复 alphaIsTransparency、mipmapEnabled 等配置");
        report.AppendLine();
        report.AppendLine("2️⃣ **重启Unity Editor** (推荐)");
        report.AppendLine("   确保配置变更生效");
        report.AppendLine();
        report.AppendLine("3️⃣ **验证UI Builder预览**");
        report.AppendLine("   打开 TeamScreen.uxml,查看是否还有警告图标");
        report.AppendLine();
        report.AppendLine("4️⃣ **如果还不行,移动到Resources**");
        report.AppendLine("   - 创建 Assets/Resources/UI/Sprites/");
        report.AppendLine("   - 移动所有PNG到这个文件夹");
        report.AppendLine("   - 使用 Tools > Fix UXML Sprite Paths");
        report.AppendLine("   - 选择 Resource Format");
        report.AppendLine();
        report.AppendLine("5️⃣ **如果还不行,检查文件名**");
        report.AppendLine("   - 随便选一个PNG改成纯英文名测试");
        report.AppendLine("   - 如果英文名可以显示 → 说明中文字符有问题");
        report.AppendLine();
        report.AppendLine("6️⃣ **查看Unity Console错误**");
        report.AppendLine("   运行游戏(Play),查看Console有无报错");
    }
}
