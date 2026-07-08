"""Quality Report - 质量报告"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class QualityReport:
    target: str
    passed: bool = False
    rules_checked: int = 0
    rules_passed: int = 0
    rules_failed: int = 0
    regression_total: int = 0
    regression_passed: int = 0
    regression_failed: int = 0
    details: List[Dict[str, Any]] = field(default_factory=list)
    repair_suggestions: List[str] = field(default_factory=list)
    impact_analysis: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    repair_cycle: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "passed": self.passed,
            "rules_checked": self.rules_checked,
            "rules_passed": self.rules_passed,
            "rules_failed": self.rules_failed,
            "regression_total": self.regression_total,
            "regression_passed": self.regression_passed,
            "regression_failed": self.regression_failed,
            "details": self.details,
            "repair_suggestions": self.repair_suggestions,
            "impact_analysis": self.impact_analysis,
            "timestamp": self.timestamp,
            "repair_cycle": self.repair_cycle,
        }

    def to_text(self) -> str:
        lines = [
            "=" * 60,
            f"  Quality Guardian Report",
            f"  Target: {self.target}",
            f"  Result: {'PASSED' if self.passed else 'FAILED'}",
            f"  Timestamp: {self.timestamp}",
            f"  Repair Cycle: {self.repair_cycle}",
            "=" * 60,
            "",
            f"Rules: {self.rules_passed}/{self.rules_checked} passed, {self.rules_failed} failed",
            f"Regression: {self.regression_passed}/{self.regression_total} passed, {self.regression_failed} failed",
            "",
        ]
        if self.details:
            lines.append("Details:")
            for d in self.details:
                status = "PASS" if d.get("passed") else "FAIL"
                lines.append(f"  [{status}] {d.get('rule_id', 'N/A')}: {d.get('message', '')}")
        if self.repair_suggestions:
            lines.append("")
            lines.append("Repair Suggestions:")
            for s in self.repair_suggestions:
                lines.append(f"  - {s}")
        return "\n".join(lines)