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


class ConnectionListItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    type: str
    display_name: str = Field(alias="displayName")
    capabilities: list[str]
    workspace_path: str | None = Field(alias="workspacePath", default=None)


class ConnectionListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    authenticated: bool
    source: str
    connections: list[ConnectionListItem]


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


class ConnectionSetupStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    setup_session_id: str | None = Field(alias="setupSessionId", default=None)
    status: str
    close_popup: bool | None = Field(alias="closePopup", default=None)
    resume_embedded: bool | None = Field(alias="resumeEmbedded", default=None)
    refresh_connections: bool | None = Field(alias="refreshConnections", default=None)
    connection_name: str | None = Field(alias="connectionName", default=None)
    connection_type: str | None = Field(alias="connectionType", default=None)
    display_name: str | None = Field(alias="displayName", default=None)
    error_code: str | None = Field(alias="errorCode", default=None)
    error_message: str | None = Field(alias="errorMessage", default=None)
    resume_context: dict[str, Any] = Field(alias="resumeContext", default_factory=dict)
    host_mode: str | None = Field(alias="hostMode", default=None)
    host_return_url: str | None = Field(alias="hostReturnUrl", default=None)
    host_origin: str | None = Field(alias="hostOrigin", default=None)
    host_session_id: str | None = Field(alias="hostSessionId", default=None)


class EmbeddedConnectionSetupResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    resource_uri: str = Field(alias="resourceUri")
    tool_result: dict[str, Any] = Field(alias="toolResult")
    tool_output: dict[str, Any] = Field(alias="toolOutput")
    widget_meta: dict[str, Any] = Field(alias="widgetMeta")
    status_url: str | None = Field(alias="statusUrl", default=None)


class EmbeddedConnectionOAuthInitiateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    connection_type: str = Field(alias="connectionType")
    display_name: str = Field(alias="displayName")
    widget_token: str = Field(alias="widgetToken")
    is_sandbox: bool = Field(alias="isSandbox", default=False)


class EmbeddedConnectionOAuthInitiateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    oauth_url: str = Field(alias="oauthUrl")


class EmbeddedSetupSessionLookupResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    setup_session_id: str = Field(alias="setupSessionId")


class WorkspaceShellResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    success: bool
    exit_code: int | None = Field(alias="exitCode", default=None)
    stdout: str = ""
    stderr: str = ""
    execution_time: float | None = Field(alias="executionTime", default=None)


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
