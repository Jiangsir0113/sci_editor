import { useEditorStore } from '../store'
import { applyDecisions, deleteSession } from '../api'
import type { IssueOut } from '../types'

const SEVERITY_ICON: Record<string, string> = {
  error: '❌',
  warning: '⚠️',
  info: 'ℹ️',
}

const ACTION_LABEL: Record<string, string> = {
  pending: '待处理',
  accept: '已接受',
  reject: '已拒绝',
  manual: '手动修改',
}

const ACTION_COLOR: Record<string, string> = {
  pending: 'text-gray-400',
  accept: 'text-green-400',
  reject: 'text-red-400',
  manual: 'text-blue-400',
}

export default function ChangeList() {
  const {
    issues,
    decisions,
    setDecision,
    setFocusedParagraph,
    docId,
    filename,
    setLoading,
    setError,
    loading,
  } = useEditorStore()

  if (issues.length === 0) {
    return (
      <div className="p-4 text-gray-500 text-sm">
        执行检查后此处将显示逐条修改列表
      </div>
    )
  }

  async function handleExport() {
    if (!docId) return
    setLoading(true)
    setError(null)
    try {
      const decisionsArr = Object.values(decisions)
      const blob = await applyDecisions(docId, decisionsArr)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `edited_${filename || 'document'}.docx`
      a.click()
      URL.revokeObjectURL(url)
      // 清理服务器端 session
      await deleteSession(docId)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  function acceptAll() {
    issues.forEach((i) => setDecision(i.issue_id, 'accept'))
  }

  function rejectAll() {
    issues.forEach((i) => setDecision(i.issue_id, 'reject'))
  }

  const processedCount = Object.values(decisions).filter((d) => d.action !== 'pending').length

  return (
    <div className="flex flex-col h-full">
      {/* 操作栏 */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-700 bg-gray-900 sticky top-0 z-10">
        <span className="text-xs text-gray-400">
          共 {issues.length} 条 · 已处理 {processedCount} 条
        </span>
        <button
          onClick={acceptAll}
          className="text-xs text-green-400 hover:text-green-300"
        >
          全部接受
        </button>
        <button
          onClick={rejectAll}
          className="text-xs text-red-400 hover:text-red-300"
        >
          全部拒绝
        </button>
        <button
          onClick={handleExport}
          disabled={loading}
          className="ml-auto px-3 py-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded text-sm font-medium"
        >
          {loading ? '导出中...' : '⬇ 导出文档'}
        </button>
      </div>

      {/* 列表 */}
      <div className="flex-1 overflow-y-auto divide-y divide-gray-800">
        {issues.map((issue: IssueOut) => {
          const decision = decisions[issue.issue_id]
          const action = decision?.action ?? 'pending'
          return (
            <div
              key={issue.issue_id}
              onClick={() => setFocusedParagraph(issue.paragraph_index)}
              className="px-4 py-2.5 hover:bg-gray-800/50 cursor-pointer flex items-start gap-3 group"
            >
              <span className="text-base mt-0.5 shrink-0">
                {SEVERITY_ICON[issue.severity] ?? '•'}
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-xs text-gray-500 mb-0.5">
                  [{issue.rule_id}] {issue.rule_name}
                  {issue.section && ` · ${issue.section}`}
                </div>
                <div className="text-sm text-gray-200 truncate">{issue.context}</div>
                {issue.suggestion && (
                  <div className="text-xs text-green-400 truncate mt-0.5">
                    → {issue.suggestion}
                  </div>
                )}
              </div>
              <div
                className={`flex gap-1.5 shrink-0 items-center text-xs ${ACTION_COLOR[action]}`}
              >
                <span className="hidden group-hover:inline">{ACTION_LABEL[action]}</span>
                {action !== 'accept' && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setDecision(issue.issue_id, 'accept')
                    }}
                    title="接受"
                    className="px-1.5 py-0.5 bg-green-800 hover:bg-green-700 text-green-200 rounded"
                  >
                    ✓
                  </button>
                )}
                {action !== 'reject' && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setDecision(issue.issue_id, 'reject')
                    }}
                    title="拒绝"
                    className="px-1.5 py-0.5 bg-red-800 hover:bg-red-700 text-red-200 rounded"
                  >
                    ✗
                  </button>
                )}
                {action !== 'pending' && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setDecision(issue.issue_id, 'pending')
                    }}
                    title="撤回"
                    className="px-1.5 py-0.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded"
                  >
                    ↩
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
