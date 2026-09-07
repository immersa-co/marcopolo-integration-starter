import { useEffect, useMemo, useRef, useState } from 'react'

import type {
  ConnectionSetupField,
  ConnectionTestResult,
  ManagedConnectionResponse,
} from '../app/types'

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

type ManageConnectionDialogProps = {
  apiBaseUrl: string
  connectionName: string | null
  onClose: () => void
  onConnectionsRefresh: () => Promise<void> | void
}

const POLL_INTERVAL_MS = 2500

export default function ManageConnectionDialog({
  apiBaseUrl,
  connectionName,
  onClose,
  onConnectionsRefresh,
}: ManageConnectionDialogProps) {
  const [managedConnection, setManagedConnection] = useState<ManagedConnectionResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [displayName, setDisplayName] = useState('')
  const [shareWithCompany, setShareWithCompany] = useState(false)
  const [fieldValues, setFieldValues] = useState<Record<string, unknown>>({})
  const [submitBusy, setSubmitBusy] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [oauthSession, setOauthSession] = useState<OAuthSetupSession | null>(null)
  const [testBusy, setTestBusy] = useState(false)
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null)
  const popupRef = useRef<Window | null>(null)
  const pollTimerRef = useRef<number | null>(null)
  const clientSessionIdRef = useRef(`manage-${Math.random().toString(36).slice(2, 12)}`)

  const currentMethod = useMemo(() => {
    if (!managedConnection) {
      return null
    }
    const setupMethods = managedConnection.connectionTypeDetail.setupMethods
    const suggested = managedConnection.suggestedSetupMethod
    return (
      setupMethods.find((method) => method.method === suggested)
      ?? setupMethods.find((method) => method.kind === 'fields')
      ?? setupMethods[0]
      ?? null
    )
  }, [managedConnection])

  const editableFields = useMemo(
    () =>
      currentMethod
        ? currentMethod.fields.filter((field) => !field.secret && isSupportedField(field))
        : [],
    [currentMethod],
  )

  const secretFields = useMemo(
    () => (currentMethod ? currentMethod.fields.filter((field) => field.secret) : []),
    [currentMethod],
  )

  const unsupportedFields = useMemo(
    () =>
      currentMethod
        ? currentMethod.fields.filter((field) => !field.secret && !isSupportedField(field))
        : [],
    [currentMethod],
  )

  useEffect(() => {
    if (!connectionName) {
      return
    }
    const controller = new AbortController()
    setBusy(true)
    setError(null)
    setSubmitError(null)
    setOauthSession(null)
    setTestResult(null)
    fetch(`${apiBaseUrl}/api/connections/${encodeURIComponent(connectionName)}`, {
      credentials: 'include',
      signal: controller.signal,
    })
      .then(async (response) => {
        const body = (await response.json()) as ManagedConnectionResponse | { detail?: string }
        if (!response.ok) {
          throw new Error(
            typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string'
              ? body.detail
              : `Connection load failed with ${response.status}`,
          )
        }
        const resolved = body as ManagedConnectionResponse
        setManagedConnection(resolved)
        setDisplayName(resolved.connection.displayName)
        setShareWithCompany(resolved.connection.sharedWithCompany)
        setFieldValues(buildEditFieldValues(resolved))
      })
      .catch((fetchError) => {
        if ((fetchError as Error).name !== 'AbortError') {
          setError((fetchError as Error).message)
          setManagedConnection(null)
        }
      })
      .finally(() => setBusy(false))

    return () => controller.abort()
  }, [apiBaseUrl, connectionName])

  useEffect(() => {
    function onMessage(event: MessageEvent) {
      const data = event.data as { type?: string; setup_session_id?: string } | null
      if (data?.type !== 'marcopolo.connection_setup.complete') {
        return
      }
      const setupSessionId = data.setup_session_id ?? oauthSession?.setupSessionId
      if (!setupSessionId) {
        return
      }
      void pollSession(setupSessionId)
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [oauthSession?.setupSessionId])

  useEffect(() => () => stopPolling(), [])

  if (!connectionName) {
    return null
  }

  function stopPolling() {
    if (pollTimerRef.current !== null) {
      window.clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }

  function handleClose() {
    stopPolling()
    if (popupRef.current && !popupRef.current.closed) {
      popupRef.current.close()
    }
    popupRef.current = null
    onClose()
  }

  function updateFieldValue(fieldName: string, value: unknown) {
    setFieldValues((current) => ({ ...current, [fieldName]: value }))
  }

  async function pollSession(setupSessionId: string) {
    const response = await fetch(
      `${apiBaseUrl}/api/connections/oauth-setup/${encodeURIComponent(setupSessionId)}`,
      { credentials: 'include' },
    )
    const body = (await response.json()) as OAuthSetupSession | { detail?: string }
    if (!response.ok) {
      throw new Error(
        typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string'
          ? body.detail
          : `Setup session lookup failed with ${response.status}`,
      )
    }
    const session = body as OAuthSetupSession
    setOauthSession(session)
    if (session.status !== 'pending') {
      stopPolling()
      if (popupRef.current && !popupRef.current.closed) {
        popupRef.current.close()
      }
      popupRef.current = null
      if (session.status === 'ready') {
        await onConnectionsRefresh()
      }
    }
  }

  function startPolling(setupSessionId: string) {
    stopPolling()
    pollTimerRef.current = window.setInterval(() => {
      void pollSession(setupSessionId).catch((pollError) => {
        stopPolling()
        setSubmitError((pollError as Error).message)
      })
    }, POLL_INTERVAL_MS)
  }

  async function handleSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!managedConnection) {
      return
    }

    try {
      setSubmitBusy(true)
      setSubmitError(null)
      const response = await fetch(
        `${apiBaseUrl}/api/connections/${encodeURIComponent(managedConnection.connection.name)}`,
        {
          method: 'PATCH',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            displayName: displayName.trim(),
            configurationPatch: serializeFields(editableFields, fieldValues),
            shareWithCompany,
          }),
        },
      )
      const body = (await response.json()) as ManagedConnectionResponse | { detail?: string }
      if (!response.ok) {
        throw new Error(
          typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string'
            ? body.detail
            : `Connection update failed with ${response.status}`,
        )
      }
      const updated = body as ManagedConnectionResponse
      setManagedConnection(updated)
      setDisplayName(updated.connection.displayName)
      setShareWithCompany(updated.connection.sharedWithCompany)
      setFieldValues(buildEditFieldValues(updated))
      await onConnectionsRefresh()
    } catch (saveError) {
      setSubmitError((saveError as Error).message)
    } finally {
      setSubmitBusy(false)
    }
  }

  async function handleDelete() {
    if (!managedConnection) {
      return
    }
    if (!window.confirm(`Delete connection "${managedConnection.connection.displayName}"?`)) {
      return
    }
    try {
      setSubmitBusy(true)
      setSubmitError(null)
      const response = await fetch(
        `${apiBaseUrl}/api/connections/${encodeURIComponent(managedConnection.connection.name)}`,
        {
          method: 'DELETE',
          credentials: 'include',
        },
      )
      const body = (await response.json()) as { detail?: string }
      if (!response.ok) {
        throw new Error(typeof body.detail === 'string' ? body.detail : `Delete failed with ${response.status}`)
      }
      await onConnectionsRefresh()
      handleClose()
    } catch (deleteError) {
      setSubmitError((deleteError as Error).message)
    } finally {
      setSubmitBusy(false)
    }
  }

  async function handleReauthorize() {
    if (!managedConnection) {
      return
    }
    try {
      setSubmitBusy(true)
      setSubmitError(null)
      const response = await fetch(
        `${apiBaseUrl}/api/connections/${encodeURIComponent(managedConnection.connection.name)}/reauthorize`,
        {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ clientSessionId: clientSessionIdRef.current }),
        },
      )
      const body = (await response.json()) as OAuthSetupStart | { detail?: string }
      if (!response.ok) {
        throw new Error(
          typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string'
            ? body.detail
            : `Re-authorization failed with ${response.status}`,
        )
      }
      const started = body as OAuthSetupStart
      setOauthSession(started)
      popupRef.current = window.open(
        started.authorizationUrl,
        'marcopolo-oauth-reauthorize',
        'popup,width=720,height=780',
      )
      if (!popupRef.current) {
        window.location.href = started.authorizationUrl
        return
      }
      startPolling(started.setupSessionId)
    } catch (reauthError) {
      setSubmitError((reauthError as Error).message)
    } finally {
      setSubmitBusy(false)
    }
  }

  async function handleTestConnection() {
    if (!managedConnection) {
      return
    }
    try {
      setTestBusy(true)
      setSubmitError(null)
      const response = await fetch(
        `${apiBaseUrl}/api/connections/${encodeURIComponent(managedConnection.connection.name)}/test`,
        {
          method: 'POST',
          credentials: 'include',
        },
      )
      const body = (await response.json()) as ConnectionTestResult | { detail?: string }
      if (!response.ok) {
        throw new Error(
          typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string'
            ? body.detail
            : `Connection test failed with ${response.status}`,
        )
      }
      setTestResult(body as ConnectionTestResult)
    } catch (testError) {
      setSubmitError((testError as Error).message)
    } finally {
      setTestBusy(false)
    }
  }

  return (
    <div className="dialog-overlay" role="presentation" onClick={handleClose}>
      <section
        className="dialog-card connection-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Manage connection"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="dialog-header">
          <div>
            <p className="section-label">Connections</p>
            <h2>Manage Connection</h2>
          </div>
          <button type="button" className="secondary-button" onClick={handleClose}>
            Close
          </button>
        </div>

        {busy ? <p className="status-inline">Loading connection details…</p> : null}
        {error ? <p className="status-inline">{error}</p> : null}

        {managedConnection ? (
          <form className="connection-dialog-column" onSubmit={handleSave}>
            <div className="connection-detail-header">
              <div>
                <h3>{managedConnection.connection.displayName}</h3>
                <p className="status-inline">
                  {managedConnection.connection.type}
                  {managedConnection.connection.category ? ` · ${managedConnection.connection.category}` : ''}
                  {managedConnection.connection.authMethod ? ` · ${managedConnection.connection.authMethod}` : ''}
                </p>
              </div>
              <span className={managedConnection.connection.canManage ? 'pill ready' : 'pill pending'}>
                {managedConnection.connection.canManage ? 'Manageable' : 'Read only'}
              </span>
            </div>

            <label className="auth-field">
              <span>Display name</span>
              <input
                type="text"
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                disabled={!managedConnection.connection.canManage}
              />
            </label>

            <label className="auth-field">
              <span>Share with Entire Company</span>
              <input
                type="checkbox"
                checked={shareWithCompany}
                onChange={(event) => setShareWithCompany(event.target.checked)}
                disabled={!managedConnection.connection.canManage}
              />
              <p className="status-inline">
                {shareWithCompany
                  ? 'This connection is shared with the entire MarcoPolo company.'
                  : 'This connection is currently private to the owner unless shared separately with specific users.'}
              </p>
            </label>

            {currentMethod ? (
              <div className="connection-method-card">
                <div className="connection-method-header">
                  <div>
                    <strong>{currentMethod.displayName}</strong>
                    <p className="status-inline">
                      {currentMethod.kind}
                      {currentMethod.description ? ` · ${currentMethod.description}` : ''}
                    </p>
                  </div>
                </div>

                {editableFields.map((field) => (
                  <FieldInput
                    key={field.name}
                    field={field}
                    value={fieldValues[field.name]}
                    onChange={(value) => updateFieldValue(field.name, value)}
                  />
                ))}

                {secretFields.length ? (
                  <p className="status-inline">
                    Secret fields are write-only in the current SDK patch flow and are not editable here:
                    {' '}
                    {secretFields.map((field) => field.name).join(', ')}.
                  </p>
                ) : null}

                {unsupportedFields.length ? (
                  <p className="status-inline">
                    Some configuration fields are not editable in this demo yet:
                    {' '}
                    {unsupportedFields.map((field) => `${field.name} (${field.type})`).join(', ')}.
                  </p>
                ) : null}
              </div>
            ) : null}

            <div className="connector-actions">
              <button
                type="submit"
                className="primary-button"
                disabled={!managedConnection.connection.canManage || submitBusy}
              >
                {submitBusy ? 'Saving…' : 'Save changes'}
              </button>
              <button
                type="button"
                className="secondary-button"
                disabled={testBusy}
                onClick={() => {
                  void handleTestConnection()
                }}
              >
                {testBusy ? 'Testing…' : 'Test connection'}
              </button>
              {managedConnection.supportsReauthorize ? (
                <button
                  type="button"
                  className="secondary-button"
                  disabled={submitBusy}
                  onClick={() => {
                    void handleReauthorize()
                  }}
                >
                  Re-authorize OAuth
                </button>
              ) : null}
              <button
                type="button"
                className="secondary-button"
                disabled={!managedConnection.connection.canManage || submitBusy}
                onClick={() => {
                  void handleDelete()
                }}
              >
                Delete connection
              </button>
            </div>

            {oauthSession ? (
              <div className="placeholder-row emphasis">
                <div>
                  <strong>{oauthSession.displayName}</strong>
                  <p className="status-inline">
                    {oauthSession.status === 'ready'
                      ? `Connection ${oauthSession.connectionName} is ready to use.`
                      : oauthSession.status === 'failed'
                        ? `${oauthSession.failureCode ?? 'setup_failed'}: ${oauthSession.failureMessage ?? 'Setup failed.'}`
                        : `Session ${oauthSession.setupSessionId} is waiting for provider authorization.`}
                  </p>
                </div>
                <span className={oauthSession.status === 'ready' ? 'pill ready' : 'pill pending'}>
                  {oauthSession.status}
                </span>
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
                <span className={testResult.status === 'succeeded' ? 'pill ready' : 'pill pending'}>
                  {testResult.status}
                </span>
              </div>
            ) : null}

            {submitError ? <p className="status-inline">{submitError}</p> : null}
          </form>
        ) : null}
      </section>
    </div>
  )
}

