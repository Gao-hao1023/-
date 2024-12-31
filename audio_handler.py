import speech_recognition as sr
import sounddevice as sd
import numpy as np
from threading import Thread, Event, Lock
import queue
from PyQt5.QtCore import QObject, pyqtSignal
from vosk import Model, KaldiRecognizer
import json
import os

class AudioHandler(QObject):
    text_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.audio_queue = queue.Queue()
        self.stop_event = Event()
        self.is_recording = False
        self.current_language = 'zh-CN'
        self.sample_rate = 16000
        self.chunk_size = 1024
        self.processing_thread = None
        self.lock = Lock()
        self.vosk_model = None
        self.kaldi_recognizer = None
        self.last_text = ""  # 用于存储上一次识别的文本
        self.partial_text = ""  # 用于存储部分识别的文本
        self.silence_frames = 0  # 用于计数静音帧
        self.SILENCE_THRESHOLD = 30  # 静音阈值，可以根据需要调整
        self.initialize_vosk()
        
    def initialize_vosk(self):
        """初始化Vosk模型"""
        try:
            model_path = self.get_model_path()
            if not os.path.exists(model_path):
                self.error_occurred.emit("请先下载语音模型！\n"
                                      "1. 访问 https://alphacephei.com/vosk/models\n"
                                      "2. 下载对应语言模型（中文：vosk-model-small-cn-0.22）\n"
                                      "3. 解压到程序所在目录的 model 文件夹中")
                return
            self.vosk_model = Model(model_path)
            self.kaldi_recognizer = KaldiRecognizer(self.vosk_model, self.sample_rate)
        except Exception as e:
            self.error_occurred.emit(f"初始化语音模型失败: {str(e)}")
    
    def get_model_path(self):
        """获取模型路径"""
        if self.current_language == 'zh-CN':
            return "model/vosk-model-small-cn-0.22"
        elif self.current_language == 'en-US':
            return "model/vosk-model-small-en-us-0.15"
        return "model/vosk-model-small-cn-0.22"  # 默认中文
        
    def get_audio_devices(self):
        """获取可用的音频设备列表"""
        try:
            devices = sd.query_devices()
            input_devices = []
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    input_devices.append((i, device['name']))
            return input_devices
        except Exception as e:
            self.error_occurred.emit(f"获取音频设备失败: {str(e)}")
            return []
    
    def set_language(self, language):
        """设置识别语言"""
        self.current_language = language
        self.initialize_vosk()  # 重新初始化对应语言的模型
    
    def audio_callback(self, indata, frames, time, status):
        """音频回调函数"""
        if status:
            self.error_occurred.emit(f'音频回调状态: {status}')
        try:
            self.audio_queue.put(bytes(indata))
        except Exception as e:
            self.error_occurred.emit(f"音频处理错误: {str(e)}")
    
    def process_audio(self):
        """处理音频数据的线程函数"""
        while not self.stop_event.is_set() or not self.audio_queue.empty():
            try:
                if not self.audio_queue.empty():
                    audio_data = self.get_audio_data()
                    if audio_data:
                        text = self.recognize_audio(audio_data)
                        if text:
                            # 如果有新的完整识别结果，直接发送
                            if text != self.last_text and text.strip():
                                self.text_received.emit(text)
                                self.last_text = text
                                self.silence_frames = 0
                        else:
                            # 增加静音计数
                            self.silence_frames += 1
                            # 如果静音足够长，重置上一次识别的文本
                            if self.silence_frames >= self.SILENCE_THRESHOLD:
                                self.last_text = ""
                                self.silence_frames = 0
                else:
                    self.stop_event.wait(0.1)
            except Exception as e:
                self.error_occurred.emit(f"音频处理错误: {str(e)}")
    
    def start_recording(self, device_index=None):
        """开始录音"""
        with self.lock:
            if self.is_recording:
                return
            
            if not self.vosk_model or not self.kaldi_recognizer:
                self.error_occurred.emit("语音模型未初始化，请确保已下载并正确放置模型文件")
                return
                
            self.is_recording = True
            self.stop_event.clear()
            
            try:
                def record_audio():
                    with sd.RawInputStream(samplerate=self.sample_rate,
                                        channels=1,
                                        dtype='int16',
                                        blocksize=self.chunk_size,
                                        device=device_index,
                                        callback=self.audio_callback):
                        self.stop_event.wait()
                
                self.recording_thread = Thread(target=record_audio)
                self.recording_thread.daemon = True
                self.recording_thread.start()
                
                self.processing_thread = Thread(target=self.process_audio)
                self.processing_thread.daemon = True
                self.processing_thread.start()
                
            except Exception as e:
                self.is_recording = False
                self.error_occurred.emit(f"启动录音失败: {str(e)}")
    
    def stop_recording(self):
        """停止录音"""
        with self.lock:
            if not self.is_recording:
                return
                
            self.stop_event.set()
            self.is_recording = False
            
            if hasattr(self, 'recording_thread') and self.recording_thread:
                self.recording_thread.join()
            if hasattr(self, 'processing_thread') and self.processing_thread:
                self.processing_thread.join()
    
    def recognize_audio(self, audio_data):
        """识别音频数据"""
        try:
            if self.kaldi_recognizer.AcceptWaveform(audio_data):
                # 完整的识别结果
                result = json.loads(self.kaldi_recognizer.Result())
                text = result.get('text', '').strip()
                if text:  # 只在有实际内容时返回
                    return text
            else:
                # 部分识别结果，但我们不使用它
                partial = json.loads(self.kaldi_recognizer.PartialResult())
                return ""
        except Exception as e:
            self.error_occurred.emit(f"识别错误: {str(e)}")
            return ""
    
    def get_audio_data(self):
        """获取音频数据进行识别"""
        if self.audio_queue.empty():
            return None
            
        try:
            # 获取音频数据
            audio_data = []
            while not self.audio_queue.empty():
                audio_data.extend(self.audio_queue.get())
            return bytes(audio_data)
        except Exception as e:
            self.error_occurred.emit(f"音频数据处理错误: {str(e)}")
            return None 