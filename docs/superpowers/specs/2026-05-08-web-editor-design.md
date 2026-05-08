# SCI Editor Web 版设计文档

**日期**：2026-05-08  
**状态**：待实现  

## 背景与目标

现有工具（桌面 GUI + Python 规则引擎）是黑盒模式：上传文档 → 自动修改 → 输出结果，编辑无法在过程中审核每一条修改。这导致工具产生的错误修改只能在最后人工扫描，效率低，信任度不足。

目标是将工具改造为**透明可审核的网页版**，编辑可以：
- 选择执行哪些规则
- 逐条查看每处修改的前后对比
- 接受、拒绝或手动修改每一条建议
- 导出最终确认后的文档

部署到服务器，编辑通过浏览器访问，无需安装任何环境，便于后续收集反馈、持续迭代。

---

## 系统架构

```
浏览器（React 前端 SPA）
        ↕ HTTP / REST
FastAPI 后端
        ↕ 直接调用
现有规则引擎（engine.py / parser.py / fixer.py / rules/）
        ↕
文件存储（服务器本地临时目录，按 doc_id 隔离）
```

**前端**：React（Vite 构建），部署为静态文件，由 nginx 托管  
**后端**：FastAPI + uvicorn，复用全部现有 Python 规则代码  
**部署**：Docker Compose（nginx + FastAPI 容器），或直接在服务器上 uvicorn + nginx

现有的 `engine.py`、`parser.py`、`fixer.py` 和 `rules/` 目录**不需要重写**，直接作为后端模块引入。

---

## 页面布局

### 整体结构（A 方案）

```
┌──────────────────────────────────────────────────────────────┐
│  顶部工具栏                                                    │
│  [📁 上传文件]  [标题][作者][斜体][缩写][统计]...  [▶ 执行]    │
├────────────────────────┬─────────────────────────────────────┤
│  原文                  │  修改后（可富文本编辑）               │
│  红色高亮 = 被修改处   │  绿色高亮 = 修改内容                 │
│                        │  点击激活段落 → 直接编辑             │
│                        │                                     │
├────────────────────────┴─────────────────────────────────────┤
│  逐条修改列表                                                  │
│  [规则ID] [位置] [原文→建议]  [✓ 接受] [✗ 拒绝] [↩ 撤回]      │
│  点击某条 → 左右栏自动滚动定位到对应段落                        │
└──────────────────────────────────────────────────────────────┘
```

### 顶部工具栏

- **上传按钮**：点击选择本地 `.docx` 文件，上传后显示文件名
- **规则 Chip 多选**：每个规则组显示为可点击标签，选中/未选中状态清晰，支持全选/清空
- **执行按钮**：触发后端检查，执行期间显示 loading 状态
- 规则分组对应现有 `rules/` 目录中的模块：标题、作者/单位、摘要、关键词、斜体符号、缩写规范、统计数据、参考文献、图表引用、脚注、页脚等

### 左右对比区

- 左栏（原文）：只读，被修改的词/短语用红色背景高亮
- 右栏（修改后）：默认展示工具建议的修改结果，修改处绿色高亮
- 点击逐条列表中某条 → 左右栏同步滚动，对应段落高亮边框提示定位
- 点击右栏某个高亮处或列表中的"编辑"→ 该段落变为富文本编辑器，可直接在上下文中修改文本
- 编辑完成后点击"保存"，该条修改状态更新为"手动修改"

### 逐条修改列表（底部操作面板）

每条修改显示：
- 规则编号和名称（如 `[3.5.2] 斜体格式`）
- 所在段落位置
- 原文 → 建议修改（红/绿色区分）
- 操作按钮：✓ 接受 / ✗ 拒绝 / ✎ 编辑 / ↩ 撤回
- 状态标记：待处理 / 已接受 / 已拒绝 / 手动修改

面板底部：全部接受、全部拒绝、导出文档按钮。

---

## API 设计

### `POST /upload`
上传 `.docx` 文件。

**Response**：
```json
{
  "doc_id": "uuid",
  "filename": "manuscript.docx",
  "paragraphs": [
    { "index": 0, "text": "...", "section": "标题" }
  ],
  "available_rules": ["title", "authors", "italics", ...]
}
```

