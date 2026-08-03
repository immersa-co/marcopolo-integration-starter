import type {
  DataConnectionOperation,
  DataConnectionOperationResponse,
} from '../app/types'
import { formatChatValue, getTableColumns } from '../chatbot/utils'

type IntegrationsTabProps = {
  dataConnectionOperations: DataConnectionOperation[]
  dataConnectionOperationResults: Record<string, DataConnectionOperationResponse>
  integrationBusyId: string | null
  integrationError: string | null
  marcopoloAccessEnabled: boolean
  needsMarcoPoloAuthorization: boolean
  onInvokeDataConnectionOperation: (exampleId: string) => void
}

export default function IntegrationsTab({
  dataConnectionOperations,
  dataConnectionOperationResults,
  integrationBusyId,
  integrationError,
  marcopoloAccessEnabled,
  needsMarcoPoloAuthorization,
  onInvokeDataConnectionOperation,
}: IntegrationsTabProps) {
  return (
    <section className="integrations-layout">
      <article className="panel">
        <div className="panel-header">
          <p className="section-label">Integrations</p>
          <h2>SDK-first examples for direct application code.</h2>
        </div>
        <p className="integration-copy">
          These examples call the published <code>marcopolo-sdk</code> from the backend, separate from the Chatbot and embedded MCP app flows.
        </p>
        <div className="integration-example-list">
          {dataConnectionOperations.map((example) => {
            const result = dataConnectionOperationResults[example.id]
            const busy = integrationBusyId === example.id
            const columns = result ? getTableColumns(result.rows) : []

            return (
              <article key={example.id} className="integration-card">
                <div className="integration-card-copy">
                  <p className="section-label">Seed asset</p>
                  <h3>{example.title}</h3>
                  <p>{example.description}</p>
                  <button
                    type="button"
                    className="integration-prompt-button"
                    disabled={!marcopoloAccessEnabled || busy}
                    onClick={() => onInvokeDataConnectionOperation(example.id)}
                  >
                    {busy ? 'Running SDK example…' : example.prompt}
                  </button>
                </div>
                {result ? (
                  <div className="integration-result-card">
                    <div className="integration-result-header">
                      <div>
                        <p className="section-label">Result</p>
                        <h4>{result.message}</h4>
                      </div>
                      <span className="pill ready">{result.rowCount} rows</span>
                    </div>
                    <div className="integration-meta">
                      <span><strong>Connection:</strong> {result.connectionDisplayName}</span>
                      <span><strong>Type:</strong> {result.connectionType}</span>
                      <span><strong>Query:</strong> {result.queryName}</span>
                    </div>
                    {result.rows.length ? (
                      <div className="table-preview">
                        <table className="chat-data-table">
                          <thead>
                            <tr>
                              {columns.map((column) => (
                                <th key={`${example.id}-${column}`}>{column}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {result.rows.map((row, rowIndex) => (
                              <tr key={`${example.id}-row-${rowIndex}`}>
                                {columns.map((column) => (
                                  <td key={`${example.id}-${rowIndex}-${column}`}>{formatChatValue(row[column])}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="placeholder-row">
                        <span>Execution completed</span>
                        <span className="pill pending">No tabular rows returned</span>
                      </div>
                    )}
                  </div>
                ) : null}
              </article>
            )
          })}
        </div>
        {integrationError ? (
          <div className="placeholder-row emphasis">
            <span>Integration status</span>
            <span className="pill pending">{integrationError}</span>
          </div>
        ) : null}
        {!dataConnectionOperations.length && !integrationError ? (
          <div className="placeholder-row">
            <span>Integration examples</span>
            <span className="pill pending">Loading SDK examples</span>
          </div>
        ) : null}
        {!marcopoloAccessEnabled ? (
          <div className="placeholder-row emphasis">
            <span>SDK access</span>
            <span className="pill pending">
              {needsMarcoPoloAuthorization ? 'Completing MarcoPolo Connect sign-in' : 'Sign in to run SDK examples'}
            </span>
          </div>
        ) : null}
      </article>
    </section>
  )
}
