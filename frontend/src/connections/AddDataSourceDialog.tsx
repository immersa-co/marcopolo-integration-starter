import { useEffect, useMemo, useRef, useState } from 'react'

import type {
  ConnectionSetupField,
  ConnectionTestResult,
  ConnectionTypeDetail,
  ConnectionTypeListResponse,
  ConnectionTypeSummary,
  CreateConnectionResponse,
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

type AddDataSourceDialogProps = {
  apiBaseUrl: string
  marcopoloAccessEnabled: boolean
  onConnectionsRefresh: () => Promise<void> | void
}

const POLL_INTERVAL_MS = 2500
const SEARCH_DEBOUNCE_MS = 250

export default function AddDataSourceDialog({
  apiBaseUrl,
  marcopoloAccessEnabled,
  onConnectionsRefresh,
}: AddDataSourceDialogProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [typeOptions, setTypeOptions] = useState<ConnectionTypeSummary[]>([])
  const [typeOptionsBusy, setTypeOptionsBusy] = useState(false)
  const [typeOptionsError, setTypeOptionsError] = useState<string | null>(null)
  const [selectedType, setSelectedType] = useState('')
  const [detail, setDetail] = useState<ConnectionTypeDetail | null>(null)
  const [detailBusy, setDetailBusy] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [selectedMethod, setSelectedMethod] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [fieldValues, setFieldValues] = useState<Record<string, unknown>>({})
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [submitBusy, setSubmitBusy] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [createdConnection, setCreatedConnection] = useState<CreateConnectionResponse['connection'] | null>(null)
  const [oauthSession, setOauthSession] = useState<OAuthSetupSession | null>(null)
  const [testBusy, setTestBusy] = useState(false)
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null)
  const popupRef = useRef<Window | null>(null)
  const pollTimerRef = useRef<number | null>(null)
  const clientSessionIdRef = useRef(`dialog-${Math.random().toString(36).slice(2, 12)}`)

  const currentMethod =
    detail?.setupMethods.find((method) => method.method === selectedMethod) ?? detail?.setupMethods[0] ?? null

  const visibleTypes = useMemo(
    () => typeOptions.filter((option) => !option.deprecated),
    [typeOptions],
  )

  const visibleFields = useMemo(() => {
    if (!currentMethod) {
      return []
    }
    return currentMethod.fields.filter((field) => showAdvanced || !field.advanced)
  }, [currentMethod, showAdvanced])

  const unsupportedFields = useMemo(
    () => (currentMethod ? currentMethod.fields.filter((field) => !isSupportedField(field)) : []),
    [currentMethod],
  )

  const canSubmit =
    Boolean(marcopoloAccessEnabled && detail && currentMethod && unsupportedFields.length === 0) && !submitBusy

  useEffect(() => {
    if (!open || !marcopoloAccessEnabled) {
      return
    }
    const controller = new AbortController()
    const timeoutId = window.setTimeout(() => {
      setTypeOptionsBusy(true)
      setTypeOptionsError(null)

      const params = new URLSearchParams()
      const trimmedSearch = search.trim()
      if (trimmedSearch) {
        params.set('search', trimmedSearch)
      }
      const requestUrl = params.size
        ? `${apiBaseUrl}/api/connections/types?${params.toString()}`
        : `${apiBaseUrl}/api/connections/types`

      fetch(requestUrl, {
        credentials: 'include',
        signal: controller.signal,
      })
        .then(async (response) => {
          const body = (await response.json()) as ConnectionTypeListResponse | { detail?: string }
          if (!response.ok) {
            throw new Error(
              typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string'
                ? body.detail
                : `Connection type list failed with ${response.status}`,
            )
          }
          setTypeOptions((body as ConnectionTypeListResponse).connectionTypes)
        })
        .catch((error) => {
          if ((error as Error).name !== 'AbortError') {
            setTypeOptionsError((error as Error).message)
            setTypeOptions([])
          }
        })
        .finally(() => setTypeOptionsBusy(false))
    }, SEARCH_DEBOUNCE_MS)

    return () => {
      window.clearTimeout(timeoutId)
      controller.abort()
    }
  }, [apiBaseUrl, marcopoloAccessEnabled, open, search])

  useEffect(() => {
    if (!open || !selectedType) {
      return
    }
    const controller = new AbortController()
    setDetailBusy(true)
    setDetail(null)
    setDetailError(null)
    setSubmitError(null)
    setCreatedConnection(null)
    setOauthSession(null)
    setTestResult(null)
    setSelectedMethod('')
    setDisplayName('')
    fetch(`${apiBaseUrl}/api/connections/types/${encodeURIComponent(selectedType)}`, {
      credentials: 'include',
      signal: controller.signal,
    })
      .then(async (response) => {
        const body = (await response.json()) as ConnectionTypeDetail | { detail?: string }
        if (!response.ok) {
          throw new Error(
            typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string'
              ? body.detail
              : `Connection type detail failed with ${response.status}`,
          )
        }
        const resolved = body as ConnectionTypeDetail
        setDetail(resolved)
        setSelectedMethod(resolved.setupMethods[0]?.method ?? '')
        setDisplayName(resolved.displayName)
      })
      .catch((error) => {
        if ((error as Error).name !== 'AbortError') {
          setDetailError((error as Error).message)
          setDetail(null)
          setSelectedMethod('')
        }
      })
      .finally(() => setDetailBusy(false))

    return () => controller.abort()
  }, [apiBaseUrl, open, selectedType])

  useEffect(() => {
    if (!currentMethod) {
      setFieldValues({})
      return
    }
    setFieldValues(() => buildInitialFieldValues(currentMethod.fields))
    setShowAdvanced(false)
  }, [currentMethod?.method])

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

  function stopPolling() {
    if (pollTimerRef.current !== null) {
      window.clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }

  function resetDialogState() {
    setSearch('')
    setSelectedType('')
    setDetail(null)
    setSelectedMethod('')
    setDisplayName('')
    setFieldValues({})
    setShowAdvanced(false)
    setSubmitError(null)
    setDetailError(null)
    setCreatedConnection(null)
    setOauthSession(null)
    setTestResult(null)
    stopPolling()
    if (popupRef.current && !popupRef.current.closed) {
      popupRef.current.close()
    }
    popupRef.current = null
  }

  function closeDialog() {
    setOpen(false)
    resetDialogState()
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
    return session
  }

  function startPolling(setupSessionId: string) {
    stopPolling()
    pollTimerRef.current = window.setInterval(() => {
      void pollSession(setupSessionId).catch((error) => {
        stopPolling()
        setSubmitError((error as Error).message)
      })
    }, POLL_INTERVAL_MS)
  }

  async function submitFieldBasedConnection() {
    if (!detail || !currentMethod) {
      return
    }

    const fields = serializeFields(currentMethod.fields, fieldValues)
    const response = await fetch(`${apiBaseUrl}/api/connections`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        connectionType: detail.type,
        displayName: (displayName || detail.displayName).trim(),
        setupMethod: currentMethod.method,
        fields,
      }),
    })
    const body = (await response.json()) as CreateConnectionResponse | { detail?: string }
    if (!response.ok) {
      throw new Error(
        typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string'
          ? body.detail
          : `Connection creation failed with ${response.status}`,
      )
    }

    const created = body as CreateConnectionResponse
    setCreatedConnection(created.connection)
    setOauthSession(null)
    setTestResult(null)
    await onConnectionsRefresh()
  }

  async function submitOauthConnection() {
    if (!detail) {
      return
    }
    const response = await fetch(`${apiBaseUrl}/api/connections/oauth-setup`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        connectionType: detail.type,
        displayName: (displayName || detail.displayName).trim(),
        clientSessionId: clientSessionIdRef.current,
      }),
    })
    const body = (await response.json()) as OAuthSetupStart | { detail?: string }
    if (!response.ok) {
      throw new Error(
        typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string'
          ? body.detail
          : `OAuth setup start failed with ${response.status}`,
      )
    }

    const started = body as OAuthSetupStart
    setCreatedConnection(null)
    setOauthSession(started)
    setTestResult(null)
    popupRef.current = window.open(
      started.authorizationUrl,
      'marcopolo-oauth-setup',
      'popup,width=720,height=780',
    )
    if (!popupRef.current) {
      window.location.href = started.authorizationUrl
      return
    }
    startPolling(started.setupSessionId)
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!detail || !currentMethod) {
      setSubmitError('Choose a connection type first.')
      return
    }

    if (unsupportedFields.length > 0) {
      setSubmitError('This setup method uses field types not yet supported by the demo.')
      return
    }

    try {
      setSubmitBusy(true)
      setSubmitError(null)
      if (currentMethod.kind === 'hosted_oauth') {
        await submitOauthConnection()
      } else if (currentMethod.kind === 'fields') {
        await submitFieldBasedConnection()
      } else {
        throw new Error(`Setup method kind '${currentMethod.kind}' is not supported yet.`)
      }
    } catch (error) {
      setSubmitError((error as Error).message)
    } finally {
      setSubmitBusy(false)
    }
  }

  async function handleTestConnection() {
    const connectionName = createdConnection?.name ?? (oauthSession?.status === 'ready' ? oauthSession.connectionName : null)
    if (!connectionName) {
      return
    }
    try {
      setTestBusy(true)
      setSubmitError(null)
      const response = await fetch(
        `${apiBaseUrl}/api/connections/${encodeURIComponent(connectionName)}/test`,
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
    } catch (error) {
      setSubmitError((error as Error).message)
    } finally {
      setTestBusy(false)
    }
  }

  return (
    <>
      <div className="connector-card connector-form">
        <div className="connector-copy">
          <h3>Add Data Source</h3>
          <p>
            Use the MarcoPolo API and SDK metadata to create a real connection through one unified flow
            for field-based and hosted OAuth providers.
          </p>
        </div>
        <div className="connector-actions">
          <button
            type="button"
            className="primary-button"
            disabled={!marcopoloAccessEnabled}
            onClick={() => setOpen(true)}
          >
            Add Data Source
          </button>
        </div>
      </div>

      {open ? (
        <div className="dialog-overlay" role="presentation" onClick={closeDialog}>
          <section
            className="dialog-card connection-dialog"
            role="dialog"
            aria-modal="true"
            aria-label="Add data source"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="dialog-header">
              <div>
                <p className="section-label">Connections</p>
                <h2>Add Data Source</h2>
              </div>
              <button type="button" className="secondary-button" onClick={closeDialog}>
                Close
              </button>
            </div>

            <form className="connection-dialog-body" onSubmit={handleSubmit}>
              <div className="connection-dialog-column">
                <label className="auth-field">
                  <span>Search providers</span>
                  <input
                    type="text"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search by provider or category"
                  />
                </label>
                <div className="connection-type-list" role="listbox" aria-label="Connection types">
                  {typeOptionsBusy ? <p className="status-inline">Loading providers…</p> : null}
                  {typeOptionsError ? <p className="status-inline">{typeOptionsError}</p> : null}
                  {!typeOptionsBusy && !typeOptionsError && !visibleTypes.length ? (
                    <p className="status-inline">
                      {search.trim()
                        ? 'No providers matched that search. Try a broader term.'
                        : 'No providers are currently available.'}
                    </p>
                  ) : null}
                  {visibleTypes.map((option) => (
                    <button
                      key={option.type}
                      type="button"
                      className={option.type === selectedType ? 'type-option active' : 'type-option'}
                      onClick={() => setSelectedType(option.type)}
                    >
                      <strong>{option.displayName}</strong>
                      <span>{option.type}</span>
                      <small>{option.category ?? 'uncategorized'}</small>
                    </button>
                  ))}
                </div>
              </div>

              <div className="connection-dialog-column">
                {detailBusy ? <p className="status-inline">Loading setup details…</p> : null}
                {detailError ? <p className="status-inline">{detailError}</p> : null}
                {!detailBusy && !detail && !detailError ? (
                  <p className="status-inline">Choose a provider to inspect its setup methods and required fields.</p>
                ) : null}

                {detail ? (
                  <>
                    <div className="connection-detail-header">
                      <div>
                        <h3>{detail.displayName}</h3>
                        <p className="status-inline">
                          {detail.type}
                          {detail.category ? ` · ${detail.category}` : ''}
                          {detail.description ? ` · ${detail.description}` : ''}
                        </p>
                      </div>
                      <span className={detail.uiFeatures.requiresOAuth ? 'pill pending' : 'pill ready'}>
                        {detail.uiFeatures.requiresOAuth ? 'OAuth capable' : 'Field setup'}
                      </span>
                    </div>

                    <label className="auth-field">
                      <span>Display name</span>
                      <input
                        type="text"
                        value={displayName}
                        onChange={(event) => setDisplayName(event.target.value)}
                        placeholder={detail.displayName}
                      />
                    </label>

                    {detail.setupMethods.length > 1 ? (
                      <label className="auth-field">
                        <span>Setup method</span>
                        <select value={selectedMethod} onChange={(event) => setSelectedMethod(event.target.value)}>
                          {detail.setupMethods.map((method) => (
                            <option key={method.method} value={method.method}>
                              {method.displayName} ({method.kind})
                            </option>
                          ))}
                        </select>
                      </label>
                    ) : null}

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
                          {currentMethod.fields.some((field) => field.advanced) ? (
                            <button
                              type="button"
                              className="secondary-button"
                              onClick={() => setShowAdvanced((current) => !current)}
                            >
                              {showAdvanced ? 'Hide advanced' : 'Show advanced'}
                            </button>
                          ) : null}
                        </div>

                        {unsupportedFields.length ? (
                          <div className="placeholder-row emphasis">
                            <div>
                              <strong>Unsupported field types</strong>
                              <p className="status-inline">
                                {unsupportedFields.map((field) => `${field.name} (${field.type})`).join(', ')}
                              </p>
                            </div>
                            <span className="pill pending">Not supported yet</span>
                          </div>
                        ) : null}

                        {currentMethod.kind === 'hosted_oauth' ? (
                          <p className="status-inline">
                            This provider uses hosted OAuth. The demo will open the provider authorization flow in a
                            popup and then poll the setup session until the connection is ready.
                          </p>
                        ) : (
                          visibleFields.map((field) => (
                            <FieldInput
                              key={field.name}
                              field={field}
                              value={fieldValues[field.name]}
                              onChange={(value) => updateFieldValue(field.name, value)}
                            />
                          ))
                        )}
                      </div>
                    ) : null}

                    <div className="connector-actions">
                      <button type="submit" className="primary-button" disabled={!canSubmit}>
                        {submitBusy
                          ? 'Submitting…'
                          : currentMethod?.kind === 'hosted_oauth'
                            ? 'Continue with OAuth'
                            : 'Create Connection'}
                      </button>
                      {(createdConnection || oauthSession?.status === 'ready') ? (
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
                      ) : null}
                    </div>

                    {createdConnection ? (
                      <div className="placeholder-row emphasis">
                        <div>
                          <strong>{createdConnection.displayName}</strong>
                          <p className="status-inline">
                            Created as {createdConnection.name} via {createdConnection.authMethod}.
                          </p>
                        </div>
                        <span className="pill ready">Created</span>
                      </div>
                    ) : null}

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
                  </>
                ) : null}
              </div>
            </form>
          </section>
        </div>
      ) : null}
    </>
  )
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
        type={field.secret ? 'password' : numeric ? 'number' : 'text'}
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
    field.secret ? 'Stored as a secret.' : null,
    field.file?.infoText ?? null,
  ].filter((value): value is string => Boolean(value))

  if (!parts.length) {
    return null
  }
  return <p className="status-inline">{parts.join(' ')}</p>
}

