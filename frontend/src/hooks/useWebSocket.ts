import { useState, useEffect, useCallback, useRef } from 'react'

interface UseWebSocketOptions {
  sessionId: string
  onMessage?: (data: any) => void
  onError?: (error: Event) => void
}

export function useWebSocket({ sessionId, onMessage, onError }: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    // WebSocket URL
    const wsUrl = `ws://localhost:8000/api/v1/chat/ws/${sessionId}`

    // 创建连接
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage?.(data)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      onError?.(error)
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      setIsConnected(false)
    }

    // 清理
    return () => {
      ws.close()
    }
  }, [sessionId, onMessage, onError])

  const sendMessage = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  return {
    isConnected,
    sendMessage,
  }
}
