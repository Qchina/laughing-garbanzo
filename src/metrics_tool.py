#!/usr/bin/env python3
"""中小型软件度量自动化工具（教学版）

支持：
1) 代码度量：LoC、圈复杂度（近似）
2) 面向对象度量：CK（WMC、DIT、NOC、CBO、RFC、LCOM）
3) 面向对象度量：LK（NOM、NOA、NOPM、MPC、DAC）
4) 规模-工作量-成本预测：COCOMO Basic（教学近似）
5) 设计输入：支持读取类图/用例图/流程图的结构化 JSON
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

JAVA_CLASS_RE = re.compile(
    r"class\s+(?P<name>\w+)(?:\s+extends\s+(?P<parent>\w+))?(?:\s+implements\s+(?P<impl>[\w,\s]+))?",
    re.MULTILINE,
)

METHOD_RE = re.compile(
    r"(?P<scope>public|private|protected)?\s*(?:static\s+)?(?:final\s+)?[\w<>,\[\]]+\s+(?P<name>\w+)\s*\((?P<args>[^)]*)\)\s*\{",
    re.MULTILINE,
)

FIELD_RE = re.compile(
    r"(?P<scope>public|private|protected)?\s*(?:static\s+)?(?:final\s+)?[\w<>,\[\]]+\s+(?P<name>\w+)\s*(?:=.*?)?;",
    re.MULTILINE,
)

CALL_RE = re.compile(r"(\w+)\.(\w+)\s*\(")
COMPLEXITY_TOKENS = re.compile(r"\b(if|for|while|case|catch|\?|&&|\|\|)\b")


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


def strip_comments(code: str) -> str:
    code = re.sub(r"//.*", "", code)
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    return code


def count_loc(code: str) -> int:
    return sum(1 for line in code.splitlines() if line.strip())


def estimate_complexity(code: str) -> int:
    base = 1
    return base + len(COMPLEXITY_TOKENS.findall(code))


def parse_java_file(path: Path) -> Tuple[ClassMetrics | None, str, int]:
    raw = path.read_text(encoding="utf-8")
    code = strip_comments(raw)

    class_match = JAVA_CLASS_RE.search(code)
    if not class_match:
        return None, code, count_loc(code)

    class_name = class_match.group("name")
    parent = class_match.group("parent")
    metrics = ClassMetrics(name=class_name, parent=parent)

    methods = METHOD_RE.finditer(code)
    method_spans: List[Tuple[int, int, str]] = []
    for m in methods:
        metrics.methods += 1
        scope = (m.group("scope") or "").strip()
        if scope == "public":
            metrics.public_methods += 1
        method_spans.append((m.start(), m.end(), m.group("name")))

    fields = FIELD_RE.finditer(code)
    for _ in fields:
        metrics.fields += 1

    metrics.complexity = estimate_complexity(code)

    calls = CALL_RE.findall(code)
    metrics.mpc = len(calls)
    called_objects = {obj for obj, _ in calls if obj not in {"this", "super"}}
    metrics.cbo = len(called_objects)
    metrics.rfc = metrics.methods + len({name for _, name in calls})

    # 近似 LCOM：基于字段与方法标识符是否同名引用
    field_names = {f.group("name") for f in FIELD_RE.finditer(code)}
    method_bodies = extract_method_bodies(code)
    if metrics.methods > 1 and field_names:
        share = 0
        non_share = 0
        names = list(method_bodies.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                fi = used_fields(field_names, method_bodies[names[i]])
                fj = used_fields(field_names, method_bodies[names[j]])
                if fi & fj:
                    share += 1
                else:
                    non_share += 1
        metrics.lcom = max(non_share - share, 0) / max(non_share + share, 1)

    # DAC: Data Abstraction Coupling（近似）
    primitive = {"int", "long", "double", "float", "boolean", "char", "byte", "short", "String"}
    type_refs = set(re.findall(r"\b([A-Z]\w*)\b", code))
    metrics.dac = len({t for t in type_refs if t not in primitive and t != class_name})

    return metrics, code, count_loc(code)


def extract_method_bodies(code: str) -> Dict[str, str]:
    bodies = {}
    for m in METHOD_RE.finditer(code):
        name = m.group("name")
        start = m.end() - 1
        brace = 0
        end = start
        for idx in range(start, len(code)):
            if code[idx] == "{":
                brace += 1
            elif code[idx] == "}":
                brace -= 1
                if brace == 0:
                    end = idx
                    break
        bodies[name] = code[start:end + 1]
    return bodies


def used_fields(field_names: Set[str], body: str) -> Set[str]:
    used = set()
    for field in field_names:
        if re.search(rf"\b{re.escape(field)}\b", body):
            used.add(field)
    return used


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


def build_report(source_dir: Path, design_file: Path | None, persons: int, hourly_rate: float) -> Dict:
    java_files = find_java_files(source_dir)
    class_metrics: Dict[str, ClassMetrics] = {}
    total_loc = 0

    for file in java_files:
        cm, _, loc = parse_java_file(file)
        total_loc += loc
        if cm:
            class_metrics[cm.name] = cm

    design = read_design_input(design_file)
    return aggregate(class_metrics, total_loc, design, persons, hourly_rate)


def main() -> None:
    parser = argparse.ArgumentParser(description="软件度量自动化工具（CK/LK/复杂度/规模/成本）")
    parser.add_argument("--source", required=True, help="Java 源码目录")
    parser.add_argument("--design", help="类图/用例图/流程图 JSON 输入")
    parser.add_argument("--persons", type=int, default=4, help="团队人数")
    parser.add_argument("--hourly-rate", type=float, default=120.0, help="人力小时成本（元）")
    parser.add_argument("--output", default="metrics_report.json", help="输出报告 JSON")
    args = parser.parse_args()

    source_dir = Path(args.source)
    design_file = Path(args.design) if args.design else None

    report = build_report(source_dir, design_file, args.persons, args.hourly_rate)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"报告已生成: {args.output}")


if __name__ == "__main__":
    main()
