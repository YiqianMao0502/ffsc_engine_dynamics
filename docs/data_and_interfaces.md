# 数据与接口

本页列出 `data/props/` 目录下的主要文件、字段说明与引用来源，并说明它们如何被物性/组件接口消费。

## 数据文件概览

| 路径 | 作用 | 备注 |
| --- | --- | --- |
| `mbwr_placeholders/*.json` | mBWR-32 系数、ρ<sub>crit</sub> | `metadata.source` 会注明“论文表 8”或 Younglove/Ely（Route-B） |
| `mix_pr_demo.json` | Peng–Robinson 物种参数 | 包含 Tc、Pc、ω；可自行扩展物种列表 |
| `mix_nasa7_gri30.json` | NASA-7 热力多项式 | 由 `external/gri30.yaml` 抽取，含低/高温段系数 |
| `transport_v2c2_tm86885.json` | V2C2 输运参数 | NASA TM-86885/4513；支持 Wilke + Mason–Saxena 混合 |
| `saturation/saturation_table.json` | Route-B 两相饱和表 | `scripts/update_routeB_saturation_from_coolprop.py` 调用 CoolProp 6.6 HEOS 生成 `T/p/ρ/h` |
| `pressurizer/pressurizer_hx.json` | 贮箱增压器 UA、壁体热容 | 由 Raptor mass-flow (RealismOverhaul) + Cantera cp 推算，可被 §2.5.4 数据覆盖 |
| `turbopump/*.json/csv` | 涡壳常数、叶轮几何、性能曲线、损失系数 | 当前版本利用 Raptor_Config.cfg 转速/流量 + 泵相似定律生成 |
| `preburner/default_state.json` | 预燃室初始条件与热源 | 由 `scripts/update_routeB_preburner_from_cantera.py` (Cantera 3.0.0) 输出 eq 组分/源项 |
| `nozzle/nozzle_coeffs.json` | 喷管排放、冷却系数 | throat/exit 面积、冷却系数来自 Raptor_Config.cfg + Cantera γ/输运 |
| `system/initial_conditions.json` | 系统初态 | 提供燃料/氧化剂管路、混合腔的 p/T/质量流 |

!!! tip "如何新增数据"
    复制现有 JSON，补充 `metadata` 字段（来源、Route 类型、时间戳），并在本页更新对应表格即可。

### Route-B 数据再生成脚本

| 脚本 | 依赖 | 功能 |
| --- | --- | --- |
| `scripts/update_routeB_saturation_from_coolprop.py` | `pip install CoolProp` | 重新采样 CH₄/O₂ 饱和压力、密度与焓，并覆盖 `saturation_table.json` |
| `scripts/update_routeB_preburner_from_cantera.py` | `pip install cantera` | 根据指定推力/Isp/φ 计算预燃室平衡组成与源项 |

运行脚本会直接覆盖 `data/props/` 中的对应文件，执行前可先 `git stash` 或创建备份。

## 物性接口

### `GasMixtureThermo`

```python
from ffsc.chapter_2.section_2_2_properties.interfaces import GasMixtureThermo

gas = GasMixtureThermo.from_files(
    eos_file="data/props/mix_pr_demo.json",
    thermo_file="data/props/mix_nasa7_gri30.json",
    transport_file="data/props/transport_v2c2_tm86885.json",
)
state = gas.state(p=3.5e6, T=900.0, composition={"CH4": 0.3, "O2": 0.7})
```

返回对象包含 `rho`, `h`, `cp`, `cv`, `gamma`, `mu`, `k`, `prandtl` 等字段；如请求超出可用范围会抛出 `MissingPropertyData`。

### `TwoPhaseThermo`

```python
from ffsc.chapter_2.section_2_2_properties.interfaces import TwoPhaseThermo

two_phase = TwoPhaseThermo.from_files(
    mbwr_file="data/props/mbwr_placeholders/ch4_mbwr32_placeholder.json",
    saturation_file="data/props/saturation/saturation_table.json",
)
residual = two_phase.state(rho=420.0, T=110.0)
```

除 mBWR 残余量外，接口还提供：

- `saturation_pressure(T)`：从饱和表插值得到 \(p_{sat}\)。
- `quality_from_density(rho, T)`：结合液/汽密度给出干度。
- `derivatives`：`dp_dT_at_rho`、`dp_drho_at_T`、`du_dT_at_v` 等，供两相容腔使用。

## 组件与接口耦合

| 组件 | 依赖接口 | 必要数据 |
| --- | --- | --- |
| `TwoPhasePipe` / `TwoPhasePlenum` | `TwoPhaseThermo` | mBWR 系数 + 饱和表 |
| `MixGasPipe` / `MixGasPlenum` | `GasMixtureThermo` | PR + NASA7 + V2C2 |
| `PressurizerHX` | 两种接口 | `pressurizer_hx.json` 中的 `UA`, `wall_heat_capacity` |
| `CentrifugalPump` | -- | `volute_coeffs.json`, `impeller_geometry.json`, `pump_performance.csv`, `loss_coeffs.json` |
| `PreburnerChamber` | `GasMixtureThermo` | `preburner/default_state.json` |
| `NozzleModel` | `GasMixtureThermo` | `nozzle/nozzle_coeffs.json` |

## 缺失数据跟踪

运行：

```bash
python scripts/show_missing_system_gaps.py
```

脚本会尝试构建 `EngineSystem` 并收集所有 `MissingPropertyData`，输出尚未提供的文件或字段。确保列表为空后再运行系统仿真。

## 提交数据的最佳实践

1. **记录来源**：在 `metadata.source` 中写明论文页码或外部数据库网址。
2. **注明路线**：`metadata.route` 可取 `"A"` 或 `"B"`，方便在文档中引用。
3. **保持单位一致**：所有表格默认使用 SI（Pa、K、kg/s、m³/s）。如果引用其它单位，请在 JSON 中加入 `"units": "..."` 并在文档描述。
4. **同步文档**：新增/修改数据后，更新本页及 [系统仿真指南](simulation_guide.md) 以免用户误用旧配置。
