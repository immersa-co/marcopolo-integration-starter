import { useEffect, useState } from 'react'

import type {
  ConnectionListItem,
  ConnectionListResponse,
  DemoConnectionInstallResponse,
  EmbeddedConnectionSetupResponse,
} from '../app/types'

type UseConnectionsFeatureOptions = {
  apiBaseUrl: string
  sessionAuthenticated: boolean
  needsMarcoPoloAuthorization: boolean
  selectedMarcoPoloAuthMode: string
  onMarcoPoloReadyChange: (ready: boolean) => void
}

type UseConnectionsFeatureResult = {
  connections: ConnectionListItem[]
  connectionsError: string | null
  connectionActionMessage: string | null
  demoInstallBusy: boolean
  embeddedSetupBusy: boolean
  connectionsRefreshBusy: boolean
  demoConnectionInput: string
  newConnectionTypeInput: string
  embeddedSetup: EmbeddedConnectionSetupResponse | null
  activeEmbeddedConnectionName?: string | null
  marcoPoloReady: boolean
  setDemoConnectionInput: (value: string) => void
  setNewConnectionTypeInput: (value: string) => void
  setEmbeddedSetup: (value: EmbeddedConnectionSetupResponse | null) => void
  handleConnectionsRefresh: () => Promise<void>
  handleDemoInstallSubmit: (event: React.FormEvent<HTMLFormElement>) => Promise<void>
  handleEmbeddedSetupSubmit: (event: React.FormEvent<HTMLFormElement>) => Promise<void>
  refreshConnections: (signal?: AbortSignal) => Promise<void>
  resetConnectionsState: () => void
}

export default function useConnectionsFeature({
  apiBaseUrl,
  sessionAuthenticated,
  needsMarcoPoloAuthorization,
  selectedMarcoPoloAuthMode,
  onMarcoPoloReadyChange,
}: UseConnectionsFeatureOptions): UseConnectionsFeatureResult {
  const [connections, setConnections] = useState<ConnectionListItem[]>([])
  const [connectionsError, setConnectionsError] = useState<string | null>(null)
  const [connectionActionMessage, setConnectionActionMessage] = useState<string | null>(null)
  const [demoInstallBusy, setDemoInstallBusy] = useState(false)
  const [embeddedSetupBusy, setEmbeddedSetupBusy] = useState(false)
  const [connectionsRefreshBusy, setConnectionsRefreshBusy] = useState(false)
  const [demoConnectionInput, setDemoConnectionInput] = useState('')
  const [newConnectionTypeInput, setNewConnectionTypeInput] = useState('')
  const [embeddedSetup, setEmbeddedSetup] = useState<EmbeddedConnectionSetupResponse | null>(null)
  const [marcoPoloReady, setMarcoPoloReady] = useState(false)

  async function refreshConnections(signal?: AbortSignal) {
    if (!sessionAuthenticated) {
      setConnections([])
      setMarcoPoloReady(false)
      onMarcoPoloReadyChange(false)
      return
    }

    if (needsMarcoPoloAuthorization) {
      setConnections([])
      setConnectionsError(null)
      setMarcoPoloReady(false)
      onMarcoPoloReadyChange(false)
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
    onMarcoPoloReadyChange(true)
  }

  useEffect(() => {
    const controller = new AbortController()

    refreshConnections(controller.signal).catch((error) => {
      if ((error as Error).name === 'AbortError') {
        return
      }

      setMarcoPoloReady(false)
      onMarcoPoloReadyChange(false)
      setConnectionsError((error as Error).message)
    })

    return () => controller.abort()
  }, [apiBaseUrl, needsMarcoPoloAuthorization, selectedMarcoPoloAuthMode, sessionAuthenticated])

  async function handleConnectionsRefresh() {
    try {
      setConnectionsRefreshBusy(true)
      setConnectionsError(null)
      await refreshConnections()
    } catch (error) {
      setMarcoPoloReady(false)
      onMarcoPoloReadyChange(false)
      setConnectionsError((error as Error).message)
    } finally {
      setConnectionsRefreshBusy(false)
    }
  }

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

  function resetConnectionsState() {
    setConnections([])
    setConnectionsError(null)
    setConnectionActionMessage(null)
    setEmbeddedSetup(null)
    setMarcoPoloReady(false)
    onMarcoPoloReadyChange(false)
  }

  const activeEmbeddedConnectionType =
    typeof embeddedSetup?.toolOutput?.type === 'string' ? embeddedSetup.toolOutput.type : null
  const activeEmbeddedConnectionName =
    connections.find((item) => item.type === activeEmbeddedConnectionType)?.displayName

  return {
    connections,
    connectionsError,
    connectionActionMessage,
    demoInstallBusy,
    embeddedSetupBusy,
    connectionsRefreshBusy,
    demoConnectionInput,
    newConnectionTypeInput,
    embeddedSetup,
    activeEmbeddedConnectionName,
    marcoPoloReady,
    setDemoConnectionInput,
    setNewConnectionTypeInput,
    setEmbeddedSetup,
    handleConnectionsRefresh,
    handleDemoInstallSubmit,
    handleEmbeddedSetupSubmit,
    refreshConnections,
    resetConnectionsState,
  }
}
