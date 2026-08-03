type AuthLoadingScreenProps = {
  configError: string | null
  sessionError: string | null
}

export default function AuthLoadingScreen({ configError, sessionError }: AuthLoadingScreenProps) {
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
