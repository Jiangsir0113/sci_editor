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
  const isActiveRef = useRef(isActive)
  isActiveRef.current = isActive

  const relatedIssues = issues.filter((i) => i.paragraph_index === paragraphIndex)

  // 只在非编辑状态下同步 DOM 内容（避免覆盖用户编辑中的内容）
  useEffect(() => {
    if (!isActiveRef.current && ref.current) {
      ref.current.innerHTML = sanitize(htmlContent)
    }
  }, [htmlContent])

  // isActive 变化时：激活时 focus，关闭时同步最新 htmlContent
  useEffect(() => {
    if (!ref.current) return
    if (isActive) {
      ref.current.focus()
    } else {
      ref.current.innerHTML = sanitize(htmlContent)
    }
  }, [isActive]) // eslint-disable-line react-hooks/exhaustive-deps

  // 初始渲染：设置内容
  useEffect(() => {
    if (ref.current) {
      ref.current.innerHTML = sanitize(htmlContent)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function handleBlur() {
    if (!ref.current || relatedIssues.length === 0) return
    const text = ref.current.innerText
    relatedIssues.forEach((issue) => {
      setDecision(issue.issue_id, 'manual', text)
    })
  }

  return (
    <div
      ref={ref}
      contentEditable={isActive}
      suppressContentEditableWarning
      onBlur={handleBlur}
      className={`p-2 text-sm leading-relaxed outline-none transition-colors min-h-[1.5rem] ${
        isActive ? 'bg-gray-800 ring-1 ring-blue-500 rounded cursor-text' : 'cursor-default'
      }`}
    />
  )
}
