import { ref, onUnmounted, type Ref } from 'vue'
import type { WsStageEvent } from '../api/types'

export interface UseWebSocketOptions {
  onEvent?: (event: WsStageEvent) => void
  autoReconnect?: boolean
  reconnectInterval?: number
}

export function useWebSocket(
  runId: Ref<string | null> | string | null,
  options: UseWebSocketOptions = {}
) {
  const isConnected = ref(false)
  const lastEvent = ref<WsStageEvent | null>(null)
  const error = ref<Event | null>(null)

  let socket: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let isExplicitClose = false

  const targetRunId =
    typeof runId === 'string' || runId === null ? ref(runId) : runId

  function getWsUrl(id: string): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${protocol}//${host}/ws/${encodeURIComponent(id)}`
  }

  function connect() {
    if (!targetRunId.value) return
    isExplicitClose = false

    try {
      const url = getWsUrl(targetRunId.value)
      socket = new WebSocket(url)

      socket.onopen = () => {
        isConnected.value = true
        error.value = null
      }

      socket.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as WsStageEvent
          lastEvent.value = parsed
          if (options.onEvent) {
            options.onEvent(parsed)
          }
        } catch {
          // ignore non-json messages
        }
      }

      socket.onerror = (err) => {
        error.value = err
      }

      socket.onclose = () => {
        isConnected.value = false
        if (!isExplicitClose && (options.autoReconnect ?? true)) {
          reconnectTimer = setTimeout(() => {
            connect()
          }, options.reconnectInterval ?? 2000)
        }
      }
    } catch (e) {
      console.error('Failed to establish WebSocket:', e)
    }
  }

  function disconnect() {
    isExplicitClose = true
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (socket) {
      socket.close()
      socket = null
    }
    isConnected.value = false
  }

  if (targetRunId.value) {
    connect()
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected,
    lastEvent,
    error,
    connect,
    disconnect,
  }
}
