from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTextEdit, QComboBox, QLabel,
                             QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt, QTimer
import docx

class MainWindow(QMainWindow):
    def __init__(self, audio_handler):
        super().__init__()
        self.audio_handler = audio_handler
        # 连接信号
        self.audio_handler.text_received.connect(self.append_text)
        self.audio_handler.error_occurred.connect(self.show_error)
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle('实时语音转文字工具')
        self.setMinimumSize(800, 600)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 控制面板
        control_layout = QHBoxLayout()
        
        # 设备选择
        device_label = QLabel('音频设备:')
        self.device_combo = QComboBox()
        self.update_devices()
        
        # 语言选择
        language_label = QLabel('识别语言:')
        self.language_combo = QComboBox()
        self.language_combo.addItems(['中文 (zh-CN)', '英语 (en-US)', '日语 (ja-JP)'])
        self.language_combo.currentTextChanged.connect(self.change_language)
        
        # 控制按钮
        self.start_button = QPushButton('开始录音')
        self.start_button.clicked.connect(self.toggle_recording)
        self.save_button = QPushButton('保存文本')
        self.save_button.clicked.connect(self.save_text)
        
        # 添加控件到控制面板
        control_layout.addWidget(device_label)
        control_layout.addWidget(self.device_combo)
        control_layout.addWidget(language_label)
        control_layout.addWidget(self.language_combo)
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.save_button)
        
        # 文本编辑区
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText('识别结果将显示在这里...')
        
        # 添加所有部件到主布局
        layout.addLayout(control_layout)
        layout.addWidget(self.text_edit)
        
        self.is_recording = False
    
    def update_devices(self):
        """更新音频设备列表"""
        self.device_combo.clear()
        devices = self.audio_handler.get_audio_devices()
        for device_id, device_name in devices:
            self.device_combo.addItem(device_name, device_id)
    
    def change_language(self, language_text):
        """更改识别语言"""
        language_code = language_text.split('(')[1].strip(')')
        self.audio_handler.set_language(language_code)
    
    def toggle_recording(self):
        """切换录音状态"""
        if not self.is_recording:
            device_index = self.device_combo.currentData()
            self.audio_handler.start_recording(device_index)
            self.start_button.setText('停止录音')
        else:
            self.audio_handler.stop_recording()
            self.start_button.setText('开始录音')
        
        self.is_recording = not self.is_recording
    
    def append_text(self, text):
        """添加识别文本"""
        if text:
            self.text_edit.append(text)
    
    def show_error(self, error_message):
        """显示错误信息"""
        QMessageBox.warning(self, "错误", error_message)
    
    def save_text(self):
        """保存文本内容"""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "保存文件",
            "",
            "文本文件 (*.txt);;Word文档 (*.docx)"
        )
        
        if not file_name:
            return
            
        text = self.text_edit.toPlainText()
        
        try:
            if file_name.endswith('.txt'):
                with open(file_name, 'w', encoding='utf-8') as f:
                    f.write(text)
            elif file_name.endswith('.docx'):
                doc = docx.Document()
                doc.add_paragraph(text)
                doc.save(file_name)
                
            QMessageBox.information(self, "成功", "文件保存成功！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存文件时出错：{str(e)}")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.is_recording:
            self.audio_handler.stop_recording()
        event.accept() 