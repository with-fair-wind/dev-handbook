---
title: "开发工具手册"
sources_checked_at: null
content_reviewed_at: null
tested_versions: []
tested_environment: null
pending_changes: []
---

# 开发工具手册

这里保存安装、配置和排错方法，并持续跟踪官方资料的变化。

## 开始阅读

- [Oh My Posh](tools/oh-my-posh/index.md)：安装、PowerShell 集成、字体与主题。
- [Windows Terminal](environments/windows-terminal.md)：终端与 Shell 的关系及字体配置。
- [更新策略](maintenance/update-policy.md)：自动更新能做什么，以及哪些内容需要审核。
- [项目方案](maintenance/project-plan.md)：项目结构、阶段与验收条件。

## 如何理解状态

“检测到新版”表示官方发布了版本；“内容已审核”表示维护者核对了教程；
“已实测”表示在记录的环境中实际执行过。这三种状态分别记录。

本项目初始教程依据官方资料编写，尚未进行终端命令实测。
tested_versions 为空表示没有登记实测版本；content_reviewed_at 为空表示尚无维护者审核记录。
每篇文档的元数据保存在 Markdown 顶部，可通过编辑入口查看。
来源动态信息位于工具概览，最近一次成功检查还可在 Actions 运行摘要中查看。
