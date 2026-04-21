# Software Metrics Automation Tool

This project is a course experiment tool for Software Quality Assurance.

It supports:
- CK metrics: `WMC`, `DIT`, `NOC`, `CBO`, `RFC`, `LCOM`
- LK metrics: `NOM`, `NOA`, `NOPM`, `MPC`, `DAC`
- Traditional metrics: `LoC`, cyclomatic complexity (approximation)
- Estimation: effort/cost/schedule (`COCOMO Basic`, approximation)

## Core Analyzer (B role)

```bash
python src/metrics_tool.py \
  --source ./your-java-project \
  --design src/sample_design.json \
  --persons 5 \
  --hourly-rate 150 \
  --output metrics_report.json
```

## C 同学可视化层

窗口模式（通过界面导入项目和图文件）：

```bash
python src/gui_dashboard.py
```

你可以：
- 选择 Java 项目目录
- 导入 UML/类图/用例图/流程图文件（可选）
- 导入已有度量 JSON（可选）
- 点击“生成可视化报告”输出 HTML 页面

推荐模式（读取 B 模块生成的 JSON）：

```bash
python src/presentation_tool.py \
  --input-json metrics_report.json \
  --json-output metrics_report_visual.json \
  --html-output metrics_dashboard.html
```

可选直连模式（直接调用分析模块）：

```bash
python src/presentation_tool.py \
  --source ./your-java-project \
  --design src/sample_design.json \
  --persons 5 \
  --hourly-rate 150 \
  --json-output metrics_report_visual.json \
  --html-output metrics_dashboard.html
```

输出文件：
- `metrics_report_visual.json`
- `metrics_dashboard.html`

## 测试

```bash
python -m pytest -q
```

若当前环境没有 `pytest`，请使用你们组统一的测试命令。
