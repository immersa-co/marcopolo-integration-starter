import type {
  ChatDebugToolEvent,
  ChatPromptGroup,
  ChatStatusPayload,
  ChatStatusToolCall,
  ChatThreadItem,
} from './types'

function createChatItemId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export const initialChatItems: ChatThreadItem[] = [
  {
    id: 'intro-assistant',
    kind: 'message',
    role: 'assistant',
    text: 'The chat runtime will stream LangGraph progress and final answers here once you submit a prompt against any visible MarcoPolo connection.',
  },
]

export function createChatMessageItem(role: 'assistant' | 'user', text: string): ChatThreadItem {
  return {
    id: createChatItemId(role),
    kind: 'message',
    role,
    text,
  }
}

export function createChatResultItem(
  resultKind: 'table' | 'browse',
  table: Array<Record<string, unknown>>,
): ChatThreadItem {
  return {
    id: createChatItemId('result'),
    kind: 'result',
    resultKind,
    table,
  }
}

export function createChatStepItem(payload: ChatStatusPayload): ChatThreadItem {
  const message = payload.message.trim()
  const toolNames = Array.isArray(payload.toolNames)
    ? payload.toolNames.filter((value): value is string => typeof value === 'string' && value.trim().length > 0)
    : []
  const toolCallIds = Array.isArray(payload.toolCallIds)
    ? payload.toolCallIds.filter((value): value is string => typeof value === 'string' && value.trim().length > 0)
    : []
  const derivedToolName = payload.toolName?.trim()
    ? payload.toolName.trim()
    : message.includes(':')
      ? message.split(':', 2)[1]?.split(',')[0]?.trim() || undefined
      : undefined

  if (toolNames.length) {
    return {
      id: createChatItemId('step'),
      kind: 'step',
      tone: 'status',
      title: 'Loaded MarcoPolo MCP tools',
      detail: toolNames.join(', '),
      node: payload.node,
      toolCallIds,
      toolName: derivedToolName,
      raw: payload,
    }
  }

  if (message === 'Model produced final answer') {
    return {
      id: createChatItemId('step'),
      kind: 'step',
      tone: 'final',
      title: 'Prepared final answer',
      detail: 'The model completed the agent loop and produced the final response.',
      node: payload.node,
      toolCallIds,
      toolName: derivedToolName,
      raw: payload,
    }
  }

  return {
    id: createChatItemId('step'),
    kind: 'step',
    tone: 'status',
    title: message,
    detail: payload.node ? `Node: ${payload.node}` : 'Agent workspace update',
    node: payload.node,
    toolCallIds,
    toolName: derivedToolName,
    raw: payload,
  }
}

export function applyChatStatusPayload(items: ChatThreadItem[], payload: ChatStatusPayload): ChatThreadItem[] {
  const message = payload.message.trim()
  const toolNames = Array.isArray(payload.toolNames)
    ? payload.toolNames.filter((value): value is string => typeof value === 'string' && value.trim().length > 0)
    : []
  const toolCallIds = Array.isArray(payload.toolCallIds)
    ? payload.toolCallIds.filter((value): value is string => typeof value === 'string' && value.trim().length > 0)
    : []
  const toolName = payload.toolName?.trim()
    ? payload.toolName.trim()
    : message.includes(':')
      ? message.split(':', 2)[1]?.split(',')[0]?.trim() || undefined
      : undefined
  const toolCalls = Array.isArray(payload.toolCalls)
    ? payload.toolCalls.filter(
        (value): value is ChatStatusToolCall =>
          !!value &&
          typeof value === 'object' &&
          typeof value.id === 'string' &&
          !!value.id.trim() &&
          typeof value.name === 'string' &&
          !!value.name.trim(),
      )
    : []

  if (toolNames.length) {
    return [...items, createChatStepItem(payload)]
  }

  if (message.startsWith('Model selected tool call(s):')) {
    const startedAt = Date.now()
    const invocations = toolCalls.length
      ? toolCalls.map<ChatThreadItem>((toolCall) => ({
          id: `tool-${toolCall.id}`,
          kind: 'tool',
          toolName: toolCall.name,
          node: payload.node,
          toolCallIds: [toolCall.id],
          status: 'running',
          startedAt,
          tokenUsage: payload.tokenUsage,
          raw: payload,
        }))
      : [
          {
            id: createChatItemId('tool'),
            kind: 'tool' as const,
            toolName: toolName || 'tool',
            node: payload.node,
            toolCallIds,
            status: 'running' as const,
            startedAt,
            tokenUsage: payload.tokenUsage,
            raw: payload,
          },
        ]
    return [...items, ...invocations]
  }

  if (message.startsWith('Tool returned:')) {
    const nextItems = [...items]
    for (let index = nextItems.length - 1; index >= 0; index -= 1) {
      const item = nextItems[index]
      if (item.kind !== 'tool') {
        continue
      }

      const toolCallMatch = toolCallIds.length && item.toolCallIds?.some((id) => toolCallIds.includes(id))
      const toolNameMatch = !!toolName && item.toolName === toolName
      if (!toolCallMatch && !toolNameMatch) {
        continue
      }

      const completedAt = Date.now()
      nextItems[index] = {
        ...item,
        status: 'completed',
        completedAt,
        durationMs: completedAt - item.startedAt,
        toolCallIds: toolCallIds.length ? toolCallIds : item.toolCallIds,
        tokenUsage: item.tokenUsage ?? payload.tokenUsage,
        raw: payload,
      }
      return nextItems
    }
  }

  return [...items, createChatStepItem(payload)]
}

