import type { FormEventHandler } from 'react'

import EmbeddedConnectionSetupHost from './EmbeddedConnectionSetupHost'
import type { ConnectionListItem, EmbeddedConnectionSetupResponse } from '../app/types'

type ConnectionsTabProps = {
  sessionAuthenticated: boolean
  needsMarcoPoloAuthorization: boolean
  marcopoloAccessEnabled: boolean
  connectionsRefreshBusy: boolean
  demoInstallBusy: boolean
  embeddedSetupBusy: boolean
  demoConnectionInput: string
  newConnectionTypeInput: string
  connectionActionMessage: string | null
  connections: ConnectionListItem[]
  connectionsError: string | null
  marcoPoloReady: boolean
  embeddedSetup: EmbeddedConnectionSetupResponse | null
  apiBaseUrl: string
  marcoPoloWebBaseUrl: string
  activeEmbeddedConnectionName?: string | null
  onConnectionsRefresh: () => void
  onDemoInstallSubmit: FormEventHandler<HTMLFormElement>
  onDemoConnectionInputChange: (value: string) => void
  onEmbeddedSetupSubmit: FormEventHandler<HTMLFormElement>
  onNewConnectionTypeInputChange: (value: string) => void
  onEmbeddedSetupClose: () => void
  onEmbeddedSetupRefreshConnections: () => Promise<void>
}

export default function ConnectionsTab({
  sessionAuthenticated,
  needsMarcoPoloAuthorization,
  marcopoloAccessEnabled,
  connectionsRefreshBusy,
  demoInstallBusy,
  embeddedSetupBusy,
  demoConnectionInput,
  newConnectionTypeInput,
  connectionActionMessage,
  connections,
  connectionsError,
  marcoPoloReady,
  embeddedSetup,
  apiBaseUrl,
  marcoPoloWebBaseUrl,
  activeEmbeddedConnectionName,
  onConnectionsRefresh,
  onDemoInstallSubmit,
  onDemoConnectionInputChange,
  onEmbeddedSetupSubmit,
  onNewConnectionTypeInputChange,
  onEmbeddedSetupClose,
  onEmbeddedSetupRefreshConnections,
}: ConnectionsTabProps) {
  return (
    <section className="workspace-grid">
      <article className="panel">
        <div className="panel-header panel-header-split">
          <div>
            <p className="section-label">Setup actions</p>
            <h2>Install demo data or configure a real connection.</h2>
          </div>
          <button
            type="button"
            className="secondary-button panel-header-button"
            disabled={!sessionAuthenticated || needsMarcoPoloAuthorization || connectionsRefreshBusy}
            onClick={onConnectionsRefresh}
          >
            {connectionsRefreshBusy ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
        <div className="connector-list">
          {!marcopoloAccessEnabled ? (
            <div className="placeholder-row emphasis">
              <span>MarcoPolo access</span>
              <span className="pill pending">
                {connectionsError ? 'Unavailable' : 'Checking access'}
              </span>
            </div>
          ) : null}
          <form className="connector-card connector-form" onSubmit={onDemoInstallSubmit}>
            <div className="connector-copy">
              <h3>Install Demo Data</h3>
              <p>Install a hosted demo connection into the current MarcoPolo workspace.</p>
            </div>
            <label className="auth-field">
              <span>Demo connection type</span>
              <input
                type="text"
                value={demoConnectionInput}
                onChange={(event) => onDemoConnectionInputChange(event.target.value)}
                placeholder="salesforce, aws_s3, snowflake, bigquery, mongodb"
                disabled={!marcopoloAccessEnabled || demoInstallBusy}
              />
            </label>
            <p className="status-inline">
              Available demo connections: Salesforce, AWS S3, Snowflake, BigQuery, MongoDB.
            </p>
            <div className="connector-actions">
              <button
                type="submit"
                className="primary-button"
                disabled={!marcopoloAccessEnabled || demoInstallBusy}
              >
                {demoInstallBusy ? 'Installing...' : 'Install Demo Connection'}
              </button>
            </div>
          </form>

          <form className="connector-card connector-form" onSubmit={onEmbeddedSetupSubmit}>
            <div className="connector-copy">
              <h3>Connect a Data Source</h3>
              <p>Launch the embedded MarcoPolo connection setup app for any supported connector type.</p>
            </div>
            <label className="auth-field">
              <span>Connection type</span>
              <input
                type="text"
                value={newConnectionTypeInput}
                onChange={(event) => onNewConnectionTypeInputChange(event.target.value)}
                placeholder="jira, salesforce, github, postgres, snowflake, ..."
                disabled={!marcopoloAccessEnabled || embeddedSetupBusy}
              />
            </label>
            <p className="status-inline">
              Enter any connection type supported by MarcoPolo. Review the supported connectors at{' '}
              <code>https://mcp.marcopolo.dev/app/connections/new</code>.
            </p>
            <div className="connector-actions">
              <button
                type="submit"
                className="primary-button"
                disabled={!marcopoloAccessEnabled || embeddedSetupBusy}
              >
                {embeddedSetupBusy ? 'Loading host...' : 'Connect In App'}
              </button>
            </div>
          </form>
          {connectionActionMessage ? (
            <div className="placeholder-row emphasis">
              <div>
                <strong>Last action</strong>
                <p className="status-inline">{connectionActionMessage}</p>
              </div>
              <span className="pill ready">Complete</span>
            </div>
          ) : null}
        </div>
        {embeddedSetup ? (
          <EmbeddedConnectionSetupHost
            apiBaseUrl={apiBaseUrl}
            marcoPoloWebBaseUrl={marcoPoloWebBaseUrl}
            payload={embeddedSetup}
            existingConnectionName={activeEmbeddedConnectionName ?? undefined}
            onClose={onEmbeddedSetupClose}
            onRefreshConnections={onEmbeddedSetupRefreshConnections}
          />
        ) : null}
      </article>

      <article className="panel">
        <div className="panel-header">
          <p className="section-label">Available connections</p>
          <h2>MarcoPolo `list_connections` dial tone.</h2>
        </div>
        <div className="placeholder-list">
          {connections.map((connection) => (
            <div key={connection.name} className="placeholder-row">
              <div>
                <strong>{connection.displayName}</strong>
                <p className="status-inline">
                  {connection.type} · {connection.capabilities.join(', ')}
                </p>
              </div>
              <span className="pill ready">Available</span>
            </div>
          ))}
          {!connections.length && !connectionsError && marcoPoloReady ? (
            <div className="placeholder-row">
              <span>No connections</span>
              <span className="pill pending">None available yet</span>
            </div>
          ) : null}
          {needsMarcoPoloAuthorization ? (
            <div className="placeholder-row emphasis">
              <span>Connection status</span>
              <span className="pill pending">Completing MarcoPolo Connect sign-in</span>
            </div>
          ) : null}
          {!needsMarcoPoloAuthorization && !marcoPoloReady && !connectionsError ? (
            <div className="placeholder-row">
              <span>Connection status</span>
              <span className="pill pending">Checking MarcoPolo access</span>
            </div>
          ) : null}
          {connectionsError ? (
            <div className="placeholder-row emphasis">
              <span>Connection status</span>
              <span className="pill pending">{connectionsError}</span>
            </div>
          ) : null}
        </div>
      </article>
    </section>
  )
}
