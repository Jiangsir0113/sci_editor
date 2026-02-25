"""规则引擎：加载和执行所有规则"""

import importlib
import pkgutil
from typing import List, Type
from .models import Issue, DocumentStructure
from . import rules as rules_package


class BaseRule:
    """所有规则的基类"""

    rule_id: str = ""          # e.g. "3.1.1"
    rule_name: str = ""        # 规则名称
    section_name: str = ""     # 所属章节名称 e.g. "3.1 标题"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        """检查文档，返回发现的问题列表"""
        raise NotImplementedError

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        """
        尝试自动修复问题。
        返回 True 表示修复成功。
        子类可选实现。
        """
        return False


class RuleEngine:
    """规则引擎"""

    def __init__(self):
        self.rules: List[BaseRule] = []
        self._discover_rules()

    def _discover_rules(self):
        """自动发现并加载 rules/ 下所有规则类"""
        package_path = rules_package.__path__
        for importer, modname, ispkg in pkgutil.iter_modules(package_path):
            module = importlib.import_module(f".rules.{modname}", package="sci_editor")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, BaseRule) and
                    attr is not BaseRule and
                    attr.rule_id):
                    self.rules.append(attr())

        # 按 rule_id 排序
        self.rules.sort(key=lambda r: r.rule_id)

    def check(self, doc: DocumentStructure,
              rule_filter: List[str] = None) -> List[Issue]:
        """
        对文档执行所有（或指定的）规则检查。

        Args:
            doc: 解析后的文档结构
            rule_filter: 可选，只运行指定的规则 section (e.g. ["title", "authors"])
        """
        all_issues = []
        for rule in self.rules:
            if rule_filter:
                # 按 section_name 或 module name 过滤
                module_name = type(rule).__module__.split(".")[-1]
                if not any(f.lower() in module_name.lower() or
                           f.lower() in rule.section_name.lower()
                           for f in rule_filter):
                    continue
            try:
                issues = rule.check(doc)
                all_issues.extend(issues)
            except Exception as e:
                all_issues.append(Issue(
                    rule_id=rule.rule_id,
                    rule_name=rule.rule_name,
                    severity=Issue.__dataclass_fields__["severity"].default.__class__("warning"),
                    message=f"规则执行出错: {e}",
                    section=rule.section_name,
                ))
        return all_issues

    def fix_all(self, doc: DocumentStructure, issues: List[Issue]) -> int:
        """
        对所有可修复的问题尝试自动修复。

        Returns:
            修复成功的数量
        """
        fixed_count = 0
        rule_map = {r.rule_id: r for r in self.rules}
        for issue in issues:
            if issue.fixable and not issue.fixed:
                rule = rule_map.get(issue.rule_id)
                if rule:
                    try:
                        if rule.fix(doc, issue):
                            issue.fixed = True
                            fixed_count += 1
                    except Exception:
                        pass
        return fixed_count

    def get_rule_ids(self) -> List[str]:
        """返回所有已注册的规则ID"""
        return [r.rule_id for r in self.rules]
