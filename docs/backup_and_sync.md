# 仓库备份与同步说明

本文件说明如何基于当前容器环境备份仓库、并与 GitHub 远端仓库同步：

1. **已有备份**：已经在 `/workspace/ffsc_engine_dynamics.bundle` 生成 Git bundle，
   可以通过 `scp` 或 VS Code 下载该文件，实现当前仓库的完整离线备份。
2. **恢复方式**：在任意环境运行 `git clone /path/to/ffsc_engine_dynamics.bundle ffsc_engine_dynamics` 即可还原。
3. **推送到 GitHub**：
   ```bash
   git remote add origin <你的 GitHub 仓库 URL>
   git push -u origin work:main
   ```
   或者把 `work` 分支改名为 `main` 后再推送：
   ```bash
   git branch -M main
   git push -u origin main
   ```
