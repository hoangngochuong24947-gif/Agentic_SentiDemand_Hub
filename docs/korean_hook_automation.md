# Hook 与自动化迭代方案

## 已提供的模板

- `scripts/hooks/pre-commit.ps1`
- `scripts/hooks/post-commit.ps1`
- `scripts/hooks/post-merge.ps1`
- `scripts/install_hooks.py`

## 各 hook 的职责

### pre-commit

- 执行核心测试集，阻止明显回归进入提交历史。
- 日志输出到 `outputs/hook_logs/pre-commit-*.log`。

### post-commit

- 记录最近一次提交的摘要与变更统计。
- 将学习记录写入 `docs/commit-learning-log.md`。

### post-merge

- 执行 `uv sync`，降低切分支后的依赖不一致风险。
- 把最近日志片段追加到 `docs/Skills.md`，形成可检索复盘库。

## 安装方式

```powershell
uv run python scripts/install_hooks.py
```

## 埋点建议

- pipeline 初始化时记录语言、分词后端和情感策略。
- 真实抓取接入后，额外记录来源站点、抓取批次、失败重试次数。
- 所有关键日志统一收敛到 `outputs/hook_logs/` 与分析输出目录，便于对话重启后快速恢复上下文。
