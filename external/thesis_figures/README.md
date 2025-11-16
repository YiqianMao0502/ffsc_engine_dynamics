# Thesis figure placeholders

本目录用于放置周闯博士论文图21、图23的原始扫描图像。由于提交限制，PNG
文件不随仓库分发，需要在本地自行准备：

1. 将 `figure21_whn_wtn.png` 与 `figure23_pump_head.png` 复制到本目录。
2. 运行 `python scripts/compare_turbopump_figures.py --digitize --plot-dir docs/images/validation`
   重新生成对比图或验证曲线。
3. 提交代码时请勿将这些 PNG 加入 Git（`.gitignore` 已屏蔽 `external/thesis_figures/*.png`）。

如无需求，可保持本目录仅包含此说明文件。
