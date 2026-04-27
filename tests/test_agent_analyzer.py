#!/usr/bin/env python3
"""Agent分析模块测试用例"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent_analyzer import AgentAnalyzer, analyze_report_file


def create_sample_metrics_report() -> dict:
    """创建示例度量报告"""
    return {
        "project": {
            "class_count": 5,
            "loc": 1500,
            "avg_wmc": 12.5,
            "avg_cbo": 4.2,
            "avg_rfc": 25.3,
            "avg_lcom": 0.45,
            "avg_dit": 1.2,
            "avg_noc": 0.8,
            "avg_mpc": 15.0,
            "avg_dac": 3.5
        },
        "estimation": {
            "kloc": 1.5,
            "effort_person_month": 3.8,
            "schedule_month": 2.5,
            "person_hours": 577.6,
            "cost": 69312.0,
            "duration_by_staff_month": 3.6
        },
        "classes": [
            {
                "name": "UserService",
                "parent": "BaseService",
                "methods": 15,
                "public_methods": 10,
                "fields": 8,
                "complexity": 35,
                "cbo": 12,
                "rfc": 40,
                "lcom": 0.85,
                "dit": 2,
                "noc": 1,
                "mpc": 20,
                "dac": 5
            },
            {
                "name": "OrderProcessor",
                "parent": None,
                "methods": 12,
                "public_methods": 8,
                "fields": 6,
                "complexity": 22,
                "cbo": 9,
                "rfc": 30,
                "lcom": 0.65,
                "dit": 1,
                "noc": 0,
                "mpc": 15,
                "dac": 4
            },
            {
                "name": "ProductCatalog",
                "parent": None,
                "methods": 8,
                "public_methods": 6,
                "fields": 4,
                "complexity": 8,
                "cbo": 3,
                "rfc": 15,
                "lcom": 0.30,
                "dit": 0,
                "noc": 2,
                "mpc": 8,
                "dac": 2
            },
            {
                "name": "PaymentHandler",
                "parent": None,
                "methods": 10,
                "public_methods": 7,
                "fields": 5,
                "complexity": 18,
                "cbo": 7,
                "rfc": 22,
                "lcom": 0.55,
                "dit": 1,
                "noc": 0,
                "mpc": 12,
                "dac": 3
            },
            {
                "name": "InventoryManager",
                "parent": None,
                "methods": 6,
                "public_methods": 4,
                "fields": 3,
                "complexity": 5,
                "cbo": 2,
                "rfc": 10,
                "lcom": 0.20,
                "dit": 0,
                "noc": 1,
                "mpc": 5,
                "dac": 1
            }
        ]
    }


def test_agent_analyzer_initialization():
    """测试AgentAnalyzer初始化"""
    analyzer = AgentAnalyzer()
    assert analyzer is not None
    assert analyzer.api_provider == "deepseek"

    analyzer2 = AgentAnalyzer(api_provider="openai")
    assert analyzer2.api_provider == "openai"

    analyzer3 = AgentAnalyzer(api_key="test-key", api_provider="deepseek")
    assert analyzer3.api_key == "test-key"

    print("✓ test_agent_analyzer_initialization passed")


def test_analyze_metrics():
    """测试基于规则的分析功能"""
    analyzer = AgentAnalyzer()
    report = create_sample_metrics_report()

    result = analyzer.analyze_metrics(report)

    assert result is not None
    assert len(result.summary) > 0
    assert len(result.recommendations) > 0
    assert len(result.high_complexity_methods) > 0
    assert len(result.high_coupling_classes) > 0
    assert len(result.refactoring_suggestions) > 0
    assert "risk_level" in result.risk_assessment

    assert result.risk_assessment["risk_level"] in ["low", "medium", "high"]

    print("✓ test_analyze_metrics passed")


def test_high_complexity_identification():
    """测试高复杂度识别"""
    analyzer = AgentAnalyzer()
    report = create_sample_metrics_report()

    result = analyzer.analyze_metrics(report)

    high_complex = result.high_complexity_methods
    assert len(high_complex) > 0
    assert high_complex[0]["name"] == "UserService"
    assert high_complex[0]["complexity"] == 35

    print("✓ test_high_complexity_identification passed")


def test_high_coupling_identification():
    """测试高耦合识别"""
    analyzer = AgentAnalyzer()
    report = create_sample_metrics_report()

    result = analyzer.analyze_metrics(report)

    high_coupling = result.high_coupling_classes
    assert len(high_coupling) > 0
    assert high_coupling[0]["name"] == "UserService"
    assert high_coupling[0]["cbo"] == 12

    print("✓ test_high_coupling_identification passed")


def test_refactoring_suggestions():
    """测试重构建议生成"""
    analyzer = AgentAnalyzer()
    report = create_sample_metrics_report()

    result = analyzer.analyze_metrics(report)

    suggestions = result.refactoring_suggestions
    assert len(suggestions) > 0

    high_priority = [s for s in suggestions if s["priority"] == "high"]
    assert len(high_priority) > 0

    print("✓ test_refactoring_suggestions passed")


def test_risk_assessment():
    """测试风险评估"""
    analyzer = AgentAnalyzer()
    report = create_sample_metrics_report()

    result = analyzer.analyze_metrics(report)

    risk = result.risk_assessment
    assert "risk_level" in risk
    assert "risk_score" in risk
    assert "risk_factors" in risk
    assert "maintenance_difficulty" in risk

    assert risk["risk_level"] in ["low", "medium", "high"]
    assert risk["risk_score"] >= 0
    assert len(risk["risk_factors"]) > 0

    print("✓ test_risk_assessment passed")


def test_analyze_with_ai_no_api_key():
    """测试无API密钥时的AI分析"""
    analyzer = AgentAnalyzer(api_key=None)

    os.environ.pop("DEEPSEEK_API_KEY", None)
    os.environ.pop("OPENAI_API_KEY", None)

    analyzer2 = AgentAnalyzer(api_key=None)
    report = create_sample_metrics_report()

    result = analyzer2.analyze_with_ai(report)

    assert "error" in result
    assert "fallback" in result
    assert "summary" in result["fallback"]

    print("✓ test_analyze_with_ai_no_api_key passed")


def test_analysis_result_to_dict():
    """测试AnalysisResult转字典"""
    analyzer = AgentAnalyzer()
    report = create_sample_metrics_report()

    result = analyzer.analyze_metrics(report)
    result_dict = result.to_dict()

    assert isinstance(result_dict, dict)
    assert "summary" in result_dict
    assert "recommendations" in result_dict
    assert "high_complexity_methods" in result_dict
    assert "high_coupling_classes" in result_dict
    assert "refactoring_suggestions" in result_dict
    assert "risk_assessment" in result_dict

    print("✓ test_analysis_result_to_dict passed")


def test_generate_summary():
    """测试摘要生成"""
    analyzer = AgentAnalyzer()
    report = create_sample_metrics_report()
    project_info = report["project"]
    estimation = report["estimation"]

    summary = analyzer._generate_summary(project_info, estimation)

    assert len(summary) > 0
    assert "项目概况分析" in summary
    assert str(project_info["class_count"]) in summary
    assert str(project_info["loc"]) in summary

    print("✓ test_generate_summary passed")


def test_generate_recommendations():
    """测试建议生成"""
    analyzer = AgentAnalyzer()
    report = create_sample_metrics_report()
    project_info = report["project"]
    classes = report["classes"]

    recommendations = analyzer._generate_recommendations(project_info, classes)

    assert isinstance(recommendations, list)
    assert len(recommendations) > 0

    print("✓ test_generate_recommendations passed")


def run_all_tests():
    """运行所有测试"""
    print("\n=== Agent Analyzer 模块测试 ===\n")

    test_agent_analyzer_initialization()
    test_analyze_metrics()
    test_high_complexity_identification()
    test_high_coupling_identification()
    test_refactoring_suggestions()
    test_risk_assessment()
    test_analyze_with_ai_no_api_key()
    test_analysis_result_to_dict()
    test_generate_summary()
    test_generate_recommendations()

    print("\n=== 所有测试通过 ===\n")


if __name__ == "__main__":
    run_all_tests()
