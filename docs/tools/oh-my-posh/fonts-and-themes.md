---
title: "OMP 字体与主题"
sources_checked_at: null
content_reviewed_at: null
tested_versions: []
tested_environment: null
pending_changes: []
---

# 字体与主题

## 字体安装与启用是两个步骤

主题使用图标时，需要包含相应字形的字体。安装 Nerd Font 后，还需要在实际使用的终端配置中选择它。

在 Windows Terminal 中，检查对应 PowerShell 配置的字体设置；VS Code 集成终端有自己的字体设置。
不同终端之间的设置不会因为安装了字体而自动统一。

官方提供字体安装工具，可按官方向导选择字体：

```powershell
oh-my-posh font install
```

安装是否需要额外权限取决于环境。安装完成后重新打开终端并检查显示效果。

## 主题配置

主题决定提示符的布局、颜色和显示片段。建议将自己的主题保存在固定目录，
并在 Profile 中使用明确路径引用，便于备份和跨电脑同步。

修改主题前保留副本。排错时先用简单主题确认初始化正常，再恢复个人配置。

## 排查图标异常

依次检查字体是否安装、当前终端是否选择了正确字体、是否重新打开终端，
以及主题是否使用了当前字体缺少的字形。

## 待审核说明

<!-- AUTO:BEGIN review-notes -->
暂无自动生成的修改建议。
<!-- AUTO:END review-notes -->

依据：[官方字体说明](https://ohmyposh.dev/docs/installation/fonts)、
[官方自定义说明](https://ohmyposh.dev/docs/installation/customize)。
