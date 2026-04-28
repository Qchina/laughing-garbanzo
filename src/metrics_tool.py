#!/usr/bin/env python3
"""中小型软件度量自动化工具（教学版）

支持：
1) 代码度量：LoC、圈复杂度（近似）
2) 面向对象度量：CK（WMC、DIT、NOC、CBO、RFC、LCOM）
3) 面向对象度量：LK（NOM、NOA、NOPM、MPC、DAC）
4) 规模-工作量-成本预测：COCOMO Basic（教学近似）
5) 设计输入：支持读取类图/用例图/流程图的结构化 JSON
6) AI Agent分析：调用API进行深度分析并生成改进建议
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

from src.ast_parser import ASTParser
from src.loc_counter import LoCCounter
from src.cyclomatic_complexity import CyclomaticComplexityCalculator
from src.ck_metrics import CKMetricsCalculator
from src.code_statistics import CodeStatistics
from src.method_length import MethodLengthCalculator
from src.agent_analyzer import AgentAnalyzer


@dataclass
class ClassMetrics:
    name: str
    parent: str | None
    methods: int = 0
    public_methods: int = 0
    fields: int = 0
    complexity: int = 1
    cbo: int = 0
    rfc: int = 0
    lcom: float = 0.0
    dit: int = 0
    noc: int = 0
    mpc: int = 0
    dac: int = 0

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["lcom"] = round(self.lcom, 3)
        return data


def compute_hierarchy_metrics(classes: Dict[str, ClassMetrics]) -> None:
    children: Dict[str, List[str]] = {}
    for name, cm in classes.items():
        if cm.parent:
            children.setdefault(cm.parent, []).append(name)

    for name, cm in classes.items():
        depth = 0
        p = cm.parent
        while p and p in classes:
            depth += 1
            p = classes[p].parent
        cm.dit = depth
        cm.noc = len(children.get(name, []))


def read_design_input(design_file: Path | None) -> Dict:
    if not design_file:
        return {}
    return json.loads(design_file.read_text(encoding="utf-8"))


def estimate_effort_cost(total_loc: int, persons: int, hourly_rate: float) -> Dict[str, float]:
    kloc = total_loc / 1000.0
    effort_pm = 2.4 * (kloc ** 1.05) if kloc > 0 else 0.0
    schedule_month = 2.5 * (effort_pm ** 0.38) if effort_pm > 0 else 0.0
    person_hours = effort_pm * 152
    cost = person_hours * hourly_rate
    duration_by_staff = person_hours / max(persons, 1) / 160
    return {
        "kloc": round(kloc, 3),
        "effort_person_month": round(effort_pm, 3),
        "schedule_month": round(schedule_month, 3),
        "person_hours": round(person_hours, 2),
        "cost": round(cost, 2),
        "duration_by_staff_month": round(duration_by_staff, 3),
    }


def aggregate(class_metrics: Dict[str, ClassMetrics], total_loc: int, design: Dict, persons: int, hourly_rate: float) -> Dict:
    compute_hierarchy_metrics(class_metrics)
    rows = [cm.to_dict() for cm in class_metrics.values()]

    avg = lambda key: round(sum(getattr(c, key) for c in class_metrics.values()) / max(len(class_metrics), 1), 3)

    summary = {
        "project": {
            "class_count": len(class_metrics),
            "loc": total_loc,
            "avg_wmc": avg("complexity"),
            "avg_cbo": avg("cbo"),
            "avg_rfc": avg("rfc"),
            "avg_lcom": avg("lcom"),
            "avg_dit": avg("dit"),
            "avg_noc": avg("noc"),
            "avg_mpc": avg("mpc"),
            "avg_dac": avg("dac"),
        },
        "estimation": estimate_effort_cost(total_loc, persons=persons, hourly_rate=hourly_rate),
        "design_input": {
            "class_diagram_count": len(design.get("class_diagrams", [])),
            "use_case_count": len(design.get("use_cases", [])),
            "flow_chart_count": len(design.get("flow_charts", [])),
        },
        "classes": rows,
    }
    return summary


def find_java_files(input_dir: Path) -> List[Path]:
    return sorted(input_dir.rglob("*.java"))


def parse_java_file_with_ast(path: Path) -> Tuple[ClassMetrics | None, str, int]:
    """使用AST解析Java文件

    Args:
        path: Java文件路径

    Returns:
        (ClassMetrics, 代码内容, 代码行数)
    """
    ast_parser = ASTParser()
    loc_counter = LoCCounter()
    cc_calculator = CyclomaticComplexityCalculator()
    ck_calculator = CKMetricsCalculator()

    structure = ast_parser.parse_file(path)
    if not structure or not structure['classes']:
        code = path.read_text(encoding="utf-8")
        loc = loc_counter.count_file(path)['code']
        return None, code, loc

    class_info = structure['classes'][0]
    class_name = class_info['name']
    parent = class_info.get('parent')

    metrics = ClassMetrics(name=class_name, parent=parent)

    metrics.methods = len(class_info.get('methods', []))
    metrics.fields = len(class_info.get('fields', []))

    for method in class_info.get('methods', []):
        if 'public' in method.get('modifiers', []):
            metrics.public_methods += 1

    complexity = cc_calculator.calculate_file_complexity(path)
    if class_name in complexity:
        metrics.complexity = complexity[class_name]['total_complexity']

    ck_metrics = ck_calculator.calculate_file_metrics(path)
    if class_name in ck_metrics:
        metrics.cbo = ck_metrics[class_name]['cbo']
        metrics.rfc = ck_metrics[class_name]['rfc']
        metrics.lcom = ck_metrics[class_name]['lcom']

    code = path.read_text(encoding="utf-8")
    calls = re.findall(r"(\w+)\.(\w+)\s*\(", code)
    metrics.mpc = len(calls)

    primitive = {"int", "long", "double", "float", "boolean", "char", "byte", "short", "String"}
    type_refs = set(re.findall(r"\b([A-Z]\w*)\b", code))
    metrics.dac = len({t for t in type_refs if t not in primitive and t != class_name})

    loc = loc_counter.count_file(path)['code']

    return metrics, code, loc


def build_report(source_dir: Path, design_file: Path | None, persons: int, hourly_rate: float) -> Dict:
    java_files = find_java_files(source_dir)
    class_metrics: Dict[str, ClassMetrics] = {}
    total_loc = 0

    for file in java_files:
        cm, _, loc = parse_java_file_with_ast(file)
        total_loc += loc
        if cm:
            class_metrics[cm.name] = cm

    design = read_design_input(design_file)
    return aggregate(class_metrics, total_loc, design, persons, hourly_rate)


def analyze_with_agent(report: Dict, api_key: str = None, use_ai: bool = False) -> Dict:
    """使用Agent分析度量报告

    Args:
        report: 度量报告字典
        api_key: API密钥
        use_ai: 是否使用AI深度分析

    Returns:
        包含分析结果的字典
    """
    analyzer = AgentAnalyzer(api_key=api_key)

    if use_ai:
        ai_result = analyzer.analyze_with_ai(report)
        rule_result = analyzer.analyze_metrics(report)
        return {
            "rule_based": rule_result.to_dict(),
            "ai_analysis": ai_result
        }
    else:
        result = analyzer.analyze_metrics(report)
        return result.to_dict()


def main() -> None:
    parser = argparse.ArgumentParser(description="软件度量自动化工具（CK/LK/复杂度/规模/成本/AI分析）")
    parser.add_argument("--source", required=True, help="Java 源码目录")
    parser.add_argument("--design", help="类图/用例图/流程图 JSON 输入")
    parser.add_argument("--persons", type=int, default=4, help="团队人数")
    parser.add_argument("--hourly-rate", type=float, default=120.0, help="人力小时成本（元）")
    parser.add_argument("--output", default="metrics_report.json", help="输出报告 JSON")
    parser.add_argument("--analyze", action="store_true", help="启用AI Agent分析")
    parser.add_argument("--use-ai", action="store_true", help="使用AI进行深度分析（需要API密钥）")
    parser.add_argument("--api-key", help="AI API密钥（也可通过环境变量设置）")
    parser.add_argument("--analysis-output", default="analysis_report.json", help="AI分析报告输出路径")
    args = parser.parse_args()

    source_dir = Path(args.source)
    design_file = Path(args.design) if args.design else None

    print("正在分析 Java 项目...")
    report = build_report(source_dir, design_file, args.persons, args.hourly_rate)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"基础报告已生成: {args.output}")

    if args.analyze or args.use_ai:
        print("\n正在进行AI Agent分析...")
        api_key = args.api_key or None
        analysis_result = analyze_with_agent(report, api_key=api_key, use_ai=args.use_ai)

        Path(args.analysis_output).write_text(json.dumps(analysis_result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"分析报告已生成: {args.analysis_output}")

        if args.use_ai and "error" in analysis_result.get("ai_analysis", {}):
            print(f"\n警告: {analysis_result['ai_analysis']['error']}")
            print("已使用基于规则的分析结果作为备选")


if __name__ == "__main__":
    main()
