# 架构概览

本页描述论文第 2 章在代码中的映射关系，并梳理脚本、数据与模块之间的依赖。

## 顶层目录

```text
src/ffsc/
  chapter_2/
    section_2_2_properties/   # 物性模型（MBWR、PR、NASA-7、输运）
    section_2_3_turbopump/    # 涡轮泵（涡壳 + 叶轮 + 性能插值）
    section_2_4_thrust_preburner/
    section_2_5_two_phase_mixed/
    section_2_6_system/
```

- `data/props/`：所有 JSON/CSV 数据表，按模块划分子目录。
- `scripts/`：调试脚本，例如 `run_routeB_system_demo.py`、`show_missing_system_gaps.py`。
- `docs/`：本套 MkDocs 文档，对应 README 中的引用。

## Section 2.2：物性层

| 模块 | 功能 | 输入 | 输出 |
| --- | --- | --- | --- |
| `impl/mbwr32.py` | Route-A mBWR-32 EOS，提供残余量与导数 | `mbwr_placeholders/*.json` | `ResidualProps`、`dp/dT|ρ` 等 | 
| `impl/srk_pr.py` | SRK / Peng–Robinson 混合 EOS | `mix_pr_demo.json` | 压力、a/b 混合参数 |
| `impl/nasa7_mix.py` | NASA-7 热力学 | `mix_nasa7_gri30.json` | cp、h、s、多段系数 |
| `impl/transport_mixers.py` | Wilke + Mason–Saxena 输运 | `transport_v2c2_tm86885.json` | μ、λ、Pr |
| `interfaces.py` | `GasMixtureThermo`、`TwoPhaseThermo` 聚合接口 | 来自上方所有数据 | 供 2.5/2.6 调用的 `state()` 等方法 |

## Section 2.3：涡轮泵

`section_2_3_turbopump/centrifugal_pump.py` 通过 `build_from_tables()` 将以下数据合并：

- `turbopump/volute_coeffs.json`：表 9 中的几何常数 \(C_1\dots C_4\)。
- `turbopump/impeller_geometry.json`：叶轮尺寸、转速范围。
- `turbopump/pump_performance.csv`：表 11/12 对应的流量-扬程-效率曲线。
- `turbopump/loss_coeffs.json`：经验损失项，作为 Route-B 估计。

生成的 `CentrifugalPump` 在系统级中负责提供扬程、输出功率与效率信息。

## Section 2.4：预燃室与喷管

- `preburner.py`：根据 `preburner/default_state.json` 初始化组分、热源，使用 `GasMixtureThermo` 更新焓、γ、μ 等。
- 喷管模型位于 `section_2_6_system/system.py`，引用 `nozzle/nozzle_coeffs.json`（排放系数、冷却系数）和 `GasMixtureThermo` 来评估推力、冷却需求。

## Section 2.5：两相/混合气组件

| 文件 | 描述 | 依赖 |
| --- | --- | --- |
| `base.py` | 定义 `FluidState`/`Component` 基类、共用 dataclass | -- |
| `tp_pipe.py` | 两相管路（式 2.82–2.92），支持摩擦与加速压降 | `TwoPhaseThermo` + 饱和表 |
| `tp_plenum.py` | 两相容腔（式 2.84–2.87），跟踪质量、能量 | `TwoPhaseThermo` | 
| `mix_pipe.py` | 混合气阻性 + 换热（式 2.95–2.103） | `GasMixtureThermo`、输运参数 |
| `mix_plenum.py` | 混合气容腔，处理焓积累 | `GasMixtureThermo` |
| `pressurizer.py` | 贮箱增压换热器骨架 | `pressurizer/pressurizer_hx.json` + 物性接口 |

## Section 2.6：系统装配

`section_2_6_system/system.py` 将上述模块连接成网络：

1. 加载 `system/initial_conditions.json` 获取初态。
2. 构建两相、混合气物性接口。
3. 初始化泵、管路、阀门、预燃室、喷管及增压器。
4. 在 `EngineSystem.step()` 内按论文图 48 的拓扑推进状态，并返回关键量（流量、压强、温度、推力估计等）。

`EngineSystem.missing_data()` 会扫描所有组件的 `MissingPropertyData`，用于提醒尚未填补的表格或参数。

## 关联脚本与文档

| 目标 | 入口 |
| --- | --- |
| Route-B 系统 demo | `scripts/run_routeB_system_demo.py` |
| 数据缺口清单 | `scripts/show_missing_system_gaps.py` |
| 论文笔记 | `docs/paper_notes/` 目录；在 MkDocs 导航“附录”下可快速跳转 |

## 扩展建议

- 当新增章节（如第 3 章）时，建议复制 `chapter_2` 的结构与文档模板，保持同样的 README / MkDocs 导航。
- 任何新增数据文件，请在 [数据与接口](data_and_interfaces.md) 中登记表格，说明来源与用途。
