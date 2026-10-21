---
title: "OMP 与 PowerShell 集成"
sources_checked_at: 2026-10-21
content_reviewed_at: null
tested_versions: []
tested_environment: null
pending_changes: []
---

# PowerShell 集成

## 确定使用的 Profile

在目标 PowerShell 中查看：

```powershell
$PSVersionTable.PSVersion
$PROFILE
Test-Path -LiteralPath $PROFILE
```

不同 PowerShell 版本或宿主可能读取不同的 Profile。先确认目标文件，再编辑配置。
修改前保留原文件副本；不要用教程示例整体覆盖已有内容。

如果目标文件尚不存在，可先创建父目录，再创建空文件：

```powershell
New-Item -ItemType Directory -Path (Split-Path -Parent $PROFILE) -Force
if (-not (Test-Path -LiteralPath $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE
}
```

## 加载提示符

在 Profile 中添加：

```powershell
oh-my-posh init pwsh | Invoke-Expression
```

使用本地主题时，将配置路径替换为实际文件，例如：

```powershell
oh-my-posh init pwsh --config "$HOME/.config/oh-my-posh/theme.omp.json" | Invoke-Expression
```

这里的路径是示例。主题文件需要事先存在；不要把占位路径直接当成完成配置。
上述初始化表达式执行的是已安装 OMP 生成的 Shell 初始化内容。

## 验证

打开新的目标 PowerShell 会话，确认：

- 原有 Profile 内容仍然存在。
- 提示符能够正常显示。
- 配置文件路径正确。
- 没有其他提示符工具在后续代码中再次覆盖初始化结果。

遇到异常时，先启动无 Profile 的会话排查，再参考 [常见问题](troubleshooting.md)。

## 待审核说明

<!-- AUTO:BEGIN review-notes -->
暂无自动生成的修改建议。
<!-- AUTO:END review-notes -->

依据：[官方 Shell 集成文档](https://ohmyposh.dev/docs/installation/prompt)。
