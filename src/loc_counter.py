#!/usr/bin/env python3
"""代码行统计模块

统计Java代码的总代码行、空行、注释行
"""

import re
from pathlib import Path
from typing import Dict


class LoCCounter:
    """代码行计数器"""
    
    def __init__(self):
        # 注释匹配正则
        self.single_line_comment = re.compile(r'//.*$')
        self.multi_line_comment_start = re.compile(r'/\*')
        self.multi_line_comment_end = re.compile(r'\*/')
    
    def count_file(self, file_path: Path) -> Dict[str, int]:
        """统计文件的代码行信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            包含代码行统计信息的字典
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            return self.count_lines(lines)
        except Exception as e:
            print(f"统计文件 {file_path} 时出错: {e}")
            return {
                'total': 0,
                'code': 0,
                'blank': 0,
                'comment': 0
            }
    
    def count_lines(self, lines: list) -> Dict[str, int]:
        """统计代码行信息
        
        Args:
            lines: 代码行列表
            
        Returns:
            包含代码行统计信息的字典
        """
        total = len(lines)
        code = 0
        blank = 0
        comment = 0
        in_multi_comment = False
        
        for line in lines:
            stripped = line.strip()
            
            if in_multi_comment:
                comment += 1
                if self.multi_line_comment_end.search(line):
                    in_multi_comment = False
                continue
            
            if not stripped:
                blank += 1
            elif self.single_line_comment.match(stripped):
                comment += 1
            elif self.multi_line_comment_start.match(stripped):
                comment += 1
                if not self.multi_line_comment_end.search(line):
                    in_multi_comment = True
            else:
                # 检查行内是否包含注释
                line_content = line
                if '//' in line_content:
                    comment_part = line_content.split('//', 1)[1]
                    if not self._is_string_literal(line_content, '//'):
                        comment += 1
                        code += 1
                    else:
                        code += 1
                else:
                    code += 1
        
        return {
            'total': total,
            'code': code,
            'blank': blank,
            'comment': comment
        }
    
    def _is_string_literal(self, line: str, marker: str) -> bool:
        """判断标记是否在字符串字面量中
        
        Args:
            line: 代码行
            marker: 标记字符串
            
        Returns:
            如果标记在字符串字面量中返回True，否则返回False
        """
        in_single_quote = False
        in_double_quote = False
        escaped = False
        
        for i, char in enumerate(line):
            if escaped:
                escaped = False
                continue
            
            if char == '\\':
                escaped = True
            elif char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif char == marker[0] and i + len(marker) <= len(line):
                if line[i:i+len(marker)] == marker:
                    if not in_single_quote and not in_double_quote:
                        return False
        
        return True