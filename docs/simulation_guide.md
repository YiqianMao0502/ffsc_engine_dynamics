# 系统仿真指南

本页演示如何加载第二章系统模型、运行 Route-B demo，并根据输出排查问题。示例以 `scripts/run_routeB_system_demo.py` 为入口。

## 1. 构建系统

```python
from ffsc.chapter_2.section_2_6_system.system import EngineSystem

system = EngineSystem.build_from_files()
```

`build_from_files()` 默认加载 `data/props/` 中的 Route-B 数据；如需自定义，可传入关键字参数：

```python
EngineSystem.build_from_files(
    mbwr_fuel="data/props/mbwr_placeholders/ch4_mbwr32_placeholder.json",
    saturation_fuel="data/props/saturation/saturation_table.json",
    pump_performance_file="data/props/turbopump/pump_performance.csv",
etc.
)
```

## 2. 检查缺口

```python
missing = system.missing_data()
if missing:
    for item in missing:
        print("需要补充:", item)
```

缺口为空后再调用 `step()`，否则组件会因为 `MissingPropertyData` 而终止。

## 3. 运行 Route-B demo

```bash
python scripts/run_routeB_system_demo.py --steps 10 --dt 0.1 --summary
```

常用参数：

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--steps` | 10 | 迭代次数；每一步都会调用一次 `EngineSystem.step()` |
| `--dt` | 0.1 | 时间步长，传入 `step(dt=...)` |
| `--props-root` | `data/props` | 指向包含 Route-B JSON/CSV 的目录 |
| `--summary` | 关闭 | 追加打印最后一步的完整 JSON 摘要 |

输出示例：

```
Step 10/10 (dt=0.10)
  fuel_line.mdot = 18.2 kg/s, T = 115 K
  oxidizer_line.mdot = 38.0 kg/s, T = 100 K
  mix_manifold.p = 3.4e6 Pa, T = 890 K
  nozzle.thrust ≈ 1.6e6 N
```

数值仅反映 Route-B 数据下的数量级，替换数据文件后结果会同步变化。

## 4. 常见调整

| 目标 | 文件/操作 |
| --- | --- |
| 修改初始条件 | `data/props/system/initial_conditions.json` |
| 更新泵性能曲线 | `data/props/turbopump/pump_performance.csv`；必要时同步 `volute_coeffs.json` |
| 替换预燃室源项 | `data/props/preburner/default_state.json` |
| 调整喷管参数 | `data/props/nozzle/nozzle_coeffs.json` |
| 切换 Route-A 数据 | 用论文表格覆盖上述文件；在 `metadata.route` 中标记为 `A` |

## 5. 调试技巧

- `EngineSystem.step()` 在捕获 `MissingPropertyData` 时会附带具体字段，便于快速定位缺失输入。
- 可在 demo 脚本中插入 `print(system.state_snapshot())`，或将其写入 CSV 进行后处理。
- 当修改 JSON/CSV 后，建议重新运行 `pytest` 和 `show_missing_system_gaps.py`，确认数据格式未被破坏。

## 6. 文档联动

- 新增脚本或配置时，请同步更新本页以及 [快速开始](quickstart.md)，确保所有命令都可直接复制运行。
- 若补齐 Route-A 数据，请在 [Route-A 补充说明](route_A_readme.md) 中记录状态，方便团队成员追踪。

## 7. 图 21 / 图 23 验证

> ⚠️ 由于提交流程不允许纳入 PNG，仓库 **不** 附带论文原图，只在 `external/thesis_figures/README.md` 中说明使用方法。请从论文扫描件中提取 `figure21_whn_wtn.png` 与 `figure23_pump_head.png` 并置于 `external/thesis_figures/` 后再运行下述脚本。

- `scripts/digitize_figures.py` 会把 `external/thesis_figures/figure21_whn_wtn.png` 与 `figure23_pump_head.png` 转换成 `data/validation/figure21_cross_sections.json` 与 `figure23_digitized.csv`，方便后续复用。
- `scripts/compare_turbopump_figures.py --digitize` 先刷新上述数据，再构建当前的离心泵模型：
  - Figure 23：将泵的流量/压头输出映射到图中的归一化范围，报告各转速的 RMSE（单位：m）。
  - Figure 21：提取 WH/WT 在 “前/后” 两个 Ns 截面的实验曲线，并与模型计算的无量纲系数比较（给出归一化 RMSE 及最佳线性缩放系数）。
- 运行示例：
  ```bash
  python scripts/compare_turbopump_figures.py --digitize
  ```
  输出将列出三条压头曲线与四条交叉面之间的误差，便于追踪泵模型与论文图表的差异。
- 若需要论文图 21/23 的叠加 PNG，可在上述命令后追加 `--plot-dir docs/images/validation`：
  ```bash
  python scripts/compare_turbopump_figures.py --digitize --plot-dir docs/images/validation
  ```
  该脚本会在 `docs/images/validation/` 下生成 `figure21_overlay.png` 与 `figure23_overlay.png`（已在 `.gitignore` 中排除），随时可重建而无需把图片纳入版本库。
