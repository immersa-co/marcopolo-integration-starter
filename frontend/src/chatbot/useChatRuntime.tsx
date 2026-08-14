import { useEffect, useRef, useState } from 'react'

import type {
  ChatCreateResponse,
  ChatDebugContextSnapshot,
  ChatDebugToolEvent,
  ChatFinalPayload,
  ChatPromptGroup,
  ChatStatusPayload,
  ChatThreadItem,
} from './types'
import {
  applyChatStatusPayload,
  attachDebugEventToChatItems,
  createChatMessageItem,
  createChatResultItem,
  deriveChatPromptGroups,
  findMatchingDebugToolEvent,
  formatChatValue,
  formatClockTime,
  formatDurationMs,
  formatTokenCount,
  getBrowseItemKey,
  getBrowseItemKind,
  getBrowseItemLink,
  getBrowseItemSubtitle,
  getBrowseItemTitle,
  getChatStepToneLabel,
  getTableColumns,
  getToolRequestContext,
  initialChatItems,
} from './utils'

type UseChatRuntimeOptions = {
  apiBaseUrl: string
  marcopoloAccessEnabled: boolean
  needsMarcoPoloAuthorization: boolean
  availableChatConnectionNames: string[]
}

type UseChatRuntimeResult = {
  chatBusy: boolean
  chatInput: string
  chatPlaceholder: string
  chatTranscriptRef: React.RefObject<HTMLDivElement | null>
  preambleItems: ChatThreadItem[]
  promptGroups: ChatPromptGroup[]
  collapsedPromptIds: string[]
  selectedToolItem: Extract<ChatThreadItem, { kind: 'tool' }> | null
  selectedToolContext: ChatDebugContextSnapshot | null
  selectedToolRequest: ChatDebugToolEvent | null
  selectedToolResponse: ChatDebugToolEvent | null
  setChatInput: (value: string) => void
  handleClearChat: () => void
  handleChatSubmit: (event: React.FormEvent<HTMLFormElement>) => Promise<void>
  handleDeletePromptGroup: (group: ChatPromptGroup) => void
  togglePromptGroup: (groupId: string) => void
  renderChatTranscriptItem: (item: ChatThreadItem) => React.ReactNode
}

