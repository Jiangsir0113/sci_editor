import { useRef, useEffect } from 'react'
import { useEditorStore } from '../store'
import EditablePanel from './EditablePanel'

export default function DiffView() {
  const { paragraphs, diff, focusedParagraphIndex, setFocusedParagraph } = useEditorStore()
  const leftRefs = useRef<(HTMLDivElement | null)[]>([])
  const rightRefs = useRef<(HTMLDivElement | null)[]>([])

  useEffect(() => {
    if (focusedParagraphIndex === null) return
    leftRefs.current[focusedParagraphIndex]?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    rightRefs.current[focusedParagraphIndex]?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [focusedParagraphIndex])

  if (paragraphs.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
        上传文件后执行检查，此处将显示修改对比
      </div>
    )
  }

  const diffByPara = Object.fromEntries(diff.map((d) => [d.paragraph_index, d]))
  const modifiedIndices = new Set(diff.map((d) => d.paragraph_index))

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* 左栏：原文 */}
      <div className="flex-1 overflow-y-auto border-r border-gray-700 p-4">
        <div className="text-xs text-red-400 font-mono mb-3 sticky top-0 bg-gray-950 py-1 z-10">
          原文
        </div>
        <div className="space-y-0.5">
          {paragraphs.map((para) => {
            const isFocused = focusedParagraphIndex === para.index
            const isModified = modifiedIndices.has(para.index)
            return (
              <div
                key={para.index}
                ref={(el) => { leftRefs.current[para.index] = el }}
                onClick={() => isModified && setFocusedParagraph(para.index)}
                className={`p-2 rounded text-sm leading-relaxed transition-colors ${
                  isFocused
                    ? 'bg-red-950/70 ring-1 ring-red-500'
                    : isModified
                    ? 'bg-red-950/20 cursor-pointer hover:bg-red-950/40'
                    : 'text-gray-400'
                }`}
              >
                {para.text || <span className="text-gray-700 italic text-xs">（空段落）</span>}
              </div>
            )
          })}
        </div>
      </div>

      {/* 右栏：修改后（可编辑） */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="text-xs text-green-400 font-mono mb-3 sticky top-0 bg-gray-950 py-1 z-10">
          修改后（可编辑）
        </div>
        <div className="space-y-0.5">
          {paragraphs.map((para) => {
            const diffEntry = diffByPara[para.index]
            const isFocused = focusedParagraphIndex === para.index
            const content = diffEntry ? diffEntry.modified : para.text
            return (
              <div
                key={para.index}
                ref={(el) => { rightRefs.current[para.index] = el }}
                onClick={() => diffEntry && !isFocused && setFocusedParagraph(para.index)}
                className={`rounded transition-colors ${
                  isFocused
                    ? 'ring-1 ring-green-500'
                    : diffEntry
                    ? 'bg-green-950/20 cursor-pointer hover:bg-green-950/40'
                    : ''
                }`}
              >
                <EditablePanel
                  paragraphIndex={para.index}
                  htmlContent={content}
                  isActive={isFocused}
                />
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
