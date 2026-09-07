import type { FormEventHandler } from 'react'
import { useState } from 'react'

import AddDataSourceDialog from './AddDataSourceDialog'
import ManageConnectionDialog from './ManageConnectionDialog'
import type { ConnectionListItem } from '../app/types'

type ConnectionsTabProps = {
  sessionAuthenticated: boolean
  needsMarcoPoloAuthorization: boolean
  marcopoloAccessEnabled: boolean
  connectionsRefreshBusy: boolean
  demoInstallBusy: boolean
  demoConnectionInput: string
  connectionActionMessage: string | null
  connections: ConnectionListItem[]
  connectionsError: string | null
  marcoPoloReady: boolean
  apiBaseUrl: string
  onConnectionsRefresh: () => void
  onDemoInstallSubmit: FormEventHandler<HTMLFormElement>
  onDemoConnectionInputChange: (value: string) => void
  onConnectionCreated: () => Promise<void>
}

export default function ConnectionsTab({
  sessionAuthenticated,
  needsMarcoPoloAuthorization,
  marcopoloAccessEnabled,
  connectionsRefreshBusy,
  demoInstallBusy,
  connections,
  connectionsError,
  marcoPoloReady,
  apiBaseUrl,
  demoConnectionInput,
  connectionActionMessage,
  onConnectionsRefresh,
  onDemoInstallSubmit,
  onDemoConnectionInputChange,
  onConnectionCreated,
}: ConnectionsTabProps) {
  const [managedConnectionName, setManagedConnectionName] = useState<string | null>(null)

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

          <AddDataSourceDialog
            apiBaseUrl={apiBaseUrl}
            marcopoloAccessEnabled={marcopoloAccessEnabled}
            onConnectionsRefresh={onConnectionCreated}
          />
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
                  {connection.type} · {connection.authMethod}
                  {connection.sharedWithCompany ? ' · shared with company' : ''}
                  {' · '}
                  {connection.capabilities.join(', ')}
                </p>
              </div>
              <div className="connection-row-actions">
                <span className="pill ready">Available</span>
                {connection.canManage ? (
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => setManagedConnectionName(connection.name)}
                  >
                    Manage
                  </button>
                ) : null}
              </div>
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
              <span className="pill pending">Completing MarcoPolo authorization</span>
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

      <ManageConnectionDialog
        apiBaseUrl={apiBaseUrl}
        connectionName={managedConnectionName}
        onClose={() => setManagedConnectionName(null)}
        onConnectionsRefresh={onConnectionCreated}
      />
    </section>
  )
}
