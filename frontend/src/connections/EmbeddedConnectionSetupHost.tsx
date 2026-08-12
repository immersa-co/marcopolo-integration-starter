import { useEffect, useRef, useState } from 'react'
import { AppBridge, PostMessageTransport } from '@modelcontextprotocol/ext-apps/app-bridge'

type EmbeddedConnectionSetupResponse = {
  resourceUri: string
  statusUrl?: string | null
  toolResult: Record<string, unknown>
  toolOutput: {
    type: string
    success?: boolean
    error?: string | null
    hint?: string | null
    resolution_reason?: string | null
    suggested_types?: string[]
    workflow_type?: string | null
    url?: string | null
    setup_session_id?: string | null
    host_session_id?: string | null
  }
  widgetMeta?: {
    ['marcopolo/widget']?: Record<string, unknown>
  }
}

type ConnectionSetupStatusResponse = {
  setupSessionId?: string | null
  status: string
  closePopup?: boolean | null
  resumeEmbedded?: boolean | null
  refreshConnections?: boolean | null
  connectionName?: string | null
  connectionType?: string | null
  displayName?: string | null
  hostOrigin?: string | null
  hostReturnUrl?: string | null
  errorMessage?: string | null
}

type Props = {
  apiBaseUrl: string
  marcoPoloWebBaseUrl: string
  payload: EmbeddedConnectionSetupResponse
  existingConnectionName?: string
  onClose: () => void
  onRefreshConnections: () => Promise<void>
}

function getTheme() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function getMessageText(content: unknown): string | null {
  if (!Array.isArray(content)) {
    return null
  }

  for (const block of content) {
    if (
      typeof block === 'object' &&
      block !== null &&
      'type' in block &&
      block.type === 'text' &&
      'text' in block &&
      typeof block.text === 'string'
    ) {
      return block.text
    }
  }

  return null
}

function buildToolInput(payload: EmbeddedConnectionSetupResponse): Record<string, unknown> {
  return {
    ...payload.toolOutput,
    ...(payload.widgetMeta?.['marcopolo/widget'] ?? {}),
  }
}