export function attachDebugEventToChatItems(items: ChatThreadItem[], debugEvent: ChatDebugToolEvent): ChatThreadItem[] {
  const nextItems = [...items]
  for (let index = nextItems.length - 1; index >= 0; index -= 1) {
    const item = nextItems[index]
    if (item.kind !== 'tool') {
      continue
    }

    const toolCallMatch =
      !!debugEvent.toolCallId &&
      Array.isArray(item.toolCallIds) &&
      item.toolCallIds.includes(debugEvent.toolCallId)
    const toolNameMatch = !!debugEvent.toolName && item.toolName === debugEvent.toolName
    if (!toolCallMatch && !toolNameMatch) {
      continue
    }

    if (debugEvent.phase === 'request' && !item.requestDebugEventId) {
      nextItems[index] = { ...item, requestDebugEventId: debugEvent.id, tokenUsage: debugEvent.tokenUsage ?? item.tokenUsage }
      return nextItems
    }

    if (debugEvent.phase === 'response' && !item.responseDebugEventId) {
      nextItems[index] = {
        ...item,
        responseDebugEventId: debugEvent.id,
        tokenUsage: item.tokenUsage ?? debugEvent.tokenUsage,
      }
      return nextItems
    }
  }

  return items
}

export function findMatchingDebugToolEvent({
  events,
  phase,
  debugEventId,
  toolCallIds,
  toolName,
}: {
  events: ChatDebugToolEvent[]
  phase: 'request' | 'response'
  debugEventId?: string
  toolCallIds?: string[]
  toolName?: string | null
}): ChatDebugToolEvent | null {
  if (debugEventId) {
    const byId = events.find((event) => event.id === debugEventId)
    if (byId) {
      return byId
    }
  }

  if (toolCallIds?.length) {
    const byCallId = events.find(
      (event) => event.phase === phase && !!event.toolCallId && toolCallIds.includes(event.toolCallId),
    )
    if (byCallId) {
      return byCallId
    }
  }

  if (toolName) {
    const byName = events.find((event) => event.phase === phase && event.toolName === toolName)
    if (byName) {
      return byName
    }
  }

  return null
}

export function getChatStepToneLabel(tone: 'status' | 'tool' | 'final'): string {
  if (tone === 'tool') {
    return 'Tool'
  }
  if (tone === 'final') {
    return 'Final'
  }
  return 'Status'
}

