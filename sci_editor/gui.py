"""科学编辑编辑加工工具 - GUI 界面"""

import os
import sys
import threading
import webbrowser
from datetime import datetime
from tkinter import (
    Tk, Frame, Label, Button, Text, Scrollbar, filedialog,
    messagebox, StringVar, BooleanVar, Checkbutton, PanedWindow,
    HORIZONTAL, VERTICAL, BOTH, LEFT, RIGHT, TOP, BOTTOM, END, WORD,
    DISABLED, NORMAL, X, Y, W, E, N, S, YES, font as tkfont
)
from tkinter import ttk

# 确保包路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sci_editor.parser import parse_document
from sci_editor.engine import RuleEngine
from sci_editor.reporter import generate_html_report, generate_text_report
from sci_editor.models import Severity, Issue
from docx import Document


class SciEditorApp:
    """科学编辑稿件检查工具 GUI"""

    def __init__(self, root: Tk):
        self.root = root
        self.root.title("📝 科学编辑编辑加工工具 v1.0")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)

        # 设置图标和主题
        self._setup_style()

        # 状态变量
        self.filepath = StringVar(value="")
        self.auto_fix = BooleanVar(value=True)
        self.issues: list = []
        self.engine = RuleEngine()
        self.doc_structure = None

        # 构建界面
        self._build_ui()

    def _setup_style(self):
        """配置 ttk 主题和颜色"""
        style = ttk.Style()
        style.theme_use("clam")

        # 颜色系统
        self.colors = {
            "bg": "#f5f6fa",
            "card_bg": "#ffffff",
            "primary": "#2962ff",
            "primary_hover": "#1e4fcc",
            "success": "#00c853",
            "warning": "#ff9100",
            "error": "#ff1744",
            "info": "#2979ff",
            "text": "#333333",
            "text_secondary": "#888888",
            "border": "#e0e0e0",
            "accent": "#6c5ce7",
        }

        self.root.configure(bg=self.colors["bg"])

        # 配置样式
        style.configure("Title.TLabel",
                         font=("Segoe UI", 18, "bold"),
                         foreground=self.colors["primary"],
                         background=self.colors["bg"])
        style.configure("Subtitle.TLabel",
                         font=("Segoe UI", 10),
                         foreground=self.colors["text_secondary"],
                         background=self.colors["bg"])
        style.configure("Card.TFrame",
                         background=self.colors["card_bg"],
                         relief="flat")
        style.configure("Primary.TButton",
                         font=("Segoe UI", 11, "bold"),
                         foreground="white",
                         background=self.colors["primary"],
                         padding=(20, 10))
        style.map("Primary.TButton",
                   background=[("active", self.colors["primary_hover"])])
        style.configure("Secondary.TButton",
                         font=("Segoe UI", 10),
                         padding=(15, 8))
        style.configure("Status.TLabel",
                         font=("Segoe UI", 10),
                         foreground=self.colors["text_secondary"],
                         background=self.colors["bg"])
        style.configure("Stat.TLabel",
                         font=("Segoe UI", 24, "bold"),
                         background=self.colors["card_bg"])
        style.configure("StatLabel.TLabel",
                         font=("Segoe UI", 9),
                         foreground=self.colors["text_secondary"],
                         background=self.colors["card_bg"])

    def _build_ui(self):
        """构建主界面"""
        main_frame = Frame(self.root, bg=self.colors["bg"])
        main_frame.pack(fill=BOTH, expand=True, padx=20, pady=15)

        # --- 顶部标题区 ---
        header = Frame(main_frame, bg=self.colors["bg"])
        header.pack(fill=X, pady=(0, 15))

        ttk.Label(header, text="📝 科学编辑编辑加工工具",
                  style="Title.TLabel").pack(side=LEFT)
        ttk.Label(header, text="Scientific Manuscript Editing Assistant",
                  style="Subtitle.TLabel").pack(side=LEFT, padx=(10, 0), pady=(8, 0))

        # --- 文件选择区 ---
        file_frame = Frame(main_frame, bg=self.colors["card_bg"],
                           highlightbackground=self.colors["border"],
                           highlightthickness=1, bd=0)
        file_frame.pack(fill=X, pady=(0, 12))

        file_inner = Frame(file_frame, bg=self.colors["card_bg"])
        file_inner.pack(fill=X, padx=16, pady=12)

        Label(file_inner, text="📄 选择稿件文件:",
              font=("Segoe UI", 11), bg=self.colors["card_bg"],
              fg=self.colors["text"]).pack(side=LEFT)

        self.file_label = Label(file_inner, textvariable=self.filepath,
                                font=("Segoe UI", 10),
                                bg=self.colors["card_bg"],
                                fg=self.colors["text_secondary"],
                                anchor=W)
        self.file_label.pack(side=LEFT, fill=X, expand=True, padx=(10, 10))

        ttk.Button(file_inner, text="浏览...",
                   command=self._browse_file,
                   style="Secondary.TButton").pack(side=RIGHT)

        # --- 操作区 ---
        action_frame = Frame(main_frame, bg=self.colors["bg"])
        action_frame.pack(fill=X, pady=(0, 12))

        left_actions = Frame(action_frame, bg=self.colors["bg"])
        left_actions.pack(side=LEFT)

        Checkbutton(left_actions, text="✅ 自动修复可修复的问题",
                    variable=self.auto_fix,
                    font=("Segoe UI", 10),
                    bg=self.colors["bg"],
                    activebackground=self.colors["bg"],
                    selectcolor=self.colors["card_bg"]).pack(side=LEFT)

        right_actions = Frame(action_frame, bg=self.colors["bg"])
        right_actions.pack(side=RIGHT)

        self.check_btn = ttk.Button(right_actions, text="🔍 开始检查",
                                     command=self._start_check,
                                     style="Primary.TButton")
        self.check_btn.pack(side=LEFT, padx=(0, 8))

        ttk.Button(right_actions, text="💾 导出修复文档",
                   command=self._export_fixed,
                   style="Secondary.TButton").pack(side=LEFT, padx=(0, 8))

        ttk.Button(right_actions, text="📊 导出HTML报告",
                   command=self._export_html,
                   style="Secondary.TButton").pack(side=LEFT)

        # --- 统计卡片区 ---
        stats_frame = Frame(main_frame, bg=self.colors["bg"])
        stats_frame.pack(fill=X, pady=(0, 12))

        self.stat_vars = {}
        stat_configs = [
            ("errors", "❌ 错误", self.colors["error"]),
            ("warnings", "⚠️ 警告", self.colors["warning"]),
            ("infos", "ℹ️ 提示", self.colors["info"]),
            ("fixed", "✅ 已修复", self.colors["success"]),
        ]

        for key, label_text, color in stat_configs:
            card = Frame(stats_frame, bg=self.colors["card_bg"],
                         highlightbackground=self.colors["border"],
                         highlightthickness=1)
            card.pack(side=LEFT, fill=X, expand=True, padx=(0, 8))

            self.stat_vars[key] = StringVar(value="0")
            num_label = Label(card, textvariable=self.stat_vars[key],
                              font=("Segoe UI", 28, "bold"),
                              fg=color, bg=self.colors["card_bg"])
            num_label.pack(pady=(12, 2))
            Label(card, text=label_text,
                  font=("Segoe UI", 10),
                  fg=self.colors["text_secondary"],
                  bg=self.colors["card_bg"]).pack(pady=(0, 12))

        # --- 结果区（Treeview + 详情） ---
        result_pane = PanedWindow(main_frame, orient=HORIZONTAL,
                                   bg=self.colors["bg"],
                                   sashwidth=6, sashrelief="flat")
        result_pane.pack(fill=BOTH, expand=True)

        # 左侧：问题列表
        left_panel = Frame(result_pane, bg=self.colors["card_bg"],
                           highlightbackground=self.colors["border"],
                           highlightthickness=1)
        result_pane.add(left_panel, width=650)

        Label(left_panel, text="检查结果",
              font=("Segoe UI", 12, "bold"),
              bg=self.colors["card_bg"],
              fg=self.colors["text"],
              anchor=W).pack(fill=X, padx=12, pady=(10, 6))

        tree_frame = Frame(left_panel, bg=self.colors["card_bg"])
        tree_frame.pack(fill=BOTH, expand=True, padx=8, pady=(0, 8))

        tree_scroll = ttk.Scrollbar(tree_frame)
        tree_scroll.pack(side=RIGHT, fill=Y)

        self.tree = ttk.Treeview(tree_frame,
                                  columns=("severity", "rule", "message"),
                                  show="tree headings",
                                  yscrollcommand=tree_scroll.set,
                                  selectmode="browse")
        self.tree.pack(fill=BOTH, expand=True)
        tree_scroll.config(command=self.tree.yview)

        self.tree.heading("#0", text="区段")
        self.tree.heading("severity", text="级别")
        self.tree.heading("rule", text="规则")
        self.tree.heading("message", text="问题描述")

        self.tree.column("#0", width=120, minwidth=80)
        self.tree.column("severity", width=60, minwidth=50)
        self.tree.column("rule", width=80, minwidth=60)
        self.tree.column("message", width=380, minwidth=200)

        self.tree.bind("<<TreeviewSelect>>", self._on_select_issue)

        # 配置Treeview标签颜色
        self.tree.tag_configure("error", foreground=self.colors["error"])
        self.tree.tag_configure("warning", foreground=self.colors["warning"])
        self.tree.tag_configure("info", foreground=self.colors["info"])
        self.tree.tag_configure("fixed", foreground=self.colors["success"])

        # 右侧：详情面板
        right_panel = Frame(result_pane, bg=self.colors["card_bg"],
                            highlightbackground=self.colors["border"],
                            highlightthickness=1)
        result_pane.add(right_panel, width=400)

        Label(right_panel, text="问题详情",
              font=("Segoe UI", 12, "bold"),
              bg=self.colors["card_bg"],
              fg=self.colors["text"],
              anchor=W).pack(fill=X, padx=12, pady=(10, 6))

        detail_scroll = ttk.Scrollbar(right_panel)
        detail_scroll.pack(side=RIGHT, fill=Y)

        self.detail_text = Text(right_panel, wrap=WORD,
                                 font=("Consolas", 10),
                                 bg="#fafafa", fg=self.colors["text"],
                                 relief="flat", padx=12, pady=10,
                                 yscrollcommand=detail_scroll.set,
                                 state=DISABLED)
        self.detail_text.pack(fill=BOTH, expand=True, padx=(8, 0), pady=(0, 8))
        detail_scroll.config(command=self.detail_text.yview)

        # 配置标签
        self.detail_text.tag_configure("heading",
                                        font=("Segoe UI", 11, "bold"),
                                        foreground=self.colors["primary"])
        self.detail_text.tag_configure("label",
                                        font=("Segoe UI", 10, "bold"),
                                        foreground=self.colors["text"])
        self.detail_text.tag_configure("value",
                                        font=("Segoe UI", 10),
                                        foreground=self.colors["text_secondary"])
        self.detail_text.tag_configure("context",
                                        font=("Consolas", 9),
                                        background="#f0f0f0",
                                        foreground="#555")
        self.detail_text.tag_configure("suggestion",
                                        font=("Segoe UI", 10),
                                        foreground=self.colors["success"])
        self.detail_text.tag_configure("fixed_tag",
                                        font=("Segoe UI", 10, "bold"),
                                        foreground=self.colors["success"])

        # --- 底部状态栏 ---
        self.status_var = StringVar(value="就绪。请选择一个 .docx 稿件文件。")
        status_bar = Frame(main_frame, bg=self.colors["bg"])
        status_bar.pack(fill=X, pady=(8, 0))
        ttk.Label(status_bar, textvariable=self.status_var,
                  style="Status.TLabel").pack(side=LEFT)

    def _browse_file(self):
        """选择文件"""
        path = filedialog.askopenfilename(
            title="选择稿件文件",
            filetypes=[("Word 文档", "*.docx"), ("所有文件", "*.*")]
        )
        if path:
            self.filepath.set(path)
            self.status_var.set(f"已选择: {os.path.basename(path)}")

    def _start_check(self):
        """开始检查"""
        filepath = self.filepath.get()
        if not filepath or not os.path.exists(filepath):
            messagebox.showwarning("提示", "请先选择一个有效的 .docx 文件！")
            return

        self.check_btn.configure(state=DISABLED)
        self.status_var.set("🔄 正在解析文档...")
        self.root.update()

        # 在后台线程中执行检查
        thread = threading.Thread(target=self._run_check, args=(filepath,))
        thread.daemon = True
        thread.start()

    def _run_check(self, filepath: str):
        """后台执行检查"""
        try:
            # 解析文档
            self.doc_structure = parse_document(filepath)
            self.root.after(0, lambda: self.status_var.set("🔄 正在执行规则检查..."))

            # 执行检查
            self.issues = self.engine.check(self.doc_structure)

            # 自动修复
            if self.auto_fix.get():
                fixed_count = self.engine.fix_all(self.doc_structure, self.issues)
                self.root.after(0, lambda: self.status_var.set(
                    f"✅ 检查完成！发现 {len(self.issues)} 个问题，自动修复 {fixed_count} 个"))
            else:
                self.root.after(0, lambda: self.status_var.set(
                    f"✅ 检查完成！发现 {len(self.issues)} 个问题"))

            # 更新 UI
            self.root.after(0, self._update_results)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"检查过程出错:\n{e}"))
            self.root.after(0, lambda: self.status_var.set("❌ 检查失败"))
        finally:
            self.root.after(0, lambda: self.check_btn.configure(state=NORMAL))

    def _update_results(self):
        """更新结果显示"""
        # 清空 Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 统计
        errors = sum(1 for i in self.issues if i.severity == Severity.ERROR and not i.fixed)
        warnings = sum(1 for i in self.issues if i.severity == Severity.WARNING and not i.fixed)
        infos = sum(1 for i in self.issues if i.severity == Severity.INFO and not i.fixed)
        fixed = sum(1 for i in self.issues if i.fixed)

        self.stat_vars["errors"].set(str(errors))
        self.stat_vars["warnings"].set(str(warnings))
        self.stat_vars["infos"].set(str(infos))
        self.stat_vars["fixed"].set(str(fixed))

        # 按 section 分组
        sections = {}
        for issue in self.issues:
            section = issue.section or "其他"
            if section not in sections:
                sections[section] = []
            sections[section].append(issue)

        # 填充 Treeview
        severity_icon = {
            Severity.ERROR: "❌",
            Severity.WARNING: "⚠️",
            Severity.INFO: "ℹ️",
        }

        for section_name, section_issues in sections.items():
            # 区段节点
            parent = self.tree.insert("", END, text=section_name, open=True)
            for idx, issue in enumerate(section_issues):
                tag = "fixed" if issue.fixed else issue.severity.value
                icon = "✅" if issue.fixed else severity_icon.get(issue.severity, "•")
                self.tree.insert(parent, END,
                                 values=(icon, issue.rule_id, issue.message[:80]),
                                 tags=(tag,))

        # 清空详情
        self.detail_text.configure(state=NORMAL)
        self.detail_text.delete("1.0", END)
        self.detail_text.insert(END, f"共发现 {len(self.issues)} 个问题\n", "heading")
        self.detail_text.insert(END, "点击左侧列表查看详情", "value")
        self.detail_text.configure(state=DISABLED)

    def _on_select_issue(self, event):
        """选中问题时显示详情"""
        selected = self.tree.selection()
        if not selected:
            return

        item = selected[0]
        parent = self.tree.parent(item)
        if not parent:
            return  # 选中的是区段标题

        # 获取问题索引
        section_name = self.tree.item(parent, "text")
        child_index = self.tree.index(item)

        # 按 section 分组找到对应 issue
        sections = {}
        for issue in self.issues:
            section = issue.section or "其他"
            if section not in sections:
                sections[section] = []
            sections[section].append(issue)

        if section_name in sections and child_index < len(sections[section_name]):
            issue = sections[section_name][child_index]
            self._show_issue_detail(issue)

    def _show_issue_detail(self, issue: Issue):
        """显示问题详情"""
        self.detail_text.configure(state=NORMAL)
        self.detail_text.delete("1.0", END)

        severity_text = {
            Severity.ERROR: "❌ 错误",
            Severity.WARNING: "⚠️ 警告",
            Severity.INFO: "ℹ️ 提示",
        }

        self.detail_text.insert(END, f"{issue.rule_name}\n", "heading")
        self.detail_text.insert(END, "\n")

        self.detail_text.insert(END, "规则编号: ", "label")
        self.detail_text.insert(END, f"{issue.rule_id}\n", "value")

        self.detail_text.insert(END, "严重程度: ", "label")
        self.detail_text.insert(END, f"{severity_text.get(issue.severity, '未知')}\n", "value")

        self.detail_text.insert(END, "所属区段: ", "label")
        self.detail_text.insert(END, f"{issue.section}\n", "value")

        self.detail_text.insert(END, "\n")
        self.detail_text.insert(END, "问题描述:\n", "label")
        self.detail_text.insert(END, f"{issue.message}\n", "value")

        if issue.context:
            self.detail_text.insert(END, "\n")
            self.detail_text.insert(END, "相关上下文:\n", "label")
            self.detail_text.insert(END, f"{issue.context}\n", "context")

        if issue.suggestion:
            self.detail_text.insert(END, "\n")
            self.detail_text.insert(END, "💡 修改建议:\n", "label")
            self.detail_text.insert(END, f"{issue.suggestion}\n", "suggestion")

        if issue.fixed:
            self.detail_text.insert(END, "\n")
            self.detail_text.insert(END, "✅ 已自动修复", "fixed_tag")
            if issue.fix_description:
                self.detail_text.insert(END, f"\n{issue.fix_description}", "value")

        self.detail_text.configure(state=DISABLED)

    def _export_fixed(self):
        """导出修复后的文档"""
        if not self.doc_structure:
            messagebox.showwarning("提示", "请先执行检查！")
            return

        output_path = filedialog.asksaveasfilename(
            title="保存修复后的文档",
            defaultextension=".docx",
            filetypes=[("Word 文档", "*.docx")],
            initialfile=f"fixed_{os.path.basename(self.filepath.get())}"
        )
        if output_path:
            try:
                from sci_editor.fixer import save_fixed_document
                save_fixed_document(self.doc_structure, output_path)
                self.status_var.set(f"✅ 修复文档已保存: {output_path}")
                messagebox.showinfo("成功", f"修复后的文档已保存到:\n{output_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败:\n{e}")

    def _export_html(self):
        """导出 HTML 报告"""
        if not self.issues:
            messagebox.showwarning("提示", "请先执行检查！")
            return

        output_path = filedialog.asksaveasfilename(
            title="保存 HTML 报告",
            defaultextension=".html",
            filetypes=[("HTML 文件", "*.html")],
            initialfile=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )
        if output_path:
            try:
                generate_html_report(
                    self.issues,
                    os.path.basename(self.filepath.get()),
                    output_path
                )
                self.status_var.set(f"✅ HTML 报告已保存: {output_path}")
                # 自动在浏览器中打开
                webbrowser.open(f"file:///{output_path}")
            except Exception as e:
                messagebox.showerror("错误", f"报告生成失败:\n{e}")


def main():
    root = Tk()
    app = SciEditorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