export default function EmbeddedConnectionSetupHost({
  apiBaseUrl,
  marcoPoloWebBaseUrl,
  payload,
  existingConnectionName,
  onClose,
  onRefreshConnections,
}: Props) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null)
  const iframeLoadHandlerRef = useRef<(() => void) | null>(null)
  const popupWindowsRef = useRef<Window[]>([])
  const oauthPollIdRef = useRef(0)
  const hostSessionIdRef = useRef(
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `host-${Date.now()}`,
  )
  const [currentPayload, setCurrentPayload] = useState(payload)
  const [activeSetupSessionId, setActiveSetupSessionId] = useState<string | null>(
    typeof payload.toolOutput.setup_session_id === 'string' ? payload.toolOutput.setup_session_id : null,
  )
  const [statusText, setStatusText] = useState<string | null>(null)
  const [hostError, setHostError] = useState<string | null>(null)
  const [iframeHeight, setIframeHeight] = useState(760)
  const [oauthPending, setOauthPending] = useState(false)
  const [oauthReadyName, setOauthReadyName] = useState<string | null>(null)
  const unresolvedType = currentPayload.toolOutput.success === false
  const isOAuthFlow = currentPayload.toolOutput.workflow_type === 'oauth'
  const marcoPoloOrigin = new URL(marcoPoloWebBaseUrl).origin
  const oemOrigin = window.location.origin
  const hostReturnUrl = `${window.location.origin}/oauth-return`
  const hostSessionId =
    typeof currentPayload.toolOutput.host_session_id === 'string' && currentPayload.toolOutput.host_session_id
      ? currentPayload.toolOutput.host_session_id
      : hostSessionIdRef.current

  function registerPopupWindow(popupWindow: Window | null) {
    if (!popupWindow) {
      return
    }
    popupWindowsRef.current = popupWindowsRef.current
      .filter((candidate) => candidate && !candidate.closed)
      .concat(popupWindow)
  }

  function closeAllPopupWindows() {
    for (const popupWindow of popupWindowsRef.current) {
      try {
        if (popupWindow && !popupWindow.closed) {
          popupWindow.close()
        }
      } catch {
        // Best-effort popup cleanup only.
      }
    }
    popupWindowsRef.current = []
  }

  useEffect(() => {
    setCurrentPayload(payload)
    setActiveSetupSessionId(
      typeof payload.toolOutput.setup_session_id === 'string' ? payload.toolOutput.setup_session_id : null,
    )
    setStatusText('Booting the MarcoPolo embedded MCP app...')
    setHostError(null)
    setOauthPending(false)
    setOauthReadyName(null)
  }, [payload])

  async function refreshFromSetupSession(setupSessionId: string) {
    const pollId = oauthPollIdRef.current + 1
    oauthPollIdRef.current = pollId

    for (let attempt = 0; attempt < 180; attempt += 1) {
      if (attempt > 0) {
        await new Promise((resolve) => setTimeout(resolve, 2000))
      }
      if (oauthPollIdRef.current !== pollId) {
        return
      }

      try {
        const response = await fetch(
          `${apiBaseUrl}/api/connections/setup-session-status?setupSessionId=${encodeURIComponent(setupSessionId)}`,
          {
            credentials: 'include',
          },
        )

        if (!response.ok) {
          continue
        }

        const setupStatus = (await response.json()) as ConnectionSetupStatusResponse
        if (setupStatus.closePopup) {
          closeAllPopupWindows()
        }

        if (setupStatus.resumeEmbedded) {
          const resumeResponse = await fetch(
            `${apiBaseUrl}/api/connections/setup-session-resume?setupSessionId=${encodeURIComponent(setupSessionId)}`,
            {
              credentials: 'include',
            },
          )
          if (resumeResponse.ok) {
            const resumedPayload = (await resumeResponse.json()) as EmbeddedConnectionSetupResponse
            setCurrentPayload(resumedPayload)
            setActiveSetupSessionId(setupSessionId)
            setOauthPending(false)
            setStatusText('OAuth complete. Resuming the embedded MarcoPolo setup flow inside MarcoPolo Integration Demo...')
            setHostError(null)
          }
        }

        if (setupStatus.status === 'ready') {
          closeAllPopupWindows()
          setOauthPending(false)
          await onRefreshConnections()
          setOauthReadyName(
            setupStatus.displayName ??
              setupStatus.connectionName ??
              existingConnectionName ??
              setupStatus.connectionType ??
              'connection',
          )
          setStatusText('Connection setup completed inside MarcoPolo Integration Demo.')
          setHostError(null)
          return
        }

        if (setupStatus.status === 'failed' || setupStatus.status === 'cancelled') {
          closeAllPopupWindows()
          setOauthPending(false)
          setHostError(setupStatus.errorMessage ?? `Authorization ${setupStatus.status}.`)
          return
        }
      } catch (error) {
        if ((error as Error).name === 'AbortError') {
          return
        }
      }
    }

    setOauthPending(false)
    setHostError('Authorization did not finish before the MarcoPolo Integration Demo timeout. Retry the flow or use the popup fallback.')
  }

  async function resolveSetupSessionFromHostSession() {
    for (let attempt = 0; attempt < 15; attempt += 1) {
      try {
        const response = await fetch(
          `${apiBaseUrl}/api/connections/setup-session-lookup?hostSessionId=${encodeURIComponent(hostSessionId)}`,
          { credentials: 'include' },
        )
        if (response.ok) {
          const payload = (await response.json()) as { setupSessionId: string }
          if (payload.setupSessionId) {
            setActiveSetupSessionId(payload.setupSessionId)
            return
          }
        }
      } catch {
        // Continue polling while the initiate response is being processed.
      }
      await new Promise((resolve) => setTimeout(resolve, 500))
    }
  }

  useEffect(() => {
    if (!activeSetupSessionId || !isOAuthFlow || oauthReadyName) {
      return
    }
    void refreshFromSetupSession(activeSetupSessionId)
    return () => {
      oauthPollIdRef.current += 1
    }
  }, [activeSetupSessionId, apiBaseUrl, isOAuthFlow, oauthReadyName])

  useEffect(() => {
    if (!isOAuthFlow) {
      return
    }

    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== marcoPoloOrigin && event.origin !== oemOrigin) {
        return
      }
      const data = event.data
      if (typeof data !== 'object' || data === null) {
        return
      }
      if (!('type' in data) || data.type !== 'marcopolo.connection_setup.complete') {
        return
      }

      const setupSessionId =
        typeof data.setup_session_id === 'string'
          ? data.setup_session_id
          : typeof data.setupSessionId === 'string'
            ? data.setupSessionId
            : null
      if (!setupSessionId) {
        return
      }

      setOauthPending(true)
      setActiveSetupSessionId(setupSessionId)
      setStatusText('OAuth completed in the popup. Syncing the continuation state back into MarcoPolo Integration Demo...')
      setHostError(null)
    }

    window.addEventListener('message', handleMessage)
    return () => {
      window.removeEventListener('message', handleMessage)
    }
  }, [isOAuthFlow, marcoPoloOrigin, oemOrigin])

  useEffect(() => {
    if (unresolvedType) {
      return
    }
    const iframe = iframeRef.current
    if (!iframe) {
      return
    }

    let closed = false
    let bridge: AppBridge | null = null

    const handleLoad = () => {
      const targetWindow = iframe.contentWindow
      if (!targetWindow || closed) {
        return
      }

      setStatusText('Connecting MarcoPolo Integration Demo to the MarcoPolo embedded app...')

      const transport = new PostMessageTransport(targetWindow, targetWindow)
      bridge = new AppBridge(
        null,
        { name: 'MarcoPoloOEMDemo', version: '0.2.0' },
        {
          openLinks: {},
          message: { text: {} },
          logging: {},
        },
        {
          hostContext: {
            theme: getTheme(),
            displayMode: 'inline',
            platform: 'web',
            userAgent: 'MarcoPoloOEMDemo',
            locale: navigator.language,
            timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            containerDimensions: {
              maxWidth: 1200,
              maxHeight: 1600,
            },
          },
        },
      )

      bridge.onopenlink = async ({ url }) => {
        if (isOAuthFlow) {
          const isResumedPopupStep = Boolean(activeSetupSessionId)
          closeAllPopupWindows()
          const popupWindow = window.open(
            url,
            'marcopolo-embedded-oauth',
            'popup=yes,width=1280,height=900,resizable=yes,scrollbars=yes',
          )
          if (!popupWindow) {
            setOauthPending(false)
            setHostError('MarcoPolo Integration Demo could not open the authorization popup. Allow popups for this site and retry.')
            return {}
          }
          registerPopupWindow(popupWindow)
          setOauthPending(true)
          setStatusText(
            isResumedPopupStep
              ? 'Google Picker is running in a separate window. Stay on the MarcoPolo Integration Demo page while the host waits for completion.'
              : 'Authorization is running in a separate window. Stay on the MarcoPolo Integration Demo page while the host waits for MarcoPolo to return control.',
          )
          if (!isResumedPopupStep) {
            void resolveSetupSessionFromHostSession()
          }
        } else {
          window.open(url, '_blank', 'noopener,noreferrer')
        }
        return {}
      }

      bridge.onmessage = async ({ content }) => {
        const text = getMessageText(content)
        if (text && !closed) {
          setStatusText(text)
        }
        return {}
      }

      bridge.onsizechange = ({ height }) => {
        if (typeof height === 'number' && Number.isFinite(height) && !closed) {
          const nextHeight = Math.max(520, Math.min(Math.ceil(height) + 8, 1600))
          // Keep the iframe height monotonic for the current session so transient
          // overlays like Google Picker do not trigger a resize feedback loop.
          setIframeHeight((currentHeight) => Math.max(currentHeight, nextHeight))
        }
      }

      bridge.oninitialized = () => {
        void (async () => {
          try {
            setStatusText('Hydrating the MarcoPolo embedded app...')
            await bridge?.sendToolInput({
              arguments: {
                ...buildToolInput(currentPayload),
                ...(isOAuthFlow
                  ? {
                      host_mode: 'embedded',
                      host_return_url: hostReturnUrl,
                      host_origin: oemOrigin,
                      host_session_id: hostSessionId,
                    }
                  : {}),
              },
            })
            await bridge?.sendToolResult(currentPayload.toolResult as never)
            if (!closed) {
              setStatusText('MarcoPolo embedded app loaded inside MarcoPolo Integration Demo.')
            }
          } catch (error) {
            if (!closed) {
              setHostError((error as Error).message)
            }
          }
        })()
      }

      void bridge.connect(transport).catch((error: unknown) => {
        if (!closed) {
          setHostError((error as Error).message)
        }
      })
    }

    iframeLoadHandlerRef.current = handleLoad
    iframe.src = `${apiBaseUrl}/api/connections/ext-app/connection-setup?resourceUri=${encodeURIComponent(
      currentPayload.resourceUri,
    )}`

    return () => {
      closed = true
      closeAllPopupWindows()
      if (iframeLoadHandlerRef.current === handleLoad) {
        iframeLoadHandlerRef.current = null
      }
      if (bridge) {
        void bridge.close().catch(() => {})
      }
    }
  }, [apiBaseUrl, currentPayload, hostReturnUrl, hostSessionId, isOAuthFlow, oemOrigin, unresolvedType])

  return (
    <section className="embedded-host-card">
      <div className="embedded-host-header">
        <div>
          <p className="section-label">Embedded MCP app</p>
          <h3>MarcoPolo connection setup rendered in place.</h3>
        </div>
        <div className="connector-actions">
          <button type="button" className="secondary-button" onClick={onRefreshConnections}>
            Refresh connections
          </button>
          <button type="button" className="secondary-button" onClick={onClose}>
            Close
          </button>
        </div>
      </div>

      {statusText ? <p className="embedded-status">{statusText}</p> : null}
      {existingConnectionName ? (
        <p className="embedded-success">
          MarcoPolo currently shows this connector as <strong>{existingConnectionName}</strong>.
        </p>
      ) : null}
      {oauthPending ? (
        <div className="embedded-oauth-state">
          <p className="embedded-status">
            Continue the provider sign-in in the separate window. When authorization completes, this MarcoPolo Integration Demo page will refresh the connection list and show success here.
          </p>
        </div>
      ) : null}
      {oauthReadyName ? (
        <div className="embedded-oauth-state embedded-oauth-ready">
          <p className="section-label">Connection Ready</p>
          <h4>{oauthReadyName} was connected without leaving MarcoPolo Integration Demo.</h4>
          <p className="embedded-success">
            The MarcoPolo setup flow is complete. The MarcoPolo Integration Demo connections list has been refreshed and the auxiliary authorization window was closed.
          </p>
        </div>
      ) : null}
      {hostError ? <p className="embedded-error">{hostError}</p> : null}

      {unresolvedType ? (
        <div className="embedded-oauth-state">
          <p className="embedded-error">
            {currentPayload.toolOutput.error ?? 'MarcoPolo could not resolve that connection type.'}
          </p>
          {currentPayload.toolOutput.hint ? (
            <p className="embedded-status">{currentPayload.toolOutput.hint}</p>
          ) : null}
          {currentPayload.toolOutput.resolution_reason ? (
            <p className="embedded-status">{currentPayload.toolOutput.resolution_reason}</p>
          ) : null}
          {Array.isArray(currentPayload.toolOutput.suggested_types) && currentPayload.toolOutput.suggested_types.length ? (
            <p className="embedded-status">
              Suggested types: {currentPayload.toolOutput.suggested_types.join(', ')}
            </p>
          ) : null}
        </div>
      ) : !(isOAuthFlow && oauthReadyName) ? (
        <iframe
          ref={iframeRef}
          title="MarcoPolo connection setup"
          className="embedded-host-frame"
          onLoad={() => iframeLoadHandlerRef.current?.()}
          style={{ height: `${iframeHeight}px` }}
        />
      ) : null}
    </section>
  )
}
