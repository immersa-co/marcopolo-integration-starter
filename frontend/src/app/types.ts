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
  company: string | null
  namespace: string | null
}

export type RuntimeSkill = {
  name: string
  description: string
}

export type ConnectionListItem = {
  name: string
  type: string
  displayName: string
  authMethod: string
  canManage: boolean
  accessReason?: string | null
  shareMode?: string | null
  sharedWithCompany?: boolean
  capabilities: string[]
  workspacePath?: string | null
}

export type ConnectionListResponse = {
  authenticated: boolean
  source: string
  connections: ConnectionListItem[]
}

export type ConnectionTypeSummary = {
  type: string
  displayName: string
  category?: string | null
  description?: string | null
  authMethods: string[]
  setupMethodKinds: string[]
  requiresOAuth: boolean
  deprecated: boolean
}

export type ConnectionTypeListResponse = {
  connectionTypes: ConnectionTypeSummary[]
}

export type ConnectionTypeUiFeatures = {
  deleteWarning: string
  filePicker: string[]
  isFileProvider: boolean
  isPersonal: boolean
  logoKey?: string | null
  requiresOAuth: boolean
  supportsDownload: boolean
  supportsUpload: boolean
  usesLocalFilePicker: boolean
}

export type ConnectionSetupFieldChoice = {
  label: string
  value: string
}

export type ConnectionSetupFileSpec = {
  allowCreateEmpty?: boolean | null
  extensions?: string[] | null
  infoText?: string | null
  maxSizeMb?: number | null
}

export type ConnectionSetupField = {
  advanced?: boolean | null
  choices?: ConnectionSetupFieldChoice[] | null
  default?: unknown
  description?: string | null
  file?: ConnectionSetupFileSpec | null
  groupLabel?: string | null
  itemType?: string | null
  label?: string | null
  minItems?: number | null
  name: string
  required: boolean
  secret: boolean
  type: string
}

export type ConnectionSetupMethod = {
  method: string
  kind: string
  category: string
  displayName: string
  description?: string | null
  fields: ConnectionSetupField[]
}

export type ConnectionTypeDetail = {
  type: string
  displayName: string
  category?: string | null
  description?: string | null
  authMethods: string[]
  uiFeatures: ConnectionTypeUiFeatures
  setupMethods: ConnectionSetupMethod[]
}

export type DemoConnectionInstallResponse = {
  message: string
  connectionName: string
  displayName: string
  type: string
  demoConnectionId?: string | null
}

export type CreateConnectionResponse = {
  connection: {
    name: string
    type: string
    displayName: string
    category?: string | null
    authMethod: string
    canManage: boolean
    shareMode?: string | null
    sharedWithCompany?: boolean
  }
  message: string
}

export type ManagedConnectionResponse = {
  connection: {
    name: string
    type: string
    displayName: string
    authMethod: string
    canManage: boolean
    accessReason: string
    category?: string | null
    connectionTypeDisplayName: string
    isDemoConnection: boolean
    isOwner: boolean
    isPersonal: boolean
    owner?: string | null
    shareMode: string
    sharedWithCompany: boolean
  }
  configuration: Record<string, unknown>
  connectionTypeDetail: ConnectionTypeDetail
  suggestedSetupMethod?: string | null
  supportsReauthorize: boolean
}

export type DeleteConnectionResponse = {
  message: string
}

export type ConnectionTestResult = {
  connectionName: string
  status: string
  message: string
  latencyMs: number
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
