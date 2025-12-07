import { useState, KeyboardEvent } from 'react'
import { Send, Paperclip } from 'lucide-react'

interface InputBoxProps {
  onSend: (message: string) => void
  disabled?: boolean
  placeholder?: string
}

export default function InputBox({
  onSend,
  disabled = false,
  placeholder = '输入消息...',
}: InputBoxProps) {
  const [input, setInput] = useState('')

  const handleSend = () => {
    if (!input.trim() || disabled) return

    onSend(input.trim())
    setInput('')
  }

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="border-t border-gray-200 p-4 bg-white">
      <div className="max-w-4xl mx-auto flex gap-3">
        {/* 附件按钮 */}
        <button
          className="p-3 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors"
          title="上传文档"
        >
          <Paperclip className="w-5 h-5" />
        </button>

        {/* 输入框 */}
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="flex-1 px-4 py-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          style={{
            minHeight: '52px',
            maxHeight: '200px',
          }}
        />

        {/* 发送按钮 */}
        <button
          onClick={handleSend}
          disabled={disabled || !input.trim()}
          className="px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
        >
          <Send className="w-5 h-5" />
        </button>
      </div>

      <div className="max-w-4xl mx-auto mt-2 text-xs text-gray-500 text-center">
        按 Enter 发送，Shift + Enter 换行
      </div>
    </div>
  )
}
