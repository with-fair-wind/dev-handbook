---
title: "OMP 常见问题"
sources_checked_at: 2026-10-21
content_reviewed_at: null
tested_versions: []
tested_environment: null
pending_changes: []
---

# 常见问题

## 找不到 oh-my-posh

用 `Get-Command oh-my-posh` 检查命令解析。安装后先重新打开终端；
仍然失败时核对安装结果和 PATH，避免凭空追加不存在的目录。

## 图标显示成方块

先检查当前终端配置实际选择的字体，参考 [字体与主题](fonts-and-themes.md)。

## 提示符没有变化

确认编辑的是当前 PowerShell 使用的 `$PROFILE`，初始化语句能够执行，
且后续没有另一段提示符配置覆盖它。

## Profile 加载报错

可以从新的会话启动 `pwsh -NoProfile` 隔离问题，然后逐段检查已有配置。
先保留 Profile 副本。若错误涉及执行策略，应先检查具体错误、有效策略和组织要求，
不要直接将所有作用域设为绕过。

## 主题路径失效

核对 Profile 中引用的文件是否存在，路径中包含空格时是否正确引用，
以及主题是否放在升级时可能被替换的安装目录中。

## 启动慢

分别比较无 Profile 会话和正常会话，判断延迟来自主题、其他初始化脚本，
还是终端本身。记录环境和复现步骤，再考虑精简相关配置。

## 待审核说明

<!-- AUTO:BEGIN review-notes -->
暂无自动生成的修改建议。
<!-- AUTO:END review-notes -->

参考：[官方初始化文档](https://ohmyposh.dev/docs/installation/prompt)、
[官方 Windows 安装文档](https://ohmyposh.dev/docs/installation/windows)。
