import { useEffect, useState } from 'react'

import type {
  ConnectionListItem,
  ConnectionListResponse,
  DemoConnectionInstallResponse,
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
  connectionsRefreshBusy: boolean
  demoConnectionInput: string
  marcoPoloReady: boolean
  setDemoConnectionInput: (value: string) => void
  handleConnectionsRefresh: () => Promise<void>
  handleDemoInstallSubmit: (event: React.FormEvent<HTMLFormElement>) => Promise<void>
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
  const [connectionsRefreshBusy, setConnectionsRefreshBusy] = useState(false)
  const [demoConnectionInput, setDemoConnectionInput] = useState('')
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

  function resetConnectionsState() {
    setConnections([])
    setConnectionsError(null)
    setConnectionActionMessage(null)
    setMarcoPoloReady(false)
    onMarcoPoloReadyChange(false)
  }

  return {
    connections,
    connectionsError,
    connectionActionMessage,
    demoInstallBusy,
    connectionsRefreshBusy,
    demoConnectionInput,
    marcoPoloReady,
    setDemoConnectionInput,
    handleConnectionsRefresh,
    handleDemoInstallSubmit,
    refreshConnections,
    resetConnectionsState,
  }
}
