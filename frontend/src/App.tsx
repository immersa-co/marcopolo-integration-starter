import { useEffect, useRef, useState } from 'react'
import './App.css'
import EmbeddedConnectionSetupHost from './EmbeddedConnectionSetupHost'

type TabId = 'configuration' | 'connections' | 'chatbot' | 'integrations'

type UserProfile = {
  provider?: string | null
  providerSubject?: string | null
  subject: string
  email?: string | null
  name?: string | null
  picture?: string | null
  hosted_domain?: string | null
  issuer?: string | null
  emailVerified?: boolean | null
}

type AuthSession = {
  authenticated: boolean
  configured: boolean
  provider?: string | null
  user?: UserProfile | null
  marcoPoloAuthMode: string
  marcoPoloAuthModeLabel: string
  marcoPoloAuthModeConfigured: boolean
  marcoPoloConfigured: boolean
  marcoPoloProvisioned: boolean
}

type RuntimeSkill = {
  name: string
  description: string
}

type ConnectionListItem = {
  name: string
  type: string
  displayName: string
  capabilities: string[]
  workspacePath?: string | null
}

type ConnectionListResponse = {
  authenticated: boolean
  source: string
  connections: ConnectionListItem[]
}

type DemoConnectionInstallResponse = {
  message: string
  connectionName: string
  displayName: string
  type: string
  demoConnectionId?: string | null
}

type EmbeddedConnectionSetupResponse = {
  resourceUri: string
  toolResult: Record<string, unknown>
  toolOutput: {
    type: string
    success?: boolean
    error?: string | null
    message?: string | null
    hint?: string | null
    resolution_mode?: string | null
    resolution_reason?: string | null
    suggested_types?: string[]
    company?: string | null
    workflow_type?: string | null
    url?: string | null
    instructions?: string[]
    next_actions?: string[]
  }
  widgetMeta: {
    ['marcopolo/widget']?: {
      api_token?: string
      api_base_url?: string
    }
  }
  statusUrl?: string | null
}

type ChatCreateResponse = {
  chatId: string
}

type ChatMessage = {
  role: 'assistant' | 'user' | 'status'
  text: string
}

type ChatResultKind = 'text' | 'table' | 'browse'

type ChatFinalPayload = {
  message: string
  resultKind?: ChatResultKind
  table: Array<Record<string, unknown>>
}

type DataConnectionOperation = {
  id: string
  title: string
  description: string
  prompt: string
  connectorType: string
}

type DataConnectionOperationsResponse = {
  examples: DataConnectionOperation[]
}

type DataConnectionOperationResponse = {
  exampleId: string
  title: string
  message: string
  connectionName: string
  connectionDisplayName: string
  connectionType: string
  queryName: string
  queryFile: string
  rowCount: number
  rows: Array<Record<string, unknown>>
}

type PublicConfig = {
  appEnv: string
  auth: {
    required: boolean
    configured: boolean
  }
  marcoPolo: {
    mcpUrl: string
    apiBaseUrl: string
    webBaseUrl: string
    authMode: string
    authModeLabel: string
    authModeDescription: string
    authModeConfigured: boolean
    browserBootstrapPath: string
    browserBootstrapRedirect: string
    availableAuthModes: Array<{
      key: string
      label: string
      description: string
      implemented: boolean
      configured: boolean
      requiredEnvVars: string[]
    }>
  }
  llm: {
    provider: string
    model: string
    apiBaseUrl: string
    apiKeyConfigured: boolean
  }
  skills: RuntimeSkill[]
}

const tabs: Array<{ id: TabId; label: string; eyebrow: string }> = [
  { id: 'configuration', label: 'Configuration', eyebrow: 'Runtime' },
  { id: 'connections', label: 'Connections', eyebrow: 'Setup' },
  { id: 'integrations', label: 'Integrations', eyebrow: 'SDK' },
  { id: 'chatbot', label: 'Chatbot', eyebrow: 'Agent' },
]

const initialChatMessages: ChatMessage[] = [
  {
    role: 'assistant',
    text: 'The chat runtime will stream LangGraph progress and final answers here once you submit a prompt against any visible MarcoPolo connection.',
  },
]

