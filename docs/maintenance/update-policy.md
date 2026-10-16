---
title: "自动更新策略"
sources_checked_at: null
content_reviewed_at: null
tested_versions: []
tested_environment: null
pending_changes: []
---

# 自动更新策略

每天北京时间 09:23 检查 OMP 稳定版、稳定版文档及开发分支文档。
检查完成不等于教程已审核，开发分支说明不等于稳定版已支持。

规则程序仅更新来源摘要、状态、历史和来源检查日期。
可选 AI 只生成 review-notes 草稿，不改写教程操作步骤。
安装、初始化和迁移步骤需要在 PR 中重点核对。

合并 PR 才在主分支接受基线；关闭 PR 不推进基线。
相同候选关闭后不重复打开，来源或主分支文档发生变化后再提出新候选。
每个工具最多一个活动 PR，自动分支存在人工提交时停止覆盖。

来源抓取不完整、解析或候选检查失败时保留已发布内容。AI 失败降级为基础报告。
没有变化时只记录运行摘要；持续失败更新同一个问题记录，成功后关闭。

GitHub 定时任务可能延迟，公共仓库长期无活动时可能停用。
参考 [官方调度说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)。
