import { useRef, useEffect } from 'react'
import { useEditorStore } from '../store'

interface Props {
  paragraphIndex: number
  htmlContent: string
  isActive: boolean
}

function sanitize(html: string): string {
  return html
    .replace(/<(?!\/?(?:em|strong|sup|sub)\b)[^>]*>/gi, '')
    .replace(/javascript:/gi, '')
}

export default function EditablePanel({ paragraphIndex, htmlContent, isActive }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const { setDecision, issues } = useEditorStore()

  const relatedIssues = issues.filter((i) => i.paragraph_index === paragraphIndex)

  function handleBlur() {
    if (!ref.current || relatedIssues.length === 0) return
    const text = ref.current.innerText
    relatedIssues.forEach((issue) => {
      setDecision(issue.issue_id, 'manual', text)
    })
  }

  useEffect(() => {
    if (isActive && ref.current) {
      ref.current.focus()
    }
  }, [isActive])

  // 当 isActive 变为 false 时，同步 htmlContent 到 DOM（避免编辑后残留状态）
  useEffect(() => {
    if (!isActive && ref.current) {
      ref.current.innerHTML = sanitize(htmlContent)
    }
  }, [isActive, htmlContent])

  return (
    <div
      ref={ref}
      contentEditable={isActive}
      suppressContentEditableWarning
      onBlur={handleBlur}
      className={`p-2 text-sm leading-relaxed outline-none transition-colors min-h-[1.5rem] ${
        isActive ? 'bg-gray-800 ring-1 ring-blue-500 rounded cursor-text' : 'cursor-default'
      }`}
      dangerouslySetInnerHTML={{ __html: sanitize(htmlContent) }}
    />
  )
}