export default function useChatRuntime({
  apiBaseUrl,
  marcopoloAccessEnabled,
  needsMarcoPoloAuthorization,
  availableChatConnectionNames,
}: UseChatRuntimeOptions): UseChatRuntimeResult {
  const [chatInput, setChatInput] = useState('')
  const [chatItems, setChatItems] = useState<ChatThreadItem[]>(initialChatItems)
  const [collapsedPromptIds, setCollapsedPromptIds] = useState<string[]>([])
  const [expandedChatItem, setExpandedChatItem] = useState<string | null>(null)
  const [selectedToolItemId, setSelectedToolItemId] = useState<string | null>(null)
  const [chatDebugTools, setChatDebugTools] = useState<ChatDebugToolEvent[]>([])
  const [chatBusy, setChatBusy] = useState(false)
  const chatTranscriptRef = useRef<HTMLDivElement | null>(null)

  const chatPlaceholder = marcopoloAccessEnabled
    ? availableChatConnectionNames.length
      ? `Ask about any available connection, for example ${availableChatConnectionNames.join(', ')}.`
      : 'Ask about any available MarcoPolo connection.'
    : needsMarcoPoloAuthorization
      ? 'Completing WorkOS Standalone Connect authorization.'
      : 'Sign in to enable chat.'

  const selectedToolItem =
    selectedToolItemId && chatItems.length
      ? chatItems.find(
          (item): item is Extract<ChatThreadItem, { kind: 'tool' }> => item.kind === 'tool' && item.id === selectedToolItemId,
        ) ?? null
      : null
  const selectedToolName = selectedToolItem?.toolName ?? null
  const selectedToolRequest = findMatchingDebugToolEvent({
    events: chatDebugTools,
    phase: 'request',
    debugEventId: selectedToolItem?.requestDebugEventId,
    toolCallIds: selectedToolItem?.toolCallIds,
    toolName: selectedToolName,
  })
  const selectedToolResponse = findMatchingDebugToolEvent({
    events: chatDebugTools,
    phase: 'response',
    debugEventId: selectedToolItem?.responseDebugEventId,
    toolCallIds: selectedToolItem?.toolCallIds,
    toolName: selectedToolName,
  })
  const selectedToolContext =
    selectedToolResponse?.contextSnapshot ?? selectedToolRequest?.contextSnapshot ?? null
  const { preambleItems, promptGroups } = deriveChatPromptGroups(chatItems)

  useEffect(() => {
    const node = chatTranscriptRef.current
    if (!node) {
      return
    }

    node.scrollTo({
      top: node.scrollHeight,
      behavior: 'smooth',
    })
  }, [chatItems])

  async function handleChatSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!chatInput.trim()) {
      return
    }

    const message = chatInput.trim()
    const userPromptItem = createChatMessageItem('user', message)
    setChatBusy(true)
    setExpandedChatItem(null)
    setCollapsedPromptIds((current) => current.filter((id) => id !== userPromptItem.id))
    setChatItems((current) => [...current, userPromptItem])
    setChatInput('')

    try {
      const createResponse = await fetch(`${apiBaseUrl}/api/chat`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }),
      })

      if (!createResponse.ok) {
        throw new Error(`Chat creation failed with ${createResponse.status}`)
      }

      const payload = (await createResponse.json()) as ChatCreateResponse
      const eventSource = new EventSource(`${apiBaseUrl}/api/chat/${payload.chatId}/stream`, {
        withCredentials: true,
      })
      let streamClosed = false

      function closeStream() {
        if (streamClosed) {
          return
        }
        streamClosed = true
        eventSource.close()
      }

      eventSource.addEventListener('status', (streamEvent) => {
        const payload = JSON.parse((streamEvent as MessageEvent<string>).data) as ChatStatusPayload
        setChatItems((current) => applyChatStatusPayload(current, payload))
      })

      eventSource.addEventListener('debug_tool', (streamEvent) => {
        const debugEvent = JSON.parse((streamEvent as MessageEvent<string>).data) as ChatDebugToolEvent
        setChatDebugTools((current) => {
          const existingIndex = current.findIndex((item) => item.id === debugEvent.id)
          if (existingIndex >= 0) {
            const next = [...current]
            next[existingIndex] = debugEvent
            return next
          }
          return [...current, debugEvent]
        })
        setChatItems((current) => attachDebugEventToChatItems(current, debugEvent))
      })

      eventSource.addEventListener('final', (streamEvent) => {
        const payload = JSON.parse((streamEvent as MessageEvent<string>).data) as ChatFinalPayload
        setChatItems((current) => {
          const nextItems = [...current, createChatMessageItem('assistant', payload.message)]
          if (payload.table.length && (payload.resultKind === 'table' || payload.resultKind === 'browse')) {
            nextItems.push(createChatResultItem(payload.resultKind, payload.table))
          }
          return nextItems
        })
        setExpandedChatItem(null)
        setChatBusy(false)
        closeStream()
      })

      eventSource.addEventListener('error', (streamEvent) => {
        if (streamClosed) {
          return
        }
        setChatItems((current) => [
          ...current,
          createChatMessageItem('assistant', (streamEvent as MessageEvent<string>).data || 'Chat stream failed.'),
        ])
        setChatBusy(false)
        closeStream()
      })

      eventSource.addEventListener('done', () => {
        setExpandedChatItem(null)
        setChatBusy(false)
        closeStream()
      })
    } catch (error) {
      setChatItems((current) => [
        ...current,
        createChatMessageItem('assistant', (error as Error).message),
      ])
      setChatBusy(false)
    }
  }

  function handleClearChat() {
    setChatItems(initialChatItems)
    setCollapsedPromptIds([])
    setExpandedChatItem(null)
    setSelectedToolItemId(null)
    setChatDebugTools([])
    setChatInput('')
  }

  function handleDeletePromptGroup(group: ChatPromptGroup) {
    const groupItemIds = new Set<string>([group.prompt.id, ...group.items.map((item) => item.id)])
    const deletedToolIds = new Set<string>(
      group.items.filter((item): item is Extract<ChatThreadItem, { kind: 'tool' }> => item.kind === 'tool').map((item) => item.id),
    )
    const deletedResultIds = group.items
      .filter((item): item is Extract<ChatThreadItem, { kind: 'result' }> => item.kind === 'result')
      .map((item) => item.id)

    setChatItems((current) => current.filter((item) => !groupItemIds.has(item.id)))
    setCollapsedPromptIds((current) => current.filter((id) => id !== group.id))
    setExpandedChatItem((current) =>
      current && deletedResultIds.some((resultId) => current.startsWith(`${resultId}-`)) ? null : current,
    )
    setSelectedToolItemId((current) => (current && deletedToolIds.has(current) ? null : current))
  }

  function togglePromptGroup(groupId: string) {
    setCollapsedPromptIds((current) =>
      current.includes(groupId)
        ? current.filter((id) => id !== groupId)
        : [...current, groupId],
    )
  }

  function renderChatTranscriptItem(item: ChatThreadItem) {
    if (item.kind === 'message') {
      return (
        <div key={item.id} className={`bubble ${item.role}`}>
          {item.text}
        </div>
      )
    }

    if (item.kind === 'tool') {
      const requestEvent = findMatchingDebugToolEvent({
        events: chatDebugTools,
        phase: 'request',
        debugEventId: item.requestDebugEventId,
        toolCallIds: item.toolCallIds,
        toolName: item.toolName,
      })
      const toolContext = getToolRequestContext(requestEvent?.arguments)

      return (
        <article
          key={item.id}
          className={`chat-tool-row ${item.status} ${selectedToolItemId === item.id ? 'selected' : ''}`}
        >
          <button
            type="button"
            className="chat-tool-button"
            onClick={() => setSelectedToolItemId(item.id)}
          >
            <span className="chat-tool-header">
              <span className="chat-tool-main">Invoking tool: {item.toolName}</span>
              <span className="chat-tool-meta">
                <span className={`chat-tool-status ${item.status}`}>{item.status}</span>
                <span>{formatClockTime(item.startedAt)}</span>
                {item.durationMs !== undefined ? <span>{formatDurationMs(item.durationMs)}</span> : null}
                {item.tokenUsage?.total !== undefined ? <span>{formatTokenCount(item.tokenUsage.total)}</span> : null}
              </span>
            </span>
            {toolContext ? <span className="chat-tool-context">{toolContext}</span> : null}
          </button>
        </article>
      )
    }

    if (item.kind === 'result') {
      return item.resultKind === 'browse' ? (
        <div key={item.id} className="chat-result-card">
          <div className="chat-result-header">
            <p className="section-label">Browse Results</p>
            <h3>Accessible folders and documents</h3>
          </div>
          <div className="browse-results">
            {item.table.map((row, index) => {
              const itemKey = `${item.id}-${getBrowseItemKey(row, index)}`
              const expanded = expandedChatItem === itemKey
              const itemLink = getBrowseItemLink(row)
              const itemKind = getBrowseItemKind(row)

              return (
                <article key={itemKey} className="browse-result-card">
                  <div className="browse-result-row">
                    <button
                      type="button"
                      className="browse-result-toggle"
                      onClick={() => {
                        setExpandedChatItem((current) => (current === itemKey ? null : itemKey))
                      }}
                    >
                      <span className={`browse-result-badge ${itemKind}`}>{itemKind === 'folder' ? 'Folder' : 'File'}</span>
                      <span className="browse-result-copy">
                        <strong>{getBrowseItemTitle(row, index)}</strong>
                        <span>{getBrowseItemSubtitle(row)}</span>
                      </span>
                      <span className="browse-result-expand">{expanded ? 'Hide details' : 'View details'}</span>
                    </button>
                    {itemLink ? (
                      <a
                        className="secondary-button browse-result-link"
                        href={itemLink}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open source
                      </a>
                    ) : null}
                  </div>
                  {expanded ? (
                    <dl className="browse-result-details">
                      {Object.entries(row).map(([key, value]) => (
                        <div key={key} className="browse-result-detail-row">
                          <dt>{key}</dt>
                          <dd>{formatChatValue(value)}</dd>
                        </div>
                      ))}
                    </dl>
                  ) : null}
                </article>
              )
            })}
          </div>
        </div>
      ) : (
        <div key={item.id} className="chat-result-card">
          <div className="chat-result-header">
            <p className="section-label">Query Results</p>
            <h3>Preview rows</h3>
          </div>
          <div className="table-preview">
            <table className="chat-data-table">
              <thead>
                <tr>
                  {getTableColumns(item.table).map((column) => (
                    <th key={column}>{column}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {item.table.map((row, rowIndex) => (
                  <tr key={`row-${item.id}-${rowIndex}`}>
                    {getTableColumns(item.table).map((column) => (
                      <td key={`${item.id}-${rowIndex}-${column}`}>{formatChatValue(row[column])}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )
    }

    return (
      <article
        key={item.id}
        className={`chat-step-card ${item.tone}`}
      >
        <div className="chat-step-header">
          <div>
            <p className="chat-step-kicker">{item.node ? item.node : 'agent step'}</p>
            <h3>{item.title}</h3>
          </div>
          <span className={`chat-step-pill ${item.tone}`}>{getChatStepToneLabel(item.tone)}</span>
        </div>
        <p className="chat-step-detail">{item.detail}</p>
      </article>
    )
  }

  return {
    chatBusy,
    chatInput,
    chatPlaceholder,
    chatTranscriptRef,
    preambleItems,
    promptGroups,
    collapsedPromptIds,
    selectedToolItem,
    selectedToolContext,
    selectedToolRequest,
    selectedToolResponse,
    setChatInput,
    handleClearChat,
    handleChatSubmit,
    handleDeletePromptGroup,
    togglePromptGroup,
    renderChatTranscriptItem,
  }
}
