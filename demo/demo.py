#!/usr/bin/env python3
"""核心度量模块演示脚本

展示AST解析、LoC统计、圈复杂度计算、CK指标计算等功能
"""

import sys
import os
from pathlib import Path

# 添加上级目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ast_parser import ASTParser
from src.loc_counter import LoCCounter
from src.cyclomatic_complexity import CyclomaticComplexityCalculator
from src.ck_metrics import CKMetricsCalculator
from src.code_statistics import CodeStatistics
from src.method_length import MethodLengthCalculator


def main():
    """主函数"""
    # 演示文件路径
    demo_file = Path('demo/DemoClass.java')
    
    print("=== 核心度量模块演示 ===")
    print(f"分析文件: {demo_file}")
    print("=" * 50)
    
    # 1. AST解析
    print("\n1. AST解析结果:")
    print("-" * 30)
    ast_parser = ASTParser()
    structure = ast_parser.parse_file(demo_file)
    if structure:
        print(f"包名: {structure.get('package')}")
        print(f"导入语句: {structure.get('imports')}")
        print(f"类数量: {len(structure.get('classes', []))}")
        
        for class_info in structure.get('classes', []):
            print(f"\n类名: {class_info['name']}")
            print(f"父类: {class_info.get('parent')}")
            print(f"接口: {class_info.get('interfaces')}")
            print(f"方法数量: {len(class_info.get('methods', []))}")
            print(f"字段数量: {len(class_info.get('fields', []))}")
            
            print("\n方法列表:")
            for method in class_info.get('methods', []):
                print(f"  - {method['name']}()")
    
    # 2. LoC统计
    print("\n2. LoC统计结果:")
    print("-" * 30)
    loc_counter = LoCCounter()
    loc_stats = loc_counter.count_file(demo_file)
    print(f"总代码行: {loc_stats['total']}")
    print(f"代码行: {loc_stats['code']}")
    print(f"空行: {loc_stats['blank']}")
    print(f"注释行: {loc_stats['comment']}")
    
    # 3. 圈复杂度计算
    print("\n3. 圈复杂度计算结果:")
    print("-" * 30)
    cc_calculator = CyclomaticComplexityCalculator()
    complexity = cc_calculator.calculate_file_complexity(demo_file)
    for class_name, class_complexity in complexity.items():
        print(f"类: {class_name}")
        print(f"总复杂度: {class_complexity['total_complexity']}")
        print("方法复杂度:")
        for method_name, method_complexity in class_complexity['method_complexities'].items():
            print(f"  - {method_name}(): {method_complexity}")
    
    # 4. CK指标计算
    print("\n4. CK指标计算结果:")
    print("-" * 30)
    ck_calculator = CKMetricsCalculator()
    ck_metrics = ck_calculator.calculate_file_metrics(demo_file)
    for class_name, metrics in ck_metrics.items():
        print(f"类: {class_name}")
        print(f"WMC: {metrics['wmc']}")
        print(f"CBO: {metrics['cbo']}")
        print(f"RFC: {metrics['rfc']}")
        print(f"LCOM: {metrics['lcom']:.3f}")
    
    # 5. 代码统计
    print("\n5. 代码统计结果:")
    print("-" * 30)
    code_stats = CodeStatistics()
    stats = code_stats.analyze_file(demo_file)
    print(f"类数量: {stats['classes']}")
    print(f"方法数量: {stats['methods']}")
    print(f"字段数量: {stats['fields']}")
    
    # 6. 方法长度计算
    print("\n6. 方法长度计算结果:")
    print("-" * 30)
    method_length_calculator = MethodLengthCalculator()
    method_lengths = method_length_calculator.calculate_file_method_lengths(demo_file)
    print(f"总方法长度: {method_lengths['total_method_length']}")
    print(f"总方法数: {method_lengths['total_method_count']}")
    print(f"平均方法长度: {method_lengths['overall_average']:.2f}")
    
    print("\n" + "=" * 50)
    print("演示完成！")


if __name__ == "__main__":
    main()