# dev-handbook · 开发工具手册

跟踪官方变化，为中文教程生成带证据的更新 PR，首个工具为 Oh My Posh。

- 每天北京时间 **09:23** 检测稳定版与官方文档变化。
- 相同候选复用 PR；主分支基线只随审核合并推进。
- 个人内容受自动区域边界保护，AI 默认关闭。
- [文档网站](https://with-fair-wind.github.io/dev-handbook/)
- [项目实施方案](docs/maintenance/project-plan.md)
- [运行、审核与回滚](docs/maintenance/operations.md)

## 本地使用

需要 Python 3.12 和 Git；发布更新 PR 还需要 GitHub CLI。

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install --require-hashes -r requirements.lock
$env:PYTHONPATH = "scripts"
.venv/Scripts/python.exe -m docsync check
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe -m mkdocs serve
```

Linux/macOS 使用 .venv/bin/python，并设置 export PYTHONPATH=scripts。

## 预览更新

```powershell
.venv/Scripts/python.exe -m docsync sync --tool oh-my-posh
```

默认只在忽略目录 .docsync/oh-my-posh/ 保存候选、报告和计划修改。
--apply 将候选写入当前工作区供审阅，不表示主分支已接受基线。

仅在默认分支的干净检出上使用 --publish --repository with-fair-wind/dev-handbook。
发布通过 GitHub API 写入 automation 分支，当前主分支检出保持不变。
离线 --fixture 不可用于发布。

采集读取 GH_TOKEN 或 GITHUB_TOKEN。本地也可临时向进程提供已登录 GitHub CLI 的凭据，
不要把凭据写入文件或输出。

## 可选 AI 服务协议

设置 DOCSYNC_AI_URL 和可选 DOCSYNC_AI_KEY，运行时添加 --ai。
地址应为自有 HTTPS JSON 适配服务，不是未经适配的模型厂商接口。

输入含 protocol_version=1、instructions、evidence、documents 和 max_output_characters。
evidence 以证据编号为键，提供 url、channel 及 text。
documents 以本地文档路径为键，提供当前内容。

输出示例：

```json
{
  "changes": [
    {
      "path": "docs/tools/oh-my-posh/installation.md",
      "content": "请核查安装步骤是否需要调整。",
      "evidence": ["stable:windows"]
    }
  ]
}
```

每个新候选最多一次请求。超时、缺少证据或输出不合格时保留规则报告。
草稿只进入 review-notes，不改写安装步骤，不自动合并。

## GitHub 设置

1. 推送 main。
2. Settings → Actions → General：允许工作流创建 PR。
3. Settings → Pages：Source 选择 GitHub Actions。
4. 手动运行 Docs check、Docs update、Docs deploy。
5. 审核更新 PR 后合并；如提示需要批准检查，按界面操作。

主分支必要检查可在首次成功运行后配置。暂停、恢复和回滚见维护文档。

## 依赖与验证

requirements.in 声明依赖，requirements.lock 固定完整版本和校验值。
更新锁文件后运行测试、ruff 和严格构建。Actions 固定到完整提交 SHA。
教程及程序采用 MIT 许可，外部项目及临时快照遵循各自许可。
