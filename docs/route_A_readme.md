# Route-A（论文边界内）

状态：**方程结构全部完成**，但部分数据仍需由论文原始表格补齐。本页记录各节的实现情况与待办。

## §2.2 物性模型

| 子节 | 已完成 | 待补 |
| --- | --- | --- |
| 2.2.1 mBWR-32 | `mbwr32.py` 已实现式 (2.1) 以及残余量/导数；`data/props/mbwr_placeholders/ch4,o2_*.json` 已填入论文/Younglove 系数 | 其余推进剂（若论文给出）需继续补表 8；理想气补偿项仍待论文明确 |
| 2.2.2 SRK/PR | `srk_pr.py` 复现式 (2.2)–(2.13)，并提供混合规则 | 若论文列出专用 Tc/Pc/ω，需要将数据替换现有 Route-B JSON |
| 2.2.3 NASA-7 | `nasa7_mix.py` 结构已匹配式 (2.5)–(2.7) | 需根据论文附表替换 `mix_nasa7_gri30.json`，并注明来源 |
| 2.2.4 输运 | `transport_mixers.py` 给出论文形式（Wilke + Mason–Saxena） | 待补论文提供的输运系数；当前 Route-B 数据来自 NASA TM |

## §2.3 涡轮泵

- **实现**：`section_2_3_turbopump/centrifugal_pump.py` 已按照图 20、式 (2.14)–(2.55) 的结构划分涡壳/叶轮模型，支持插值性能曲线。
- **待补**：若论文提供更精细的 C<sub>1</sub>~C<sub>4</sub>、损失系数或实验点，应替换 `data/props/turbopump/*.json/csv` 并在 `metadata.route` 标记为 `A`。

## §2.4 预燃室与喷管

- 预燃室守恒方程及喷管等熵/排放模型均已按论文结构实现。
- 仍需将论文给出的初始组分、化学源项、喷管排放系数录入 `preburner/default_state.json` 与 `nozzle/nozzle_coeffs.json`，以便 Route-A 仿真不依赖工程估计。

## §2.5 两相与混合气组件

- `TwoPhasePipe`、`TwoPhasePlenum`、`MixGasPipe`、`MixGasPlenum`、`PressurizerHX` 的方程均已编码；接口与论文式 (2.82)–(2.103) 保持一致。
- 仍需：
  - 论文 §2.5.4 的换热关联（替换 `pressurizer/pressurizer_hx.json`）。
  - 若论文提供更准确的摩擦、换热系数，请将其转录到对应 JSON。

## §2.6 系统装配

- `EngineSystem` 构建逻辑遵循论文图 48，`missing_data()` 用于跟踪尚未填充的 Route-A 数值。
- 要获得纯 Route-A 结果，需要：
  1. 用论文表 21/23/24 的参数覆盖 `data/props/system/initial_conditions.json`。
  2. 在 `data/props/` 中用 Route-A 数据替换所有当前的 Route-B 占位。

## 操作建议

1. 每当填入新的论文数据，请同步更新 `metadata.source` 与本页状态，方便核查。
2. 若某表暂缺，可在 JSON 中保留 `null` 并让组件抛出 `MissingPropertyData`，避免误用假数据。
3. 在切换 Route-A 配置后，运行 `pytest` 与 `scripts/show_missing_system_gaps.py`，确认系统仍可装配。
