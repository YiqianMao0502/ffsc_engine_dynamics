# FFSC Engine Dynamics

This repository contains a Python re-implementation of the key thermodynamic and component models from Zhou Chuang's dissertation (chapter 2).

## Branch layout
- The working branch in this repository snapshot is `work`. There is no Git remote configured inside the container, so the files you see here have **not** been pushed anywhere yet.
- If you want these commits to appear on your own remote `main` branch, run `git remote add origin <your-remote-url>` followed by `git push origin work:main` (or rename the branch locally with `git branch -M main` before pushing).

## Reference material
- Supplementary notes extracted from the dissertation are stored in `docs/paper_notes/` (e.g. `chapter2_pages71_80_notes.md`).
- Outstanding data requirements that still block end-to-end simulations can be listed with `python scripts/show_missing_system_gaps.py`.
- To exercise the approximate Route-B dataset and run a coarse §2.6 system demo, execute `python scripts/run_routeB_system_demo.py`.

## Route-B data refresh
- **Two-phase saturation**: `scripts/update_routeB_saturation_from_coolprop.py` calls CoolProp 6.6.0 (HEOS) to repopulate `data/props/saturation/saturation_table.json` with (p, ρ_l, ρ_v, h_l, h_v) pairs.
- **Preburner / nozzle inputs**: `scripts/update_routeB_preburner_from_cantera.py` uses Cantera 3.0.0 (`gri30.yaml`) plus the publicly available Raptor config in [KSP-RO/RealismOverhaul](https://github.com/KSP-RO/RealismOverhaul/blob/master/GameData/RealismOverhaul/Engine_Configs/Raptor_Config.cfg) to regenerate the oxygen-rich preburner state, species source terms, and the derived nozzle coefficients.
- **Pressurizer / pump curves**: `data/props/pressurizer/*.json` and `data/props/turbopump/*.json/csv` document the same RealismOverhaul references together with the affinity-law calculations used to convert thrust/Isp targets into UA values and head/flow tables.

> Optional dependencies: install `CoolProp` and `cantera` (e.g. `pip install CoolProp cantera`) before running the regeneration scripts.

## Figure digitization & validation
- `scripts/digitize_figures.py` uses OpenCV-based color segmentation (and the installed `plotdigitizer` fallback) to turn the thesis Figure 21/23 bitmaps into numerical datasets stored in `data/validation/`. 由于提交流程不接受二进制附件，仓库中仅保留 `external/thesis_figures/README.md`，请在本地自行把 `figure21_whn_wtn.png`、`figure23_pump_head.png` 复制到 `external/thesis_figures/` 后再运行脚本。
- `scripts/compare_turbopump_figures.py --digitize --plot-dir docs/images/validation` rebuilds those datasets, prints the RMSE statistics, **and saves overlay figures** (head/flow for Figure 23 plus head/torque coefficients for Figure 21) that juxtapose the digitized thesis traces with the current pump model. The generated PNGs live under `docs/images/validation/` and stay untracked because `.gitignore` excludes them.

## Documentation (ReadTheDocs style)
- The documentation stack now uses **MkDocs Material** (configured in `mkdocs.yml`) to provide tabbed navigation, instant search, and code-copy buttons across `docs/`.
- Serve the documentation locally with:
  ```bash
  pip install -r docs/requirements.txt
  mkdocs serve
  ```
  or build the static site with `mkdocs build --clean`.
- Key pages:
  - `docs/index.md`：文档地图与入口说明。
  - `docs/quickstart.md`：环境准备、测试、文档构建。
  - `docs/architecture.md` / `docs/data_and_interfaces.md`：模块映射与数据表字段。
  - `docs/simulation_guide.md`：系统仿真步骤与调试技巧。
  - `docs/troubleshooting.md`：常见问题记录（如补丁中携带 PNG/CSV 等二进制文件时的处理方式）。

## Getting started
```
conda activate ffsc_engine_dynamics
```
