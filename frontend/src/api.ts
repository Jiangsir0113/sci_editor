import type { Paragraph, IssueOut, DiffEntry, Decision } from './types'

const BASE = '/api'

export async function uploadDoc(file: File): Promise<{
  doc_id: string
  filename: string
  paragraphs: Paragraph[]
  available_rules: string[]
}> {
  const form = new FormData()
  form.append('file', file)
  const r = await fetch(`${BASE}/upload`, { method: 'POST', body: form })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function checkDoc(doc_id: string, rule_filter: string[]): Promise<{
  issues: IssueOut[]
  diff: DiffEntry[]
}> {
  const r = await fetch(`${BASE}/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ doc_id, rule_filter }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function applyDecisions(doc_id: string, decisions: Decision[]): Promise<Blob> {
  const r = await fetch(`${BASE}/apply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ doc_id, decisions }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.blob()
}

export async function deleteSession(doc_id: string): Promise<void> {
  await fetch(`${BASE}/session/${doc_id}`, { method: 'DELETE' })
}
