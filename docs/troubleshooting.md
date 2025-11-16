# 常见问题（Troubleshooting）

本页汇总在生成补丁、创建 PR 或运行演示脚本时常见的错误，并给出解决方案。

## 1. PR/补丁中出现二进制文件（PNG/CSV 等）导致平台拒绝

某些代码评审/提交平台只允许纯文本差异，因此当提交中包含 `docs/images/validation/*.png` 等二进制资源时，
会提示 “current workflow does not support binary files”。

**处理建议：**

1. 不直接提交图片：在仓库中保留生成图片的脚本（如 `scripts/compare_turbopump_figures.py`），并在 PR 描述中说明如何重现。
2. 若必须携带图片，可将其转换为可读文本（例如 CSV 数据）或上传到单独的制品存储，而不是直接放入补丁。
3. 在准备 patch 时使用 `git diff --text` 仅包含文本文件，或通过 `git update-index --assume-unchanged` 暂时排除大文件。

## 2. `git apply`/`patch` 报告找不到文件片段

如果在 README 或脚本附近插入内容时出现 `Failed to find expected lines`，说明目标文件与补丁中的上下文不匹配。
这通常由以下原因引起：

- 本地文件已被其他提交修改；
- 补丁来自不同版本的 README/脚本。

**解决方案：**

1. 先执行 `git pull --rebase`（若配置了远端）或 `git fetch` + `git rebase`，确保本地文件与最新版本一致。
2. 查看当前文件内容（如 `sed -n '1,200p' README.md`），确认需要修改的段落仍存在，再手工编辑。
3. 若差异过大，可直接用编辑器改写目标文件，再提交新的 diff，避免复用过期补丁。

## 3. `python scripts/run_routeB_system_demo.py` 提示缺少数据文件

Route-B 演示依赖多份 JSON/CSV（例如 `data/props/saturation/saturation_table.json`、`data/props/turbopump/*.json`）。
若这些文件被意外删除或未生成，可执行以下命令重新生成：

```bash
python scripts/update_routeB_saturation_from_coolprop.py
python scripts/update_routeB_preburner_from_cantera.py
```

重新生成后再次运行系统演示即可。
