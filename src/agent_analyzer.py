#!/usr/bin/env python3
"""基于AI Agent的软件度量分析模块

调用AI API分析度量结果，生成改进建议和质量分析报告
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class AnalysisResult:
    """分析结果数据类"""
    summary: str
    recommendations: List[str]
    high_complexity_methods: List[Dict]
    high_coupling_classes: List[Dict]
    refactoring_suggestions: List[Dict]
    risk_assessment: Dict

    def to_dict(self) -> Dict:
        return asdict(self)


class AgentAnalyzer:
    """AI Agent分析器"""

    def __init__(self, api_key: Optional[str] = None, api_provider: str = "deepseek"):
        """初始化Agent分析器

        Args:
            api_key: API密钥，如果为None则从环境变量获取
            api_provider: API提供商，支持 "deepseek", "openai"
        """
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.api_provider = api_provider.lower()

    def analyze_metrics(self, metrics_report: Dict) -> AnalysisResult:
        """分析度量报告

        Args:
            metrics_report: 度量报告字典

        Returns:
            AnalysisResult: 分析结果
        """
        project_info = metrics_report.get("project", {})
        classes = metrics_report.get("classes", [])
        estimation = metrics_report.get("estimation", {})

        summary = self._generate_summary(project_info, estimation)
        recommendations = self._generate_recommendations(project_info, classes)
        high_complexity_methods = self._identify_high_complexity(project_info, classes)
        high_coupling_classes = self._identify_high_coupling(project_info, classes)
        refactoring_suggestions = self._generate_refactoring_suggestions(classes)
        risk_assessment = self._assess_risk(project_info, classes)

        return AnalysisResult(
            summary=summary,
            recommendations=recommendations,
            high_complexity_methods=high_complexity_methods,
            high_coupling_classes=high_coupling_classes,
            refactoring_suggestions=refactoring_suggestions,
            risk_assessment=risk_assessment
        )

    def analyze_with_ai(self, metrics_report: Dict) -> Dict:
        """调用AI API进行深度分析

        Args:
            metrics_report: 度量报告字典

        Returns:
            AI返回的深度分析结果
        """
        if not self.api_key:
            return {
                "error": "API密钥未设置，请设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY 环境变量",
                "fallback": self._get_fallback_analysis(metrics_report)
            }

        prompt = self._build_analysis_prompt(metrics_report)

        try:
            if self.api_provider == "deepseek":
                response = self._call_deepseek_api(prompt)
            elif self.api_provider == "openai":
                response = self._call_openai_api(prompt)
            else:
                response = self._call_deepseek_api(prompt)

            return {
                "success": True,
                "analysis": response,
                "provider": self.api_provider
            }
        except Exception as e:
            return {
                "error": str(e),
                "fallback": self._get_fallback_analysis(metrics_report)
            }

    def _generate_summary(self, project_info: Dict, estimation: Dict) -> str:
        """生成项目概览摘要"""
        class_count = project_info.get("class_count", 0)
        loc = project_info.get("loc", 0)
        avg_wmc = project_info.get("avg_wmc", 0)
        avg_cbo = project_info.get("avg_cbo", 0)
        avg_lcom = project_info.get("avg_lcom", 0)
        kloc = estimation.get("kloc", 0)
        effort = estimation.get("effort_person_month", 0)

        summary = f"""项目概况分析：
