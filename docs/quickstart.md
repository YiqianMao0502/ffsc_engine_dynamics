# 快速开始

本页介绍如何在本地复现 `ffsc_engine_dynamics` 第二章的仿真环境，并连接到 MkDocs 文档。每一步都可在 Linux、macOS 或 WSL 下执行。

## 1. 克隆与分支

```bash
git clone <your-repo-url>
cd ffsc_engine_dynamics
# 本仓库的活跃分支是 work，可按需重命名
```

!!! tip "推送到自己的 GitHub"
    若要把容器内的提交同步到远端：`git remote add origin <url>`，然后执行 `git push origin work:main`（或 `git branch -M main` 后 `git push -u origin main`）。

## 2. Python 环境

```bash
conda create -n ffsc python=3.11 -y
conda activate ffsc
pip install -r requirements.txt  # 若缺省，可先运行 `pip install -e .[dev]`
```

可选：安装文档依赖。

```bash
pip install -r docs/requirements.txt  # 等价于 pip install "mkdocs>=1" "mkdocs-material>=9"
```

可选：若需重建 Route-B 数据，请安装下列物性库：

```bash
pip install CoolProp cantera
```

## 3. 基础校验

| 操作 | 命令 | 说明 |
| --- | --- | --- |
| 单元测试 | `pytest` | 覆盖 mBWR 残余量等核心逻辑 |
| 缺口检查 | `python scripts/show_missing_system_gaps.py` | 输出尚未填充的数据文件 |
| Route-B demo | `python scripts/run_routeB_system_demo.py --steps 10 --dt 0.1` | 使用公开数据跑系统流程 |

!!! warning "缺失数据"
    如果 `show_missing_system_gaps.py` 报告仍有缺项，请先补齐 `data/props/` 下对应 JSON/CSV，再运行 demo。

## 4. 构建文档（可选）

```bash
mkdocs serve          # 在 http://127.0.0.1:8000 预览
mkdocs build --clean  # 生成静态站点到 site/
```

MkDocs Material 主题已在 `mkdocs.yml` 中启用，支持导航折叠、代码复制按钮与搜索高亮。

## 5. 下一步

1. 阅读 [架构概览](architecture.md) 了解目录与模块映射。
2. 在 [数据与接口](data_and_interfaces.md) 中确认自己需要补充的 JSON 字段。
3. 参考 [系统仿真指南](simulation_guide.md) 调整初始条件或替换 Route-A 数据。
