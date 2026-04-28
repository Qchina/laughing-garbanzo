#!/usr/bin/env python3
"""Metrics visualization report generator for C-layer deliverable.

This file is intentionally ASCII-only to avoid mojibake.
Chinese UI strings are injected via unicode escapes.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


TXT = {
    "title": "\u8f6f\u4ef6\u5ea6\u91cf\u53ef\u89c6\u5316\u62a5\u544a",
    "h1": "\u9762\u5411 Java \u9879\u76ee\u7684\u8f6f\u4ef6\u5ea6\u91cf\u53ef\u89c6\u5316\u62a5\u544a",
    "source": "\u5206\u6790\u6765\u6e90",
    "generated": "\u751f\u6210\u65f6\u95f4",
    "class_count": "\u7c7b\u6570\u91cf",
    "loc": "\u603b\u4ee3\u7801\u884c LoC",
    "avg_wmc": "\u5e73\u5747 WMC",
    "avg_cbo": "\u5e73\u5747 CBO",
    "complexity_coupling": "\u590d\u6742\u5ea6\u4e0e\u8026\u5408\u5206\u5e03",
    "complexity_coupling_sub": "\u6309\u7c7b\u5c55\u793a WMC / CBO \u6307\u6807",
    "lcom_dist": "LCOM \u5206\u5e03",
    "lcom_sub": "LCOM \u8d8a\u9ad8\uff0c\u7c7b\u5185\u805a\u6027\u8d8a\u5f31",
    "top_wmc": "\u9ad8\u590d\u6742\u5ea6\u7c7b Top 10",
    "top_cbo": "\u9ad8\u8026\u5408\u7c7b Top 10",
    "class_name": "\u7c7b\u540d",
    "risky_classes": "\u98ce\u9669\u7c7b\u9ad8\u4eae",
    "thresholds": "\u9608\u503c",
    "risk_level": "\u98ce\u9669\u7b49\u7ea7",
    "reason": "\u89e6\u53d1\u539f\u56e0",
    "suggestion": "\u91cd\u6784\u5efa\u8bae",
    "no_risk": "\u672a\u68c0\u6d4b\u5230\u8d85\u8fc7\u9608\u503c\u7684\u98ce\u9669\u7c7b\u3002",
    "estimation": "\u9879\u76ee\u4f30\u7b97",
    "effort_pm": "\u5de5\u4f5c\u91cf\uff08\u4eba\u6708\uff09",
    "schedule_month": "\u5f00\u53d1\u5468\u671f\uff08\u6708\uff09",
    "person_hours": "\u603b\u5de5\u65f6",
    "cost": "\u4f30\u7b97\u6210\u672c",
    "duration_staff": "\u5f53\u524d\u4eba\u5458\u914d\u7f6e\u4e0b\u5468\u671f",
    "ai_section": "AI Agent \u5206\u6790\u7ed3\u679c",
    "ai_model": "AI \u6a21\u578b",
    "ai_status": "AI \u72b6\u6001",
    "ai_generated": "AI \u751f\u6210\u65f6\u95f4",
    "ai_unavailable": "AI \u5206\u6790\u672a\u542f\u7528\u6216\u6682\u4e0d\u53ef\u7528\u3002",
    "json_ok": "\u5df2\u751f\u6210 JSON \u62a5\u544a",
    "html_ok": "\u5df2\u751f\u6210 HTML \u53ef\u89c6\u5316\u9875\u9762",
}


def _json_js(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _find_java_files(source: Path) -> List[Path]:
    return sorted(source.rglob("*.java"))


def _strip_comments(code: str) -> str:
    code = re.sub(r"//.*", "", code)
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    return code


def _count_loc(code: str) -> int:
    return sum(1 for line in code.splitlines() if line.strip())


def _estimate_complexity(code: str) -> int:
    return 1 + len(re.findall(r"\b(if|for|while|case|catch|switch)\b|\?|&&|\|\|", code))


def _fallback_analyze(source: Path, design: Path | None, persons: int, hourly_rate: float) -> Dict:
    class_pattern = re.compile(r"\bclass\s+(\w+)(?:\s+extends\s+(\w+))?", re.MULTILINE)
    method_pattern = re.compile(
        r"(public|private|protected)?\s*(?:static\s+)?(?:final\s+)?[\w<>,\[\]]+\s+(\w+)\s*\(([^)]*)\)\s*\{",
        re.MULTILINE,
    )
    field_pattern = re.compile(
        r"(public|private|protected)?\s*(?:static\s+)?(?:final\s+)?[\w<>,\[\]]+\s+(\w+)\s*(?:=.*?)?;",
        re.MULTILINE,
    )
    call_pattern = re.compile(r"(\w+)\.(\w+)\s*\(")

    classes: List[Dict] = []
    total_loc = 0

    for java_file in _find_java_files(source):
        raw = java_file.read_text(encoding="utf-8", errors="ignore")
        code = _strip_comments(raw)
        total_loc += _count_loc(code)

        class_match = class_pattern.search(code)
        if not class_match:
            continue

        class_name = class_match.group(1)
        parent = class_match.group(2)
        methods = list(method_pattern.finditer(code))
        calls = call_pattern.findall(code)
        type_refs = set(re.findall(r"\b([A-Z]\w*)\b", code))
        primitive = {"String", "Integer", "Long", "Double", "Float", "Boolean", "Character", "Byte", "Short"}

        classes.append(
            {
                "name": class_name,
                "parent": parent,
                "methods": len(methods),
                "public_methods": sum(1 for m in methods if (m.group(1) or "").strip() == "public"),
                "fields": len(list(field_pattern.finditer(code))),
                "complexity": _estimate_complexity(code),
                "cbo": len({obj for obj, _ in calls if obj not in {"this", "super"}}),
                "rfc": len(methods) + len({name for _, name in calls}),
                "lcom": 0.0,
                "dit": 0,
                "noc": 0,
                "mpc": len(calls),
                "dac": len({t for t in type_refs if t not in primitive and t != class_name}),
            }
        )

    class_map = {c["name"]: c for c in classes}
    children: Dict[str, List[str]] = {}
    for c in classes:
        if c.get("parent"):
            children.setdefault(c["parent"], []).append(c["name"])
    for c in classes:
        depth = 0
        p = c.get("parent")
        while p and p in class_map:
            depth += 1
            p = class_map[p].get("parent")
        c["dit"] = depth
        c["noc"] = len(children.get(c["name"], []))

    design_data = {}
    if design and design.exists():
        try:
            design_data = json.loads(design.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            design_data = {}

    count = max(len(classes), 1)
    avg = lambda key: round(sum(float(c.get(key, 0)) for c in classes) / count, 3)

    kloc = total_loc / 1000.0
    effort_pm = 2.4 * (kloc ** 1.05) if kloc > 0 else 0.0
    schedule_month = 2.5 * (effort_pm ** 0.38) if effort_pm > 0 else 0.0
    person_hours = effort_pm * 152
    cost = person_hours * hourly_rate
    duration = person_hours / max(persons, 1) / 160

    return {
        "project": {
            "class_count": len(classes),
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
        "estimation": {
            "kloc": round(kloc, 3),
            "effort_person_month": round(effort_pm, 3),
            "schedule_month": round(schedule_month, 3),
            "person_hours": round(person_hours, 2),
            "cost": round(cost, 2),
            "duration_by_staff_month": round(duration, 3),
        },
        "design_input": {
            "class_diagram_count": len(design_data.get("class_diagrams", [])),
            "use_case_count": len(design_data.get("use_cases", [])),
            "flow_chart_count": len(design_data.get("flow_charts", [])),
        },
        "classes": classes,
    }


def _load_report(input_json: Path | None, source: Path | None, design: Path | None, persons: int, hourly_rate: float) -> Dict:
    if input_json:
        return json.loads(input_json.read_text(encoding="utf-8"))
    if not source:
        raise ValueError("Please provide --input-json or --source.")

    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from src.metrics_tool import build_report
        return build_report(source, design, persons=persons, hourly_rate=hourly_rate)
    except Exception:
        return _fallback_analyze(source, design, persons=persons, hourly_rate=hourly_rate)


def _score_class(cls: Dict, thresholds: Dict) -> Tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []
    wmc = int(cls.get("complexity", 0))
    cbo = int(cls.get("cbo", 0))
    rfc = int(cls.get("rfc", 0))
    lcom = float(cls.get("lcom", 0.0))
    if wmc >= thresholds["class_wmc"]:
        score += 1
        reasons.append(f"WMC={wmc}")
    if cbo >= thresholds["class_cbo"]:
        score += 1
        reasons.append(f"CBO={cbo}")
    if rfc >= thresholds["class_rfc"]:
        score += 1
        reasons.append(f"RFC={rfc}")
    if lcom >= thresholds["class_lcom"]:
        score += 1
        reasons.append(f"LCOM={round(lcom, 3)}")
    return score, reasons


def _derive_quality_analysis(report: Dict) -> Dict:
    thresholds = {"class_wmc": 20, "class_cbo": 8, "class_rfc": 30, "class_lcom": 0.8}
    risky_classes = []
    for cls in report.get("classes", []):
        score, reasons = _score_class(cls, thresholds)
        if score == 0:
            continue
        risky_classes.append(
            {
                "class": cls.get("name", "Unknown"),
                "severity": "high" if score >= 2 else "medium",
                "reasons": reasons,
                "suggestion": "\u5efa\u8bae\u62c6\u5206\u7c7b\u804c\u8d23\uff0c\u964d\u4f4e\u8026\u5408\u5e76\u63d0\u70bc\u590d\u6742\u903b\u8f91\u3002",
            }
        )
    risky_classes.sort(key=lambda x: (x["severity"] != "high", x["class"]))
    return {"thresholds": thresholds, "risky_classes": risky_classes}


def _top_classes(classes: List[Dict], key: str, top_n: int = 10) -> List[Dict]:
    return sorted(classes, key=lambda x: x.get(key, 0), reverse=True)[:top_n]


def _build_ai_prompt(report: Dict, source_label: str) -> str:
    project = report.get("project", {})
    estimation = report.get("estimation", {})
    classes = report.get("classes", [])
    top_wmc = _top_classes(classes, "complexity", top_n=5)
    top_cbo = _top_classes(classes, "cbo", top_n=5)
    payload = {
        "source": source_label,
        "project": project,
        "estimation": estimation,
        "top_wmc": [
            {"name": c.get("name"), "wmc": c.get("complexity"), "cbo": c.get("cbo"), "rfc": c.get("rfc"), "lcom": c.get("lcom")}
            for c in top_wmc
        ],
        "top_cbo": [
            {"name": c.get("name"), "cbo": c.get("cbo"), "wmc": c.get("complexity"), "rfc": c.get("rfc"), "dit": c.get("dit")}
            for c in top_cbo
        ],
    }
    return (
        "You are a senior software quality agent. "
        "Write a concise analysis in Chinese. "
        "Use 4 sections with short headings: 1) Overall quality judgement 2) Key risks 3) Refactoring priorities 4) Next sprint actions. "
        "Keep it practical and concrete. Avoid hallucinating code details that are not in input.\n\n"
        "Input JSON:\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )


def _extract_response_text(response: Dict) -> str:
    text = response.get("output_text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    output = response.get("output", [])
    for item in output:
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                value = content.get("text", "")
                if value and value.strip():
                    return value.strip()
    return ""


def _extract_chat_text(response: Dict) -> str:
    choices = response.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                txt = item.get("text")
                if isinstance(txt, str) and txt.strip():
                    parts.append(txt.strip())
        return "\n".join(parts).strip()
    return ""


def _post_json(url: str, headers: Dict[str, str], payload: Dict, timeout_sec: int) -> Dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=max(timeout_sec, 5)) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def _run_ai_analysis(
    report: Dict,
    source_label: str,
    model: str,
    timeout_sec: int,
    api_base_url: str,
    api_mode: str,
) -> Dict:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return {
            "enabled": False,
            "status": "skipped",
            "reason": "missing_api_key",
            "model": model,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": "No OPENAI_API_KEY found. AI analysis skipped.",
        }

    prompt = _build_ai_prompt(report, source_label)
    base = api_base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    if api_mode == "chat-completions":
        url = f"{base}/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a senior software quality analysis agent."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }
    else:
        url = f"{base}/responses"
        payload = {
            "model": model,
            "input": prompt,
            "temperature": 0.3,
        }

    try:
        body = _post_json(url=url, headers=headers, payload=payload, timeout_sec=timeout_sec)
        if api_mode == "chat-completions":
            content = _extract_chat_text(body) or "AI response is empty."
        else:
            content = _extract_response_text(body) or "AI response is empty."
        return {
            "enabled": True,
            "status": "ok",
            "reason": "",
            "model": model,
            "api_mode": api_mode,
            "api_base_url": api_base_url,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": content,
        }
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="ignore")
        except Exception:
            detail = str(exc)
        return {
            "enabled": True,
            "status": "failed",
            "reason": f"http_{exc.code}",
            "model": model,
            "api_mode": api_mode,
            "api_base_url": api_base_url,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": f"AI request failed: HTTP {exc.code}. {detail[:500]}",
        }
    except Exception as exc:
        return {
            "enabled": True,
            "status": "failed",
            "reason": "runtime_error",
            "model": model,
            "api_mode": api_mode,
            "api_base_url": api_base_url,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": f"AI request failed: {exc}",
        }


def generate_html(report: Dict, source_label: str) -> str:
    project = report.get("project", {})
    estimation = report.get("estimation", {})
    classes = report.get("classes", [])
    quality = report.get("quality_analysis") or _derive_quality_analysis(report)
    ai_analysis = report.get("ai_analysis", {})

    thresholds = quality.get("thresholds", {})
    risky_classes = quality.get("risky_classes", [])
    class_names = [c.get("name", "") for c in classes]
    class_wmc = [int(c.get("complexity", 0)) for c in classes]
    class_cbo = [int(c.get("cbo", 0)) for c in classes]
    class_lcom = [round(float(c.get("lcom", 0.0)), 3) for c in classes]

    top_wmc = _top_classes(classes, "complexity")
    top_cbo = _top_classes(classes, "cbo")
    generated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ai_content = str(ai_analysis.get("content", "")).strip()
    ai_model = str(ai_analysis.get("model", "N/A"))
    ai_status = str(ai_analysis.get("status", "skipped"))
    ai_generated = str(ai_analysis.get("generated_at", "-"))
    ai_html = html.escape(ai_content).replace("\n", "<br>") if ai_content else TXT["ai_unavailable"]

    risky_rows = "".join(
        f"<tr><td>{item.get('class')}</td><td><span class='badge {item.get('severity')}'>{item.get('severity')}</span></td><td>{', '.join(item.get('reasons', []))}</td><td>{item.get('suggestion')}</td></tr>"
        for item in risky_classes
    ) or f"<tr><td colspan='4'>{TXT['no_risk']}</td></tr>"

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{TXT['title']}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --bg: #f4f7fb; --card: #ffffff; --text: #1f2a44; --muted: #65708a;
      --accent: #005f73; --warn: #ee9b00; --danger: #bb3e03; --line: #dce3ef;
      --shadow: 0 6px 18px rgba(31, 42, 68, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
      background: radial-gradient(circle at top left, rgba(10,147,150,0.08), transparent 35%), var(--bg);
      color: var(--text);
    }}
    .container {{ width: min(1180px, 94vw); margin: 24px auto 40px; }}
    .hero {{
      background: linear-gradient(135deg, #005f73 0%, #0a9396 65%, #94d2bd 100%);
      color: #fff; border-radius: 16px; padding: 22px 24px; box-shadow: var(--shadow); margin-bottom: 16px;
    }}
    .hero h1 {{ margin: 0 0 6px; font-size: 1.45rem; }}
    .hero p {{ margin: 0; opacity: 0.95; font-size: 0.95rem; }}
    .grid {{ display: grid; gap: 12px; grid-template-columns: repeat(4, minmax(0, 1fr)); margin-bottom: 12px; }}
    .card {{ background: var(--card); border-radius: 13px; padding: 14px 16px; box-shadow: var(--shadow); border: 1px solid var(--line); }}
    .kpi-title {{ color: var(--muted); font-size: 0.85rem; }}
    .kpi-value {{ font-size: 1.5rem; font-weight: 700; margin-top: 2px; color: var(--accent); }}
    .section {{ display: grid; gap: 12px; grid-template-columns: 1fr 1fr; margin-bottom: 12px; }}
    .card h2 {{ margin: 0 0 10px; font-size: 1.04rem; }}
    .sub {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 8px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
    th, td {{ padding: 8px 6px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 2px 10px; font-size: 0.76rem; color: #fff; }}
    .badge.high {{ background: var(--danger); }}
    .badge.medium {{ background: var(--warn); color: #333; }}
    .badge.ai-ok {{ background: #0a9396; }}
    .badge.ai-failed {{ background: #bb3e03; }}
    .badge.ai-skipped {{ background: #94a3b8; }}
    .ai-panel {{ white-space: normal; line-height: 1.65; color: #1f2a44; }}
    .ai-meta {{ color: var(--muted); font-size: 0.84rem; margin-bottom: 10px; }}
    .list {{ margin: 0; padding-left: 18px; }}
    @media (max-width: 980px) {{ .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} .section {{ grid-template-columns: 1fr; }} }}
    @media (max-width: 560px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class="container">
    <header class="hero">
      <h1>{TXT['h1']}</h1>
      <p>{TXT['source']}: {source_label} | {TXT['generated']}: {generated_time}</p>
    </header>
    <section class="grid">
      <div class="card"><div class="kpi-title">{TXT['class_count']}</div><div class="kpi-value">{project.get("class_count", 0)}</div></div>
      <div class="card"><div class="kpi-title">{TXT['loc']}</div><div class="kpi-value">{project.get("loc", 0)}</div></div>
      <div class="card"><div class="kpi-title">{TXT['avg_wmc']}</div><div class="kpi-value">{project.get("avg_wmc", 0)}</div></div>
      <div class="card"><div class="kpi-title">{TXT['avg_cbo']}</div><div class="kpi-value">{project.get("avg_cbo", 0)}</div></div>
    </section>
    <section class="section">
      <article class="card">
        <h2>{TXT['complexity_coupling']}</h2>
        <div class="sub">{TXT['complexity_coupling_sub']}</div>
        <canvas id="wmcCboChart"></canvas>
      </article>
      <article class="card">
        <h2>{TXT['lcom_dist']}</h2>
        <div class="sub">{TXT['lcom_sub']}</div>
        <canvas id="lcomChart"></canvas>
      </article>
    </section>
    <section class="section">
      <article class="card">
        <h2>{TXT['top_wmc']}</h2>
        <table><thead><tr><th>{TXT['class_name']}</th><th>WMC</th><th>CBO</th><th>RFC</th><th>LCOM</th></tr></thead>
          <tbody>
            {"".join(f"<tr><td>{c.get('name')}</td><td>{c.get('complexity')}</td><td>{c.get('cbo')}</td><td>{c.get('rfc')}</td><td>{round(float(c.get('lcom', 0.0)), 3)}</td></tr>" for c in top_wmc)}
          </tbody>
        </table>
      </article>
      <article class="card">
        <h2>{TXT['top_cbo']}</h2>
        <table><thead><tr><th>{TXT['class_name']}</th><th>CBO</th><th>WMC</th><th>RFC</th><th>DIT</th></tr></thead>
          <tbody>
            {"".join(f"<tr><td>{c.get('name')}</td><td>{c.get('cbo')}</td><td>{c.get('complexity')}</td><td>{c.get('rfc')}</td><td>{c.get('dit')}</td></tr>" for c in top_cbo)}
          </tbody>
        </table>
      </article>
    </section>
    <section class="section">
      <article class="card">
        <h2>{TXT['risky_classes']}</h2>
        <div class="sub">{TXT['thresholds']}: WMC>={thresholds.get("class_wmc", "-")}, CBO>={thresholds.get("class_cbo", "-")}, RFC>={thresholds.get("class_rfc", "-")}, LCOM>={thresholds.get("class_lcom", "-")}</div>
        <table><thead><tr><th>{TXT['class_name']}</th><th>{TXT['risk_level']}</th><th>{TXT['reason']}</th><th>{TXT['suggestion']}</th></tr></thead><tbody>{risky_rows}</tbody></table>
      </article>
      <article class="card">
        <h2>{TXT['estimation']}</h2>
        <ul class="list">
          <li>KLoC: {estimation.get("kloc", 0)}</li>
          <li>{TXT['effort_pm']}: {estimation.get("effort_person_month", 0)}</li>
          <li>{TXT['schedule_month']}: {estimation.get("schedule_month", 0)}</li>
          <li>{TXT['person_hours']}: {estimation.get("person_hours", 0)}</li>
          <li>{TXT['cost']}: {estimation.get("cost", 0)}</li>
          <li>{TXT['duration_staff']}: {estimation.get("duration_by_staff_month", 0)} \u6708</li>
        </ul>
      </article>
    </section>
    <section class="section">
      <article class="card" style="grid-column: 1 / -1;">
        <h2>{TXT['ai_section']}</h2>
        <div class="ai-meta">
          {TXT['ai_model']}: {html.escape(ai_model)} |
          {TXT['ai_status']}: <span class="badge ai-{'ok' if ai_status == 'ok' else ('failed' if ai_status == 'failed' else 'skipped')}">{html.escape(ai_status)}</span> |
          {TXT['ai_generated']}: {html.escape(ai_generated)}
        </div>
        <div class="ai-panel">{ai_html}</div>
      </article>
    </section>
  </div>
  <script>
    const classNames = {_json_js(class_names)};
    const classWmc = {_json_js(class_wmc)};
    const classCbo = {_json_js(class_cbo)};
    const classLcom = {_json_js(class_lcom)};
    new Chart(document.getElementById("wmcCboChart"), {{
      type: "bar",
      data: {{ labels: classNames, datasets: [
        {{ label: "WMC", data: classWmc, backgroundColor: "rgba(10,147,150,0.6)", borderColor: "rgba(10,147,150,1)", borderWidth: 1 }},
        {{ label: "CBO", data: classCbo, backgroundColor: "rgba(238,155,0,0.6)", borderColor: "rgba(238,155,0,1)", borderWidth: 1 }}
      ]}},
      options: {{ responsive: true, plugins: {{ legend: {{ position: "top" }} }} }}
    }});
    new Chart(document.getElementById("lcomChart"), {{
      type: "line",
      data: {{ labels: classNames, datasets: [{{ label: "LCOM", data: classLcom, borderColor: "rgba(187,62,3,1)", backgroundColor: "rgba(187,62,3,0.2)", tension: 0.28, fill: true, pointRadius: 3 }}] }},
      options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true, suggestedMax: 1.0 }} }} }}
    }});
  </script>
</body>
</html>
"""


