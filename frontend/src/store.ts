import { create } from 'zustand'
import type { Paragraph, IssueOut, DiffEntry, Decision, DecisionAction } from './types'

interface EditorState {
  docId: string | null
  filename: string
  availableRules: string[]
  selectedRules: string[]
  paragraphs: Paragraph[]
  issues: IssueOut[]
  diff: DiffEntry[]
  decisions: Record<string, Decision>
  focusedParagraphIndex: number | null
  loading: boolean
  error: string | null

  setUploadResult: (docId: string, filename: string, paragraphs: Paragraph[], availableRules: string[]) => void
  toggleRule: (rule: string) => void
  selectAllRules: () => void
  clearRules: () => void
  setCheckResult: (issues: IssueOut[], diff: DiffEntry[]) => void
  setDecision: (issueId: string, action: DecisionAction, finalText?: string) => void
  setFocusedParagraph: (index: number | null) => void
  setLoading: (v: boolean) => void
  setError: (msg: string | null) => void
  reset: () => void
}

export const useEditorStore = create<EditorState>((set) => ({
  docId: null,
  filename: '',
  availableRules: [],
  selectedRules: [],
  paragraphs: [],
  issues: [],
  diff: [],
  decisions: {},
  focusedParagraphIndex: null,
  loading: false,
  error: null,

  setUploadResult: (docId, filename, paragraphs, availableRules) =>
    set({ docId, filename, paragraphs, availableRules, selectedRules: availableRules }),

  toggleRule: (rule) =>
    set((s) => ({
      selectedRules: s.selectedRules.includes(rule)
        ? s.selectedRules.filter((r) => r !== rule)
        : [...s.selectedRules, rule],
    })),

  selectAllRules: () => set((s) => ({ selectedRules: [...s.availableRules] })),
  clearRules: () => set({ selectedRules: [] }),

  setCheckResult: (issues, diff) => {
    const decisions: Record<string, Decision> = {}
    issues.forEach((i) => { decisions[i.issue_id] = { issue_id: i.issue_id, action: 'pending' } })
    set({ issues, diff, decisions })
  },

  setDecision: (issueId, action, finalText) =>
    set((s) => ({
      decisions: {
        ...s.decisions,
        [issueId]: { issue_id: issueId, action, final_text: finalText },
      },
    })),

  setFocusedParagraph: (index) => set({ focusedParagraphIndex: index }),
  setLoading: (v) => set({ loading: v }),
  setError: (msg) => set({ error: msg }),
  reset: () => set({
    docId: null, filename: '', availableRules: [], selectedRules: [],
    paragraphs: [], issues: [], diff: [], decisions: {},
    focusedParagraphIndex: null, loading: false, error: null,
  }),
}))
