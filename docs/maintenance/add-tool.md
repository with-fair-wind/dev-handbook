---
title: "新工具接入"
sources_checked_at: null
content_reviewed_at: null
tested_versions: []
tested_environment: null
pending_changes: []
---

# 新工具接入

1. 在 docs/tools/工具ID/ 建立教程、概览和更新历史。
2. 使用模板添加元数据及必要自动区域。
3. 添加 sources/工具ID.yml，声明官方仓库、源码路径和本地受影响文件。
4. 添加 MkDocs 导航。
5. 增加离线样本及适配测试，验证仅文档变化和版本变化。
6. 预览首次候选，核对不可变证据链接。
7. 将工具 ID 加入工作流选项和调度矩阵。

通用适配要求上游使用 GitHub Releases，并将官方文档保存在同一仓库中。
不满足条件的工具需要扩展适配器。

输出必须在对应工具目录内；文档 ID 不可重复。
来源配置样例为 sources/oh-my-posh.yml。

## 可选 JSON 草稿服务

AI 默认关闭，不配置密钥也能检测变化和生成报告。
DOCSYNC_AI_URL 应为自有 HTTPS JSON 适配服务；DOCSYNC_AI_KEY 作为 Secret 保存。
它不是未适配的模型厂商直连地址，请按 README 中的协议实现服务。

每个新候选最多请求一次，限制输入、输出和超时时间，禁止重定向。
草稿只进入 review-notes。解释、命令和版本适用性仍需人工核查。
