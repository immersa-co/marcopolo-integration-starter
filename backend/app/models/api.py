from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserProfile(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    provider: str | None = None
    provider_subject: str | None = Field(alias="providerSubject", default=None)
    subject: str
    email: str | None = None
    name: str | None = None
    picture: str | None = None
    hosted_domain: str | None = None
    issuer: str | None = None
    email_verified: bool | None = Field(alias="emailVerified", default=None)


class AuthSessionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    authenticated: bool
    configured: bool
    provider: str | None = None
    user: UserProfile | None = None
    marco_polo_auth_mode: str = Field(alias="marcoPoloAuthMode")
    marco_polo_auth_mode_label: str = Field(alias="marcoPoloAuthModeLabel")
    marco_polo_auth_mode_configured: bool = Field(alias="marcoPoloAuthModeConfigured", default=False)
    marco_polo_configured: bool = Field(alias="marcoPoloConfigured", default=False)
    marco_polo_provisioned: bool = Field(alias="marcoPoloProvisioned", default=False)
    company: str | None = None
    namespace: str | None = None


class ConnectionListItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    type: str
    display_name: str = Field(alias="displayName")
    auth_method: str = Field(alias="authMethod")
    can_manage: bool = Field(alias="canManage")
    access_reason: str | None = Field(alias="accessReason", default=None)
    capabilities: list[str]
    workspace_path: str | None = Field(alias="workspacePath", default=None)


class ConnectionListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    authenticated: bool
    source: str
    connections: list[ConnectionListItem]


class ConnectionTypeSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: str
    display_name: str = Field(alias="displayName")
    category: str | None = None
    description: str | None = None
    auth_methods: list[str] = Field(alias="authMethods")
    setup_method_kinds: list[str] = Field(alias="setupMethodKinds")
    requires_oauth: bool = Field(alias="requiresOAuth")
    deprecated: bool


class ConnectionTypeListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    connection_types: list[ConnectionTypeSummary] = Field(alias="connectionTypes")


class ConnectionTypeUiFeatures(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    delete_warning: str = Field(alias="deleteWarning")
    file_picker: list[str] = Field(alias="filePicker")
    is_file_provider: bool = Field(alias="isFileProvider")
    is_personal: bool = Field(alias="isPersonal")
    logo_key: str | None = Field(alias="logoKey", default=None)
    requires_oauth: bool = Field(alias="requiresOAuth")
    supports_download: bool = Field(alias="supportsDownload")
    supports_upload: bool = Field(alias="supportsUpload")
    uses_local_file_picker: bool = Field(alias="usesLocalFilePicker")


class ConnectionSetupFieldChoice(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    label: str
    value: str


class ConnectionSetupFileSpec(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    allow_create_empty: bool | None = Field(alias="allowCreateEmpty", default=None)
    extensions: list[str] | None = None
    info_text: str | None = Field(alias="infoText", default=None)
    max_size_mb: int | None = Field(alias="maxSizeMb", default=None)


class ConnectionSetupField(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    advanced: bool | None = None
    choices: list[ConnectionSetupFieldChoice] | None = None
    default: Any = None
    description: str | None = None
    file: ConnectionSetupFileSpec | None = None
    group_label: str | None = Field(alias="groupLabel", default=None)
    item_type: str | None = Field(alias="itemType", default=None)
    label: str | None = None
    min_items: int | None = Field(alias="minItems", default=None)
    name: str
    required: bool
    secret: bool = False
    type: str


class ConnectionSetupMethod(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    method: str
    kind: str
    category: str
    display_name: str = Field(alias="displayName")
    description: str | None = None
    fields: list[ConnectionSetupField]


class ConnectionTypeDetailResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: str
    display_name: str = Field(alias="displayName")
    category: str | None = None
    description: str | None = None
    auth_methods: list[str] = Field(alias="authMethods")
    ui_features: ConnectionTypeUiFeatures = Field(alias="uiFeatures")
    setup_methods: list[ConnectionSetupMethod] = Field(alias="setupMethods")


class ConnectionSetupRequest(BaseModel):
    connection_type: str = Field(alias="connectionType")


class DemoConnectionInstallRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    demo_connection: str = Field(alias="demoConnection")


class DemoConnectionInstallResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    connection_name: str = Field(alias="connectionName")
    display_name: str = Field(alias="displayName")
    type: str
    demo_connection_id: str | None = Field(alias="demoConnectionId", default=None)


class CreateConnectionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    connection_type: str = Field(alias="connectionType")
    display_name: str = Field(alias="displayName")
    setup_method: str = Field(alias="setupMethod")
    fields: dict[str, Any]


class CreatedConnectionSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    type: str
    display_name: str = Field(alias="displayName")
    category: str | None = None
    auth_method: str = Field(alias="authMethod")
    can_manage: bool = Field(alias="canManage")


class CreateConnectionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    connection: CreatedConnectionSummary
    message: str


class ManagedConnectionSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    type: str
    display_name: str = Field(alias="displayName")
    auth_method: str = Field(alias="authMethod")
    can_manage: bool = Field(alias="canManage")
    access_reason: str = Field(alias="accessReason")
    category: str | None = None
    connection_type_display_name: str = Field(alias="connectionTypeDisplayName")
    is_demo_connection: bool = Field(alias="isDemoConnection")
    is_owner: bool = Field(alias="isOwner")
    is_personal: bool = Field(alias="isPersonal")
    owner: str | None = None
    share_mode: str = Field(alias="shareMode")


class ManagedConnectionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    connection: ManagedConnectionSummary
    configuration: dict[str, Any]
    connection_type_detail: ConnectionTypeDetailResponse = Field(alias="connectionTypeDetail")
    suggested_setup_method: str | None = Field(alias="suggestedSetupMethod", default=None)
    supports_reauthorize: bool = Field(alias="supportsReauthorize")


class UpdateConnectionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    display_name: str | None = Field(alias="displayName", default=None)
    configuration_patch: dict[str, Any] = Field(alias="configurationPatch", default_factory=dict)


class DeleteConnectionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str


class WorkspaceShellResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    success: bool
    exit_code: int | None = Field(alias="exitCode", default=None)
    stdout: str = ""
    stderr: str = ""
    execution_time: float | None = Field(alias="executionTime", default=None)


class OAuthConnectionTypeOption(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: str
    display_name: str = Field(alias="displayName")
    category: str | None = None


class OAuthConnectionTypesResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    connection_types: list[OAuthConnectionTypeOption] = Field(alias="connectionTypes")


class OAuthSetupStartRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    connection_type: str = Field(alias="connectionType")
    display_name: str = Field(alias="displayName")
    client_session_id: str | None = Field(alias="clientSessionId", default=None)


class ReauthorizeConnectionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    client_session_id: str | None = Field(alias="clientSessionId", default=None)


class OAuthSetupStartResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    setup_session_id: str = Field(alias="setupSessionId")
    status: str
    connection_type: str = Field(alias="connectionType")
    connection_name: str = Field(alias="connectionName")
    display_name: str = Field(alias="displayName")
    authorization_url: str = Field(alias="authorizationUrl")
    return_url: str | None = Field(alias="returnUrl", default=None)
    expires_at: str = Field(alias="expiresAt")


class OAuthSetupSessionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    setup_session_id: str = Field(alias="setupSessionId")
    status: str
    connection_type: str = Field(alias="connectionType")
    connection_name: str = Field(alias="connectionName")
    display_name: str = Field(alias="displayName")
    expires_at: str = Field(alias="expiresAt")
    failure_code: str | None = Field(alias="failureCode", default=None)
    failure_message: str | None = Field(alias="failureMessage", default=None)


class ConnectionTestResultResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    connection_name: str = Field(alias="connectionName")
    status: str
    message: str
    latency_ms: int = Field(alias="latencyMs")


class ChatCreateRequest(BaseModel):
    message: str


class ChatCreateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    chat_id: str = Field(alias="chatId")


class DataConnectionOperation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    description: str
    prompt: str
    connector_type: str = Field(alias="connectorType")


class DataConnectionOperationsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    examples: list[DataConnectionOperation]


class DataConnectionOperationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    example_id: str = Field(alias="exampleId")


class DataConnectionOperationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    example_id: str = Field(alias="exampleId")
    title: str
    message: str
    connection_name: str = Field(alias="connectionName")
    connection_display_name: str = Field(alias="connectionDisplayName")
    connection_type: str = Field(alias="connectionType")
    query_name: str = Field(alias="queryName")
    query_file: str = Field(alias="queryFile")
    row_count: int = Field(alias="rowCount")
    rows: list[dict[str, Any]]


class PublicAuthConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    required: bool
    configured: bool


class PublicMarcoPoloConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mcp_url: str = Field(alias="mcpUrl")
    api_base_url: str = Field(alias="apiBaseUrl")
    web_base_url: str = Field(alias="webBaseUrl")
    auth_mode: str = Field(alias="authMode")
    auth_mode_label: str = Field(alias="authModeLabel")
    auth_mode_description: str = Field(alias="authModeDescription")
    auth_mode_configured: bool = Field(alias="authModeConfigured")
    browser_bootstrap_path: str = Field(alias="browserBootstrapPath")
    browser_bootstrap_redirect: str = Field(alias="browserBootstrapRedirect")
    available_auth_modes: list["PublicMarcoPoloAuthModeOption"] = Field(alias="availableAuthModes")


class PublicMarcoPoloAuthModeOption(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: str
    label: str
    description: str
    implemented: bool
    configured: bool
    required_env_vars: list[str] = Field(alias="requiredEnvVars")


class PublicLlmConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    provider: str
    model: str
    api_base_url: str = Field(alias="apiBaseUrl")
    api_key_configured: bool = Field(alias="apiKeyConfigured")


class RuntimeSkillSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str


class PublicConfigResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    app_env: str = Field(alias="appEnv")
    auth: PublicAuthConfig
    marco_polo: PublicMarcoPoloConfig = Field(alias="marcoPolo")
    llm: PublicLlmConfig
    skills: list[RuntimeSkillSummary]
