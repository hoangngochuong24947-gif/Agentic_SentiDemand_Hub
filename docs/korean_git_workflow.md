# 韩语功能 Git 方案

## 目标

在不影响现有中文舆情分析能力的前提下，使用独立 worktree 和独立分支开发韩语评论原型。

## 当前隔离方案

- 主仓库：`master`
- 开发分支：`codex/korean-review-prototype`
- 开发 worktree：`.worktrees/codex-korean-review-prototype`

## 推荐工作流

1. 主工作区只负责参考项目克隆、对照和稳定版本查看。
2. 韩语功能开发、文档和 hooks 全部在 `codex/korean-review-prototype` worktree 内进行。
3. 每次提交前由 `pre-commit` 运行核心测试。
4. 每次提交后由 `post-commit` 记录变更摘要到 `docs/commit-learning-log.md`。
5. 合并或拉取后由 `post-merge` 同步依赖并把最近日志片段写入 `docs/Skills.md`。

## 新手常用命令

```powershell
git worktree list
git status
git switch master
git -C .worktrees/codex-korean-review-prototype status
git add .
git commit -m "feat: add korean review prototype"
git push -u origin codex/korean-review-prototype
```

## 注意事项

- 不要在 `master` 直接改韩语原型代码。
- `external/` 目录里的参考仓库只用于学习，不直接并入主代码。
- 若 hook 失败，先查看 `outputs/hook_logs/`，再决定是否提交。
