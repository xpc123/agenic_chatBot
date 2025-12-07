import { useState, useRef, useEffect } from 'react'
import MessageList from './MessageList'
import InputBox from './InputBox'
import { useWebSocket } from '../hooks/useWebSocket'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  type?: 'text' | 'thought' | 'tool_call' | 'source'
  metadata?: any
}

interface ChatWindowProps {
  sessionId: string
}

export default function ChatWindow({ sessionId }: ChatWindowProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const { sendMessage, isConnected } = useWebSocket({
    sessionId,
    onMessage: (data) => {
      if (data.type === 'text') {
        setMessages((prev) => {
          const lastMessage = prev[prev.length - 1]
          
          if (lastMessage && lastMessage.role === 'assistant' && lastMessage.type === 'text') {
            // 追加到现有消息
            return [
              ...prev.slice(0, -1),
              {
                ...lastMessage,
                content: lastMessage.content + data.content,
              },
            ]
          } else {
            // 新消息
            return [
              ...prev,
              {
                id: `msg_${Date.now()}`,
                role: 'assistant',
                content: data.content,
                type: 'text',
              },
            ]
          }
        })
      } else if (data.type === 'thought') {
        setMessages((prev) => [
          ...prev,
          {
            id: `thought_${Date.now()}`,
            role: 'system',
            content: data.content,
            type: 'thought',
          },
        ])
      } else if (data.type === 'tool_call') {
        setMessages((prev) => [
          ...prev,
          {
            id: `tool_${Date.now()}`,
            role: 'system',
            content: data.content,
            type: 'tool_call',
            metadata: data.metadata,
          },
        ])
      } else if (data.type === 'done') {
        setIsLoading(false)
      }
    },
  })

  const handleSendMessage = async (content: string) => {
    // 添加用户消息
    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content,
    }
    
    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    // 发送到后端
    sendMessage({
      message: content,
      use_rag: true,
      use_planning: true,
    })
  }

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex-1 flex flex-col bg-white">
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-6">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center text-gray-500">
              <p className="text-lg font-medium mb-2">👋 你好！</p>
              <p>我是你的智能助手，有什么可以帮助你的吗？</p>
              <div className="mt-6 space-y-2">
                <p className="text-sm text-gray-400">你可以:</p>
                <ul className="text-sm text-gray-400 space-y-1">
                  <li>💬 直接与我对话</li>
                  <li>📄 上传文档作为知识库</li>
                  <li>🔧 我会自动调用合适的工具</li>
                </ul>
              </div>
            </div>
          </div>
        ) : (
          <>
            <MessageList messages={messages} />
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* 输入框 */}
      <InputBox
        onSend={handleSendMessage}
        disabled={!isConnected || isLoading}
        placeholder={
          !isConnected
            ? '连接中...'
            : isLoading
            ? '思考中...'
            : '输入消息... (支持 Shift+Enter 换行)'
        }
      />
    </div>
  )
}