function buildEditFieldValues(managedConnection: ManagedConnectionResponse) {
  const values: Record<string, unknown> = {}
  const suggestedMethod = managedConnection.suggestedSetupMethod
  const currentMethod = managedConnection.connectionTypeDetail.setupMethods.find(
    (method) => method.method === suggestedMethod,
  ) ?? managedConnection.connectionTypeDetail.setupMethods.find((method) => method.kind === 'fields')

  for (const field of currentMethod?.fields ?? []) {
    if (field.secret) {
      continue
    }
    if (Object.prototype.hasOwnProperty.call(managedConnection.configuration, field.name)) {
      values[field.name] = managedConnection.configuration[field.name]
      continue
    }
    if (field.default !== undefined && field.default !== null) {
      values[field.name] = field.default
      continue
    }
    if (field.type === 'boolean') {
      values[field.name] = false
      continue
    }
    if (field.type === 'array') {
      values[field.name] = []
      continue
    }
    values[field.name] = ''
  }
  return values
}

function FieldInput({
  field,
  value,
  onChange,
}: {
  field: ConnectionSetupField
  value: unknown
  onChange: (value: unknown) => void
}) {
  const fieldLabel = field.label || field.name
  const choiceOptions = field.choices ?? []

  if (field.type === 'boolean') {
    return (
      <label className="auth-field">
        <span>{fieldLabel}</span>
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(event) => onChange(event.target.checked)}
        />
        <FieldHelp field={field} />
      </label>
    )
  }

  if (field.type === 'array') {
    return (
      <label className="auth-field">
        <span>{fieldLabel}</span>
        <textarea
          value={Array.isArray(value) ? value.map((item) => String(item)).join('\n') : ''}
          onChange={(event) => onChange(parseArrayInput(event.target.value, field.itemType))}
          placeholder="One item per line"
          rows={Math.max(3, field.minItems ?? 3)}
        />
        <FieldHelp field={field} />
      </label>
    )
  }

  if (choiceOptions.length > 0) {
    return (
      <label className="auth-field">
        <span>{fieldLabel}</span>
        <select value={typeof value === 'string' ? value : ''} onChange={(event) => onChange(event.target.value)}>
          <option value="">Choose…</option>
          {choiceOptions.map((choice) => (
            <option key={choice.value} value={choice.value}>
              {choice.label}
            </option>
          ))}
        </select>
        <FieldHelp field={field} />
      </label>
    )
  }

  const numeric = field.type === 'number' || field.type === 'integer'
  return (
    <label className="auth-field">
      <span>{fieldLabel}</span>
      <input
        type={numeric ? 'number' : 'text'}
        step={field.type === 'integer' ? '1' : field.type === 'number' ? 'any' : undefined}
        value={typeof value === 'string' || typeof value === 'number' ? String(value) : ''}
        onChange={(event) => onChange(event.target.value)}
      />
      <FieldHelp field={field} />
    </label>
  )
}

