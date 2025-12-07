"""
桌面应用集成示例

演示如何将Universal Agentic ChatBot集成到Python桌面应用中
"""
import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QSplitter, QFileDialog,
    QListWidget, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

# 添加SDK路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../sdk/python'))
from chatbot_sdk import create_client, ChatBotConfig


class ChatThread(QThread):
    """聊天线程，避免阻塞UI"""
    message_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, client, message, session_id):
        super().__init__()
        self.client = client
        self.message = message
        self.session_id = session_id
    
    def run(self):
        try:
            # 流式获取响应
            for chunk in self.client.chat(
                message=self.message,
                session_id=self.session_id,
                stream=True
            ):
                self.message_received.emit(chunk)
        except Exception as e:
            self.error_occurred.emit(str(e))


class ChatBotIntegratedApp(QMainWindow):
    """
    集成ChatBot的桌面应用示例
    
    功能：
    1. 文件管理器
    2. AI聊天助手
    3. @路径引用
    4. 知识库上传
    """
    
    def __init__(self):
        super().__init__()
        self.session_id = f"desktop_app_{int(os.times().system * 1000)}"
        self.current_workspace = os.path.expanduser("~")
        
        # 初始化ChatBot SDK
        self.chatbot_client = None
        self.init_chatbot()
        
        # 初始化UI
        self.init_ui()
    
    def init_chatbot(self):
        """初始化ChatBot客户端"""
        try:
            self.chatbot_client = create_client(
                app_id="desktop_demo_app",
                app_secret="demo_secret_123",
                base_url="http://localhost:8000",
                workspace_root=self.current_workspace
            )
            
            # 初始化配置
            result = self.chatbot_client.initialize()
            print(f"ChatBot initialized: {result}")
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "ChatBot初始化失败",
                f"无法连接到ChatBot服务: {e}\n\n请确保服务已启动。"
            )
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("My App with AI Assistant")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：文件浏览器
        left_panel = self.create_file_browser()
        splitter.addWidget(left_panel)
        
        # 右侧：ChatBot助手
        right_panel = self.create_chatbot_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割比例
        splitter.setSizes([400, 800])
        
        main_layout.addWidget(splitter)
    
    def create_file_browser(self):
        """创建文件浏览器"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 标题
        title = QLabel("📁 文件浏览器")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)
        
        # 工作区路径
        path_layout = QHBoxLayout()
        self.workspace_label = QLabel(f"工作区: {self.current_workspace}")
        change_btn = QPushButton("更改")
        change_btn.clicked.connect(self.change_workspace)
        path_layout.addWidget(self.workspace_label)
        path_layout.addWidget(change_btn)
        layout.addLayout(path_layout)
        
        # 文件列表
        self.file_list = QListWidget()
        self.file_list.itemDoubleClicked.connect(self.on_file_double_clicked)
        layout.addWidget(self.file_list)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        upload_btn = QPushButton("📤 上传到知识库")
        upload_btn.clicked.connect(self.upload_to_knowledge_base)
        btn_layout.addWidget(upload_btn)
        
        reference_btn = QPushButton("📎 引用到对话")
        reference_btn.clicked.connect(self.reference_in_chat)
        btn_layout.addWidget(reference_btn)
        
        layout.addLayout(btn_layout)
        
        # 加载文件列表
        self.refresh_file_list()
        
        return panel
    
    def create_chatbot_panel(self):
        """创建ChatBot对话面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 标题
        title_layout = QHBoxLayout()
        title = QLabel("🤖 AI助手")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title_layout.addWidget(title)
        
        status_label = QLabel("● 在线" if self.chatbot_client else "● 离线")
        status_label.setStyleSheet(
            "color: green;" if self.chatbot_client else "color: red;"
        )
        title_layout.addWidget(status_label)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # 聊天历史
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Arial", 10))
        layout.addWidget(self.chat_display)
        
        # 输入区域
        input_layout = QHBoxLayout()
        
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText(
            "输入消息... (支持 @/path/to/file 引用文件)"
        )
        self.message_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.message_input)
        
        send_btn = QPushButton("发送")
        send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(send_btn)
        
        layout.addLayout(input_layout)
        
        # 提示信息
        hint = QLabel(
            "💡 提示: 你可以使用 @/path/to/file 来引用文件，或直接双击文件浏览器中的文件"
        )
        hint.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(hint)
        
        return panel
    
    def refresh_file_list(self):
        """刷新文件列表"""
        self.file_list.clear()
        
        try:
            files = os.listdir(self.current_workspace)
            for f in sorted(files):
                full_path = os.path.join(self.current_workspace, f)
                if os.path.isfile(full_path):
                    # 只显示文本文件
                    if f.endswith(('.txt', '.md', '.py', '.json', '.yaml', '.csv')):
                        self.file_list.addItem(f"📄 {f}")
                elif os.path.isdir(full_path):
                    self.file_list.addItem(f"📁 {f}")
        except Exception as e:
            self.file_list.addItem(f"❌ 无法读取: {e}")
    
    def change_workspace(self):
        """更改工作区"""
        new_path = QFileDialog.getExistingDirectory(
            self,
            "选择工作区目录",
            self.current_workspace
        )
        
        if new_path:
            self.current_workspace = new_path
            self.workspace_label.setText(f"工作区: {new_path}")
            self.refresh_file_list()
            
            # 更新ChatBot的工作区
            if self.chatbot_client:
                self.chatbot_client.config.workspace_root = new_path
    
    def on_file_double_clicked(self, item):
        """双击文件时引用到对话"""
        filename = item.text().replace("📄 ", "").replace("📁 ", "")
        relative_path = f"/{filename}"
        
        current_text = self.message_input.text()
        self.message_input.setText(f"{current_text} @{relative_path}")
        self.message_input.setFocus()
    
    def reference_in_chat(self):
        """将选中文件引用到对话"""
        current_item = self.file_list.currentItem()
        if current_item:
            self.on_file_double_clicked(current_item)
    
    def upload_to_knowledge_base(self):
        """上传文件到知识库"""
        current_item = self.file_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择一个文件")
            return
        
        if not self.chatbot_client:
            QMessageBox.warning(self, "错误", "ChatBot未连接")
            return
        
        filename = current_item.text().replace("📄 ", "")
        file_path = os.path.join(self.current_workspace, filename)
        
        try:
            result = self.chatbot_client.upload_file(
                file_path=file_path,
                metadata={
                    "source": "desktop_app",
                    "workspace": self.current_workspace
                }
            )
            
            QMessageBox.information(
                self,
                "成功",
                f"文件 {filename} 已上传到知识库"
            )
            
            self.append_chat_message(
                "系统",
                f"📤 已将 {filename} 上传到知识库"
            )
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"上传失败: {e}")
    
    def send_message(self):
        """发送消息"""
        message = self.message_input.text().strip()
        if not message:
            return
        
        if not self.chatbot_client:
            QMessageBox.warning(self, "错误", "ChatBot未连接")
            return
        
        # 显示用户消息
        self.append_chat_message("你", message)
        self.message_input.clear()
        
        # 显示思考状态
        self.append_chat_message("AI", "💭 思考中...")
        
        # 创建线程处理聊天
        self.chat_thread = ChatThread(
            self.chatbot_client,
            message,
            self.session_id
        )
        self.chat_thread.message_received.connect(self.on_chat_chunk)
        self.chat_thread.error_occurred.connect(self.on_chat_error)
        self.chat_thread.start()
    
    def on_chat_chunk(self, chunk):
        """处理聊天响应块"""
        chunk_type = chunk.get("type")
        content = chunk.get("content", "")
        
        if chunk_type == "text":
            # 追加文本（清除"思考中"提示）
            current_text = self.chat_display.toPlainText()
            if "💭 思考中..." in current_text:
                current_text = current_text.replace("AI: 💭 思考中...\n", "AI: ")
            self.chat_display.setPlainText(current_text + content)
        
        elif chunk_type == "thought":
            self.append_chat_message("💭", content)
        
        elif chunk_type == "tool_call":
            self.append_chat_message("🔧", content)
        
        elif chunk_type == "context":
            self.append_chat_message("📎", content)
        
        elif chunk_type == "sources":
            sources = chunk.get("metadata", {}).get("count", 0)
            self.append_chat_message("📚", f"检索到 {sources} 个相关文档")
    
    def on_chat_error(self, error):
        """处理聊天错误"""
        self.append_chat_message("❌ 错误", error)
    
    def append_chat_message(self, sender, message):
        """追加聊天消息"""
        self.chat_display.append(f"\n{sender}: {message}")
        # 滚动到底部
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 创建主窗口
    window = ChatBotIntegratedApp()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
