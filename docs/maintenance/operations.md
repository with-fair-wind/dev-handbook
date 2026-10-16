---
title: "运行、审核与回滚"
sources_checked_at: null
content_reviewed_at: null
tested_versions: []
tested_environment: null
pending_changes: []
---

# 运行、审核与回滚

## 日常操作

在 GitHub Actions 选择 Docs update 手动运行。
查看 PR 的来源变化、候选检查和相关章节，然后记录审核结论。

首次采集登记来源，不代表教程已完整适配最新版本。
仅在实际执行后填写 tested_versions 和 tested_environment；
维护者核对完成后填写 content_reviewed_at。

sources_checked_at 保存最近一次写入文档的来源检查日期；
无变化运行只更新 Actions 摘要，不单独提交时间戳。

## GitHub 配置

- 允许 Actions 创建 PR。
- Pages 的构建来源选择 GitHub Actions。
- 首次检查成功后，可在主分支规则中要求 Docs check 通过。
- 默认机器人 PR 如提示需要批准检查运行，按界面操作；更新任务自身也验证候选。

## 暂停、恢复与冲突

暂停时禁用 Docs update，恢复时重新启用并手动运行一次。
定期查看最近运行记录，避免长期无仓库活动导致定时任务停用后未发现。

人工修改 automation 分支会触发保护停止。先合并、迁移或处理这些修改，
再恢复对应工具更新。相同候选关闭后不每日重建；
如需重新提出，先在主分支修正文档或来源配置。

## 回滚

撤销对应合并，确认来源状态和教程一起恢复，再重新发布。
机器人分支提交可能有两个父提交，优先撤销合并到主分支的 PR，
避免直接对多父提交执行没有指定父项的撤销。

发布失败保留上一成功版本。修复构建错误后重新运行 Docs deploy。
失败通知只提供安全摘要，不公开凭据或服务响应。

## 迁移状态

已核对 common_records 文件清单，暂未发现可直接迁移的 OMP 教程。
原有脚本与其他资料继续保留，新仓库先提供通用教程。
