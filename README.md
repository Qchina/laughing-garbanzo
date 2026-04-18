# laughing-garbanzo - 软件度量自动化工具

一个用于课程实践的中小型软件度量自动化工具，支持：

- CK 模型：WMC、DIT、NOC、CBO、RFC、LCOM
- LK 模型：NOM、NOA、NOPM、MPC、DAC
- 传统度量：LoC、圈复杂度（近似）
- 项目估算：工作量/成本/时间（COCOMO Basic）
- 输入：Java 代码 + 设计图 JSON（类图、用例图、流程图）

## 快速开始

```bash
python3 src/metrics_tool.py \
  --source ./your-java-project \
  --design src/sample_design.json \
  --persons 5 \
  --hourly-rate 150 \
  --output metrics_report.json
```

## 测试

```bash
python3 -m pytest -q
```

## 报告

详见：`docs/project_report.md`
