import sys
from PyQt5.QtWidgets import QApplication
from gui import MainWindow
from audio_handler import AudioHandler

def main():
    """主程序入口"""
    # 创建应用实例
    app = QApplication(sys.argv)
    
    try:
        # 创建音频处理器
        audio_handler = AudioHandler()
        
        # 创建主窗口
        window = MainWindow(audio_handler)
        window.show()
        
        # 运行应用
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"程序启动错误: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 