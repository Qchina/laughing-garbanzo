#!/usr/bin/env python3
"""核心度量模块测试用例"""

import pytest
from pathlib import Path

from src.ast_parser import ASTParser
from src.loc_counter import LoCCounter
from src.cyclomatic_complexity import CyclomaticComplexityCalculator
from src.ck_metrics import CKMetricsCalculator
from src.code_statistics import CodeStatistics
from src.method_length import MethodLengthCalculator


@pytest.fixture
def demo_file():
    """演示文件路径"""
    return Path('demo/DemoClass.java')


def test_ast_parser(demo_file):
    """测试AST解析模块"""
    parser = ASTParser()
    structure = parser.parse_file(demo_file)
    
    assert structure is not None
    assert len(structure['classes']) == 1
    
    class_info = structure['classes'][0]
    assert class_info['name'] == 'DemoClass'
    assert len(class_info['methods']) >= 9
    assert len(class_info['fields']) >= 3


def test_loc_counter(demo_file):
    """测试LoC统计模块"""
    counter = LoCCounter()
    stats = counter.count_file(demo_file)
    
    assert stats['total'] > 0
    assert stats['code'] > 0
    assert stats['blank'] >= 0
    assert stats['comment'] >= 0


def test_cyclomatic_complexity(demo_file):
    """测试圈复杂度计算模块"""
    calculator = CyclomaticComplexityCalculator()
    complexity = calculator.calculate_file_complexity(demo_file)
    
    assert 'DemoClass' in complexity
    assert complexity['DemoClass']['total_complexity'] > 0
    assert len(complexity['DemoClass']['method_complexities']) >= 9


def test_ck_metrics(demo_file):
    """测试CK指标计算模块"""
    calculator = CKMetricsCalculator()
    metrics = calculator.calculate_file_metrics(demo_file)
    
    assert 'DemoClass' in metrics
    assert metrics['DemoClass']['wmc'] > 0
    assert metrics['DemoClass']['rfc'] > 0


def test_code_statistics(demo_file):
    """测试代码统计模块"""
    stats = CodeStatistics()
    result = stats.analyze_file(demo_file)
    
    assert result['classes'] >= 1
    assert result['methods'] >= 9
    assert result['fields'] >= 3


def test_method_length(demo_file):
    """测试方法长度计算模块"""
    calculator = MethodLengthCalculator()
    result = calculator.calculate_file_method_lengths(demo_file)
    
    assert result['total_method_count'] >= 9
    assert result['overall_average'] >= 0