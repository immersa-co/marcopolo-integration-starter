import type { FormEventHandler } from 'react'

import type { MarcoPoloAuthModeOption, PublicConfig } from '../app/types'

type AuthGateScreenProps = {
  config: PublicConfig | null
  selectableMarcoPoloModes: MarcoPoloAuthModeOption[]
  selectedMarcoPoloAuthMode: string
  modeSelectionBusy: boolean
  demoSessionBusy: boolean
  demoUserEmail: string
  sessionError: string | null
  configError: string | null
  onMarcoPoloAuthModeChange: (mode: string) => void
  onDemoUserEmailChange: (email: string) => void
  onDemoSessionSubmit: FormEventHandler<HTMLFormElement>
}

export default function AuthGateScreen({
  config,
  selectableMarcoPoloModes,
  selectedMarcoPoloAuthMode,
  modeSelectionBusy,
  demoSessionBusy,
  demoUserEmail,
  sessionError,
  configError,
  onMarcoPoloAuthModeChange,
  onDemoUserEmailChange,
  onDemoSessionSubmit,
}: AuthGateScreenProps) {
  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-header">
          <p className="auth-brand">MarcoPolo Integration Demo</p>
          <p className="auth-copy">
            This starter assumes your application already authenticated the user. Enter a demo user email to simulate
            that app session, then WorkOS Standalone Connect authorizes MarcoPolo access and resolves the user's namespace.
          </p>
        </div>
        {config ? (
          <div className="auth-mode-picker auth-mode-picker-gated">
            <p className="section-label">MarcoPolo auth mode</p>
            <div className="auth-mode-radio-list" role="radiogroup" aria-label="MarcoPolo auth mode">
              {selectableMarcoPoloModes.map((mode) => (
                <label key={mode.key} className="auth-mode-radio">
                  <input
                    type="radio"
                    name="marcopolo-auth-mode-gated"
                    value={mode.key}
                    checked={selectedMarcoPoloAuthMode === mode.key}
                    onChange={() => onMarcoPoloAuthModeChange(mode.key)}
                    disabled={modeSelectionBusy || demoSessionBusy}
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
        ) : null}
        <form className="auth-actions" onSubmit={onDemoSessionSubmit}>
          <label className="auth-field">
            <span>Demo user email</span>
            <input
              type="email"
              name="email"
              placeholder="user@company.com"
              autoComplete="email"
              value={demoUserEmail}
              onChange={(event) => onDemoUserEmailChange(event.target.value)}
              disabled={demoSessionBusy}
            />
          </label>
          <button type="submit" className="primary-button auth-submit" disabled={demoSessionBusy}>
            {demoSessionBusy ? 'Creating demo app session…' : 'Create demo app session'}
          </button>
        </form>
        {sessionError || configError ? (
          <p className="status-text auth-status">{sessionError || configError}</p>
        ) : null}
      </section>
    </main>
  )
}
