---
title: "OMP 安装与更新"
sources_checked_at: 2026-10-16
content_reviewed_at: null
tested_versions: []
tested_environment: null
pending_changes: []
---

# 安装与更新

## 前置条件

准备可用的 PowerShell、终端以及 WinGet。没有 WinGet 时，先按官方文档选择其他安装方式。
本页命令尚未在你的电脑上自动执行。

## 使用 WinGet 安装

```powershell
winget install JanDeDobbeleer.OhMyPosh --source winget
```

完成后打开新的 PowerShell 会话，检查：

```powershell
oh-my-posh version
Get-Command oh-my-posh
```

第一条检查工具版本，第二条检查命令解析到的位置。安装成功不代表当前终端字体或提示符已经配置完成。

## 更新

```powershell
winget upgrade JanDeDobbeleer.OhMyPosh --source winget
```

更新后重新打开 Shell，记录实际版本并检查主题能否加载。若同时使用多种安装方式，
先核对命令路径，避免更新了一个安装副本却继续使用另一个。

## 后续配置

继续阅读 [PowerShell 集成](powershell.md) 和 [字体与主题](fonts-and-themes.md)。
自动更新功能仅跟踪文档来源，不会升级你电脑上的 OMP。

## 待审核说明

<!-- AUTO:BEGIN review-notes -->
暂无自动生成的修改建议。
<!-- AUTO:END review-notes -->

依据：[官方 Windows 安装说明](https://ohmyposh.dev/docs/installation/windows)、
[官方升级说明](https://ohmyposh.dev/docs/installation/upgrade)。
