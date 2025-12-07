import { useState } from 'react'
import ChatWindow from './components/ChatWindow'
import Sidebar from './components/Sidebar'
import { Bot } from 'lucide-react'

function App() {
  const [sessionId, setSessionId] = useState<string>(() => {
    return `session_${Date.now()}`
  })

  const handleNewChat = () => {
    setSessionId(`session_${Date.now()}`)
  }

  return (
    <div className="flex h-screen bg-gray-100">
      {/* 侧边栏 */}
      <Sidebar onNewChat={handleNewChat} />
      
      {/* 主聊天区域 */}
      <div className="flex-1 flex flex-col">
        {/* 头部 */}
        <header className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center gap-3">
            <Bot className="w-8 h-8 text-primary-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Agentic ChatBot
              </h1>
              <p className="text-sm text-gray-600">
                智能对话助手 · 支持Planning、Memory和RAG
              </p>
            </div>
          </div>
        </header>

        {/* 聊天窗口 */}
        <ChatWindow sessionId={sessionId} />
      </div>
    </div>
  )
}

export default App
