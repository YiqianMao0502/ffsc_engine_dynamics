# Route-A 与 Route-B

Route-A/Route-B 是本项目在实现与数据使用上的两条“轨道”。本页总结差异、切换方法及推荐实践。

## 总体原则

| 项目术语 | 含义 | 数据来源 |
| --- | --- | --- |
| Route-A | 严格复现论文给出的方程结构，不引入论文外数值；缺失数据以 TODO/异常标注 | 论文章节、表格、附录 |
| Route-B | 在不改变方程形式的前提下，使用权威公开数据库补齐参数，确保可以数值闭合 | NIST、Cantera、NASA、公开泵曲线等 |

!!! note "当前状态"
    - §2.2 的 MBWR、SRK/PR、NASA-7、输运方程均已 Route-A 实现；甲烷/氧气的 mBWR 系数已由论文/Younglove 数据填充。
    - Route-B 数据文件（PR、NASA-7、饱和表、泵性能等）位于 `data/props/`，可直接驱动 `scripts/run_routeB_system_demo.py`。

## 代码层体现

- Route-A：`section_2_5_two_phase_mixed` 的组件骨架、`mbwr32.py` 的系数结构、`EngineSystem` 的拓扑等，全部严格对应论文方程。
- Route-B：通过 JSON/CSV 填充 `GasMixtureThermo`、`TwoPhaseThermo` 与泵/增压器参数。缺少数据时，代码会抛出 `MissingPropertyData`，提示需要回到论文或外部数据库。

## 如何切换

1. **物性数据**：替换 `data/props/mbwr_placeholders/*.json`、`mix_pr_demo.json` 等文件，即可在 Route-A/Route-B 之间切换。
2. **组件配置**：`EngineSystem.build_from_files()` 接受可选参数，可在脚本中指定不同的数据路径。
3. **脚本联动**：在 `scripts/run_routeB_system_demo.py` 中传入 `--config <file>`（可自行扩展）指向另一组 Route-A 数据。

## 数据管理建议

- 每个 JSON 建议包含 `"metadata": {"source": "...", "route": "A/B"}`，方便文档引用。
- 当 Route-A 数据尚未整理完成时，可用 Route-B 占位，但必须在 README/文档中说明“来源不在论文内部”。
- 更新数据后，请运行 `python scripts/show_missing_system_gaps.py` 确认所有缺口被清除。

## 关联脚本

| 脚本 | 用途 |
| --- | --- |
| `scripts/extract_gri30_coeffs.py` | 从 Cantera `gri30.yaml` 抽取 NASA-7 系数（Route-B） |
| `scripts/run_routeB_system_demo.py` | 使用 Route-B 数据跑系统 demo |
| `scripts/show_missing_system_gaps.py` | 报告当前缺失的数据项 |

## 常见问题

- **能否在 Route-B 数据上发表结果？** 建议在文档或图表中明确标注“Route-B（公开数据库）”。
- **如何引入新的物种？** 在 NASA-7、输运 JSON 中新增物种，同时更新 `GasMixtureThermo` 的注册表，不影响 Route-A 方程。
- **如何确认 Route-A 已完整？** 对照论文表格/公式，确保所有占位 JSON 已填入原始数值并通过测试；必要时在 [Route-A 补充说明](route_A_readme.md) 中更新状态。
