import type { ReactNode } from 'react'

import { tabs } from './constants'
import type { AuthSession, MarcoPoloAuthModeOption, PublicConfig, TabId } from './types'

type AppShellProps = {
  activeTab: TabId
  children: ReactNode
  config: PublicConfig
  modeSelectionBusy: boolean
  selectableMarcoPoloModes: MarcoPoloAuthModeOption[]
  selectedMarcoPoloAuthMode: string
  session: AuthSession
  sessionError: string | null
  usesWorkosConnect: boolean
  onLogout: () => void
  onMarcoPoloAuthModeChange: (mode: string) => void
  onTabChange: (tabId: TabId) => void
}

export default function AppShell({
  activeTab,
  children,
  config,
  modeSelectionBusy,
  selectableMarcoPoloModes,
  selectedMarcoPoloAuthMode,
  session,
  sessionError,
  usesWorkosConnect,
  onLogout,
  onMarcoPoloAuthModeChange,
  onTabChange,
}: AppShellProps) {
  return (
    <main className="app-shell">
      <section className="hero-panel">
        <p className="kicker">WorkOS Connect partner namespace E2E</p>
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
              {session.authenticated
                ? `Test user${session.user?.email ? ` ${session.user.email}` : ''}`
                : 'Authentication required'}
            </h2>
            <p className="session-detail">
              {session.authenticated
                ? `${session.user?.email ?? 'No email entered'}${session.provider ? ` · ${session.provider}` : ''}`
                : 'Select a test user email to establish the demo app session.'}
            </p>
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
                      onChange={() => onMarcoPoloAuthModeChange(mode.key)}
                      disabled={modeSelectionBusy}
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
            {session.authenticated ? (
              <div className="resolved-identity" aria-label="MarcoPolo resolved identity">
                <div className="resolved-identity-header">
                  <p className="section-label">MarcoPolo resolved identity</p>
                  <span className={session.marcoPoloProvisioned ? 'pill ready' : 'pill pending'}>
                    {session.marcoPoloProvisioned ? 'Bootstrap complete' : 'Waiting for bootstrap'}
                  </span>
                </div>
                <dl>
                  <div>
                    <dt>Namespace</dt>
                    <dd>
                      {session.namespace ?? (usesWorkosConnect ? 'Pending WorkOS bootstrap' : 'Not provided by local shortcut')}
                    </dd>
                  </div>
                  <div>
                    <dt>Company</dt>
                    <dd>
                      {session.company ?? (usesWorkosConnect ? 'Pending WorkOS bootstrap' : 'Not provided by local shortcut')}
                    </dd>
                  </div>
                </dl>
              </div>
            ) : null}
          </div>
          <div className="session-actions">
            {session.authenticated ? (
              <button type="button" className="secondary-button" onClick={onLogout}>
                Sign out
              </button>
            ) : null}
            {session.authenticated && usesWorkosConnect && !session.marcoPoloProvisioned && config.marcoPolo.authModeConfigured ? (
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
            onClick={() => onTabChange(tab.id)}
          >
            <span>{tab.eyebrow}</span>
            <strong>{tab.label}</strong>
          </button>
        ))}
      </nav>

      {children}
    </main>
  )
}
