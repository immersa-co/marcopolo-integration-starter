import { useEffect, useState } from 'react'

export default function OAuthReturnBridge() {
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
