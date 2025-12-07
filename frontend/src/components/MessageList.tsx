import { User, Bot, Brain, Wrench } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  type?: 'text' | 'thought' | 'tool_call' | 'source'
  metadata?: any
}

interface MessageListProps {
  messages: Message[]
}

export default function MessageList({ messages }: MessageListProps) {
  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <MessageItem key={message.id} message={message} />
      ))}
    </div>
  )
}

function MessageItem({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  const isThought = message.type === 'thought'
  const isToolCall = message.type === 'tool_call'

  if (isThought) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500 italic">
        <Brain className="w-4 h-4" />
        <span>{message.content}</span>
      </div>
    )
  }

  if (isToolCall) {
    return (
      <div className="flex items-center gap-2 text-sm text-blue-600">
        <Wrench className="w-4 h-4" />
        <span>{message.content}</span>
      </div>
    )
  }

  return (
    <div
      className={`flex gap-3 message-enter ${
        isUser ? 'flex-row-reverse' : 'flex-row'
      }`}
    >
      {/* 头像 */}
      <div
        className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
          isUser
            ? 'bg-primary-500 text-white'
            : 'bg-gray-200 text-gray-700'
        }`}
      >
        {isUser ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
      </div>

      {/* 消息内容 */}
      <div
        className={`max-w-3xl px-4 py-3 rounded-2xl ${
          isUser
            ? 'bg-primary-500 text-white'
            : 'bg-gray-100 text-gray-900'
        }`}
      >
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
      </div>
    </div>
  )
}
