"""自动修复器：保存修复后的文档"""

import os
from docx import Document
from .models import DocumentStructure


def save_fixed_document(doc: DocumentStructure, output_path: str) -> str:
    """
    将修复后的文档保存到新路径。

    规则的 fix() 方法直接修改了 doc.word_doc 中的 Run/Paragraph 对象，
    这里直接保存该对象即可（不能重新从磁盘读取，否则修改会丢失）。
    """
    if doc.word_doc is None:
        raise ValueError("DocumentStructure.word_doc 未设置，无法保存修复后的文档")

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    doc.word_doc.save(output_path)
    return output_path
