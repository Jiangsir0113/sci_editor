"""报告生成器：HTML 和 Excel 报告"""

import os
from datetime import datetime
from collections import OrderedDict
from typing import List
from jinja2 import Environment, FileSystemLoader
from .models import Issue, Severity


def _group_issues_by_section(issues: List[Issue]) -> OrderedDict:
    """按 section 分组"""
    grouped = OrderedDict()
    for issue in issues:
        section = issue.section or "其他"
        if section not in grouped:
            grouped[section] = []
        grouped[section].append(issue)
    return grouped


def generate_html_report(issues: List[Issue], filename: str,
                         output_path: str,
                         template_dir: str = None) -> str:
    """生成 HTML 检查报告"""
    if template_dir is None:
        template_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates"
        )

    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("report.html")

    sections = _group_issues_by_section(issues)
    error_count = sum(1 for i in issues if i.severity == Severity.ERROR and not i.fixed)
    warning_count = sum(1 for i in issues if i.severity == Severity.WARNING and not i.fixed)
    info_count = sum(1 for i in issues if i.severity == Severity.INFO and not i.fixed)
    fixed_count = sum(1 for i in issues if i.fixed)

    html = template.render(
        filename=filename,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        sections=sections,
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
        fixed_count=fixed_count,
    )

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


def generate_text_report(issues: List[Issue], filename: str) -> str:
    """生成纯文本报告（用于GUI显示）"""
    if not issues:
        return "🎉 恭喜！未发现任何问题。"

    lines = [f"📝 检查报告: {filename}", "=" * 50, ""]

    sections = _group_issues_by_section(issues)
    for section_name, section_issues in sections.items():
        lines.append(f"▶ {section_name}")
        lines.append("-" * 40)
        for issue in section_issues:
            status = "✅已修复" if issue.fixed else ""
            icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(
                issue.severity.value, "•")
            lines.append(f"  {icon} [{issue.rule_id}] {issue.message} {status}")
            if issue.context:
                ctx = issue.context[:80] + ("..." if len(issue.context) > 80 else "")
                lines.append(f"      ↳ {ctx}")
            if issue.suggestion:
                lines.append(f"      💡 {issue.suggestion}")
        lines.append("")

    # 汇总
    error_count = sum(1 for i in issues if i.severity == Severity.ERROR and not i.fixed)
    warning_count = sum(1 for i in issues if i.severity == Severity.WARNING and not i.fixed)
    info_count = sum(1 for i in issues if i.severity == Severity.INFO and not i.fixed)
    fixed_count = sum(1 for i in issues if i.fixed)

    lines.append("=" * 50)
    lines.append(f"汇总: ❌ 错误 {error_count} | ⚠️ 警告 {warning_count} | "
                 f"ℹ️ 提示 {info_count} | ✅ 已修复 {fixed_count}")

    return "\n".join(lines)
