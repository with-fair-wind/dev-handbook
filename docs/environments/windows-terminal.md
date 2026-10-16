---
title: "Windows Terminal 配置"
sources_checked_at: null
content_reviewed_at: null
tested_versions: []
tested_environment: null
pending_changes: []
---

# Windows Terminal

Windows Terminal 是终端宿主；PowerShell 是 Shell；OMP 是提示符引擎。
排查显示或启动问题时，先确定是哪一层的设置发生作用。

## 配置顺序

1. 先确认目标 PowerShell 能正常启动。
2. 安装所需字体。
3. 在 Windows Terminal 的目标配置中选择字体。
4. 在对应 PowerShell 的 Profile 中加载 OMP。
5. 新开会话检查显示和启动错误。

多个终端宿主使用同一套 Shell 配置时，字体仍需要分别设置。
参考 [OMP 配置入口](../tools/oh-my-posh/index.md)。

本页作为环境说明维护，第一阶段不自动采集 Windows Terminal 的发布变化。

官方资料：[Windows Terminal 文档](https://learn.microsoft.com/windows/terminal/)。
