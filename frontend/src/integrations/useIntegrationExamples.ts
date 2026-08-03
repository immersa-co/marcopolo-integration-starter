import { useEffect, useState } from 'react'

import type {
  DataConnectionOperation,
  DataConnectionOperationResponse,
  DataConnectionOperationsResponse,
} from '../app/types'

type UseIntegrationExamplesResult = {
  dataConnectionOperations: DataConnectionOperation[]
  dataConnectionOperationResults: Record<string, DataConnectionOperationResponse>
  integrationBusyId: string | null
  integrationError: string | null
  handleInvokeDataConnectionOperation: (exampleId: string) => Promise<void>
  resetIntegrationState: () => void
}

export default function useIntegrationExamples(apiBaseUrl: string): UseIntegrationExamplesResult {
  const [dataConnectionOperations, setDataConnectionOperations] = useState<DataConnectionOperation[]>([])
  const [dataConnectionOperationResults, setDataConnectionOperationResults] = useState<Record<string, DataConnectionOperationResponse>>({})
  const [integrationBusyId, setIntegrationBusyId] = useState<string | null>(null)
  const [integrationError, setIntegrationError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function loadDataConnectionOperations() {
      try {
        const response = await fetch(`${apiBaseUrl}/api/integrations/examples`, {
          signal: controller.signal,
          credentials: 'include',
        })
        if (!response.ok) {
          throw new Error(`Integration examples request failed with ${response.status}`)
        }
        const payload = (await response.json()) as DataConnectionOperationsResponse
        setDataConnectionOperations(payload.examples)
      } catch (error) {
        if ((error as Error).name === 'AbortError') {
          return
        }
        setIntegrationError((error as Error).message)
      }
    }

    loadDataConnectionOperations()

    return () => controller.abort()
  }, [apiBaseUrl])

  async function handleInvokeDataConnectionOperation(exampleId: string) {
    try {
      setIntegrationBusyId(exampleId)
      setIntegrationError(null)
      const response = await fetch(`${apiBaseUrl}/api/integrations/run`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ exampleId }),
      })

      if (!response.ok) {
        let detail = ''
        try {
          const payload = (await response.json()) as { detail?: string }
          detail = typeof payload.detail === 'string' ? payload.detail : ''
        } catch {
          detail = ''
        }
        throw new Error(
          detail ? `SDK example failed: ${detail}` : `SDK example failed with ${response.status}`,
        )
      }

      const payload = (await response.json()) as DataConnectionOperationResponse
      setDataConnectionOperationResults((current) => ({
        ...current,
        [exampleId]: payload,
      }))
    } catch (error) {
      setIntegrationError((error as Error).message)
    } finally {
      setIntegrationBusyId(null)
    }
  }

  function resetIntegrationState() {
    setIntegrationError(null)
    setDataConnectionOperationResults({})
  }

  return {
    dataConnectionOperations,
    dataConnectionOperationResults,
    integrationBusyId,
    integrationError,
    handleInvokeDataConnectionOperation,
    resetIntegrationState,
  }
}
