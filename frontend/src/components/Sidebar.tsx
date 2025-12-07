import { Plus, MessageSquare, Settings, FileText } from 'lucide-react'

interface SidebarProps {
  onNewChat: () => void
}

export default function Sidebar({ onNewChat }: SidebarProps) {
  return (
    <div className="w-64 bg-gray-900 text-white flex flex-col">
      {/* 新建对话按钮 */}
      <div className="p-4">
        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-2 px-4 py-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
        >
          <Plus className="w-5 h-5" />
          <span>新建对话</span>
        </button>
      </div>

      {/* 历史对话列表 */}
      <div className="flex-1 overflow-y-auto px-4">
        <div className="text-xs font-semibold text-gray-400 mb-2">
          历史对话
        </div>
        <div className="space-y-1">
          {/* TODO: 加载历史对话 */}
          <div className="px-3 py-2 text-sm text-gray-400 italic">
            暂无历史
          </div>
        </div>
      </div>

      {/* 底部菜单 */}
      <div className="border-t border-gray-800 p-4 space-y-1">
        <button className="w-full flex items-center gap-2 px-3 py-2 hover:bg-gray-800 rounded-lg transition-colors text-sm">
          <FileText className="w-4 h-4" />
          <span>知识库</span>
        </button>
        <button className="w-full flex items-center gap-2 px-3 py-2 hover:bg-gray-800 rounded-lg transition-colors text-sm">
          <Settings className="w-4 h-4" />
          <span>设置</span>
        </button>
      </div>
    </div>
  )
}
