import type { TabId } from './types'

export const tabs: Array<{ id: TabId; label: string; eyebrow: string }> = [
  { id: 'configuration', label: 'Configuration', eyebrow: 'Runtime' },
  { id: 'connections', label: 'Connections', eyebrow: 'Setup' },
  { id: 'integrations', label: 'Integrations', eyebrow: 'SDK' },
  { id: 'chatbot', label: 'Chatbot', eyebrow: 'Agent' },
]