function buildInitialFieldValues(fields: ConnectionSetupField[]) {
  const values: Record<string, unknown> = {}
  for (const field of fields) {
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

function isSupportedField(field: ConnectionSetupField) {
  if (field.file) {
    return false
  }
  if (field.type === 'object') {
    return false
  }
  if (field.type === 'array') {
    return !field.itemType || ['string', 'number', 'integer'].includes(field.itemType)
  }
  return ['string', 'number', 'integer', 'boolean'].includes(field.type)
}

function parseArrayInput(value: string, itemType: string | null | undefined) {
  const items = value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
  if (itemType === 'number') {
    return items.map((item) => Number(item))
  }
  if (itemType === 'integer') {
    return items.map((item) => Number.parseInt(item, 10))
  }
  return items
}

function serializeFields(fields: ConnectionSetupField[], values: Record<string, unknown>) {
  const payload: Record<string, unknown> = {}

  for (const field of fields) {
    if (!isSupportedField(field)) {
      throw new Error(`Field '${field.name}' uses an unsupported setup shape.`)
    }

    const raw = values[field.name]
    const value = serializeFieldValue(field, raw)
    const isEmpty =
      value === '' ||
      value === null ||
      value === undefined ||
      (Array.isArray(value) && value.length === 0)

    if (field.required && isEmpty) {
      throw new Error(`'${field.label || field.name}' is required.`)
    }
    if (!isEmpty) {
      payload[field.name] = value
    }
  }

  return payload
}

function serializeFieldValue(field: ConnectionSetupField, raw: unknown) {
  if (field.type === 'boolean') {
    return Boolean(raw)
  }
  if (field.type === 'integer') {
    if (raw === '' || raw === null || raw === undefined) {
      return null
    }
    const parsed = Number.parseInt(String(raw), 10)
    if (Number.isNaN(parsed)) {
      throw new Error(`'${field.label || field.name}' must be an integer.`)
    }
    return parsed
  }
  if (field.type === 'number') {
    if (raw === '' || raw === null || raw === undefined) {
      return null
    }
    const parsed = Number(String(raw))
    if (Number.isNaN(parsed)) {
      throw new Error(`'${field.label || field.name}' must be a number.`)
    }
    return parsed
  }
  if (field.type === 'array') {
    if (Array.isArray(raw)) {
      return raw
    }
    return []
  }
  if (raw === null || raw === undefined) {
    return ''
  }
  return String(raw).trim()
}
