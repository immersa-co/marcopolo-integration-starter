export type TabId = 'configuration' | 'connections' | 'chatbot' | 'integrations'

export type UserProfile = {
  provider?: string | null
  providerSubject?: string | null
  subject: string
  email?: string | null
  name?: string | null
  picture?: string | null
  hosted_domain?: string | null
  issuer?: string | null
  emailVerified?: boolean | null
}

export type AuthSession = {
  authenticated: boolean
  configured: boolean
  provider?: string | null
  user?: UserProfile | null
  marcoPoloAuthMode: string
  marcoPoloAuthModeLabel: string
  marcoPoloAuthModeConfigured: boolean
  marcoPoloConfigured: boolean
  marcoPoloProvisioned: boolean
}

export type RuntimeSkill = {
  name: string
  description: string
}

export type ConnectionListItem = {
  name: string
  type: string
  displayName: string
  capabilities: string[]
  workspacePath?: string | null
}

export type ConnectionListResponse = {
  authenticated: boolean
  source: string
  connections: ConnectionListItem[]
}

export type DemoConnectionInstallResponse = {
  message: string
  connectionName: string
  displayName: string
  type: string
  demoConnectionId?: string | null
}

export type EmbeddedConnectionSetupResponse = {
  resourceUri: string
  toolResult: Record<string, unknown>
  toolOutput: {
    type: string
    success?: boolean
    error?: string | null
    message?: string | null
    hint?: string | null
    resolution_mode?: string | null
    resolution_reason?: string | null
    suggested_types?: string[]
    company?: string | null
    workflow_type?: string | null
    url?: string | null
    instructions?: string[]
    next_actions?: string[]
  }
  widgetMeta: {
    ['marcopolo/widget']?: {
      api_token?: string
      api_base_url?: string
    }
  }
  statusUrl?: string | null
}

export type DataConnectionOperation = {
  id: string
  title: string
  description: string
  prompt: string
  connectorType: string
}

export type DataConnectionOperationsResponse = {
  examples: DataConnectionOperation[]
}

export type DataConnectionOperationResponse = {
  exampleId: string
  title: string
  message: string
  connectionName: string
  connectionDisplayName: string
  connectionType: string
  queryName: string
  queryFile: string
  rowCount: number
  rows: Array<Record<string, unknown>>
}

export type MarcoPoloAuthModeOption = {
  key: string
  label: string
  description: string
  implemented: boolean
  configured: boolean
  requiredEnvVars: string[]
}

export type PublicConfig = {
  appEnv: string
  auth: {
    required: boolean
    configured: boolean
  }
  marcoPolo: {
    mcpUrl: string
    apiBaseUrl: string
    webBaseUrl: string
    authMode: string
    authModeLabel: string
    authModeDescription: string
    authModeConfigured: boolean
    browserBootstrapPath: string
    browserBootstrapRedirect: string
    availableAuthModes: MarcoPoloAuthModeOption[]
  }
  llm: {
    provider: string
    model: string
    apiBaseUrl: string
    apiKeyConfigured: boolean
  }
  skills: RuntimeSkill[]
}