function FieldHelp({ field }: { field: ConnectionSetupField }) {
  const parts = [
    field.description,
    field.required ? 'Required.' : 'Optional.',
    field.file?.infoText ?? null,
  ].filter((value): value is string => Boolean(value))

  if (!parts.length) {
    return null
  }
  return <p className="status-inline">{parts.join(' ')}</p>
}

function serializeFields(fields: ConnectionSetupField[], values: Record<string, unknown>) {
  const serialized: Record<string, unknown> = {}
  for (const field of fields) {
    if (field.secret) {
      continue
    }
    const raw = values[field.name]
    if (field.type === 'boolean') {
      serialized[field.name] = Boolean(raw)
      continue
    }
    if (field.type === 'array') {
      serialized[field.name] = Array.isArray(raw) ? raw : []
      continue
    }
    if (field.type === 'integer') {
      if (raw === '' || raw === null || raw === undefined) {
        continue
      }
      serialized[field.name] = Number.parseInt(String(raw), 10)
      continue
    }
    if (field.type === 'number') {
      if (raw === '' || raw === null || raw === undefined) {
        continue
      }
      serialized[field.name] = Number.parseFloat(String(raw))
      continue
    }
    if (typeof raw === 'string') {
      const trimmed = raw.trim()
      if (!trimmed) {
        continue
      }
      serialized[field.name] = trimmed
      continue
    }
    if (raw !== undefined) {
      serialized[field.name] = raw
    }
  }
  return serialized
}

function parseArrayInput(value: string, itemType: string | null | undefined) {
  const lines = value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
  if (itemType === 'integer') {
    return lines.map((line) => Number.parseInt(line, 10)).filter((item) => !Number.isNaN(item))
  }
  if (itemType === 'number') {
    return lines.map((line) => Number.parseFloat(line)).filter((item) => !Number.isNaN(item))
  }
  return lines
}

function isSupportedField(field: ConnectionSetupField) {
  return (
    field.type === 'string'
    || field.type === 'number'
    || field.type === 'integer'
    || field.type === 'boolean'
    || field.type === 'array'
  )
}
