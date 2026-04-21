#!/usr/bin/env python3
"""圈复杂度计算模块

基于AST计算Java代码的圈复杂度
"""

import re
from typing import Dict, List

from src.ast_parser import ASTParser


class CyclomaticComplexityCalculator:
    """圈复杂度计算器"""
    
    def __init__(self):
        self.ast_parser = ASTParser()
        # 增加复杂度的控制结构
        self.complexity_patterns = [
            r'\bif\b',
            r'\bfor\b',
            r'\bwhile\b',
            r'\bdo\b.*\bwhile\b',
            r'\bswitch\b',
            r'\bcase\b',
            r'\bcatch\b',
            r'&&',
            r'\|\|',
            r'\?.*:',
            r'\bdefault\b'
        ]
    
    def calculate_method_complexity(self, method_body: str) -> int:
        """计算方法的圈复杂度
        
        Args:
            method_body: 方法体字符串
            
        Returns:
            圈复杂度值
        """
        if not method_body:
            return 1
        
        complexity = 1  # 基础复杂度为1
        
        # 直接从方法体字符串中统计控制结构关键字
        # 不使用_clean_code，因为它会移除太多信息
        
        # 统计控制结构
        if_count = method_body.count('IfThenElse') + method_body.count('if')
        for_count = method_body.count('For') + method_body.count('for')
        while_count = method_body.count('While') + method_body.count('while')
        do_while_count = method_body.count('DoWhile') + method_body.count('do')
        case_count = method_body.count('Case') + method_body.count('case')
        catch_count = method_body.count('Catch') + method_body.count('catch')
        ternary_count = method_body.count('?')
        and_count = method_body.count('&&')
        or_count = method_body.count('||')
        
        # 计算总复杂度
        complexity += if_count + for_count + while_count + do_while_count + case_count + catch_count + ternary_count + and_count + or_count
        
        return max(1, complexity)
    
    def calculate_class_complexity(self, class_info: Dict) -> Dict:
        """计算类的圈复杂度
        
        Args:
            class_info: 类信息字典
            
        Returns:
            包含方法复杂度和类总复杂度的字典
        """
        method_complexities = {}
        total_complexity = 0
        
        for method in class_info.get('methods', []):
            method_body = method.get('body', '')
            complexity = self.calculate_method_complexity(method_body)
            method_complexities[method['name']] = complexity
            total_complexity += complexity
        
        return {
            'method_complexities': method_complexities,
            'total_complexity': total_complexity
        }
    
    def calculate_file_complexity(self, file_path) -> Dict:
        """计算文件的圈复杂度
        
        Args:
            file_path: 文件路径
            
        Returns:
            包含类复杂度信息的字典
        """
        structure = self.ast_parser.parse_file(file_path)
        if not structure:
            return {}
        
        file_complexity = {}
        
        for class_info in structure.get('classes', []):
            class_name = class_info['name']
            class_complexity = self.calculate_class_complexity(class_info)
            file_complexity[class_name] = class_complexity
        
        return file_complexity
    
    def _clean_code(self, code: str) -> str:
        """清理代码，移除字符串字面量和注释
        
        Args:
            code: 代码字符串
            
        Returns:
            清理后的代码
        """
        # 移除字符串字面量
        code = re.sub(r'"(?:\\"|[^"])*"', '', code)
        code = re.sub(r"'(?:\\'|[^'])*'", '', code)
        
        # 移除注释
        code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        
        return code