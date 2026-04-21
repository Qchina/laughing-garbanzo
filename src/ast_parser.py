#!/usr/bin/env python3
"""基于AST的Java代码解析模块

使用plyj库解析Java代码，生成抽象语法树，提取结构信息
"""

from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

import plyj.parser as plyj_parser


class ASTParser:
    """AST解析器，用于解析Java代码并提取结构信息"""
    
    def __init__(self):
        self.parser = plyj_parser.Parser()
    
    def parse_file(self, file_path: Path) -> Optional[Dict]:
        """解析Java文件，返回结构信息
        
        Args:
            file_path: Java文件路径
            
        Returns:
            包含类、方法、字段等结构信息的字典，解析失败返回None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = self.parser.parse_string(content)
            return self._extract_structure(tree)
        except Exception as e:
            print(f"解析文件 {file_path} 时出错: {e}")
            return None
    
    def _extract_structure(self, tree) -> Dict:
        """从AST中提取结构信息
        
        Args:
            tree: plyj解析生成的AST树
            
        Returns:
            结构信息字典
        """
        structure = {
            'classes': [],
            'imports': [],
            'package': None
        }
        
        # 提取包声明
        if hasattr(tree, 'package') and tree.package:
            if hasattr(tree.package, 'name'):
                if isinstance(tree.package.name, (list, tuple)):
                    structure['package'] = '.'.join(tree.package.name)
                else:
                    structure['package'] = str(tree.package.name)
        
        # 提取导入语句
        if hasattr(tree, 'imports'):
            for imp in tree.imports:
                if hasattr(imp, 'name'):
                    if isinstance(imp.name, (list, tuple)):
                        structure['imports'].append('.'.join(imp.name))
                    else:
                        structure['imports'].append(str(imp.name))
        
        # 提取类型声明（类、接口等）
        if hasattr(tree, 'type_declarations'):
            for type_decl in tree.type_declarations:
                if hasattr(type_decl, 'name'):
                    class_info = self._extract_class_info(type_decl)
                    if class_info:
                        structure['classes'].append(class_info)
        
        return structure
    
    def _extract_class_info(self, type_decl) -> Dict:
        """提取类信息
        
        Args:
            type_decl: 类型声明节点
            
        Returns:
            类信息字典
        """
        class_info = {
            'name': type_decl.name,
            'parent': None,
            'interfaces': [],
            'methods': [],
            'fields': [],
            'inner_classes': []
        }
        
        # 提取父类
        if hasattr(type_decl, 'extends') and type_decl.extends:
            if hasattr(type_decl.extends, 'name'):
                if isinstance(type_decl.extends.name, (list, tuple)):
                    class_info['parent'] = '.'.join(type_decl.extends.name)
                else:
                    # 处理Name对象的字符串表示，提取实际的类名
                    name_str = str(type_decl.extends.name)
                    # 提取Name(value='ClassName')中的ClassName
                    if name_str.startswith('Name(value=') and name_str.endswith(')'):
                        class_info['parent'] = name_str.split("'", 2)[1]
                    else:
                        class_info['parent'] = name_str
        
        # 提取实现的接口
        if hasattr(type_decl, 'implements'):
            for iface in type_decl.implements:
                if hasattr(iface, 'name'):
                    if isinstance(iface.name, (list, tuple)):
                        class_info['interfaces'].append('.'.join(iface.name))
                    else:
                        # 处理Name对象的字符串表示，提取实际的接口名
                        name_str = str(iface.name)
                        if name_str.startswith('Name(value=') and name_str.endswith(')'):
                            class_info['interfaces'].append(name_str.split("'", 2)[1])
                        else:
                            class_info['interfaces'].append(name_str)
        
        # 提取类成员
        if hasattr(type_decl, 'body'):
            for member in type_decl.body:
                # 检查是否是方法（MethodDeclaration）
                if hasattr(member, 'name') and hasattr(member, 'parameters'):
                    # 方法
                    method_info = self._extract_method_info(member)
                    class_info['methods'].append(method_info)
                # 检查是否是字段（FieldDeclaration）
                elif hasattr(member, 'variable_declarators'):
                    # 字段
                    field_info = self._extract_field_info(member)
                    if field_info['name']:
                        class_info['fields'].append(field_info)
                # 检查是否是内部类
                elif hasattr(member, 'type') and hasattr(member.type, 'name'):
                    # 内部类
                    inner_class_info = self._extract_class_info(member)
                    class_info['inner_classes'].append(inner_class_info)
        
        return class_info
    
    def _extract_method_info(self, method) -> Dict:
        """提取方法信息
        
        Args:
            method: 方法节点
            
        Returns:
            方法信息字典
        """
        method_info = {
            'name': method.name,
            'parameters': [],
            'return_type': None,
            'modifiers': [],
            'body': '',
            'loc': 0
        }
        
        # 提取修饰符
        if hasattr(method, 'modifiers'):
            method_info['modifiers'] = [modifier for modifier in method.modifiers]
        
        # 提取返回类型
        if hasattr(method, 'return_type') and method.return_type:
            if hasattr(method.return_type, 'name'):
                if isinstance(method.return_type.name, (list, tuple)):
                    method_info['return_type'] = '.'.join(method.return_type.name)
                else:
                    method_info['return_type'] = str(method.return_type.name)
            elif hasattr(method.return_type, 'type'):
                method_info['return_type'] = str(method.return_type.type)
        
        # 提取参数
        if hasattr(method, 'parameters'):
            for param in method.parameters:
                # 提取参数类型
                if hasattr(param, 'type') and hasattr(param.type, 'name'):
                    if isinstance(param.type.name, (list, tuple)):
                        param_type = '.'.join(param.type.name)
                    else:
                        param_type = str(param.type.name)
                else:
                    param_type = str(param.type)
                
                # 提取参数名
                param_name = ''
                if hasattr(param, 'name'):
                    param_name = param.name
                elif hasattr(param, 'variable') and hasattr(param.variable, 'name'):
                    param_name = param.variable.name
                
                method_info['parameters'].append({
                    'name': param_name,
                    'type': param_type
                })
        
        # 提取方法体
        if hasattr(method, 'body') and method.body:
            # 尝试多种方式获取方法体
            try:
                # 方法1：直接使用str()获取方法体的字符串表示
                body_str = str(method.body)
                method_info['body'] = body_str
                
                # 方法2：检查是否有statements属性
                if hasattr(method.body, 'statements'):
                    method_info['loc'] = len(method.body.statements)
                else:
                    # 估算代码行数
                    method_info['loc'] = len(body_str.split('\n'))
            except:
                # 如果获取失败，使用空方法体
                method_info['body'] = '{}'
                method_info['loc'] = 0
        
        return method_info
    
    def _extract_field_info(self, field) -> Dict:
        """提取字段信息
        
        Args:
            field: 字段节点
            
        Returns:
            字段信息字典
        """
        field_info = {
            'name': '',
            'type': None,
            'modifiers': []
        }
        
        # 提取修饰符
        if hasattr(field, 'modifiers'):
            field_info['modifiers'] = [modifier for modifier in field.modifiers]
        
        # 提取类型
        if hasattr(field, 'type') and field.type:
            if hasattr(field.type, 'name'):
                if isinstance(field.type.name, (list, tuple)):
                    field_info['type'] = '.'.join(field.type.name)
                else:
                    field_info['type'] = str(field.type.name)
            else:
                field_info['type'] = str(field.type)
        
        # 提取字段名
        if hasattr(field, 'variable_declarators') and field.variable_declarators:
            # plyj的FieldDeclaration使用variable_declarators属性存储字段名
            for var in field.variable_declarators:
                # 检查var的属性
                if hasattr(var, 'variable') and hasattr(var.variable, 'name'):
                    field_info['name'] = var.variable.name
                    break
                elif hasattr(var, 'name'):
                    field_info['name'] = var.name
                    break
                elif hasattr(var, 'declarator') and hasattr(var.declarator, 'name'):
                    field_info['name'] = var.declarator.name
                    break
                elif hasattr(var, 'id') and hasattr(var.id, 'name'):
                    field_info['name'] = var.id.name
                    break
        elif hasattr(field, 'name'):
            # 兼容其他可能的结构
            field_info['name'] = field.name
        
        return field_info