### `POST /check`
对已上传文档执行规则检查。

**Request**：
```json
{
  "doc_id": "uuid",
  "rule_filter": ["italics", "abbreviations", "statistics"]
}
```

**Response**：
```json
{
  "issues": [
    {
      "issue_id": "uuid",
      "rule_id": "3.5.2",
      "rule_name": "斜体格式",
      "severity": "warning",
      "section": "正文",
      "paragraph_index": 12,
      "context": "P value = 0.05",
      "suggestion": "<em>P</em> value = 0.05",
      "fixable": true,
      "fix_description": "将 P 改为斜体"
    }
  ],
  "diff": [
    {
      "paragraph_index": 12,
      "original": "P value = 0.05",
      "modified": "<em>P</em> value = 0.05",
      "issue_ids": ["uuid"]
    }
  ]
}
```

### `POST /apply`
将编辑的决策（接受/拒绝/手动修改）应用到文档并导出。

**Request**：
```json
{
  "doc_id": "uuid",
  "decisions": [
    { "issue_id": "uuid", "action": "accept" },
    { "issue_id": "uuid", "action": "reject" },
    { "issue_id": "uuid", "action": "manual", "final_text": "自定义文本" }
  ]
}
```

**Response**：返回修改后的 `.docx` 文件（binary 下载）。

### `DELETE /session/{doc_id}`
清理服务器上的临时文件（用户关闭页面时调用）。

---

## 数据流

```
1. 用户上传 docx
   → 后端调用 parser.py 解析文档结构
   → 生成 doc_id，保存文档到临时目录
   → 返回段落列表 + 可用规则列表

2. 用户选择规则，点击执行
   → 后端调用 engine.py 的 check() 方法
   → 返回 issue 列表 + 每段落的 diff 数据
   → 前端渲染左右对比 + 逐条列表

3. 编辑逐条审核
   → 接受：记录 action=accept
   → 拒绝：记录 action=reject，右栏还原为原文
   → 手动编辑：右栏段落变为富文本编辑器，保存后记录 action=manual + 最终文本

4. 点击导出
   → 后端调用 fixer.py，按决策列表写入修改
   → 返回修改后的 docx 文件供下载

5. 会话结束
   → 清理临时文件
```

---

## 前端技术选型

- **框架**：React + Vite（生态成熟，组件化适合这种交互复杂的界面）
- **富文本编辑**：`contenteditable` + 自定义高亮逻辑（避免引入重型富文本编辑器，只需支持简单的斜体/加粗等格式）
- **安全**：后端返回的 `suggestion` 字段包含受控 HTML（如 `<em>`），前端渲染时使用白名单过滤（只允许 `<em>`、`<strong>`、`<sup>`、`<sub>`），不直接 `innerHTML` 拼接用户输入
- **状态管理**：Zustand（轻量，管理 doc_id、issues、decisions 等状态）
- **样式**：Tailwind CSS（快速开发，无需自定义 CSS 体系）

---

## 后端技术选型

- **框架**：FastAPI（异步支持，自动生成 API 文档，Python 生态）
- **文件处理**：python-docx（现有依赖，直接复用）
- **临时文件**：按 `doc_id` 在服务器临时目录隔离，定期清理
- **会话管理**：无需数据库，状态存在内存 + 临时文件中（无需登录系统）

---

## 部署方案

```yaml
# docker-compose.yml 示意
services:
  backend:
    build: ./backend   # FastAPI + 现有规则引擎
    ports: ["8000:8000"]
    volumes:
      - ./tmp:/tmp/sci_editor  # 临时文件挂载

  frontend:
    build: ./frontend  # React 静态构建 + nginx
    ports: ["80:80"]
    depends_on: [backend]
```

- 前端 nginx 同时做静态文件托管和 `/api` 反向代理
- 文件大小限制：建议 10MB（单篇论文 docx 通常 <2MB）
- 临时文件 TTL：1小时后自动清理

---

## 不在本期范围内

- 用户登录 / 权限管理（暂时不需要，内部使用）
- 修改历史记录持久化（每次导出即为最终结果）
- 多人协作（单文档单会话）
- 移动端适配（编辑工作在桌面端进行）
