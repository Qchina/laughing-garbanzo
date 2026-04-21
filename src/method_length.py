#!/usr/bin/env python3
"""方法长度计算模块

计算Java代码的平均方法长度
"""

from pathlib import Path
from typing import Dict, List

from src.ast_parser import ASTParser
from src.loc_counter import LoCCounter


class MethodLengthCalculator:
    """方法长度计算器"""
    
    def __init__(self):
        self.ast_parser = ASTParser()
        self.loc_counter = LoCCounter()
    
    def calculate_method_length(self, method_body: str) -> int:
        """计算单个方法的长度
        
        Args:
            method_body: 方法体字符串
            
        Returns:
            方法长度（代码行数）
        """
        if not method_body:
            return 0
        
        lines = method_body.split('\n')
        code_lines = 0
        
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('//'):
                code_lines += 1
        
        return code_lines
    
    def calculate_class_method_lengths(self, class_info: Dict) -> Dict:
        """计算类中所有方法的长度
        
        Args:
            class_info: 类信息字典
            
        Returns:
            包含方法长度信息的字典
        """
        method_lengths = {}
        total_length = 0
        method_count = len(class_info.get('methods', []))
        
        for method in class_info.get('methods', []):
            method_body = method.get('body', '')
            length = self.calculate_method_length(method_body)
            method_lengths[method['name']] = length
            total_length += length
        
        average_length = total_length / method_count if method_count > 0 else 0
        
        return {
            'method_lengths': method_lengths,
            'total_length': total_length,
            'average_length': average_length
        }
    
    def calculate_file_method_lengths(self, file_path: Path) -> Dict:
        """计算文件中所有方法的长度
        
        Args:
            file_path: 文件路径
            
        Returns:
            包含文件方法长度信息的字典
        """
        structure = self.ast_parser.parse_file(file_path)
        if not structure:
            return {}
        
        file_method_lengths = {}
        total_method_length = 0
        total_method_count = 0
        
        for class_info in structure.get('classes', []):
            class_name = class_info['name']
            class_method_lengths = self.calculate_class_method_lengths(class_info)
            file_method_lengths[class_name] = class_method_lengths
            
            total_method_length += class_method_lengths['total_length']
            total_method_count += len(class_method_lengths['method_lengths'])
        
        overall_average = total_method_length / total_method_count if total_method_count > 0 else 0
        
        return {
            'class_method_lengths': file_method_lengths,
            'total_method_length': total_method_length,
            'total_method_count': total_method_count,
            'overall_average': overall_average
        }
    
    def calculate_directory_method_lengths(self, directory: Path) -> Dict:
        """计算目录中所有方法的长度
        
        Args:
            directory: 目录路径
            
        Returns:
            包含目录方法长度信息的字典
        """
        total_method_length = 0
        total_method_count = 0
        file_method_lengths = {}
        
        for java_file in directory.rglob('*.java'):
            file_path_str = str(java_file)
            file_stats = self.calculate_file_method_lengths(java_file)
            if file_stats:
                file_method_lengths[file_path_str] = file_stats
                total_method_length += file_stats['total_method_length']
                total_method_count += file_stats['total_method_count']
        
        overall_average = total_method_length / total_method_count if total_method_count > 0 else 0
        
        return {
            'file_method_lengths': file_method_lengths,
            'total_method_length': total_method_length,
            'total_method_count': total_method_count,
            'overall_average': overall_average
        }