import type { FormEventHandler, ReactNode, RefObject } from 'react'

import type {
  ChatDebugContextSnapshot,
  ChatDebugToolEvent,
  ChatPromptGroup,
  ChatThreadItem,
} from './types'
import { formatClockTime, formatDurationMs, formatTokenCount } from './utils'

type ChatWorkspaceTabProps = {
  chatBusy: boolean
  chatInput: string
  chatPlaceholder: string
  marcopoloAccessEnabled: boolean
  chatTranscriptRef: RefObject<HTMLDivElement | null>
  preambleItems: ChatThreadItem[]
  promptGroups: ChatPromptGroup[]
  collapsedPromptIds: string[]
  selectedToolItem: Extract<ChatThreadItem, { kind: 'tool' }> | null
  selectedToolContext: ChatDebugContextSnapshot | null
  selectedToolRequest: ChatDebugToolEvent | null
  selectedToolResponse: ChatDebugToolEvent | null
  onClearChat: () => void
  onChatSubmit: FormEventHandler<HTMLFormElement>
  onChatInputChange: (value: string) => void
  onTogglePromptGroup: (groupId: string) => void
  onDeletePromptGroup: (group: ChatPromptGroup) => void
  renderChatTranscriptItem: (item: ChatThreadItem) => ReactNode
}

export default function ChatWorkspaceTab({
  chatBusy,
  chatInput,
  chatPlaceholder,
  marcopoloAccessEnabled,
  chatTranscriptRef,
  preambleItems,
  promptGroups,
  collapsedPromptIds,
  selectedToolItem,
  selectedToolContext,
  selectedToolRequest,
  selectedToolResponse,
  onClearChat,
  onChatSubmit,
  onChatInputChange,
  onTogglePromptGroup,
  onDeletePromptGroup,
  renderChatTranscriptItem,
}: ChatWorkspaceTabProps) {
  return (
    <section className="chat-layout">
      <article className="panel chat-panel">
        <div className="panel-header">
          <div>
            <p className="section-label">Chatbot</p>
            <h2>LangGraph agent workspace</h2>
          </div>
          <button
            type="button"
            className="secondary-button"
            onClick={onClearChat}
            disabled={chatBusy}
          >
            Clear chat
          </button>
        </div>
        <div ref={chatTranscriptRef} className="chat-transcript">
          {preambleItems.map((item) => renderChatTranscriptItem(item))}
          {promptGroups.map((group) => {
            const collapsed = collapsedPromptIds.includes(group.id)

            return (
              <section key={group.id} className="chat-turn">
                <div className="chat-turn-header">
                  <button
                    type="button"
                    className="chat-turn-toggle"
                    onClick={() => onTogglePromptGroup(group.id)}
                  >
                    <span className="chat-turn-arrow">{collapsed ? '▶' : '▼'}</span>
                    <span className="chat-turn-prompt">{group.prompt.text}</span>
                    <span className={`chat-tool-status ${group.status}`}>{group.status}</span>
                  </button>
                  <button
                    type="button"
                    className="chat-turn-delete"
                    aria-label={`Delete prompt trace: ${group.prompt.text}`}
                    title="Delete prompt trace"
                    onClick={() => onDeletePromptGroup(group)}
                  >
                    ×
                  </button>
                </div>
                {!collapsed ? (
                  <div className="chat-turn-body">
                    {group.items.map((item) => renderChatTranscriptItem(item))}
                  </div>
                ) : null}
              </section>
            )
          })}
        </div>
        <form className="chat-composer" onSubmit={onChatSubmit}>
          <textarea
            rows={4}
            placeholder={chatPlaceholder}
            value={chatInput}
            onChange={(event) => onChatInputChange(event.target.value)}
            disabled={!marcopoloAccessEnabled || chatBusy}
          />
          <button type="submit" className="primary-button" disabled={!marcopoloAccessEnabled || chatBusy}>
            {chatBusy ? 'Running...' : 'Send'}
          </button>
        </form>
      </article>

      <aside className="panel debug-panel">
        <div className="panel-header">
          <p className="section-label">Tool inspector</p>
          <h2>Selected tool invocation</h2>
        </div>
        <div className="debug-pane-scroll">
          <div className="debug-list">
            {selectedToolItem ? (
              <article className="debug-card">
                <div className="debug-card-header">
                  <strong>{selectedToolItem.toolName}</strong>
                  <span className={`chat-tool-status ${selectedToolItem.status}`}>{selectedToolItem.status}</span>
                </div>
                <p>
                  Started {formatClockTime(selectedToolItem.startedAt)}
                  {selectedToolItem.durationMs !== undefined ? ` · Duration ${formatDurationMs(selectedToolItem.durationMs)}` : ''}
                  {selectedToolItem.tokenUsage?.total !== undefined ? ` · Tokens ${formatTokenCount(selectedToolItem.tokenUsage.total)}` : ''}
                </p>

                {selectedToolItem.tokenUsage ? (
                  <div className="debug-token-grid">
                    <div className="debug-token-card">
                      <small>Input tokens</small>
                      <strong>{formatTokenCount(selectedToolItem.tokenUsage.input)}</strong>
                    </div>
                    <div className="debug-token-card">
                      <small>Output tokens</small>
                      <strong>{formatTokenCount(selectedToolItem.tokenUsage.output)}</strong>
                    </div>
                    <div className="debug-token-card">
                      <small>Total tokens</small>
                      <strong>{formatTokenCount(selectedToolItem.tokenUsage.total)}</strong>
                    </div>
                  </div>
                ) : null}
                {selectedToolItem.tokenUsage?.source ? (
                  <p className="debug-token-note">
                    {selectedToolItem.tokenUsage.approximate ? 'Approximate' : 'Exact'} token usage from {selectedToolItem.tokenUsage.source}
                    {selectedToolItem.tokenUsage.sharedAcrossToolCalls && selectedToolItem.tokenUsage.sharedAcrossToolCalls > 1
                      ? ` · shared across ${selectedToolItem.tokenUsage.sharedAcrossToolCalls} tool calls`
                      : ''}
                  </p>
                ) : null}

                {selectedToolContext ? (
                  <details className="debug-details" open>
                    <summary>Context sent to the model around this tool call</summary>
                    <pre>{JSON.stringify(selectedToolContext, null, 2)}</pre>
                  </details>
                ) : null}

                {selectedToolRequest ? (
                  <details className="debug-details" open>
                    <summary>Tool request</summary>
                    <pre>{JSON.stringify(selectedToolRequest.arguments ?? {}, null, 2)}</pre>
                  </details>
                ) : null}

                {selectedToolResponse?.normalizedPayload !== undefined ? (
                  <details className="debug-details" open>
                    <summary>Normalized tool response</summary>
                    <pre>{JSON.stringify(selectedToolResponse.normalizedPayload, null, 2)}</pre>
                  </details>
                ) : null}

                {selectedToolResponse?.previewRows?.length ? (
                  <details className="debug-details">
                    <summary>Preview rows</summary>
                    <pre>{JSON.stringify(selectedToolResponse.previewRows, null, 2)}</pre>
                  </details>
                ) : null}

                {selectedToolResponse?.error ? <p className="debug-error">Error: {selectedToolResponse.error}</p> : null}
              </article>
            ) : (
              <div className="placeholder-row">
                <span>Inspector</span>
                <span className="pill pending">
                  Select a tool invocation row on the left
                </span>
              </div>
            )}
          </div>
        </div>
      </aside>
    </section>
  )
}
