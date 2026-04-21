#!/usr/bin/env python3
"""代码统计模块

统计Java代码的类数量、方法数量、属性数量等
"""

from pathlib import Path
from typing import Dict, List

from src.ast_parser import ASTParser


class CodeStatistics:
    """代码统计器"""
    
    def __init__(self):
        self.ast_parser = ASTParser()
    
    def count_classes(self, structure: Dict) -> int:
        """统计类数量
        
        Args:
            structure: 解析后的结构信息
            
        Returns:
            类数量
        """
        classes = structure.get('classes', [])
        count = len(classes)
        
        # 统计内部类
        for class_info in classes:
            count += len(class_info.get('inner_classes', []))
        
        return count
    
    def count_methods(self, structure: Dict) -> int:
        """统计方法数量
        
        Args:
            structure: 解析后的结构信息
            
        Returns:
            方法数量
        """
        methods_count = 0
        
        for class_info in structure.get('classes', []):
            methods_count += len(class_info.get('methods', []))
            
            # 统计内部类的方法
            for inner_class in class_info.get('inner_classes', []):
                methods_count += len(inner_class.get('methods', []))
        
        return methods_count
    
    def count_fields(self, structure: Dict) -> int:
        """统计属性数量
        
        Args:
            structure: 解析后的结构信息
            
        Returns:
            属性数量
        """
        fields_count = 0
        
        for class_info in structure.get('classes', []):
            fields_count += len(class_info.get('fields', []))
            
            # 统计内部类的属性
            for inner_class in class_info.get('inner_classes', []):
                fields_count += len(inner_class.get('fields', []))
        
        return fields_count
    
    def get_class_details(self, structure: Dict) -> List[Dict]:
        """获取类的详细信息
        
        Args:
            structure: 解析后的结构信息
            
        Returns:
            类详细信息列表
        """
        class_details = []
        
        def process_class(class_info, outer_class=None):
            details = {
                'name': class_info['name'],
                'outer_class': outer_class,
                'methods': len(class_info.get('methods', [])),
                'fields': len(class_info.get('fields', [])),
                'parent': class_info.get('parent'),
                'interfaces': class_info.get('interfaces', [])
            }
            class_details.append(details)
            
            # 处理内部类
            for inner_class in class_info.get('inner_classes', []):
                process_class(inner_class, class_info['name'])
        
        for class_info in structure.get('classes', []):
            process_class(class_info)
        
        return class_details
    
    def analyze_file(self, file_path: Path) -> Dict:
        """分析文件的统计信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            统计信息字典
        """
        structure = self.ast_parser.parse_file(file_path)
        if not structure:
            return {
                'classes': 0,
                'methods': 0,
                'fields': 0,
                'class_details': []
            }
        
        return {
            'classes': self.count_classes(structure),
            'methods': self.count_methods(structure),
            'fields': self.count_fields(structure),
            'class_details': self.get_class_details(structure)
        }
    
    def analyze_directory(self, directory: Path) -> Dict:
        """分析目录的统计信息
        
        Args:
            directory: 目录路径
            
        Returns:
            统计信息字典
        """
        total_classes = 0
        total_methods = 0
        total_fields = 0
        all_class_details = []
        
        for java_file in directory.rglob('*.java'):
            file_stats = self.analyze_file(java_file)
            total_classes += file_stats['classes']
            total_methods += file_stats['methods']
            total_fields += file_stats['fields']
            all_class_details.extend(file_stats['class_details'])
        
        return {
            'total_classes': total_classes,
            'total_methods': total_methods,
            'total_fields': total_fields,
            'all_class_details': all_class_details
        }