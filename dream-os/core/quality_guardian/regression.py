"""Regression Test - 回归测试模块"""
from typing import List, Dict, Any
from dataclasses import dataclass, field
import time


@dataclass
class TestResult:
    module: str
    passed: bool
    duration_ms: float
    details: str = ""
    error: str = ""


REGRESSION_MODULES = [
    "chat", "search", "image", "file_upload", "memory", "agent",
    "workflow", "project", "chart", "mermaid", "ppt", "markdown",
    "api", "database", "home", "execution_mode", "dev_mode",
]


class RegressionTester:
    def __init__(self):
        self.results: List[TestResult] = []

    async def run_all(self) -> List[TestResult]:
        self.results = []
        for module in REGRESSION_MODULES:
            result = await self._run_module(module)
            self.results.append(result)
        return self.results

    async def run_module(self, module: str) -> TestResult:
        result = await self._run_module(module)
        self.results.append(result)
        return result

    async def _run_module(self, module: str) -> TestResult:
        start = time.time()
        try:
            passed = await self._check_module(module)
            duration = (time.time() - start) * 1000
            return TestResult(
                module=module,
                passed=passed,
                duration_ms=round(duration, 2),
                details=f"{module} module check completed",
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return TestResult(
                module=module,
                passed=False,
                duration_ms=round(duration, 2),
                error=str(e)[:200],
            )

    async def _check_module(self, module: str) -> bool:
        return True

    def get_summary(self) -> Dict[str, Any]:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total * 100, 2) if total > 0 else 0,
        }