- 规模：{class_count}个类，{loc}行代码（KLoC={kloc:.2f}）
- 复杂度：平均WMC={avg_wmc:.2f}，处于{'低' if avg_wmc < 10 else '中' if avg_wmc < 20 else '高'}复杂度水平
- 耦合度：平均CBO={avg_cbo:.2f}，{'良好' if avg_cbo < 5 else '需要注意' if avg_cbo < 8 else '过高'}
- 内聚性：平均LCOM={avg_lcom:.3f}，{'良好' if avg_lcom < 0.5 else '一般' if avg_lcom < 0.8 else '较差'}
- 预估工作量：{effort:.2f}人月"""

        return summary

    def _generate_recommendations(self, project_info: Dict, classes: List[Dict]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        avg_wmc = project_info.get("avg_wmc", 0)
        avg_cbo = project_info.get("avg_cbo", 0)
        avg_lcom = project_info.get("avg_lcom", 0)

        if avg_wmc > 15:
            recommendations.append("整体圈复杂度偏高，建议对高复杂度方法进行重构，拆分为多个简单方法")
        elif avg_wmc > 10:
            recommendations.append("复杂度处于中等水平，建议持续关注方法复杂度变化")

        if avg_cbo > 6:
            recommendations.append("类之间耦合度较高，建议使用接口或抽象类降低耦合")
        elif avg_cbo > 4:
            recommendations.append("存在一定耦合，建议检查类之间的依赖关系是否合理")

        if avg_lcom > 0.7:
            recommendations.append("类内聚性较差，建议重新审视类的职责划分，考虑拆分类")
        elif avg_lcom > 0.5:
            recommendations.append("类内聚性一般，建议在后续开发中注意类的单一职责原则")

        high_wmc_classes = [c for c in classes if c.get("complexity", 0) > 20]
        if high_wmc_classes:
            recommendations.append(f"发现{len(high_wmc_classes)}个高复杂度类（WMC>20），建议优先进行重构")

        high_cbo_classes = [c for c in classes if c.get("cbo", 0) > 8]
        if high_cbo_classes:
            recommendations.append(f"发现{len(high_cbo_classes)}个高耦合类（CBO>8），建议使用中介者模式或观察者模式解耦")

        return recommendations if recommendations else ["各项指标均处于合理范围，建议保持当前开发规范"]

    def _identify_high_complexity(self, project_info: Dict, classes: List[Dict]) -> List[Dict]:
        """识别高复杂度方法/类"""
        threshold_wmc = 20
        high_complexity = []

        for cls in classes:
            complexity = cls.get("complexity", 0)
            if complexity >= threshold_wmc:
                high_complexity.append({
                    "name": cls.get("name", "Unknown"),
                    "type": "class",
                    "complexity": complexity,
                    "risk_level": "high" if complexity > 30 else "medium",
                    "reason": f"WMC={complexity}超过阈值{threshold_wmc}"
                })

        return sorted(high_complexity, key=lambda x: x["complexity"], reverse=True)[:10]

    def _identify_high_coupling(self, project_info: Dict, classes: List[Dict]) -> List[Dict]:
        """识别高耦合类"""
        threshold_cbo = 8
        high_coupling = []

        for cls in classes:
            cbo = cls.get("cbo", 0)
            if cbo >= threshold_cbo:
                high_coupling.append({
                    "name": cls.get("name", "Unknown"),
                    "cbo": cbo,
                    "risk_level": "high" if cbo > 12 else "medium",
                    "reason": f"CBO={cbo}超过阈值{threshold_cbo}"
                })

        return sorted(high_coupling, key=lambda x: x["cbo"], reverse=True)[:10]

    def _generate_refactoring_suggestions(self, classes: List[Dict]) -> List[Dict]:
        """生成重构建议"""
        suggestions = []

        for cls in classes:
            name = cls.get("name", "Unknown")
            complexity = cls.get("complexity", 0)
            cbo = cls.get("cbo", 0)
            lcom = cls.get("lcom", 0)
            methods = cls.get("methods", 0)
            fields = cls.get("fields", 0)

            if complexity > 30:
                suggestions.append({
                    "class_name": name,
                    "issue": f"复杂度过高(WMC={complexity})",
                    "suggestion": "考虑将复杂方法拆分为多个简单方法，或使用策略模式替代复杂条件逻辑",
                    "priority": "high"
                })

            if cbo > 10:
                suggestions.append({
                    "class_name": name,
                    "issue": f"耦合度过高(CBO={cbo})",
                    "suggestion": "使用接口隔离依赖，引入中介类管理类间通信",
                    "priority": "high"
                })

            if lcom > 0.8 and methods > 5:
                suggestions.append({
                    "class_name": name,
                    "issue": f"内聚性差(LCOM={lcom:.3f})，方法数={methods}",
                    "suggestion": "考虑拆分类，将相关方法及其字段提取到新类中",
                    "priority": "medium"
                })

            if methods > 20:
                suggestions.append({
                    "class_name": name,
                    "issue": f"方法过多({methods}个)",
                    "suggestion": "遵循接口隔离原则，将大类拆分为多个职责单一的小类",
                    "priority": "medium"
                })

            if fields > 15:
                suggestions.append({
                    "class_name": name,
                    "issue": f"字段过多({fields}个)",
                    "suggestion": "考虑使用组合模式或将相关字段分组到新类中",
                    "priority": "low"
                })

        return sorted(suggestions, key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["priority"], 3))

    def _assess_risk(self, project_info: Dict, classes: List[Dict]) -> Dict:
        """评估项目风险"""
        avg_wmc = project_info.get("avg_wmc", 0)
        avg_cbo = project_info.get("avg_cbo", 0)
        avg_lcom = project_info.get("avg_lcom", 0)
        avg_rfc = project_info.get("avg_rfc", 0)

        risk_score = 0
        risk_factors = []

        if avg_wmc > 20:
            risk_score += 3
            risk_factors.append("圈复杂度普遍过高")
        elif avg_wmc > 15:
            risk_score += 1
            risk_factors.append("部分类复杂度偏高")

        if avg_cbo > 8:
            risk_score += 3
            risk_factors.append("类之间耦合度过高")
        elif avg_cbo > 5:
            risk_score += 1
            risk_factors.append("存在一定的类间依赖")

        if avg_lcom > 0.8:
            risk_score += 2
            risk_factors.append("类内聚性较差")

        if avg_rfc > 50:
            risk_score += 2
            risk_factors.append("响应集合过大，类职责可能不清晰")

        high_risk_classes = len([c for c in classes if c.get("complexity", 0) > 30 or c.get("cbo", 0) > 12])
        if high_risk_classes > 0:
            risk_score += 2
            risk_factors.append(f"存在{high_risk_classes}个高风险类")

        if risk_score >= 8:
            risk_level = "high"
        elif risk_score >= 4:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "maintenance_difficulty": "高" if risk_score >= 6 else "中" if risk_score >= 3 else "低"
        }

    def _build_analysis_prompt(self, metrics_report: Dict) -> str:
        """构建AI分析提示词"""
        project_info = metrics_report.get("project", {})
        classes = metrics_report.get("classes", [])
        estimation = metrics_report.get("estimation", {})

        top_classes = sorted(classes, key=lambda x: x.get("complexity", 0), reverse=True)[:5]

        prompt = f"""请分析以下Java项目的软件度量结果，并给出专业的改进建议：

