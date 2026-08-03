import { useEffect, useRef, useState } from 'react'

import type { AuthSession, MarcoPoloAuthModeOption, PublicConfig } from '../app/types'

type UseAuthRuntimeOptions = {
  apiBaseUrl: string
  onResetAppState: () => void
  onMarcoPoloReadyChange: (ready: boolean) => void
}

type UseAuthRuntimeResult = {
  config: PublicConfig | null
  session: AuthSession | null
  configError: string | null
  sessionError: string | null
  modeSelectionBusy: boolean
  impersonateBusy: boolean
  impersonateEmail: string
  setImpersonateEmail: (value: string) => void
  selectableMarcoPoloModes: MarcoPoloAuthModeOption[]
  selectedMarcoPoloAuthMode: string
  usesWorkosConnect: boolean
  needsMarcoPoloAuthorization: boolean
  shouldGateApp: boolean
  handleLogout: () => Promise<void>
  handleMarcoPoloAuthModeChange: (mode: string) => Promise<void>
  handleImpersonateSubmit: (event: React.FormEvent<HTMLFormElement>) => Promise<void>
}

export default function useAuthRuntime({
  apiBaseUrl,
  onResetAppState,
  onMarcoPoloReadyChange,
}: UseAuthRuntimeOptions): UseAuthRuntimeResult {
  const [config, setConfig] = useState<PublicConfig | null>(null)
  const [session, setSession] = useState<AuthSession | null>(null)
  const [configError, setConfigError] = useState<string | null>(null)
  const [sessionError, setSessionError] = useState<string | null>(null)
  const [modeSelectionBusy, setModeSelectionBusy] = useState(false)
  const [impersonateBusy, setImpersonateBusy] = useState(false)
  const [impersonateEmail, setImpersonateEmail] = useState('')
  const connectRedirectAttemptRef = useRef<string | null>(null)

  const selectedMarcoPoloAuthMode = session?.marcoPoloAuthMode ?? config?.marcoPolo.authMode ?? 'developer_api_token'
  const usesWorkosConnect = selectedMarcoPoloAuthMode === 'workos_connect'
  const selectableMarcoPoloModes =
    config?.marcoPolo.availableAuthModes.filter((mode) => ['developer_api_token', 'workos_connect'].includes(mode.key)) ?? []
  const needsMarcoPoloAuthorization = Boolean(
    session?.authenticated && usesWorkosConnect && !session?.marcoPoloProvisioned,
  )
  const shouldGateApp = Boolean(config?.auth.required && !session?.authenticated)

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

  async function handleLogout() {
    try {
      const response = await fetch(`${apiBaseUrl}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error(`Logout failed with ${response.status}`)
      }

      onMarcoPoloReadyChange(false)
      onResetAppState()
      setImpersonateEmail('')
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
      onResetAppState()
      onMarcoPoloReadyChange(false)

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
      onResetAppState()
      onMarcoPoloReadyChange(false)

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

  return {
    config,
    session,
    configError,
    sessionError,
    modeSelectionBusy,
    impersonateBusy,
    impersonateEmail,
    setImpersonateEmail,
    selectableMarcoPoloModes,
    selectedMarcoPoloAuthMode,
    usesWorkosConnect,
    needsMarcoPoloAuthorization,
    shouldGateApp,
    handleLogout,
    handleMarcoPoloAuthModeChange,
    handleImpersonateSubmit,
  }
}