function App() {
  const [activeTab, setActiveTab] = useState<TabId>('connections')
  const [config, setConfig] = useState<PublicConfig | null>(null)
  const [session, setSession] = useState<AuthSession | null>(null)
  const [connections, setConnections] = useState<ConnectionListItem[]>([])
  const [configError, setConfigError] = useState<string | null>(null)
  const [sessionError, setSessionError] = useState<string | null>(null)
  const [connectionsError, setConnectionsError] = useState<string | null>(null)
  const [connectionActionMessage, setConnectionActionMessage] = useState<string | null>(null)
  const [demoInstallBusy, setDemoInstallBusy] = useState(false)
  const [embeddedSetupBusy, setEmbeddedSetupBusy] = useState(false)
  const [connectionsRefreshBusy, setConnectionsRefreshBusy] = useState(false)
  const [demoConnectionInput, setDemoConnectionInput] = useState('')
  const [newConnectionTypeInput, setNewConnectionTypeInput] = useState('')
  const [embeddedSetup, setEmbeddedSetup] = useState<EmbeddedConnectionSetupResponse | null>(null)
  const [dataConnectionOperations, setDataConnectionOperations] = useState<DataConnectionOperation[]>([])
  const [dataConnectionOperationResults, setDataConnectionOperationResults] = useState<Record<string, DataConnectionOperationResponse>>({})
  const [integrationBusyId, setIntegrationBusyId] = useState<string | null>(null)
  const [integrationError, setIntegrationError] = useState<string | null>(null)
  const [chatInput, setChatInput] = useState('')
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(initialChatMessages)
  const [chatTable, setChatTable] = useState<Array<Record<string, unknown>>>([])
  const [chatResultKind, setChatResultKind] = useState<ChatResultKind>('text')
  const [expandedChatItem, setExpandedChatItem] = useState<string | null>(null)
  const [chatBusy, setChatBusy] = useState(false)
  const [marcoPoloReady, setMarcoPoloReady] = useState(false)
  const [modeSelectionBusy, setModeSelectionBusy] = useState(false)
  const [impersonateBusy, setImpersonateBusy] = useState(false)
  const [impersonateEmail, setImpersonateEmail] = useState('')
  const chatTranscriptRef = useRef<HTMLDivElement | null>(null)
  const connectRedirectAttemptRef = useRef<string | null>(null)
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8001'
  const selectedMarcoPoloAuthMode = session?.marcoPoloAuthMode ?? config?.marcoPolo.authMode ?? 'developer_api_token'
  const usesWorkosConnect = selectedMarcoPoloAuthMode === 'workos_connect'
  const selectableMarcoPoloModes =
    config?.marcoPolo.availableAuthModes.filter((mode) => ['developer_api_token', 'workos_connect'].includes(mode.key)) ?? []
  const needsMarcoPoloAuthorization = Boolean(
    session?.authenticated && usesWorkosConnect && !session?.marcoPoloProvisioned,
  )
  const marcopoloAccessEnabled = Boolean(session?.authenticated && marcoPoloReady)
  const shouldGateApp = Boolean(config?.auth.required && !session?.authenticated)
  const availableChatConnectionNames = connections
    .map((connection) => connection.displayName)
    .filter((name, index, values) => values.indexOf(name) === index)
    .slice(0, 4)

  const chatPlaceholder = marcopoloAccessEnabled
    ? availableChatConnectionNames.length
      ? `Ask about any available connection, for example ${availableChatConnectionNames.join(', ')}.`
      : 'Ask about any available MarcoPolo connection.'
    : needsMarcoPoloAuthorization
      ? 'Completing MarcoPolo Connect sign-in.'
      : 'Sign in to enable chat.'

  async function loadRuntime(signal?: AbortSignal) {
    const [configResponse, sessionResponse] = await Promise.all([
      fetch(`${apiBaseUrl}/api/config/public`, {
        signal,
        credentials: 'include',
      }),
      fetch(`${apiBaseUrl}/api/auth/session`, {
        signal,
        credentials: 'include',
      }),
    ])

    if (!configResponse.ok) {
      throw new Error(`Config request failed with ${configResponse.status}`)
    }

    if (!sessionResponse.ok) {
      throw new Error(`Session request failed with ${sessionResponse.status}`)
    }

    setConfig((await configResponse.json()) as PublicConfig)
    setSession((await sessionResponse.json()) as AuthSession)
  }

  useEffect(() => {
    const controller = new AbortController()

    async function initializeRuntime() {
      try {
        await loadRuntime(controller.signal)
      } catch (error) {
        if ((error as Error).name === 'AbortError') {
          return
        }

        const message = (error as Error).message
        setConfigError(message)
        setSessionError(message)
      }
    }

    initializeRuntime()

    return () => controller.abort()
  }, [apiBaseUrl])

  useEffect(() => {
    const controller = new AbortController()

    async function loadDataConnectionOperations() {
      try {
        const response = await fetch(`${apiBaseUrl}/api/integrations/examples`, {
          signal: controller.signal,
          credentials: 'include',
        })
        if (!response.ok) {
          throw new Error(`Integration examples request failed with ${response.status}`)
        }
        const payload = (await response.json()) as DataConnectionOperationsResponse
        setDataConnectionOperations(payload.examples)
      } catch (error) {
        if ((error as Error).name === 'AbortError') {
          return
        }
        setIntegrationError((error as Error).message)
      }
    }

    loadDataConnectionOperations()

    return () => controller.abort()
  }, [apiBaseUrl])

  async function handleLogout() {
    try {
      const response = await fetch(`${apiBaseUrl}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error(`Logout failed with ${response.status}`)
      }

      setMarcoPoloReady(false)
      setDataConnectionOperationResults({})
      setIntegrationError(null)
      setImpersonateEmail('')
      setConnectionActionMessage(null)
      setSession((await response.json()) as AuthSession)
      await loadRuntime()
    } catch (error) {
      setSessionError((error as Error).message)
    }
  }

  async function handleMarcoPoloAuthModeChange(mode: string) {
    if (mode === selectedMarcoPoloAuthMode) {
      return
    }

    try {
      setModeSelectionBusy(true)
      setSessionError(null)
      setConnections([])
      setConnectionsError(null)
      setConnectionActionMessage(null)
      setIntegrationError(null)
      setDataConnectionOperationResults({})
      setMarcoPoloReady(false)

      const response = await fetch(`${apiBaseUrl}/api/auth/marcopolo/mode`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ mode }),
      })

      if (!response.ok) {
        let detail = ''
        try {
          const payload = (await response.json()) as { detail?: string }
          detail = typeof payload.detail === 'string' ? payload.detail : ''
        } catch {
          detail = ''
        }
        throw new Error(detail || `MarcoPolo auth mode update failed with ${response.status}`)
      }

      setSession((await response.json()) as AuthSession)
      await loadRuntime()
    } catch (error) {
      setSessionError((error as Error).message)
    } finally {
      setModeSelectionBusy(false)
    }
  }

  async function handleImpersonateSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const email = impersonateEmail.trim()
    if (!email) {
      setSessionError('Enter a test user email address.')
      return
    }

    try {
      setImpersonateBusy(true)
      setSessionError(null)
      setConnections([])
      setConnectionsError(null)
      setConnectionActionMessage(null)
      setIntegrationError(null)
      setDataConnectionOperationResults({})
      setMarcoPoloReady(false)

      const response = await fetch(`${apiBaseUrl}/api/auth/impersonate`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      })

      if (!response.ok) {
        let detail = ''
        try {
          const payload = (await response.json()) as { detail?: string }
          detail = typeof payload.detail === 'string' ? payload.detail : ''
        } catch {
          detail = ''
        }
        throw new Error(detail || `Impersonation failed with ${response.status}`)
      }

      setSession((await response.json()) as AuthSession)
      await loadRuntime()
    } catch (error) {
      setSessionError((error as Error).message)
    } finally {
      setImpersonateBusy(false)
    }
  }

  async function refreshConnections(signal?: AbortSignal) {
    if (!session?.authenticated) {
      setConnections([])
      setMarcoPoloReady(false)
      return
    }

    if (needsMarcoPoloAuthorization) {
      setConnections([])
      setConnectionsError(null)
      setMarcoPoloReady(false)
      return
    }

    const response = await fetch(`${apiBaseUrl}/api/connections`, {
      signal,
      credentials: 'include',
    })

    if (!response.ok) {
      let detail = ''
      try {
        const payload = (await response.json()) as { detail?: string }
        detail = typeof payload.detail === 'string' ? payload.detail : ''
      } catch {
        detail = ''
      }
      throw new Error(
        detail ? `Connections request failed: ${detail}` : `Connections request failed with ${response.status}`,
      )
    }

    const payload = (await response.json()) as ConnectionListResponse
    setConnections(payload.connections)
    setConnectionsError(null)
    setMarcoPoloReady(true)
  }

  useEffect(() => {
    const controller = new AbortController()

    refreshConnections(controller.signal).catch((error) => {
      if ((error as Error).name === 'AbortError') {
        return
      }

      setMarcoPoloReady(false)
      setConnectionsError((error as Error).message)
    })

    return () => controller.abort()
  }, [apiBaseUrl, needsMarcoPoloAuthorization, selectedMarcoPoloAuthMode, session?.authenticated])

  async function handleConnectionsRefresh() {
    try {
      setConnectionsRefreshBusy(true)
      setConnectionsError(null)
      await refreshConnections()
    } catch (error) {
      setMarcoPoloReady(false)
      setConnectionsError((error as Error).message)
    } finally {
      setConnectionsRefreshBusy(false)
    }
  }

  useEffect(() => {
    if (!session?.authenticated || !usesWorkosConnect || !needsMarcoPoloAuthorization) {
      connectRedirectAttemptRef.current = null
      return
    }
    if (!config?.marcoPolo.authModeConfigured) {
      return
    }

    const redirectKey = `${session.user?.subject ?? 'anonymous'}:${selectedMarcoPoloAuthMode}:${session.marcoPoloProvisioned ? 'ready' : 'pending'}`
    if (connectRedirectAttemptRef.current === redirectKey) {
      return
    }
    connectRedirectAttemptRef.current = redirectKey

    const returnTo = `${window.location.origin}${window.location.pathname}`
    window.location.href = `${apiBaseUrl}/api/auth/marcopolo/authorize?returnTo=${encodeURIComponent(returnTo)}`
  }, [
    apiBaseUrl,
    config?.marcoPolo.authModeConfigured,
    needsMarcoPoloAuthorization,
    selectedMarcoPoloAuthMode,
    session?.authenticated,
    session?.marcoPoloProvisioned,
    session?.user?.subject,
    usesWorkosConnect,
  ])

  useEffect(() => {
    const node = chatTranscriptRef.current
    if (!node) {
      return
    }

    node.scrollTo({
      top: node.scrollHeight,
      behavior: 'smooth',
    })
  }, [chatMessages, chatTable, chatResultKind])

  async function handleDemoInstallSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const demoConnection = demoConnectionInput.trim()
    if (!demoConnection) {
      setConnectionsError('Enter a demo connection type to install.')
      return
    }

    try {
      setDemoInstallBusy(true)
      setConnectionActionMessage(null)
      setConnectionsError(null)
      const response = await fetch(`${apiBaseUrl}/api/connections/demo-install`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ demoConnection }),
      })

      if (!response.ok) {
        let detail = ''
        try {
          const payload = (await response.json()) as { detail?: string }
          detail = typeof payload.detail === 'string' ? payload.detail : ''
        } catch {
          detail = ''
        }
        throw new Error(detail || `Demo install failed with ${response.status}`)
      }

      const payload = (await response.json()) as DemoConnectionInstallResponse
      setConnectionActionMessage(payload.message)
      await refreshConnections()
    } catch (error) {
      setConnectionsError((error as Error).message)
    } finally {
      setDemoInstallBusy(false)
    }
  }

  async function handleEmbeddedSetupSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const connectionType = newConnectionTypeInput.trim()
    if (!connectionType) {
      setConnectionsError('Enter a connection type to configure in the embedded setup host.')
      return
    }

    try {
      setEmbeddedSetupBusy(true)
      setConnectionActionMessage(null)
      setConnectionsError(null)
      const hostSessionId =
        typeof crypto !== 'undefined' && 'randomUUID' in crypto
          ? crypto.randomUUID()
          : `host-${Date.now()}`
      const response = await fetch(`${apiBaseUrl}/api/connections/setup/embedded`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          connectionType,
          hostOrigin: window.location.origin,
          hostReturnUrl: `${window.location.origin}/oauth-return`,
          hostSessionId,
        }),
      })

      if (!response.ok) {
        let detail = ''
        try {
          const payload = (await response.json()) as { detail?: string }
          detail = typeof payload.detail === 'string' ? payload.detail : ''
        } catch {
          detail = ''
        }
        throw new Error(detail || `Embedded setup request failed with ${response.status}`)
      }

      const payload = (await response.json()) as EmbeddedConnectionSetupResponse
      if (payload.toolOutput.success === false) {
        const suggestions = Array.isArray(payload.toolOutput.suggested_types)
          ? payload.toolOutput.suggested_types.filter((value) => typeof value === 'string' && value.trim()).slice(0, 6)
          : []
        const detail = [
          payload.toolOutput.error,
          payload.toolOutput.message,
          payload.toolOutput.hint,
          payload.toolOutput.resolution_reason,
        ]
          .filter((value): value is string => typeof value === 'string' && value.trim().length > 0)
          .join(' ')
        setEmbeddedSetup(null)
        throw new Error(
          suggestions.length
            ? `${detail} Suggested types: ${suggestions.join(', ')}.`
            : detail || 'MarcoPolo could not resolve that connection type.',
        )
      }
      setEmbeddedSetup(payload)
    } catch (error) {
      setConnectionsError((error as Error).message)
    } finally {
      setEmbeddedSetupBusy(false)
    }
  }

  async function handleInvokeDataConnectionOperation(exampleId: string) {
    try {
      setIntegrationBusyId(exampleId)
      setIntegrationError(null)
      const response = await fetch(`${apiBaseUrl}/api/integrations/run`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ exampleId }),
      })

      if (!response.ok) {
        let detail = ''
        try {
          const payload = (await response.json()) as { detail?: string }
          detail = typeof payload.detail === 'string' ? payload.detail : ''
        } catch {
          detail = ''
        }
        throw new Error(
          detail ? `SDK example failed: ${detail}` : `SDK example failed with ${response.status}`,
        )
      }

      const payload = (await response.json()) as DataConnectionOperationResponse
      setDataConnectionOperationResults((current) => ({
        ...current,
        [exampleId]: payload,
      }))
    } catch (error) {
      setIntegrationError((error as Error).message)
    } finally {
      setIntegrationBusyId(null)
    }
  }

  const activeEmbeddedConnectionType =
    typeof embeddedSetup?.toolOutput?.type === 'string' ? embeddedSetup.toolOutput.type : null
  const activeEmbeddedConnectionName =
    connections.find((item) => item.type === activeEmbeddedConnectionType)?.displayName

  const isOauthReturnPage = window.location.pathname === '/oauth-return'

  if (isOauthReturnPage) {
    return (
      <OAuthReturnBridge />
    )
  }

  async function handleChatSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!chatInput.trim()) {
      return
    }

    const message = chatInput.trim()
    setChatBusy(true)
    setChatTable([])
    setChatResultKind('text')
    setExpandedChatItem(null)
    setChatMessages((current) => [...current, { role: 'user', text: message }])
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

      eventSource.addEventListener('status', (event) => {
        const data = JSON.parse((event as MessageEvent).data) as { message: string }
        setChatMessages((current) => [...current, { role: 'status', text: data.message }])
      })

      eventSource.addEventListener('error', (event) => {
        let message = 'The chat stream ended before the agent returned a final response.'
        const raw = (event as MessageEvent).data
        if (typeof raw === 'string' && raw.trim()) {
          try {
            const data = JSON.parse(raw) as { message?: string }
            if (typeof data.message === 'string' && data.message.trim()) {
              message = data.message
            }
          } catch {
            message = raw
          }
        }
        setChatMessages((current) => [...current, { role: 'assistant', text: message }])
        setChatBusy(false)
        eventSource.close()
      })

      eventSource.addEventListener('final', (event) => {
        const data = JSON.parse((event as MessageEvent).data) as ChatFinalPayload
        setChatMessages((current) => [...current, { role: 'assistant', text: data.message }])
        setChatTable(data.table)
        setChatResultKind(data.resultKind ?? 'text')
        setExpandedChatItem(null)
        setChatBusy(false)
        eventSource.close()
      })
    } catch (error) {
      setChatMessages((current) => [
        ...current,
        { role: 'assistant', text: (error as Error).message },
      ])
      setChatBusy(false)
    }
  }

  function handleClearChat() {
    setChatMessages(initialChatMessages)
    setChatTable([])
    setChatResultKind('text')
    setExpandedChatItem(null)
    setChatInput('')
  }

  if (!config || !session) {
    return (
      <main className="app-shell">
        <section className="auth-page">
          <div className="auth-card">
            <p className="auth-brand">MarcoPolo Integration Demo</p>
            <p className="auth-copy">
              Access connection setup and agent workflows through MarcoPolo Integration Demo.
            </p>
            <p className="status-text">
              {configError || sessionError || 'Loading authentication state...'}
            </p>
          </div>
        </section>
      </main>
    )
  }

  if (shouldGateApp) {
    return (
      <main className="auth-page">
        <section className="auth-card">
          <div className="auth-header">
            <p className="auth-brand">MarcoPolo Integration Demo</p>
            <p className="auth-copy">
              Enter any email address and the demo will establish MarcoPolo access using the selected integration mode.
            </p>
          </div>
          {config ? (
            <div className="auth-mode-picker auth-mode-picker-gated">
              <p className="section-label">MarcoPolo auth mode</p>
              <div className="auth-mode-radio-list" role="radiogroup" aria-label="MarcoPolo auth mode">
                {selectableMarcoPoloModes.map((mode) => (
                  <label key={mode.key} className="auth-mode-radio">
                    <input
                      type="radio"
                      name="marcopolo-auth-mode-gated"
                      value={mode.key}
                      checked={selectedMarcoPoloAuthMode === mode.key}
                      onChange={() => void handleMarcoPoloAuthModeChange(mode.key)}
                      disabled={modeSelectionBusy || impersonateBusy}
                    />
                    <span>
                      <strong>{mode.label}</strong>
                      <small>{mode.configured ? 'configured' : 'missing required env'}</small>
                    </span>
                  </label>
                ))}
              </div>
              <p className="status-inline">{config.marcoPolo.authModeDescription}</p>
            </div>
          ) : null}
          <form className="auth-actions" onSubmit={handleImpersonateSubmit}>
            <label className="auth-field">
              <span>Email</span>
              <input
                type="email"
                name="email"
                placeholder="user@company.com"
                autoComplete="email"
                value={impersonateEmail}
                onChange={(event) => setImpersonateEmail(event.target.value)}
                disabled={impersonateBusy}
              />
            </label>
            <button type="submit" className="primary-button auth-submit" disabled={impersonateBusy}>
              {impersonateBusy ? 'Loading Test User…' : 'Test User'}
            </button>
          </form>
          {sessionError || configError ? (
            <p className="status-text auth-status">{sessionError || configError}</p>
          ) : null}
        </section>
      </main>
    )
  }

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <p className="kicker">Connect using MarcoPolo Token</p>
        <div className="hero-copy">
          <div>
            <h1>MarcoPolo Integration Demo</h1>
            <p className="lede">
            Configure MarcoPolo connections and integrate with data sources.
            </p>
          </div>
        </div>
      </section>

      <section className="session-strip panel">
        <div className="session-summary">
          <div>
            <p className="section-label">Identity</p>
            <h2>
              {session?.authenticated
                ? `Test user${session.user?.email ? ` ${session.user.email}` : ''}`
                : 'Authentication required'}
            </h2>
            <p className="session-detail">
              {session?.authenticated
                ? `${session.user?.email ?? 'No email entered'}${session.provider ? ` · ${session.provider}` : ''}`
                : 'Select a test user email to establish the demo app session.'}
            </p>
            {config ? (
              <div className="auth-mode-picker">
                <p className="section-label">MarcoPolo auth mode</p>
                <div className="auth-mode-radio-list" role="radiogroup" aria-label="MarcoPolo auth mode">
                  {selectableMarcoPoloModes.map((mode) => (
                    <label key={mode.key} className="auth-mode-radio">
                      <input
                        type="radio"
                        name="marcopolo-auth-mode"
                        value={mode.key}
                        checked={selectedMarcoPoloAuthMode === mode.key}
                        onChange={() => void handleMarcoPoloAuthModeChange(mode.key)}
                        disabled={modeSelectionBusy}
                      />
                      <span>
                        <strong>{mode.label}</strong>
                        <small>{mode.configured ? 'configured' : 'missing required env'}</small>
                      </span>
                    </label>
                  ))}
                </div>
                <p className="status-inline">
                  {config.marcoPolo.authModeDescription}
                </p>
              </div>
            ) : null}
          </div>
          <div className="session-actions">
            {session?.authenticated ? (
              <>
                <button type="button" className="secondary-button" onClick={handleLogout}>
                  Sign out
                </button>
              </>
            ) : (
              <></>
            )}
            {session?.authenticated && usesWorkosConnect && !session.marcoPoloProvisioned && config?.marcoPolo.authModeConfigured ? (
              <p className="status-text">Completing MarcoPolo Connect sign-in...</p>
            ) : null}
            {sessionError ? <p className="status-text">{sessionError}</p> : null}
          </div>
        </div>
      </section>

      <nav className="tab-nav" aria-label="Primary">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={tab.id === activeTab ? 'tab-button active' : 'tab-button'}
            onClick={() => setActiveTab(tab.id)}
          >
            <span>{tab.eyebrow}</span>
            <strong>{tab.label}</strong>
          </button>
        ))}
      </nav>

      {activeTab === 'configuration' ? (
        <section className="configuration-layout">
          <article className="panel">
            <div className="panel-header">
              <p className="section-label">Configuration</p>
              <h2>Runtime environment and integration status.</h2>
            </div>
            <div className="config-card config-card-panel">
              {config ? (
                <>
                  <dl>
                    <div>
                      <dt>Environment</dt>
                      <dd>{config.appEnv}</dd>
                    </div>
                    <div>
                      <dt>Demo identity</dt>
                      <dd>
                        Test user email / {config.auth.configured ? 'configured' : 'session config missing'}
                      </dd>
                    </div>
                    <div>
                      <dt>MarcoPolo auth</dt>
                      <dd>
                        {config.marcoPolo.authModeLabel} /{' '}
                        {config.marcoPolo.authModeConfigured ? 'configured' : 'missing mode secrets'}
                      </dd>
                    </div>
                    <div>
                      <dt>MarcoPolo MCP</dt>
                      <dd>{config.marcoPolo.mcpUrl}</dd>
                    </div>
                    <div>
                      <dt>MarcoPolo API</dt>
                      <dd>{config.marcoPolo.apiBaseUrl}</dd>
                    </div>
                    <div>
                      <dt>MarcoPolo web</dt>
                      <dd>{config.marcoPolo.webBaseUrl}</dd>
                    </div>
                    <div>
                      <dt>LLM</dt>
                      <dd>
                        {config.llm.provider} / {config.llm.model}
                      </dd>
                    </div>
                  </dl>
                  <div className="pill-row">
                    <span className={config.auth.configured ? 'pill ready' : 'pill pending'}>
                      {config.auth.configured ? 'Impersonation ready' : 'Session config missing'}
                    </span>
                    <span className={config.marcoPolo.authModeConfigured ? 'pill ready' : 'pill pending'}>
                      {config.marcoPolo.authModeConfigured
                        ? `${config.marcoPolo.authModeLabel} ready`
                        : `${config.marcoPolo.authModeLabel} incomplete`}
                    </span>
                    <span className={marcoPoloReady ? 'pill ready' : 'pill pending'}>
                      {marcoPoloReady ? 'MarcoPolo connected' : 'MarcoPolo pending'}
                    </span>
                    <span className={config.llm.apiKeyConfigured ? 'pill ready' : 'pill pending'}>
                      {config.llm.apiKeyConfigured ? 'LLM key configured' : 'LLM key missing'}
                    </span>
                    <span className={config.skills.length ? 'pill ready' : 'pill pending'}>
                      {config.skills.length} skills loaded
                    </span>
                  </div>
                  <div className="auth-mode-note">
                    <p className="status-inline">{config.marcoPolo.authModeDescription}</p>
                    <div className="auth-mode-list">
                      {config.marcoPolo.availableAuthModes.map((mode) => (
                        <div key={mode.key} className="auth-mode-row">
                          <strong>{mode.label}</strong>
                          <span>
                            {mode.key === config.marcoPolo.authMode ? 'Selected' : mode.implemented ? 'Available' : 'Placeholder'}
                            {' · '}
                            {mode.configured ? 'configured' : 'not configured'}
                          </span>
                          <p>{mode.description}</p>
                          <code>{mode.requiredEnvVars.join(', ')}</code>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <p className="status-text">
                  {configError ? `Config unavailable: ${configError}` : 'Loading runtime config...'}
                </p>
              )}
            </div>
          </article>
        </section>
      ) : activeTab === 'connections' ? (
        <section className="workspace-grid">
          <article className="panel">
            <div className="panel-header panel-header-split">
              <div>
                <p className="section-label">Setup actions</p>
                <h2>Install demo data or configure a real connection.</h2>
              </div>
              <button
                type="button"
                className="secondary-button panel-header-button"
                disabled={!session?.authenticated || needsMarcoPoloAuthorization || connectionsRefreshBusy}
                onClick={() => {
                  handleConnectionsRefresh().catch(() => undefined)
                }}
              >
                {connectionsRefreshBusy ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
            <div className="connector-list">
              {!marcopoloAccessEnabled ? (
                <div className="placeholder-row emphasis">
                  <span>MarcoPolo access</span>
                  <span className="pill pending">
                    {connectionsError ? 'Unavailable' : 'Checking access'}
                  </span>
                </div>
              ) : null}
              <form className="connector-card connector-form" onSubmit={handleDemoInstallSubmit}>
                <div className="connector-copy">
                  <h3>Install Demo Data</h3>
                  <p>Install a hosted demo connection into the current MarcoPolo workspace.</p>
                </div>
                <label className="auth-field">
                  <span>Demo connection type</span>
                  <input
                    type="text"
                    value={demoConnectionInput}
                    onChange={(event) => setDemoConnectionInput(event.target.value)}
                    placeholder="salesforce, aws_s3, snowflake, bigquery, mongodb"
                    disabled={!marcopoloAccessEnabled || demoInstallBusy}
                  />
                </label>
                <p className="status-inline">
                  Available demo connections: Salesforce, AWS S3, Snowflake, BigQuery, MongoDB.
                </p>
                <div className="connector-actions">
                  <button
                    type="submit"
                    className="primary-button"
                    disabled={!marcopoloAccessEnabled || demoInstallBusy}
                  >
                    {demoInstallBusy ? 'Installing...' : 'Install Demo Connection'}
                  </button>
                </div>
              </form>

              <form className="connector-card connector-form" onSubmit={handleEmbeddedSetupSubmit}>
                <div className="connector-copy">
                  <h3>Connect a Data Source</h3>
                  <p>Launch the embedded MarcoPolo connection setup app for any supported connector type.</p>
                </div>
                <label className="auth-field">
                  <span>Connection type</span>
                  <input
                    type="text"
                    value={newConnectionTypeInput}
                    onChange={(event) => setNewConnectionTypeInput(event.target.value)}
                    placeholder="jira, salesforce, github, postgres, snowflake, ..."
                    disabled={!marcopoloAccessEnabled || embeddedSetupBusy}
                  />
                </label>
                <p className="status-inline">
                  Enter any connection type supported by MarcoPolo. Review the supported connectors at
                  {' '}
                  <code>https://mcp.marcopolo.dev/app/connections/new</code>.
                </p>
                <div className="connector-actions">
                  <button
                    type="submit"
                    className="primary-button"
                    disabled={!marcopoloAccessEnabled || embeddedSetupBusy}
                  >
                    {embeddedSetupBusy ? 'Loading host...' : 'Connect In App'}
                  </button>
                </div>
              </form>
              {connectionActionMessage ? (
                <div className="placeholder-row emphasis">
                  <div>
                    <strong>Last action</strong>
                    <p className="status-inline">{connectionActionMessage}</p>
                  </div>
                  <span className="pill ready">Complete</span>
                </div>
              ) : null}
            </div>
            {embeddedSetup ? (
              <EmbeddedConnectionSetupHost
                apiBaseUrl={apiBaseUrl}
                marcoPoloWebBaseUrl={config.marcoPolo.webBaseUrl}
                payload={embeddedSetup}
                existingConnectionName={activeEmbeddedConnectionName}
                onClose={() => setEmbeddedSetup(null)}
                onRefreshConnections={async () => {
                  await refreshConnections()
                }}
              />
            ) : null}
          </article>

          <article className="panel">
            <div className="panel-header">
              <p className="section-label">Available connections</p>
              <h2>MarcoPolo `list_connections` dial tone.</h2>
            </div>
            <div className="placeholder-list">
              {connections.map((connection) => (
                <div key={connection.name} className="placeholder-row">
                  <div>
                    <strong>{connection.displayName}</strong>
                    <p className="status-inline">
                      {connection.type} · {connection.capabilities.join(', ')}
                    </p>
                  </div>
                  <span className="pill ready">Available</span>
                </div>
              ))}
              {!connections.length && !connectionsError && marcoPoloReady ? (
                <div className="placeholder-row">
                  <span>No connections</span>
                  <span className="pill pending">None available yet</span>
                </div>
              ) : null}
              {needsMarcoPoloAuthorization ? (
                <div className="placeholder-row emphasis">
                  <span>Connection status</span>
                  <span className="pill pending">Completing MarcoPolo Connect sign-in</span>
                </div>
              ) : null}
              {!needsMarcoPoloAuthorization && !marcoPoloReady && !connectionsError ? (
                <div className="placeholder-row">
                  <span>Connection status</span>
                  <span className="pill pending">Checking MarcoPolo access</span>
                </div>
              ) : null}
              {connectionsError ? (
                <div className="placeholder-row emphasis">
                  <span>Connection status</span>
                  <span className="pill pending">{connectionsError}</span>
                </div>
              ) : null}
            </div>
          </article>
        </section>
      ) : activeTab === 'integrations' ? (
        <section className="integrations-layout">
          <article className="panel">
            <div className="panel-header">
              <p className="section-label">Integrations</p>
              <h2>SDK-first examples for direct application code.</h2>
            </div>
            <p className="integration-copy">
              These examples call the published <code>marcopolo-sdk</code> from the backend, separate from the Chatbot and embedded MCP app flows.
            </p>
            <div className="integration-example-list">
              {dataConnectionOperations.map((example) => {
                const result = dataConnectionOperationResults[example.id]
                const busy = integrationBusyId === example.id
                return (
                  <article key={example.id} className="integration-card">
                    <div className="integration-card-copy">
                      <p className="section-label">Seed asset</p>
                      <h3>{example.title}</h3>
                      <p>{example.description}</p>
                      <button
                        type="button"
                        className="integration-prompt-button"
                        disabled={!marcopoloAccessEnabled || busy}
                        onClick={() => handleInvokeDataConnectionOperation(example.id)}
                      >
                        {busy ? 'Running SDK example…' : example.prompt}
                      </button>
                    </div>
                    {result ? (
                      <div className="integration-result-card">
                        <div className="integration-result-header">
                          <div>
                            <p className="section-label">Result</p>
                            <h4>{result.message}</h4>
                          </div>
                          <span className="pill ready">{result.rowCount} rows</span>
                        </div>
                        <div className="integration-meta">
                          <span><strong>Connection:</strong> {result.connectionDisplayName}</span>
                          <span><strong>Type:</strong> {result.connectionType}</span>
                          <span><strong>Query:</strong> {result.queryName}</span>
                        </div>
                        {result.rows.length ? (
                          <div className="table-preview">
                            <table className="chat-data-table">
                              <thead>
                                <tr>
                                  {getTableColumns(result.rows).map((column) => (
                                    <th key={`${example.id}-${column}`}>{column}</th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {result.rows.map((row, rowIndex) => (
                                  <tr key={`${example.id}-row-${rowIndex}`}>
                                    {getTableColumns(result.rows).map((column) => (
                                      <td key={`${example.id}-${rowIndex}-${column}`}>{formatChatValue(row[column])}</td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <div className="placeholder-row">
                            <span>Execution completed</span>
                            <span className="pill pending">No tabular rows returned</span>
                          </div>
                        )}
                      </div>
                    ) : null}
                  </article>
                )
              })}
            </div>
            {integrationError ? (
              <div className="placeholder-row emphasis">
                <span>Integration status</span>
                <span className="pill pending">{integrationError}</span>
              </div>
            ) : null}
            {!dataConnectionOperations.length && !integrationError ? (
              <div className="placeholder-row">
                <span>Integration examples</span>
                <span className="pill pending">Loading SDK examples</span>
              </div>
            ) : null}
            {!marcopoloAccessEnabled ? (
              <div className="placeholder-row emphasis">
                <span>SDK access</span>
                <span className="pill pending">
                  {needsMarcoPoloAuthorization ? 'Completing MarcoPolo Connect sign-in' : 'Sign in to run SDK examples'}
                </span>
              </div>
            ) : null}
          </article>
        </section>
      ) : (
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
                onClick={handleClearChat}
                disabled={chatBusy}
              >
                Clear chat
              </button>
            </div>
            <div ref={chatTranscriptRef} className="chat-transcript">
              {chatMessages.map((message, index) => (
                <div key={`${message.role}-${index}`} className={`bubble ${message.role}`}>
                  {message.text}
                </div>
              ))}
              {chatResultKind === 'browse' && chatTable.length ? (
                <div className="chat-result-card">
                  <div className="chat-result-header">
                    <p className="section-label">Browse Results</p>
                    <h3>Accessible folders and documents</h3>
                  </div>
                  <div className="browse-results">
                    {chatTable.map((row, index) => {
                      const itemKey = getBrowseItemKey(row, index)
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
              ) : null}
              {chatResultKind === 'table' && chatTable.length ? (
                <div className="chat-result-card">
                  <div className="chat-result-header">
                    <p className="section-label">Query Results</p>
                    <h3>Preview rows</h3>
                  </div>
                  <div className="table-preview">
                    <table className="chat-data-table">
                      <thead>
                        <tr>
                          {getTableColumns(chatTable).map((column) => (
                            <th key={column}>{column}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {chatTable.map((row, rowIndex) => (
                          <tr key={`row-${rowIndex}`}>
                            {getTableColumns(chatTable).map((column) => (
                              <td key={`${rowIndex}-${column}`}>{formatChatValue(row[column])}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : null}
            </div>
            <form className="chat-composer" onSubmit={handleChatSubmit}>
              <textarea
                rows={4}
                placeholder={chatPlaceholder}
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                disabled={!marcopoloAccessEnabled || chatBusy}
              />
              <button type="submit" className="primary-button" disabled={!marcopoloAccessEnabled || chatBusy}>
                {chatBusy ? 'Running...' : 'Send'}
              </button>
            </form>
          </article>

          <aside className="panel prompt-panel">
            <div className="panel-header">
              <p className="section-label">Seed assets</p>
              <h2>Prompt paths and loaded skills</h2>
            </div>
            <ul className="prompt-list">
              <li>Ask about any visible connection by naming it directly in your prompt.</li>
              <li>List open Jira issues assigned to the current user.</li>
              <li>Show the highest-priority Jira tickets that need attention this week.</li>
              <li>List top 5 customer accounts by revenue from Salesforce.</li>
              <li>Display all errors over past 24 hours from Grafana-Loki.</li>
              {config?.skills.map((skill) => (
                <li key={skill.name}>
                  <strong>{skill.name}</strong>: {skill.description || 'No description provided.'}
                </li>
              ))}
            </ul>
          </aside>
        </section>
      )}
    </main>
  )
}

export default App

function getTableColumns(rows: Array<Record<string, unknown>>): string[] {
  const columns = new Set<string>()
  rows.forEach((row) => {
    Object.keys(row).forEach((key) => columns.add(key))
  })
  return Array.from(columns).slice(0, 8)
}

function getBrowseItemKey(row: Record<string, unknown>, index: number): string {
  const candidate =
    row.id ??
    row.path ??
    row.workspace_path ??
    row.name ??
    row.title
  return typeof candidate === 'string' && candidate ? candidate : `browse-item-${index}`
}

function getBrowseItemTitle(row: Record<string, unknown>, index: number): string {
  const candidate = row.name ?? row.title ?? row.path ?? row.workspace_path
  return typeof candidate === 'string' && candidate ? candidate : `Item ${index + 1}`
}

function getBrowseItemSubtitle(row: Record<string, unknown>): string {
  const parts = [
    typeof row.path === 'string' ? row.path : null,
    typeof row.mimeType === 'string' ? row.mimeType : null,
    typeof row.modifiedTime === 'string' ? `Modified ${row.modifiedTime}` : null,
    typeof row.size === 'number' || typeof row.size === 'string' ? `Size ${row.size}` : null,
  ].filter((value): value is string => Boolean(value))

  return parts.join(' · ') || 'Open to inspect the returned metadata.'
}

function getBrowseItemLink(row: Record<string, unknown>): string | null {
  const candidates = [row.webViewLink, row.url, row.link, row.web_url]
  for (const candidate of candidates) {
    if (typeof candidate === 'string' && /^https?:\/\//.test(candidate)) {
      return candidate
    }
  }
  return null
}

function getBrowseItemKind(row: Record<string, unknown>): 'folder' | 'file' {
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

function formatChatValue(value: unknown): string {
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

function OAuthReturnBridge() {
  const [message, setMessage] = useState('Returning control to MarcoPolo Integration Demo…')

  useEffect(() => {
    const payload = {
      type: 'marcopolo.connection_setup.complete',
      setup_session_id: new URLSearchParams(window.location.search).get('setup_session_id'),
      status: new URLSearchParams(window.location.search).get('status'),
      connection_name: new URLSearchParams(window.location.search).get('connection_name'),
    }

    try {
      if (window.opener && !window.opener.closed) {
        window.opener.postMessage(payload, window.location.origin)
        setMessage('OAuth completed. Closing this window…')
        window.close()
        return
      }
    } catch {
      // Fall through to root redirect when opener signaling is unavailable.
    }

    const timer = window.setTimeout(() => {
      window.location.replace('/')
    }, 1200)

    return () => {
      window.clearTimeout(timer)
    }
  }, [])

  return (
    <main className="auth-page">
      <section className="auth-card">
        <p className="auth-brand">MarcoPolo Integration Demo</p>
        <h1>Completing sign-in</h1>
        <p className="auth-copy">{message}</p>
      </section>
    </main>
  )
}
