import { useState } from 'react'
import './App.css'
import AppShell from './app/AppShell'
import type { TabId } from './app/types'
import AuthGateScreen from './auth/AuthGateScreen'
import AuthLoadingScreen from './auth/AuthLoadingScreen'
import OAuthReturnBridge from './auth/OAuthReturnBridge'
import useAuthRuntime from './auth/useAuthRuntime'
import ChatWorkspaceTab from './chatbot/ChatWorkspaceTab'
import useChatRuntime from './chatbot/useChatRuntime'
import ConfigurationTab from './configuration/ConfigurationTab'
import ConnectionsTab from './connections/ConnectionsTab'
import useConnectionsFeature from './connections/useConnectionsFeature'
import IntegrationsTab from './integrations/IntegrationsTab'
import useIntegrationExamples from './integrations/useIntegrationExamples'

function App() {
  const [activeTab, setActiveTab] = useState<TabId>('connections')
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8001'

  function resetAppState() {
    connectionsFeature.resetConnectionsState()
    integrationsFeature.resetIntegrationState()
  }

  const {
    config,
    session,
    configError,
    sessionError,
    modeSelectionBusy,
    demoSessionBusy,
    demoUserEmail,
    setDemoUserEmail,
    selectableMarcoPoloModes,
    selectedMarcoPoloAuthMode,
    usesWorkosConnect,
    needsMarcoPoloAuthorization,
    shouldGateApp,
    handleLogout,
    handleMarcoPoloAuthModeChange,
    handleDemoSessionSubmit,
  } = useAuthRuntime({
    apiBaseUrl,
    onResetAppState: resetAppState,
    onMarcoPoloReadyChange: () => undefined,
  })

  const connectionsFeature = useConnectionsFeature({
    apiBaseUrl,
    sessionAuthenticated: Boolean(session?.authenticated),
    needsMarcoPoloAuthorization,
    selectedMarcoPoloAuthMode,
    onMarcoPoloReadyChange: () => undefined,
  })
  const integrationsFeature = useIntegrationExamples(apiBaseUrl)

  const {
    connections,
    connectionsError,
    connectionActionMessage,
    demoInstallBusy,
    embeddedSetupBusy,
    connectionsRefreshBusy,
    demoConnectionInput,
    newConnectionTypeInput,
    embeddedSetup,
    activeEmbeddedConnectionName,
    marcoPoloReady,
    setDemoConnectionInput,
    setNewConnectionTypeInput,
    setEmbeddedSetup,
    handleConnectionsRefresh,
    handleDemoInstallSubmit,
    handleEmbeddedSetupSubmit,
    refreshConnections,
  } = connectionsFeature

  const {
    dataConnectionOperations,
    dataConnectionOperationResults,
    integrationBusyId,
    integrationError,
    handleInvokeDataConnectionOperation,
  } = integrationsFeature

  const marcopoloAccessEnabled = Boolean(session?.authenticated && marcoPoloReady)
  const availableChatConnectionNames = connections
    .map((connection) => connection.displayName)
    .filter((name, index, values) => values.indexOf(name) === index)
    .slice(0, 4)
  const {
    chatBusy,
    chatInput,
    chatPlaceholder,
    chatTranscriptRef,
    preambleItems,
    promptGroups,
    collapsedPromptIds,
    selectedToolItem,
    selectedToolContext,
    selectedToolRequest,
    selectedToolResponse,
    setChatInput,
    handleClearChat,
    handleChatSubmit,
    handleDeletePromptGroup,
    togglePromptGroup,
    renderChatTranscriptItem,
  } = useChatRuntime({
    apiBaseUrl,
    marcopoloAccessEnabled,
    needsMarcoPoloAuthorization,
    availableChatConnectionNames,
  })

  const isOauthReturnPage = window.location.pathname === '/oauth-return'

  if (isOauthReturnPage) {
    return (
      <OAuthReturnBridge />
    )
  }

  if (!config || !session) {
    return <AuthLoadingScreen configError={configError} sessionError={sessionError} />
  }

  if (shouldGateApp) {
    return (
      <AuthGateScreen
        config={config}
        selectableMarcoPoloModes={selectableMarcoPoloModes}
        selectedMarcoPoloAuthMode={selectedMarcoPoloAuthMode}
        modeSelectionBusy={modeSelectionBusy}
        demoSessionBusy={demoSessionBusy}
        demoUserEmail={demoUserEmail}
        sessionError={sessionError}
        configError={configError}
        onMarcoPoloAuthModeChange={(mode) => {
          void handleMarcoPoloAuthModeChange(mode)
        }}
        onDemoUserEmailChange={setDemoUserEmail}
        onDemoSessionSubmit={handleDemoSessionSubmit}
      />
    )
  }

  const activeTabContent =
    activeTab === 'configuration' ? (
      <ConfigurationTab
        config={config}
        configError={configError}
        marcoPoloReady={marcoPoloReady}
      />
    ) : activeTab === 'connections' ? (
      <ConnectionsTab
        sessionAuthenticated={Boolean(session?.authenticated)}
        needsMarcoPoloAuthorization={needsMarcoPoloAuthorization}
        marcopoloAccessEnabled={marcopoloAccessEnabled}
        connectionsRefreshBusy={connectionsRefreshBusy}
        demoInstallBusy={demoInstallBusy}
        embeddedSetupBusy={embeddedSetupBusy}
        demoConnectionInput={demoConnectionInput}
        newConnectionTypeInput={newConnectionTypeInput}
        connectionActionMessage={connectionActionMessage}
        connections={connections}
        connectionsError={connectionsError}
        marcoPoloReady={marcoPoloReady}
        embeddedSetup={embeddedSetup}
        apiBaseUrl={apiBaseUrl}
        marcoPoloWebBaseUrl={config.marcoPolo.webBaseUrl}
        activeEmbeddedConnectionName={activeEmbeddedConnectionName}
        onConnectionsRefresh={() => {
          handleConnectionsRefresh().catch(() => undefined)
        }}
        onDemoInstallSubmit={handleDemoInstallSubmit}
        onDemoConnectionInputChange={setDemoConnectionInput}
        onEmbeddedSetupSubmit={handleEmbeddedSetupSubmit}
        onNewConnectionTypeInputChange={setNewConnectionTypeInput}
        onEmbeddedSetupClose={() => setEmbeddedSetup(null)}
        onEmbeddedSetupRefreshConnections={async () => {
          await refreshConnections()
        }}
      />
    ) : activeTab === 'integrations' ? (
      <IntegrationsTab
        dataConnectionOperations={dataConnectionOperations}
        dataConnectionOperationResults={dataConnectionOperationResults}
        integrationBusyId={integrationBusyId}
        integrationError={integrationError}
        marcopoloAccessEnabled={marcopoloAccessEnabled}
        needsMarcoPoloAuthorization={needsMarcoPoloAuthorization}
        onInvokeDataConnectionOperation={(exampleId) => {
          void handleInvokeDataConnectionOperation(exampleId)
        }}
      />
    ) : (
      <ChatWorkspaceTab
        chatBusy={chatBusy}
        chatInput={chatInput}
        chatPlaceholder={chatPlaceholder}
        marcopoloAccessEnabled={marcopoloAccessEnabled}
        chatTranscriptRef={chatTranscriptRef}
        preambleItems={preambleItems}
        promptGroups={promptGroups}
        collapsedPromptIds={collapsedPromptIds}
        selectedToolItem={selectedToolItem}
        selectedToolContext={selectedToolContext}
        selectedToolRequest={selectedToolRequest}
        selectedToolResponse={selectedToolResponse}
        onClearChat={handleClearChat}
        onChatSubmit={handleChatSubmit}
        onChatInputChange={setChatInput}
        onTogglePromptGroup={togglePromptGroup}
        onDeletePromptGroup={handleDeletePromptGroup}
        renderChatTranscriptItem={renderChatTranscriptItem}
      />
    )

  return (
    <AppShell
      activeTab={activeTab}
      config={config}
      modeSelectionBusy={modeSelectionBusy}
      selectableMarcoPoloModes={selectableMarcoPoloModes}
      selectedMarcoPoloAuthMode={selectedMarcoPoloAuthMode}
      session={session}
      sessionError={sessionError}
      usesWorkosConnect={usesWorkosConnect}
      onLogout={() => {
        void handleLogout()
      }}
      onMarcoPoloAuthModeChange={(mode) => {
        void handleMarcoPoloAuthModeChange(mode)
      }}
      onTabChange={setActiveTab}
    >
      {activeTabContent}
    </AppShell>
  )
}

export default App
