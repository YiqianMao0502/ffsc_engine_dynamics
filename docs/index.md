# FFSC Engine Dynamics 文档

欢迎来到 **ffsc_engine_dynamics** 项目的集中式文档。本套内容以 MkDocs Material 打造，提供类似 Read the Docs 的导航体验，覆盖论文第 2 章的全部代码实现、数据文件与运行脚本。

> 文档语言以中文为主，必要处提供英文术语，以便对照论文与源码。

## 文档地图

| 模块 | 作用 | 入口 |
| --- | --- | --- |
| 概览 | 入门指引、环境准备 | [快速开始](quickstart.md) |
| 实现细节 | 目录结构、物性接口、Route 选择 | [架构概览](architecture.md)、[Route-A 与 Route-B](route_modes.md)、[数据与接口](data_and_interfaces.md) |
| 仿真流程 | 系统搭建、脚本运行、调试建议 | [系统仿真指南](simulation_guide.md) |
| 附录 | Route-A 说明与逐页论文笔记 | [Route-A 补充说明](route_A_readme.md)、[论文笔记索引](paper_notes/README.md) |

## 使用建议

1. **新同学**：按 [快速开始](quickstart.md) 配置环境、安装依赖并运行 `pytest`。
2. **补数据/查缺口**：在 [数据与接口](data_and_interfaces.md) 查找 JSON/CSV 的字段含义，同时运行 `python scripts/show_missing_system_gaps.py`。
3. **调试系统级仿真**：阅读 [系统仿真指南](simulation_guide.md)，结合 `scripts/run_routeB_system_demo.py` 验证 Route-B 数据链。
4. **回溯公式**：从附录跳转至对应页码笔记，确认实现是否匹配论文描述。

## 版本

- 文档版本：`v0.2`（随仓库最新提交更新）
- 覆盖范围：论文第 2 章（§2.2–§2.6）及其 Route-A / Route-B 数据

## 反馈

若文档与代码不一致，请在提交 PR 时同步修改对应 `.md` 文件，并在 `mkdocs serve` 本地预览后再提交，以确保导航、链接及表格展示正确。