项目规模：
- 类数量：{project_info.get('class_count', 0)}
- 代码行数：{project_info.get('loc', 0)}
- 平均圈复杂度(WMC)：{project_info.get('avg_wmc', 0):.2f}
- 平均耦合度(CBO)：{project_info.get('avg_cbo', 0):.2f}
- 平均内聚度(LCOM)：{project_info.get('avg_lcom', 0):.3f}
- 平均响应集合(RFC)：{project_info.get('avg_rfc', 0):.2f}
- 预估工作量：{estimation.get('effort_person_month', 0):.2f}人月

复杂度最高的5个类：
{json.dumps(top_classes, ensure_ascii=False, indent=2)}

请从以下几个方面进行分析：
1. 整体架构和设计质量评估
2. 主要问题和风险点
3. 具体的重构建议（按优先级排序）
4. 开发维护建议

请用中文回答。"""

        return prompt

    def _call_deepseek_api(self, prompt: str) -> str:
        """调用DeepSeek API"""
        import urllib.request
        import urllib.error

        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一个专业的软件工程专家，擅长代码质量分析和重构建议。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['choices'][0]['message']['content']
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"DeepSeek API HTTP错误: {e.code} - {error_body}")
        except Exception as e:
            raise Exception(f"DeepSeek API调用失败: {str(e)}")

    def _call_openai_api(self, prompt: str) -> str:
        """调用OpenAI API"""
        import urllib.request
        import urllib.error

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "你是一个专业的软件工程专家，擅长代码质量分析和重构建议。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['choices'][0]['message']['content']
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"OpenAI API HTTP错误: {e.code} - {error_body}")
        except Exception as e:
            raise Exception(f"OpenAI API调用失败: {str(e)}")

    def _get_fallback_analysis(self, metrics_report: Dict) -> Dict:
        """当API不可用时，返回基于规则的分析结果"""
        result = self.analyze_metrics(metrics_report)
        return {
            "summary": result.summary,
            "recommendations": result.recommendations,
            "high_complexity_methods": result.high_complexity_methods,
            "high_coupling_classes": result.high_coupling_classes,
            "refactoring_suggestions": result.refactoring_suggestions,
            "risk_assessment": result.risk_assessment,
            "note": "这是基于规则的分析结果，要获得更深入的AI分析，请设置API密钥"
        }


def analyze_report_file(report_path: Path, api_key: Optional[str] = None, use_ai: bool = False) -> Dict:
    """分析度量报告文件

    Args:
        report_path: 度量报告JSON文件路径
        api_key: API密钥
        use_ai: 是否使用AI分析

    Returns:
        分析结果字典
    """
    report = json.loads(report_path.read_text(encoding="utf-8"))

    analyzer = AgentAnalyzer(api_key=api_key)

    if use_ai:
        ai_result = analyzer.analyze_with_ai(report)
        rule_result = analyzer.analyze_metrics(report)
        return {
            "rule_based": rule_result.to_dict(),
            "ai_analysis": ai_result
        }
    else:
        result = analyzer.analyze_metrics(report)
        return result.to_dict()


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="AI驱动的软件度量分析工具")
    parser.add_argument("--report", required=True, help="度量报告JSON文件路径")
    parser.add_argument("--api-key", help="API密钥（也可通过环境变量设置）")
    parser.add_argument("--use-ai", action="store_true", help="使用AI进行深度分析")
    parser.add_argument("--output", help="输出文件路径")

    args = parser.parse_args()

    result = analyze_report_file(
        report_path=Path(args.report),
        api_key=args.api_key,
        use_ai=args.use_ai
    )

    output = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"分析结果已保存到: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
