export type ChatCreateResponse = {
  chatId: string
}

export type ChatTokenUsage = {
  input?: number
  output?: number
  total?: number
  source?: string
  approximate?: boolean
  sharedAcrossToolCalls?: number
}

export type ChatStatusToolCall = {
  id: string
  name: string
}

export type ChatThreadItem =
  | {
      id: string
      kind: 'message'
      role: 'assistant' | 'user'
      text: string
    }
  | {
      id: string
      kind: 'result'
      resultKind: 'table' | 'browse'
      table: Array<Record<string, unknown>>
    }
  | {
      id: string
      kind: 'tool'
      toolName: string
      node?: string
      toolCallIds?: string[]
      status: 'running' | 'completed'
      startedAt: number
      completedAt?: number
      durationMs?: number
      tokenUsage?: ChatTokenUsage
      requestDebugEventId?: string
      responseDebugEventId?: string
      raw: Record<string, unknown>
    }
  | {
      id: string
      kind: 'step'
      tone: 'status' | 'tool' | 'final'
      title: string
      detail: string
      node?: string
      toolName?: string
      toolCallIds?: string[]
      inspectable?: boolean
      requestDebugEventId?: string
      responseDebugEventId?: string
      raw: Record<string, unknown>
    }

export type ChatResultKind = 'text' | 'table' | 'browse'

export type ChatFinalPayload = {
  message: string
  resultKind?: ChatResultKind
  table: Array<Record<string, unknown>>
}

export type ChatStatusPayload = {
  message: string
  node?: string
  toolNames?: string[]
  toolName?: string
  toolCallIds?: string[]
  toolCalls?: ChatStatusToolCall[]
  tokenUsage?: ChatTokenUsage
}

export type ChatDebugContextSnapshot = {
  id: string
  phase: string
  title: string
  systemPrompt?: string
  bootstrapSkillNames?: string[]
  userMessage?: string
  toolNames?: string[]
  messageCount?: number
  messages: Array<Record<string, unknown>>
}

export type ChatDebugToolEvent = {
  id: string
  phase: 'request' | 'response'
  node?: string
  toolName?: string
  toolCallId?: string
  tokenUsage?: ChatTokenUsage
  arguments?: unknown
  rawPayload?: unknown
  normalizedPayload?: unknown
  previewRows?: Array<Record<string, unknown>>
  error?: string | null
  contextSnapshot?: ChatDebugContextSnapshot
}

export type ChatPromptGroup = {
  id: string
  prompt: {
    id: string
    kind: 'message'
    role: 'user'
    text: string
  }
  items: ChatThreadItem[]
  status: 'running' | 'completed'
}
