from pathlib import Path

from src.metrics_tool import build_report, parse_java_file


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

    cm, _, loc = parse_java_file(f)
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
