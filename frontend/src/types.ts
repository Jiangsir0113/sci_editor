export interface Paragraph {
  index: number
  text: string
  section: string
}

export interface IssueOut {
  issue_id: string
  rule_id: string
  rule_name: string
  severity: 'error' | 'warning' | 'info'
  section: string
  paragraph_index: number
  context: string
  suggestion: string
  fixable: boolean
  fix_description: string
}

export interface DiffEntry {
  paragraph_index: number
  original: string
  modified: string
  issue_ids: string[]
}

export type DecisionAction = 'pending' | 'accept' | 'reject' | 'manual'

export interface Decision {
  issue_id: string
  action: DecisionAction
  final_text?: string
}
