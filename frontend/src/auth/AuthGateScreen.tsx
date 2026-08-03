import type { FormEventHandler } from 'react'

import type { MarcoPoloAuthModeOption, PublicConfig } from '../app/types'

type AuthGateScreenProps = {
  config: PublicConfig | null
  selectableMarcoPoloModes: MarcoPoloAuthModeOption[]
  selectedMarcoPoloAuthMode: string
  modeSelectionBusy: boolean
  impersonateBusy: boolean
  impersonateEmail: string
  sessionError: string | null
  configError: string | null
  onMarcoPoloAuthModeChange: (mode: string) => void
  onImpersonateEmailChange: (email: string) => void
  onImpersonateSubmit: FormEventHandler<HTMLFormElement>
}

export default function AuthGateScreen({
  config,
  selectableMarcoPoloModes,
  selectedMarcoPoloAuthMode,
  modeSelectionBusy,
  impersonateBusy,
  impersonateEmail,
  sessionError,
  configError,
  onMarcoPoloAuthModeChange,
  onImpersonateEmailChange,
  onImpersonateSubmit,
}: AuthGateScreenProps) {
  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-header">
          <p className="auth-brand">MarcoPolo Integration Demo</p>
          <p className="auth-copy">
            Enter any email address and the demo will establish MarcoPolo access using the selected integration mode.
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
                    disabled={modeSelectionBusy || impersonateBusy}
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
        <form className="auth-actions" onSubmit={onImpersonateSubmit}>
          <label className="auth-field">
            <span>Email</span>
            <input
              type="email"
              name="email"
              placeholder="user@company.com"
              autoComplete="email"
              value={impersonateEmail}
              onChange={(event) => onImpersonateEmailChange(event.target.value)}
              disabled={impersonateBusy}
            />
          </label>
          <button type="submit" className="primary-button auth-submit" disabled={impersonateBusy}>
            {impersonateBusy ? 'Loading Test User…' : 'Test User'}
          </button>
        </form>
        {sessionError || configError ? (
          <p className="status-text auth-status">{sessionError || configError}</p>
        ) : null}
      </section>
    </main>
  )
}