def generate_dashboard(
    report: Dict,
    output_json: Path,
    output_html: Path,
    source_label: str,
    ai_model: str,
    ai_timeout: int,
    disable_ai: bool,
    ai_base_url: str,
    ai_api_mode: str,
) -> None:
    if not disable_ai:
        report["ai_analysis"] = _run_ai_analysis(
            report,
            source_label=source_label,
            model=ai_model,
            timeout_sec=ai_timeout,
            api_base_url=ai_base_url,
            api_mode=ai_api_mode,
        )
    else:
        report["ai_analysis"] = {
            "enabled": False,
            "status": "skipped",
            "reason": "disabled_by_flag",
            "model": ai_model,
            "api_mode": ai_api_mode,
            "api_base_url": ai_base_url,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": "AI analysis disabled by --disable-ai-analysis.",
        }
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    output_html.write_text(generate_html(report, source_label), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate metrics visualization HTML report.")
    parser.add_argument("--input-json", help="Input JSON report generated by core analyzer.")
    parser.add_argument("--source", help="Java source directory (direct mode).")
    parser.add_argument("--design", help="Design input JSON file.")
    parser.add_argument("--persons", type=int, default=4, help="Team size for estimation.")
    parser.add_argument("--hourly-rate", type=float, default=120.0, help="Hourly labor cost.")
    parser.add_argument("--ai-model", default=os.getenv("OPENAI_MODEL", "gpt-5.2"), help="Model name for AI analysis.")
    parser.add_argument("--ai-timeout", type=int, default=45, help="AI request timeout in seconds.")
    parser.add_argument(
        "--ai-base-url",
        default=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
        help="AI API base URL. Example: https://api.openai.com/v1 or https://ark.cn-beijing.volces.com/api/v3",
    )
    parser.add_argument(
        "--ai-api-mode",
        choices=["responses", "chat-completions"],
        default=os.getenv("AI_API_MODE", "responses"),
        help="API style for AI call.",
    )
    parser.add_argument("--disable-ai-analysis", action="store_true", help="Disable AI analysis module.")
    parser.add_argument("--json-output", default="metrics_report_visual.json", help="Output JSON path.")
    parser.add_argument("--html-output", default="metrics_dashboard.html", help="Output HTML path.")
    args = parser.parse_args()

    input_json = Path(args.input_json) if args.input_json else None
    source = Path(args.source) if args.source else None
    design = Path(args.design) if args.design else None
    output_json = Path(args.json_output)
    output_html = Path(args.html_output)

    report = _load_report(
        input_json=input_json,
        source=source,
        design=design,
        persons=args.persons,
        hourly_rate=args.hourly_rate,
    )
    source_label = str(source) if source else (str(input_json) if input_json else "N/A")
    generate_dashboard(
        report,
        output_json=output_json,
        output_html=output_html,
        source_label=source_label,
        ai_model=args.ai_model,
        ai_timeout=args.ai_timeout,
        disable_ai=args.disable_ai_analysis,
        ai_base_url=args.ai_base_url,
        ai_api_mode=args.ai_api_mode,
    )
    print(f"{TXT['json_ok']}: {output_json}")
    print(f"{TXT['html_ok']}: {output_html}")


if __name__ == "__main__":
    main()