export function formatDurationMs(value?: number): string {
  if (value === undefined || Number.isNaN(value) || value < 0) {
    return '--:--'
  }

  const totalSeconds = Math.max(0, Math.round(value / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

export function formatTokenCount(value?: number): string {
  if (value === undefined || Number.isNaN(value)) {
    return '--'
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(value >= 10000 ? 0 : 1)}k`
  }
  return `${value}`
}

export function formatClockTime(value: number): string {
  return new Intl.DateTimeFormat([], {
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
  }).format(value)
}

export function getToolRequestContext(argumentsPayload: unknown): string | null {
  if (!argumentsPayload || typeof argumentsPayload !== 'object' || Array.isArray(argumentsPayload)) {
    return null
  }

  const context = (argumentsPayload as Record<string, unknown>).context
  return typeof context === 'string' && context.trim() ? context.trim() : null
}

export function deriveChatPromptGroups(items: ChatThreadItem[]): {
  preambleItems: ChatThreadItem[]
  promptGroups: ChatPromptGroup[]
} {
  const preambleItems: ChatThreadItem[] = []
  const promptGroups: ChatPromptGroup[] = []
  let activeGroup: ChatPromptGroup | null = null

  for (const item of items) {
    if (item.kind === 'message' && item.role === 'user') {
      const nextGroup: ChatPromptGroup = {
        id: item.id,
        prompt: {
          id: item.id,
          kind: 'message',
          role: 'user',
          text: item.text,
        },
        items: [],
        status: 'running',
      }
      activeGroup = nextGroup
      promptGroups.push(nextGroup)
      continue
    }

    if (!activeGroup) {
      preambleItems.push(item)
      continue
    }

    activeGroup.items.push(item)
    if (item.kind === 'tool' && item.status === 'running') {
      activeGroup.status = 'running'
      continue
    }

    if (!activeGroup.items.some((groupItem) => groupItem.kind === 'tool' && groupItem.status === 'running')) {
      activeGroup.status = 'completed'
    }
  }

  return { preambleItems, promptGroups }
}

export function getTableColumns(rows: Array<Record<string, unknown>>): string[] {
  const columns = new Set<string>()
  rows.forEach((row) => {
    Object.keys(row).forEach((key) => columns.add(key))
  })
  return Array.from(columns).slice(0, 8)
}

export function getBrowseItemKey(row: Record<string, unknown>, index: number): string {
  const candidate =
    row.id ??
    row.path ??
    row.workspace_path ??
    row.name ??
    row.title
  return typeof candidate === 'string' && candidate ? candidate : `browse-item-${index}`
}

export function getBrowseItemTitle(row: Record<string, unknown>, index: number): string {
  const candidate = row.name ?? row.title ?? row.path ?? row.workspace_path
  return typeof candidate === 'string' && candidate ? candidate : `Item ${index + 1}`
}

export function getBrowseItemSubtitle(row: Record<string, unknown>): string {
  const parts = [
    typeof row.path === 'string' ? row.path : null,
    typeof row.mimeType === 'string' ? row.mimeType : null,
    typeof row.modifiedTime === 'string' ? `Modified ${row.modifiedTime}` : null,
    typeof row.size === 'number' || typeof row.size === 'string' ? `Size ${row.size}` : null,
  ].filter((value): value is string => Boolean(value))

  return parts.join(' · ') || 'Open to inspect the returned metadata.'
}

export function getBrowseItemLink(row: Record<string, unknown>): string | null {
  const candidates = [row.webViewLink, row.url, row.link, row.web_url]
  for (const candidate of candidates) {
    if (typeof candidate === 'string' && /^https?:\/\//.test(candidate)) {
      return candidate
    }
  }
  return null
}

export function getBrowseItemKind(row: Record<string, unknown>): 'folder' | 'file' {
  const mimeType = typeof row.mimeType === 'string' ? row.mimeType.toLowerCase() : ''
  const type = typeof row.type === 'string' ? row.type.toLowerCase() : ''
  const name = typeof row.name === 'string' ? row.name.toLowerCase() : ''
  const path = typeof row.path === 'string' ? row.path.toLowerCase() : ''

  if (
    mimeType.includes('folder') ||
    type.includes('folder') ||
    name.endsWith('/') ||
    path.endsWith('/')
  ) {
    return 'folder'
  }

  return 'file'
}

export function formatChatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '—'
  }
  if (typeof value === 'string') {
    return value
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}
