"""数据模型定义"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Any


class Severity(Enum):
    """问题严重程度"""
    ERROR = "error"       # 必须修复
    WARNING = "warning"   # 建议修复
    INFO = "info"         # 仅提示


class SectionType(Enum):
    """文档区段类型"""
    TITLE = "标题"
    RUNNING_TITLE = "短标题"
    AUTHORS = "作者"
    AFFILIATIONS = "机构"
    CONTRIBUTIONS = "作者贡献"
    FUNDING = "基金"
    CORRESPONDING = "通讯作者"
    ABSTRACT = "摘要"
    CORE_TIP = "Core Tip"
    KEYWORDS = "关键词"
    ARTICLE_INFO = "文章信息"
    BODY = "正文"
    REFERENCES = "参考文献"
    FOOTNOTES = "脚注"
    FIGURES = "图"
    TABLES = "表格"
    PAGE_HEADER = "页眉"
    UNKNOWN = "未知"


@dataclass
class Issue:
    """检查发现的问题"""
    rule_id: str                         # 规则编号, e.g. "3.1.1"
    rule_name: str                       # 规则名称
    severity: Severity                   # 严重程度
    message: str                         # 问题描述
    section: str = ""                    # 所属区段
    paragraph_index: int = -1            # 段落索引
    context: str = ""                    # 上下文（问题文本片段）
    suggestion: str = ""                 # 修改建议
    fixable: bool = False                # 是否可自动修复
    fixed: bool = False                  # 是否已修复
    fix_description: str = ""            # 修复描述

    def __str__(self):
        icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}
        s = icon.get(self.severity.value, "•")
        return f"{s} [{self.rule_id}] {self.message}"


@dataclass
class Section:
    """文档中的一个区段"""
    section_type: SectionType
    paragraphs: list = field(default_factory=list)
    # 每个元素是 (paragraph_index_in_doc, paragraph_object)
    start_index: int = 0
    end_index: int = 0
    raw_text: str = ""

    @property
    def text(self) -> str:
        """合并段落文本"""
        return "\n".join(p.text for _, p in self.paragraphs)


@dataclass
class DocumentStructure:
    """解析后的文档结构"""
    filepath: str = ""
    sections: dict = field(default_factory=dict)    # SectionType -> Section
    all_paragraphs: list = field(default_factory=list)
    tables: list = field(default_factory=list)
    reference_count: int = 0
    word_doc: Any = None          # 原始 python-docx Document 对象，用于保存修复后的文档
    manuscript_type: str = ""     # 稿件类型，如 META-ANALYSIS, CASE REPORT, REVIEW 等

    def get_section(self, section_type: SectionType) -> Optional[Section]:
        return self.sections.get(section_type)

    def get_section_text(self, section_type: SectionType) -> str:
        s = self.sections.get(section_type)
        return s.text if s else ""
