"""Rule Engine - 质量规则引擎"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Rule:
    id: str
    name: str
    category: str
    description: str
    severity: str
    enabled: bool = True

    def check(self, context: Dict[str, Any]) -> Optional["RuleResult"]:
        raise NotImplementedError


@dataclass
class RuleResult:
    rule_id: str
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None


DEFAULT_RULES = [
    {"id": "CQ-001", "name": "Syntax Check", "category": "code_quality",
     "description": "代码语法检查，确保无语法错误", "severity": "critical"},
    {"id": "CQ-002", "name": "File Size Limit", "category": "code_quality",
     "description": "单个文件不超过 500 行", "severity": "high"},
    {"id": "CQ-003", "name": "Line Length Limit", "category": "code_quality",
     "description": "单行不超过 120 字符", "severity": "medium"},
    {"id": "ARC-001", "name": "Architecture Layer Check", "category": "architecture",
     "description": "代码不允许越层调用", "severity": "critical"},
    {"id": "ARC-002", "name": "Module Boundary Check", "category": "architecture",
     "description": "模块间禁止直接调用，必须通过 EventBus", "severity": "critical"},
    {"id": "DS-001", "name": "Design System Compliance", "category": "design",
     "description": "UI 组件必须遵循设计系统规范", "severity": "medium"},
    {"id": "CD-001", "name": "Circular Dependency Check", "category": "dependency",
     "description": "禁止循环依赖", "severity": "critical"},
    {"id": "RG-001", "name": "Regression Test Pass", "category": "regression",
     "description": "所有回归测试必须通过", "severity": "critical"},
    {"id": "API-001", "name": "API Contract Check", "category": "api",
     "description": "API 接口必须符合 OpenAPI 规范", "severity": "high"},
    {"id": "DB-001", "name": "Database Migration Check", "category": "database",
     "description": "数据库迁移必须向后兼容", "severity": "high"},
    {"id": "PF-001", "name": "Performance Baseline", "category": "performance",
     "description": "API 响应时间不超过 500ms", "severity": "medium"},
    {"id": "SC-001", "name": "Security Scan", "category": "security",
     "description": "安全扫描无高危漏洞", "severity": "critical"},
    {"id": "ST-001", "name": "Stability Check", "category": "stability",
     "description": "服务稳定性检查", "severity": "critical"},
]


class RuleEngine:
    def __init__(self):
        self._rules: Dict[str, Rule] = {}
        self._load_default_rules()

    def _load_default_rules(self):
        for rule_config in DEFAULT_RULES:
            rule = Rule(**rule_config)
            self._rules[rule.id] = rule

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        return self._rules.get(rule_id)

    def get_rules(self, category: Optional[str] = None) -> List[Rule]:
        if category:
            return [r for r in self._rules.values() if r.category == category and r.enabled]
        return [r for r in self._rules.values() if r.enabled]

    def add_rule(self, rule: Rule):
        self._rules[rule.id] = rule

    def disable_rule(self, rule_id: str):
        if rule_id in self._rules:
            self._rules[rule_id].enabled = False

    def enable_rule(self, rule_id: str):
        if rule_id in self._rules:
            self._rules[rule_id].enabled = True