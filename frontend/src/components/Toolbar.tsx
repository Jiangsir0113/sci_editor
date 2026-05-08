import { useRef } from 'react'
import { useEditorStore } from '../store'
import { uploadDoc, checkDoc } from '../api'

const RULE_LABELS: Record<string, string> = {
  title: '标题', authors: '作者', affiliations: '单位',
  abstract: '摘要', keywords: '关键词', italics: '斜体',
  abbreviations: '缩写', statistics: '统计', citations: '引用',
  references: '参考文献', figures_tables: '图表', footnotes: '脚注',
  punctuation: '标点', numbers: '数字', units: '单位符号',
  symbols: '符号', ranges: '数值范围', ci_format: 'CI格式',
  headings: '小标题', running_title: '短标题', funding: '基金',
  corresponding: '通讯作者', contributions: '作者贡献', footer: '页脚',
}

export default function Toolbar() {
  const fileRef = useRef<HTMLInputElement>(null)
  const {
    docId, filename, availableRules, selectedRules,
    toggleRule, selectAllRules, clearRules,
    setUploadResult, setCheckResult, setLoading, setError, loading,
  } = useEditorStore()

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      const result = await uploadDoc(file)
      setUploadResult(result.doc_id, result.filename, result.paragraphs, result.available_rules)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  async function handleRun() {
    if (!docId || selectedRules.length === 0) return
    setLoading(true)
    setError(null)
    try {
      const result = await checkDoc(docId, selectedRules)
      setCheckResult(result.issues, result.diff)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-gray-900 border-b border-gray-700 px-4 py-2 flex flex-wrap items-center gap-3">
      <input ref={fileRef} type="file" accept=".docx" className="hidden" onChange={handleFileChange} />
      <button
        onClick={() => fileRef.current?.click()}
        disabled={loading}
        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded text-sm font-medium shrink-0"
      >
        📁 {filename || '上传文件'}
      </button>

      {availableRules.length > 0 && (
        <>
          <div className="flex flex-wrap gap-1.5">
            {availableRules.map((rule) => (
              <button
                key={rule}
                onClick={() => toggleRule(rule)}
                className={`px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors ${
                  selectedRules.includes(rule)
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                }`}
              >
                {RULE_LABELS[rule] ?? rule}
              </button>
            ))}
          </div>
          <button
            onClick={selectAllRules}
            className="text-xs text-gray-400 hover:text-gray-200 shrink-0"
          >
            全选
          </button>
          <button
            onClick={clearRules}
            className="text-xs text-gray-400 hover:text-gray-200 shrink-0"
          >
            清空
          </button>
          <button
            onClick={handleRun}
            disabled={loading || selectedRules.length === 0}
            className="px-3 py-1.5 bg-green-600 hover:bg-green-500 disabled:opacity-50 rounded text-sm font-medium ml-auto shrink-0"
          >
            {loading ? '处理中...' : '▶ 执行'}
          </button>
        </>
      )}
    </div>
  )
}
