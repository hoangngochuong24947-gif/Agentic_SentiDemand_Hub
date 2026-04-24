"""把仓库中的 hook 模板安装到 .git/hooks。"""

from __future__ import annotations

import subprocess
from pathlib import Path


HOOKS = ["pre-commit", "post-commit", "post-merge"]


def main() -> None:
    # 根据当前脚本位置（scripts/install_hooks.py）定位仓库根目录。
    repo_root = Path(__file__).resolve().parents[1]
    # hook 模板来源目录：scripts/hooks/*.ps1
    source_dir = repo_root / "scripts" / "hooks"
    # 通过 git 获取实际 hooks 路径，兼容自定义 core.hooksPath。
    hooks_path = subprocess.check_output(
        ["git", "rev-parse", "--git-path", "hooks"],
        cwd=repo_root,
        text=True,
    ).strip()
    target_dir = (repo_root / hooks_path).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    for hook_name in HOOKS:
        # 复制 PowerShell 版本的 hook 实现到目标 hooks 目录。
        source = source_dir / f"{hook_name}.ps1"
        target = target_dir / f"{hook_name}.ps1"
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Installed {hook_name} -> {target}")

        # 创建一个无扩展名的 shim 文件。
        # Git 按固定文件名触发 hook（例如 pre-commit），
        # 这个 shim 在 Windows 上转发到对应的 .ps1 脚本执行。
        shim = target_dir / hook_name
        shim.write_text(
            "#!/bin/sh\n"
            'exec powershell.exe -NoProfile -ExecutionPolicy Bypass '
            f'-File "$(dirname "$0")/{hook_name}.ps1"\n',
            encoding="utf-8",
        )
        print(f"Installed {hook_name} shim -> {shim}")


if __name__ == "__main__":
    main()
