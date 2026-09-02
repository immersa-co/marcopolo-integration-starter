import { useEffect, useRef, useState } from 'react'
import type { FormEventHandler } from 'react'

type OAuthConnectionTypeOption = {
  type: string
  displayName: string
  category?: string | null
}

type OAuthSetupSession = {
  setupSessionId: string
  status: 'pending' | 'ready' | 'failed'
  connectionType: string
  connectionName: string
  displayName: string
  expiresAt: string
  failureCode?: string | null
  failureMessage?: string | null
}

type OAuthSetupStart = OAuthSetupSession & {
  authorizationUrl: string
  returnUrl?: string | null
}

type ConnectionTestResult = {
  connectionName: string
  status: string
  message: string
  latencyMs: number
}

type SdkOAuthSetupPanelProps = {
  apiBaseUrl: string
  marcopoloAccessEnabled: boolean
  onConnectionsRefresh: () => Promise<void> | void
}

const POLL_INTERVAL_MS = 2500

export default function SdkOAuthSetupPanel({
  apiBaseUrl,
  marcopoloAccessEnabled,
  onConnectionsRefresh,
}: SdkOAuthSetupPanelProps) {
  const [typeOptions, setTypeOptions] = useState<OAuthConnectionTypeOption[]>([])
  const [typeOptionsError, setTypeOptionsError] = useState<string | null>(null)
  const [selectedType, setSelectedType] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [busy, setBusy] = useState(false)
  const [setupError, setSetupError] = useState<string | null>(null)
  const [session, setSession] = useState<OAuthSetupSession | null>(null)
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null)
  const [testBusy, setTestBusy] = useState(false)
  const clientSessionIdRef = useRef(`demo-${Math.random().toString(36).slice(2, 12)}`)
  const popupRef = useRef<Window | null>(null)
  const pollTimerRef = useRef<number | null>(null)

  useEffect(() => {
    if (!marcopoloAccessEnabled) {
      return
    }
    const controller = new AbortController()
    async function loadTypes() {
      try {
        const response = await fetch(`${apiBaseUrl}/api/connections/oauth-types`, {
          credentials: 'include',
          signal: controller.signal,
        })
        if (!response.ok) {
          throw new Error(`OAuth type list failed with ${response.status}`)
        }
        const body = (await response.json()) as { connectionTypes: OAuthConnectionTypeOption[] }
        setTypeOptions(body.connectionTypes)
        setTypeOptionsError(null)
      } catch (error) {
        if ((error as Error).name !== 'AbortError') {
          setTypeOptionsError((error as Error).message)
        }
      }
    }
    loadTypes()
    return () => controller.abort()
  }, [apiBaseUrl, marcopoloAccessEnabled])

  async function pollSession(setupSessionId: string) {
    const response = await fetch(
      `${apiBaseUrl}/api/connections/oauth-setup/${encodeURIComponent(setupSessionId)}`,
      { credentials: 'include' },
    )
    if (!response.ok) {
      throw new Error(`Setup session lookup failed with ${response.status}`)
    }
    const body = (await response.json()) as OAuthSetupSession
    setSession(body)
    if (body.status !== 'pending') {
      stopPolling()
      if (popupRef.current && !popupRef.current.closed) {
        popupRef.current.close()
      }
      if (body.status === 'ready') {
        await onConnectionsRefresh()
      }
    }
    return body
  }

  function stopPolling() {
    if (pollTimerRef.current !== null) {
      window.clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }

  function startPolling(setupSessionId: string) {
    stopPolling()
    pollTimerRef.current = window.setInterval(() => {
      pollSession(setupSessionId).catch((error) => {
        stopPolling()
        setSetupError((error as Error).message)
      })
    }, POLL_INTERVAL_MS)
  }

  useEffect(() => {
    // host-complete posts this from the MarcoPolo origin (popup flow), and the
    // demo's own /oauth-return bridge posts it after a full-redirect fallback.
    // The message is only a wake-up: session state always comes from the
    // backend, so the origin does not need to be trusted.
    function onMessage(event: MessageEvent) {
      const data = event.data as { type?: string; setup_session_id?: string } | null
      if (data?.type !== 'marcopolo.connection_setup.complete') {
        return
      }
      const setupSessionId = data.setup_session_id ?? session?.setupSessionId
      if (setupSessionId) {
        pollSession(setupSessionId).catch((error) => setSetupError((error as Error).message))
      }
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  })

  useEffect(() => () => stopPolling(), [])

  const handleSubmit: FormEventHandler<HTMLFormElement> = async (event) => {
    event.preventDefault()
    if (!selectedType) {
      setSetupError('Choose a connection type first.')
      return
    }
    setBusy(true)
    setSetupError(null)
    setTestResult(null)
    setSession(null)
    try {
      const response = await fetch(`${apiBaseUrl}/api/connections/oauth-setup`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          connectionType: selectedType,
          displayName:
            displayName.trim() ||
            (typeOptions.find((option) => option.type === selectedType)?.displayName ?? selectedType),
          clientSessionId: clientSessionIdRef.current,
        }),
      })
      const body = await response.json()
      if (!response.ok) {
        throw new Error(String(body?.detail ?? `Setup start failed with ${response.status}`))
      }
      const started = body as OAuthSetupStart
      setSession(started)
      popupRef.current = window.open(
        started.authorizationUrl,
        'marcopolo-oauth-setup',
        'popup,width=720,height=780',
      )
      if (!popupRef.current) {
        // Popup blocked: authorize in this tab; the /oauth-return bridge
        // redirects back to the app root afterwards.
        window.location.href = started.authorizationUrl
        return
      }
      startPolling(started.setupSessionId)
    } catch (error) {
      setSetupError((error as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function handleTestConnection() {
    if (!session || session.status !== 'ready') {
      return
    }
    setTestBusy(true)
    setTestResult(null)
    try {
      const response = await fetch(
        `${apiBaseUrl}/api/connections/${encodeURIComponent(session.connectionName)}/test`,
        { method: 'POST', credentials: 'include' },
      )
      const body = await response.json()
      if (!response.ok) {
        throw new Error(String(body?.detail ?? `Connection test failed with ${response.status}`))
      }
      setTestResult(body as ConnectionTestResult)
    } catch (error) {
      setSetupError((error as Error).message)
    } finally {
      setTestBusy(false)
    }
  }

  const statusPill =
    session?.status === 'ready' ? (
      <span className="pill ready">Ready</span>
    ) : session?.status === 'failed' ? (
      <span className="pill pending">Failed</span>
    ) : session ? (
      <span className="pill pending">Waiting for authorization…</span>
    ) : null

  return (
    <form className="connector-card connector-form" onSubmit={handleSubmit}>
      <div className="connector-copy">
        <h3>Connect via OAuth (Python SDK)</h3>
        <p>
          Start a hosted setup session through the versioned API, authorize at the provider in a
          popup, and watch the session until the connection is ready.
        </p>
      </div>
      <label className="auth-field">
        <span>OAuth connection type</span>
        <select
          value={selectedType}
          onChange={(event) => setSelectedType(event.target.value)}
          disabled={!marcopoloAccessEnabled || busy}
        >
          <option value="">Choose a provider…</option>
          {typeOptions.map((option) => (
            <option key={option.type} value={option.type}>
              {option.displayName} ({option.type})
            </option>
          ))}
        </select>
      </label>
      <label className="auth-field">
        <span>Display name (optional)</span>
        <input
          type="text"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          placeholder="My GitHub"
          disabled={!marcopoloAccessEnabled || busy}
        />
      </label>
      {typeOptionsError ? <p className="status-inline">{typeOptionsError}</p> : null}
      <div className="connector-actions">
        <button
          type="submit"
          className="primary-button"
          disabled={!marcopoloAccessEnabled || busy || !selectedType}
        >
          {busy ? 'Starting…' : 'Connect via OAuth'}
        </button>
        {session?.status === 'ready' ? (
          <button
            type="button"
            className="secondary-button"
            onClick={handleTestConnection}
            disabled={testBusy}
          >
            {testBusy ? 'Testing…' : 'Test connection'}
          </button>
        ) : null}
      </div>
      {session ? (
        <div className="placeholder-row emphasis">
          <div>
            <strong>{session.displayName}</strong>
            <p className="status-inline">
              {session.status === 'ready'
                ? `Connection ${session.connectionName} is ready to use.`
                : session.status === 'failed'
                  ? `${session.failureCode ?? 'setup_failed'}: ${session.failureMessage ?? 'Setup failed.'}`
                  : `Session ${session.setupSessionId} · complete the provider authorization in the popup.`}
            </p>
          </div>
          {statusPill}
        </div>
      ) : null}
      {testResult ? (
        <div className="placeholder-row emphasis">
          <div>
            <strong>Connection test</strong>
            <p className="status-inline">
              {testResult.status} · {testResult.message} · {testResult.latencyMs}ms
            </p>
          </div>
          <span className={`pill ${testResult.status === 'succeeded' ? 'ready' : 'pending'}`}>
            {testResult.status}
          </span>
        </div>
      ) : null}
      {setupError ? <p className="status-inline">{setupError}</p> : null}
    </form>
  )
}
