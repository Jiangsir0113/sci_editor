# SCI Editor (科学论文辅助编辑工具)

SCI Editor 是一款专为生物医学科学论文设计的自动化编辑与格式校对工具。它通过强大的语义解析和规则引擎，帮助科研人员自动化处理复杂的投稿规范，显著提升论文质量。

## 核心功能图谱

### 1. 手稿信息规范 (Manuscript Info)
*   **标题与短标题**：自动校对标题大小写；智能生成符合规范的 Running Title（如 `FirstAuthor Surname Initials et al.`）。 [Update: 2026-02-25]
*   **作者与单位**：标准化中国作者姓名格式（如 `Tai-Xian Song`）；校对多单位标注一致性。 [Update: 2026-02-25]
*   **摘要与关键词**：根据稿件类型（Original Article / Case Report / Review）核对摘要必备结构；自动规范关键词的大小写及分隔符。 [Update: 2026-02-25]

### 2. 术语与一致性 (Consistency)
*   **缩略词一致性 (Rule 3.10)**：[NEW: 2026-02-25]
    *   动态频次统计：自动识别术语出现次数，仅在 $\ge 3$ 次时启用缩写。
    *   定义修复：确保首次出现时为 `Full Name (ABBR)`，后续统一。
    *   低频回退：频次不足时自动恢复全称并清理定义。
*   **斜体与符号**：自动识别并修正 `p value`、`in vivo`、`et al.` 等固定词汇的斜体格式。
*   **物理量与单位**：规范物理量数值与单位间的数值空格（如 `20 kg` ）。

### 3. 统计结果与数据 (Statistics)
*   **CI/OR 格式修复**：支持复杂统计结果的自动化标准化（如 `OR = 0.85 (95%CI: 0.7-1.2, P = 0.01)`）。 [Update: 2026-02-25]
*   **标点与数值范围**：自动修正 `20-30%`、`1.5 ~ 2.5` 等数值范围的学术符号规范。

### 4. 参考文献与交叉引用 (References)
*   **引用顺序**：检查正文引用标号是否按顺序出现。
*   **引用格式**：规范 `[1-3, 5]` 类似的引用标点与合并。
*   **图表引用**：确保 `Figure 1`、`Table 2` 的引用在正文中有对应体现。

## 实现时间轴与更新日志

### 2026-02-25 (最新更新)
- **[Feature]** 实现了 **Rule 3.10 缩写增强逻辑**：支持区段独立统计与自动化全称回退。
- **[Fix]** 重构 **解析引擎 (parser.py)**：显著提升了对 `Introduction` 等正文边界的识别精度，彻底解决了摘要与正文频次统计干扰的问题。
- **[Fix]** 增强 **CI/OR 修复能力**：支持更多样化的 P 值表达格式及嵌套括号修复。
- **[Feature]** 完善 **Running Title 自动补全**：第一作者姓氏提取及斜体 `et al.` 的精准处理。
- **[Infrastructure]** 更新 **PyInstaller 打包配置**：支持资源模板打包，生成的 `.exe` 可直接生成 HTML 报告。

### 2026-02-20
- **[Feature]** 实现基础文档结构解析（Section-based parsing）。
- **[Feature]** 建立基础规则库：包含标点、标度、数学符号一致性。
- **[Feature]** 开发 GUI 界面与 HTML 报告生成系统。

## 如何使用

### 1. 快速开始 (Windows)
1. 下载最新发布的 `dist/sci_editor.exe`。
2. 启动程序并点击 **"选择文件"**。
3. 点击 **"执行检查"**，稍后浏览器将自动弹出详细的 HTML 修复建议。
4. 对确认无误的建议，点击 **"应用修复"** 即可生成修改后的文档。

### 2. 开发者模式
```bash
# 1. 克隆控制仓库
git clone https://github.com/Jiangsir0113/sci_editor.git

# 2. 安装 Python 核心依赖 (推荐 Python 3.10+)
pip install python-docx jinja2

# 3. 运行主程序
python sci_editor/main.py
```

---
*© 2026 SCI Editor Project Team. Powered by Advanced Agentic Coding.*
