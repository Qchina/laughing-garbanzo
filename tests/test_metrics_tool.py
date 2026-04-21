from pathlib import Path

from src.metrics_tool import build_report, parse_java_file_with_ast
from src.presentation_tool import generate_dashboard


def test_parse_java_file_basic(tmp_path: Path):
    code = '''
    public class A extends B {
      private int x;
      public void m1() { if (x > 0) { x--; } helper.call(); }
      public void m2() { for (int i=0;i<10;i++) { x += i; } }
    }
    '''
    f = tmp_path / 'A.java'
    f.write_text(code, encoding='utf-8')

    cm, _, loc = parse_java_file_with_ast(f)
    assert cm is not None
    assert cm.name == 'A'
    assert cm.parent == 'B'
    assert cm.methods >= 2
    assert cm.public_methods == 2
    assert cm.fields >= 1
    assert cm.complexity >= 3
    assert loc > 0


def test_build_report(tmp_path: Path):
    src = tmp_path / 'src'
    src.mkdir()
    (src / 'A.java').write_text('public class A { public void x(){} }', encoding='utf-8')
    design = tmp_path / 'design.json'
    design.write_text('{"class_diagrams":[],"use_cases":[],"flow_charts":[]}', encoding='utf-8')

    report = build_report(src, design, persons=3, hourly_rate=100)
    assert report['project']['class_count'] == 1
    assert 'estimation' in report


def test_generate_dashboard_from_report(tmp_path: Path):
    report = {
        "project": {
            "class_count": 2,
            "loc": 220,
            "avg_wmc": 18,
            "avg_cbo": 6,
            "avg_rfc": 22,
            "avg_lcom": 0.52,
            "avg_dit": 1,
            "avg_noc": 0,
            "avg_mpc": 10,
            "avg_dac": 3,
        },
        "estimation": {
            "kloc": 0.22,
            "effort_person_month": 0.42,
            "schedule_month": 1.5,
            "person_hours": 64.0,
            "cost": 7680.0,
            "duration_by_staff_month": 0.1,
        },
        "classes": [
            {"name": "A", "complexity": 26, "cbo": 10, "rfc": 35, "lcom": 0.91, "dit": 1},
            {"name": "B", "complexity": 10, "cbo": 3, "rfc": 12, "lcom": 0.2, "dit": 0},
        ],
    }
    out_json = tmp_path / "visual.json"
    out_html = tmp_path / "dashboard.html"

    generate_dashboard(report, output_json=out_json, output_html=out_html, source_label="unit-test")
    assert out_json.exists()
    assert out_html.exists()
    html = out_html.read_text(encoding="utf-8")
    assert "软件度量可视化报告" in html
    assert "风险类高亮" in html
