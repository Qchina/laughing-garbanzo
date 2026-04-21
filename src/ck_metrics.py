#!/usr/bin/env python3
"""CK指标计算模块

计算CK模型中的指标：WMC、CBO、RFC、LCOM
"""

import re
from pathlib import Path
from typing import Dict, List, Set

from src.ast_parser import ASTParser
from src.cyclomatic_complexity import CyclomaticComplexityCalculator


class CKMetricsCalculator:
    """CK指标计算器"""
    
    def __init__(self):
        self.ast_parser = ASTParser()
        self.cc_calculator = CyclomaticComplexityCalculator()
    
    def calculate_wmc(self, class_info: Dict) -> int:
        """计算加权方法复杂度（WMC）
        
        Args:
            class_info: 类信息字典
            
        Returns:
            WMC值
        """
        wmc = 0
        
        for method in class_info.get('methods', []):
            method_body = method.get('body', '')
            complexity = self.cc_calculator.calculate_method_complexity(method_body)
            wmc += complexity
        
        return wmc
    
    def calculate_cbo(self, class_info: Dict, all_classes: List[Dict]) -> int:
        """计算对象间耦合度（CBO）
        
        Args:
            class_info: 类信息字典
            all_classes: 所有类的信息列表
            
        Returns:
            CBO值
        """
        coupled_classes = set()
        class_name = class_info['name']
        
        # 检查父类
        if class_info.get('parent'):
            parent_name = class_info['parent'].split('.')[-1]
            if parent_name != class_name:
                coupled_classes.add(parent_name)
        
        # 检查实现的接口
        for interface in class_info.get('interfaces', []):
            interface_name = interface.split('.')[-1]
            coupled_classes.add(interface_name)
        
        # 检查字段类型
        for field in class_info.get('fields', []):
            field_type = field.get('type')
            if field_type:
                type_name = field_type.split('.')[-1]
                # 排除基本类型
                if type_name[0].isupper() and type_name != class_name:
                    coupled_classes.add(type_name)
        
        # 检查方法参数类型和返回类型
        for method in class_info.get('methods', []):
            # 检查返回类型
            return_type = method.get('return_type')
            if return_type:
                type_name = return_type.split('.')[-1]
                if type_name[0].isupper() and type_name != class_name:
                    coupled_classes.add(type_name)
            
            # 检查参数类型
            for param in method.get('parameters', []):
                param_type = param.get('type')
                if param_type:
                    type_name = param_type.split('.')[-1]
                    if type_name[0].isupper() and type_name != class_name:
                        coupled_classes.add(type_name)
        
        # 检查方法体中的方法调用
        for method in class_info.get('methods', []):
            method_body = method.get('body', '')
            # 查找方法调用
            method_calls = re.findall(r'(\w+)\.(\w+)\s*\(', method_body)
            for obj, _ in method_calls:
                if obj[0].isupper() and obj != class_name:
                    coupled_classes.add(obj)
        
        # 过滤掉不存在的类
        existing_class_names = {c['name'] for c in all_classes}
        coupled_classes = {c for c in coupled_classes if c in existing_class_names}
        
        return len(coupled_classes)
    
    def calculate_rfc(self, class_info: Dict) -> int:
        """计算响应集合（RFC）
        
        Args:
            class_info: 类信息字典
            
        Returns:
            RFC值
        """
        rfc = 0
        
        # 类自身的方法数
        rfc += len(class_info.get('methods', []))
        
        # 方法体中调用的其他方法数
        method_calls = set()
        for method in class_info.get('methods', []):
            method_body = method.get('body', '')
            # 查找方法调用
            calls = re.findall(r'(\w+)\.(\w+)\s*\(', method_body)
            for _, method_name in calls:
                method_calls.add(method_name)
        
        rfc += len(method_calls)
        
        return rfc
    
    def calculate_lcom(self, class_info: Dict) -> float:
        """计算类内聚缺失程度（LCOM）
        
        Args:
            class_info: 类信息字典
            
        Returns:
            LCOM值
        """
        methods = class_info.get('methods', [])
        fields = class_info.get('fields', [])
        
        if len(methods) <= 1 or len(fields) == 0:
            return 0.0
        
        # 提取字段名
        field_names = {field['name'] for field in fields}
        
        # 记录每个方法使用的字段
        method_field_usage = {}
        for method in methods:
            method_name = method['name']
            method_body = method.get('body', '')
            used_fields = set()
            
            for field_name in field_names:
                # 查找字段使用
                if re.search(rf'\b{re.escape(field_name)}\b', method_body):
                    used_fields.add(field_name)
            
            method_field_usage[method_name] = used_fields
        
        # 计算LCOM
        share = 0
        non_share = 0
        method_names = list(method_field_usage.keys())
        
        for i in range(len(method_names)):
            for j in range(i + 1, len(method_names)):
                fi = method_field_usage[method_names[i]]
                fj = method_field_usage[method_names[j]]
                
                if fi & fj:
                    share += 1
                else:
                    non_share += 1
        
        if share + non_share == 0:
            return 0.0
        
        lcom = max(non_share - share, 0) / (share + non_share)
        return lcom
    
    def calculate_all_ck_metrics(self, class_info: Dict, all_classes: List[Dict]) -> Dict:
        """计算所有CK指标
        
        Args:
            class_info: 类信息字典
            all_classes: 所有类的信息列表
            
        Returns:
            包含所有CK指标的字典
        """
        return {
            'wmc': self.calculate_wmc(class_info),
            'cbo': self.calculate_cbo(class_info, all_classes),
            'rfc': self.calculate_rfc(class_info),
            'lcom': self.calculate_lcom(class_info)
        }
    
    def calculate_file_metrics(self, file_path: Path) -> Dict:
        """计算文件中所有类的CK指标
        
        Args:
            file_path: 文件路径
            
        Returns:
            包含所有类CK指标的字典
        """
        structure = self.ast_parser.parse_file(file_path)
        if not structure:
            return {}
        
        all_classes = structure.get('classes', [])
        file_metrics = {}
        
        for class_info in all_classes:
            class_name = class_info['name']
            metrics = self.calculate_all_ck_metrics(class_info, all_classes)
            file_metrics[class_name] = metrics
        
        return file_metrics