import type { PublicConfig } from '../app/types'

type ConfigurationTabProps = {
  config: PublicConfig | null
  configError: string | null
  marcoPoloReady: boolean
}

export default function ConfigurationTab({ config, configError, marcoPoloReady }: ConfigurationTabProps) {
  return (
    <section className="configuration-layout">
      <article className="panel">
        <div className="panel-header">
          <p className="section-label">Configuration</p>
          <h2>Runtime environment and integration status.</h2>
        </div>
        <div className="config-card config-card-panel">
          {config ? (
            <>
              <dl>
                <div>
                  <dt>Environment</dt>
                  <dd>{config.appEnv}</dd>
                </div>
                <div>
                  <dt>Demo identity</dt>
                  <dd>
                    Test user email / {config.auth.configured ? 'configured' : 'session config missing'}
                  </dd>
                </div>
                <div>
                  <dt>MarcoPolo auth</dt>
                  <dd>
                    {config.marcoPolo.authModeLabel} /{' '}
                    {config.marcoPolo.authModeConfigured ? 'configured' : 'missing mode secrets'}
                  </dd>
                </div>
                <div>
                  <dt>MarcoPolo MCP</dt>
                  <dd>{config.marcoPolo.mcpUrl}</dd>
                </div>
                <div>
                  <dt>MarcoPolo API</dt>
                  <dd>{config.marcoPolo.apiBaseUrl}</dd>
                </div>
                <div>
                  <dt>MarcoPolo web</dt>
                  <dd>{config.marcoPolo.webBaseUrl}</dd>
                </div>
                <div>
                  <dt>LLM</dt>
                  <dd>
                    {config.llm.provider} / {config.llm.model}
                  </dd>
                </div>
              </dl>
              <div className="pill-row">
                <span className={config.auth.configured ? 'pill ready' : 'pill pending'}>
                  {config.auth.configured ? 'Impersonation ready' : 'Session config missing'}
                </span>
                <span className={config.marcoPolo.authModeConfigured ? 'pill ready' : 'pill pending'}>
                  {config.marcoPolo.authModeConfigured
                    ? `${config.marcoPolo.authModeLabel} ready`
                    : `${config.marcoPolo.authModeLabel} incomplete`}
                </span>
                <span className={marcoPoloReady ? 'pill ready' : 'pill pending'}>
                  {marcoPoloReady ? 'MarcoPolo connected' : 'MarcoPolo pending'}
                </span>
                <span className={config.llm.apiKeyConfigured ? 'pill ready' : 'pill pending'}>
                  {config.llm.apiKeyConfigured ? 'LLM key configured' : 'LLM key missing'}
                </span>
                <span className={config.skills.length ? 'pill ready' : 'pill pending'}>
                  {config.skills.length} skills loaded
                </span>
              </div>
              <div className="auth-mode-note">
                <p className="status-inline">{config.marcoPolo.authModeDescription}</p>
                <div className="auth-mode-list">
                  {config.marcoPolo.availableAuthModes.map((mode) => (
                    <div key={mode.key} className="auth-mode-row">
                      <strong>{mode.label}</strong>
                      <span>
                        {mode.key === config.marcoPolo.authMode ? 'Selected' : mode.implemented ? 'Available' : 'Placeholder'}
                        {' · '}
                        {mode.configured ? 'configured' : 'not configured'}
                      </span>
                      <p>{mode.description}</p>
                      <code>{mode.requiredEnvVars.join(', ')}</code>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <p className="status-text">
              {configError ? `Config unavailable: ${configError}` : 'Loading runtime config...'}
            </p>
          )}
        </div>
      </article>
    </section>
  )
}
