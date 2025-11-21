import sys
import os
import subprocess
import threading
import time
import psutil
import shutil
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QTextEdit, QLabel,
    QMessageBox, QProgressBar, QGroupBox, QSplitter, QFileDialog,
    QTabWidget, QFormLayout, QLineEdit, QStatusBar, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QDateTime
from PyQt6.QtGui import QFont, QColor, QIcon, QPalette, QTextCursor

class CommandExecutor(QThread):
    """命令执行线程，负责在后台执行命令并发送结果信号"""
    output_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    status_signal = pyqtSignal(int, str)  # (index, status: "running", "success", "failed")
    finished_signal = pyqtSignal(int)  # (exit_code)

    def __init__(self, command, index, requires_sudo=False, new_terminal=True):
        super().__init__()
        self.command = command
        self.index = index
        self.requires_sudo = requires_sudo
        self.new_terminal = new_terminal  # 新增参数，控制是否在新终端中执行
        self.process = None
        self.running = False
        # 添加超时相关变量
        self.timeout_timer = None
        self.timeout_seconds = 300  # 默认5分钟超时
        self.is_timeout = False

    def run(self):
        self.running = True
        self.status_signal.emit(self.index, "running")
        self.output_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 开始执行: {self.command}")
        
        # 启动超时计时器
        self.start_timeout_timer()

        try:
            # 根据操作系统和权限需求设置不同的执行方式
            if self.requires_sudo:
                if sys.platform == 'win32':
                    # Windows系统下的管理员权限执行
                    self.output_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] Windows下需要管理员权限，请确保程序以管理员身份运行")
                    # 使用临时批处理文件执行命令，提供更好的错误处理
                    temp_bat = os.path.join(tempfile.gettempdir(), f"command_{self.index}.bat")
                    with open(temp_bat, 'w') as f:
                        f.write(self.command)
                    
                    try:
                        # 尝试以管理员权限执行批处理文件
                        creationflags = subprocess.CREATE_NEW_CONSOLE if self.new_terminal else 0
                        self.process = subprocess.Popen(
                            ["cmd", "/c", temp_bat],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            bufsize=1,
                            shell=True,
                            creationflags=creationflags
                        )
                    finally:
                        # 确保临时文件被删除
                        try:
                            if os.path.exists(temp_bat):
                                os.remove(temp_bat)
                        except:
                            pass
                else:
                    # Linux/Mac系统下使用sudo执行
                    self.output_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 请求sudo权限...")
                    
                    if self.new_terminal:
                        # 在新终端中执行带sudo的命令
                        # 注意：这种方式可能无法正确处理密码输入，实际使用时可能需要调整
                        terminal_cmd = []
                        if sys.platform == 'darwin':  # macOS
                            terminal_cmd = ['open', '-a', 'Terminal', 'bash', '-c']
                        else:  # Linux
                            # 尝试不同的终端程序
                            for term in ['gnome-terminal', 'konsole', 'xterm', 'xfce4-terminal']:
                                if shutil.which(term):
                                    if term == 'gnome-terminal':
                                        terminal_cmd = [term, '--', 'bash', '-c']
                                    elif term == 'konsole':
                                        terminal_cmd = [term, '-e', 'bash', '-c']
                                    elif term == 'xterm':
                                        terminal_cmd = [term, '-e', 'bash', '-c']
                                    elif term == 'xfce4-terminal':
                                        terminal_cmd = [term, '-x', 'bash', '-c']
                                    break
                        
                        if terminal_cmd:
                            full_cmd = terminal_cmd + [f'sudo {self.command} && read -p "按Enter键继续..."']
                            self.process = subprocess.Popen(
                                full_cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True
                            )
                            # 在新终端中执行时，我们无法直接捕获输出，所以模拟成功
                            self.output_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 命令已在新终端中启动: {self.command}")
                            # 模拟命令完成，发送成功信号
                            self.stop_timeout_timer()
                            self.status_signal.emit(self.index, "success")
                            self.output_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 命令已在新终端中启动，请在终端窗口中查看执行结果")
                            self.finished_signal.emit(0)
                            return
                        else:
                            self.output_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 未找到可用的终端程序，将在当前进程中执行")
                    
                    # 尝试使用sudo执行，并处理密码输入
                    # 注意：在实际使用中，可能需要配置sudo免密或使用其他安全的权限管理方式
                    self.process = subprocess.Popen(
                        ['sudo', '-S', 'bash', '-c', self.command],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        bufsize=1
                    )
            else:
                # 不需要特殊权限时执行
                if self.new_terminal:
                    if sys.platform == 'win32':
                        # Windows下在新终端中执行
                        # 使用临时批处理文件执行命令
                        temp_bat = os.path.join(tempfile.gettempdir(), f"command_{self.index}.bat")
                        with open(temp_bat, 'w') as f:
                            f.write(self.command + '\npause')  # 添加pause以便查看输出
                        
                        try:
                            self.process = subprocess.Popen(
                                ["start", "cmd", "/c", temp_bat],
                                shell=True
                            )
                            # 在新终端中执行时，我们无法直接捕获输出，所以模拟成功
                            self.output_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 命令已在新终端中启动: {self.command}")
                            return
                        finally:
                            # 确保临时文件被删除
                            try:
                                # 延迟删除，让命令有时间执行
                                import threading
                                def remove_temp_file():
                                    time.sleep(5)
                                    if os.path.exists(temp_bat):
                                        try:
                                            os.remove(temp_bat)
                                        except:
                                            pass
                                threading.Thread(target=remove_temp_file, daemon=True).start()
                            except:
                                pass
                    else:
                        # Linux/Mac下在新终端中执行
                        terminal_cmd = []
                        if sys.platform == 'darwin':  # macOS
                            terminal_cmd = ['open', '-a', 'Terminal', 'bash', '-c']
                        else:  # Linux
                            # 尝试不同的终端程序
                            for term in ['gnome-terminal', 'konsole', 'xterm', 'xfce4-terminal']:
                                if shutil.which(term):
                                    if term == 'gnome-terminal':
                                        terminal_cmd = [term, '--', 'bash', '-c']
                                    elif term == 'konsole':
                                        terminal_cmd = [term, '-e', 'bash', '-c']
                                    elif term == 'xterm':
                                        terminal_cmd = [term, '-e', 'bash', '-c']
                                    elif term == 'xfce4-terminal':
                                        terminal_cmd = [term, '-x', 'bash', '-c']
                                    break
                        
                        if terminal_cmd:
                            full_cmd = terminal_cmd + [f'{self.command} && read -p "按Enter键继续..."']
                            self.process = subprocess.Popen(
                                full_cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True
                            )
                            # 在新终端中执行时，我们无法直接捕获输出，所以模拟成功
                            self.output_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 命令已在新终端中启动: {self.command}")
                            return
                        else:
                            self.output_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 未找到可用的终端程序，将在当前进程中执行")
                
                # 在当前进程中执行（默认方式）
                shell = True if sys.platform == 'win32' else False
                cmd_args = self.command if shell else self.command.split()
                self.output_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 命令参数: {cmd_args}")
                
                try:
                    self.process = subprocess.Popen(
                        cmd_args,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        bufsize=1,
                        shell=shell,
                        universal_newlines=True  # 确保输出是文本模式
                    )
                except FileNotFoundError:
                    self.error_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 错误: 找不到命令或可执行文件")
                    raise
                except PermissionError:
                    self.error_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 错误: 权限不足，请尝试以管理员/root权限运行")
                    raise

            # 实时读取输出和错误
            self.read_output()

            # 等待进程结束并获取退出码
            try:
                exit_code = self.process.wait(timeout=5)  # 额外等待5秒确保进程完全结束
            except subprocess.TimeoutExpired:
                exit_code = -1
                self.error_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 警告: 进程等待超时，强制终止")
                self.process.kill()

            # 停止超时计时器
            self.stop_timeout_timer()
            
            # 检查是否是超时导致的
            if self.is_timeout:
                exit_code = -2
                self.error_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 命令执行超时")
            
            if exit_code == 0:
                self.status_signal.emit(self.index, "success")
                self.output_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 命令执行成功")
            else:
                self.status_signal.emit(self.index, "failed")
                error_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 命令执行失败，退出码: {exit_code}"
                if exit_code == -2:
                    error_msg += " (超时)"
                elif exit_code == 127:
                    error_msg += " (命令未找到)"
                elif exit_code == 126:
                    error_msg += " (权限被拒绝)"
                self.error_signal.emit(error_msg)
            self.finished_signal.emit(exit_code)

        except subprocess.SubprocessError as e:
            self.stop_timeout_timer()
            error_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 子进程错误: {str(e)}"
            self.error_signal.emit(error_msg)
            self.status_signal.emit(self.index, "failed")
            self.finished_signal.emit(-1)
        except Exception as e:
            self.stop_timeout_timer()
            error_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 执行出错: {str(e)}"
            error_msg += f"\n错误类型: {type(e).__name__}"
            self.error_signal.emit(error_msg)
            self.status_signal.emit(self.index, "failed")
            self.finished_signal.emit(-1)

    def read_output(self):
        """读取进程的输出和错误"""
        # 使用多线程同时读取stdout和stderr，避免死锁
        import threading
        import queue
        
        output_queue = queue.Queue()
        error_queue = queue.Queue()
        
        def read_stdout():
            for line in iter(self.process.stdout.readline, ''):
                if line and self.running:
                    output_queue.put(line.strip())
        
        def read_stderr():
            for line in iter(self.process.stderr.readline, ''):
                if line and self.running:
                    # 过滤掉sudo密码提示等敏感信息
                    if 'password' in line.lower() and 'sudo' in line.lower():
                        error_queue.put("[sudo] 密码提示信息 (已过滤)")
                    else:
                        error_queue.put(line.strip())
        
        # 启动读取线程
        stdout_thread = threading.Thread(target=read_stdout)
        stderr_thread = threading.Thread(target=read_stderr)
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()
        
        # 主循环，定时检查队列并发送信号
        while self.running and (stdout_thread.is_alive() or stderr_thread.is_alive() or not output_queue.empty() or not error_queue.empty()):
            # 读取输出队列
            while not output_queue.empty() and self.running:
                try:
                    line = output_queue.get_nowait()
                    self.output_signal.emit(line)
                except queue.Empty:
                    break
            
            # 读取错误队列
            while not error_queue.empty() and self.running:
                try:
                    line = error_queue.get_nowait()
                    self.error_signal.emit(line)
                except queue.Empty:
                    break
            
            # 短暂休眠避免CPU占用过高
            time.sleep(0.1)

    def start_timeout_timer(self):
        """启动超时计时器"""
        self.is_timeout = False
        self.timeout_timer = threading.Timer(self.timeout_seconds, self.on_timeout)
        self.timeout_timer.daemon = True
        self.timeout_timer.start()

    def stop_timeout_timer(self):
        """停止超时计时器"""
        if self.timeout_timer:
            self.timeout_timer.cancel()
            self.timeout_timer = None

    def on_timeout(self):
        """处理超时事件"""
        self.is_timeout = True
        self.error_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 警告: 命令执行时间超过 {self.timeout_seconds} 秒")
        self.stop()

    def stop(self):
        """停止正在执行的命令"""
        self.running = False
        self.stop_timeout_timer()
        
        if self.process:
            try:
                if sys.platform == 'win32':
                    # Windows下的终止方法
                    try:
                        # 先尝试优雅终止
                        self.process.terminate()
                        # 等待1秒
                        self.process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        # 如果超时，强制终止
                        import signal
                        try:
                            os.kill(self.process.pid, signal.SIGTERM)
                        except (AttributeError, OSError):
                            # 在Windows上可能无法使用SIGTERM
                            pass
                else:
                    # 在Unix系统上，可以尝试优雅终止
                    self.process.terminate()
                    # 等待一段时间后强制终止
                    try:
                        self.process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
            except Exception as e:
                self.error_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 停止进程时出错: {str(e)}")
            finally:
                self.process = None

class GelloLauncher(QMainWindow):
    """Gello项目启动自动化工具主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gello 项目启动工具")
        self.setGeometry(100, 100, 1200, 800)
        
        # 检测操作系统类型
        self.is_windows = sys.platform == 'win32'
        
        # 初始化变量
        # 根据操作系统类型配置不同的命令
        if self.is_windows:
            # Windows系统下的命令
            self.commands = [
                {"cmd": "echo 设置USB权限 (Windows)", "desc": "设置USB权限", "requires_sudo": True},
                {"cmd": "conda activate gello", "desc": "激活conda环境", "requires_sudo": False},
                {"cmd": "python d:\\WorkSpace\\gello_software\\experiments\\launch_camera_nodes.py", "desc": "启动相机节点", "requires_sudo": False},
                {"cmd": "python d:\\WorkSpace\\gello_software\\experiments\\launch_nodes.py", "desc": "启动机器人节点", "requires_sudo": False},
                {"cmd": "python d:\\WorkSpace\\gello_software\\experiments\\run_env_with_footpedal.py --agent=gello", "desc": "启动带脚踏板的环境", "requires_sudo": False}
            ]
        else:
            # Linux/Mac系统下的命令
            self.commands = [
                {"cmd": "sudo chmod 777 /dev/ttyCH343USB0", "desc": "设置USB0权限", "requires_sudo": True},
                {"cmd": "sudo chmod 777 /dev/ttyCH343USB2", "desc": "设置USB2权限", "requires_sudo": True},
                # {"cmd": "conda run -n gello python /home/ju/Workspace/gello_software/experiments/launch_camera_nodes.py", "desc": "启动相机节点", "requires_sudo": False},
                {"cmd": "conda run -n gello python /home/ju/Workspace/gello_software/experiments/launch_nodes.py", "desc": "启动机器人节点", "requires_sudo": False},
                {"cmd": "conda run -n gello python experiments/run_env_with_footpedal.py --agent=gello", "desc": "启动带脚踏板的环境", "requires_sudo": False}
            ]
        
        self.current_command_index = -1
        self.executor = None
        self.is_running = False
        self.all_processes = []
        # 新增: 存储所有命令执行器实例
        self.command_executors = []
        # 新增: 跟踪已完成的命令数量
        self.completed_commands = 0
        # 新增: 跟踪每个命令的状态
        self.command_statuses = ["pending"] * len(self.commands)
        
        # 添加状态监控变量
        self.start_time = None
        self.last_update_time = None
        self.resource_monitor_timer = QTimer()
        self.resource_monitor_timer.timeout.connect(self.update_resource_usage)
        
        # 用于保存日志的变量
        self.log_history = []
        self.log_folder = os.path.join(os.path.expanduser("~"), "gello_logs")
        
        # 确保日志文件夹存在
        if not os.path.exists(self.log_folder):
            try:
                os.makedirs(self.log_folder)
            except Exception as e:
                print(f"无法创建日志文件夹: {e}")
        
        # 创建UI
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 标题标签
        title_label = QLabel("Gello 项目启动自动化工具")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 创建水平分割器，用于左侧命令列表和右侧详细信息
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：命令列表和基本信息
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 命令列表组
        command_group = QGroupBox("执行步骤")
        command_layout = QVBoxLayout()
        
        # 命令列表
        self.command_list = QListWidget()
        self.command_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        for i, cmd_info in enumerate(self.commands):
            item = QListWidgetItem(f"[{i+1}] {cmd_info['desc']}")
            item.setData(Qt.ItemDataRole.UserRole, i)  # 存储索引
            item.setForeground(QColor(100, 100, 100))  # 默认灰色
            self.command_list.addItem(item)
        
        command_layout.addWidget(self.command_list)
        command_group.setLayout(command_layout)
        left_layout.addWidget(command_group, 1)
        
        # 状态信息组
        status_group = QGroupBox("运行状态")
        status_layout = QFormLayout()
        
        self.total_time_label = QLabel("00:00:00")
        self.current_step_time_label = QLabel("00:00:00")
        self.cpu_usage_label = QLabel("0%")
        self.memory_usage_label = QLabel("0 MB")
        
        status_layout.addRow("总运行时间:", self.total_time_label)
        status_layout.addRow("当前步骤时间:", self.current_step_time_label)
        status_layout.addRow("CPU使用率:", self.cpu_usage_label)
        status_layout.addRow("内存使用:", self.memory_usage_label)
        
        status_group.setLayout(status_layout)
        left_layout.addWidget(status_group)
        
        # 日志过滤器
        filter_group = QGroupBox("日志过滤")
        filter_layout = QHBoxLayout()
        
        self.log_filter_combo = QComboBox()
        self.log_filter_combo.addItems(["全部日志", "仅错误", "仅成功", "仅信息"])
        self.log_filter_combo.currentIndexChanged.connect(self.on_log_filter_changed)
        
        filter_layout.addWidget(QLabel("显示类型:"))
        filter_layout.addWidget(self.log_filter_combo)
        
        save_log_button = QPushButton("保存日志")
        save_log_button.clicked.connect(self.on_save_logs)
        filter_layout.addWidget(save_log_button)
        
        filter_group.setLayout(filter_layout)
        left_layout.addWidget(filter_group)
        
        # 添加左侧部件到主分割器
        main_splitter.addWidget(left_widget)
        
        # 右侧：日志显示和详细信息
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 日志显示标签页
        self.tab_widget = QTabWidget()
        
        # 日志标签
        self.log_tab = QWidget()
        log_tab_layout = QVBoxLayout(self.log_tab)
        
        # 日志文本编辑框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.log_text.setStyleSheet("font-family: Consolas, Monaco, 'Courier New', monospace;")
        
        log_tab_layout.addWidget(self.log_text)
        self.tab_widget.addTab(self.log_tab, "运行日志")
        
        # 当前命令详情标签
        self.details_tab = QWidget()
        details_layout = QVBoxLayout(self.details_tab)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setStyleSheet("font-family: Consolas, Monaco, 'Courier New', monospace;")
        
        details_layout.addWidget(self.details_text)
        self.tab_widget.addTab(self.details_tab, "命令详情")
        
        right_layout.addWidget(self.tab_widget, 1)
        
        # 添加右侧部件到主分割器
        main_splitter.addWidget(right_widget)
        
        # 设置初始大小比例
        main_splitter.setSizes([300, 900])
        
        main_layout.addWidget(main_splitter, 1)  # 1表示伸展因子
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("准备就绪")
        main_layout.addWidget(self.progress_bar)
        
        # 控制按钮布局
        control_layout = QHBoxLayout()
        
        # 启动按钮
        self.start_button = QPushButton("一键启动")
        self.start_button.setMinimumHeight(40)
        self.start_button.clicked.connect(self.start_all_commands)
        
        # 停止按钮
        self.stop_button = QPushButton("停止运行")
        self.stop_button.setMinimumHeight(40)
        self.stop_button.clicked.connect(self.stop_current_command)
        self.stop_button.setEnabled(False)
        
        # 重试按钮
        self.retry_button = QPushButton("重试当前步骤")
        self.retry_button.setMinimumHeight(40)
        self.retry_button.clicked.connect(self.retry_current_command)
        self.retry_button.setEnabled(False)
        
        # 跳过按钮
        self.skip_button = QPushButton("跳过当前步骤")
        self.skip_button.setMinimumHeight(40)
        self.skip_button.clicked.connect(self.skip_current_command)
        self.skip_button.setEnabled(False)
        
        # 清除日志按钮
        self.clear_logs_button = QPushButton("清除日志")
        self.clear_logs_button.setMinimumHeight(40)
        self.clear_logs_button.clicked.connect(self.clear_logs)
        
        # 退出按钮
        self.exit_button = QPushButton("退出")
        self.exit_button.setMinimumHeight(40)
        self.exit_button.clicked.connect(self.close)
        
        # 添加按钮到布局
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.retry_button)
        control_layout.addWidget(self.skip_button)
        control_layout.addWidget(self.clear_logs_button)
        control_layout.addWidget(self.exit_button)
        
        main_layout.addLayout(control_layout)
        
        # 创建自定义状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 添加状态栏组件
        self.status_label = QLabel("准备就绪")
        self.status_bar.addWidget(self.status_label, 1)  # 1表示伸展因子
        
        self.current_command_label = QLabel("无")
        self.status_bar.addWidget(QLabel("当前命令: "))
        self.status_bar.addWidget(self.current_command_label)
        
        # 创建计时器用于更新运行时间
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time_display)
        # 添加总时间计时器
        self.total_time_timer = QTimer()
        self.total_time_timer.timeout.connect(self.update_time_display)
        # 初始化最后更新时间
        self.last_update_time = datetime.now()
        # 创建资源监控定时器
        self.resource_timer = QTimer()
        self.resource_timer.timeout.connect(self.update_resource_usage)
    
    def clear_logs(self):
        """清空日志"""
        self.log_text.clear()
        self.log_history = []

    def start_time_tracking(self):
        """开始时间跟踪"""
        self.start_time = datetime.now()
        self.current_step_start_time = datetime.now()
        self.timer.start(1000)  # 每秒更新一次
        self.resource_timer.start(2000)  # 每2秒更新一次资源使用情况
    
    def stop_time_tracking(self):
        """停止时间跟踪"""
        self.timer.stop()
        self.resource_monitor_timer.stop()
    
    def update_time_display(self):
        """更新时间显示"""
        if not self.start_time:
            return
        
        current_time = datetime.now()
        
        # 计算总运行时间
        total_time = current_time - self.start_time
        self.total_time_label.setText(str(total_time).split('.')[0])  # 移除毫秒部分
        
        # 计算当前步骤运行时间
        if self.current_command_index >= 0:
            step_time = current_time - self.last_update_time
            self.current_step_time_label.setText(str(step_time).split('.')[0])
    
    def update_resource_usage(self):
        """更新资源使用情况"""
        try:
            # 获取当前进程
            current_process = psutil.Process()
            
            # 获取CPU使用率
            cpu_percent = current_process.cpu_percent(interval=0.1)
            self.cpu_usage_label.setText(f"{cpu_percent:.1f}%")
            
            # 获取内存使用量
            memory_info = current_process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)  # 转换为MB
            self.memory_usage_label.setText(f"{memory_mb:.1f} MB")
        except Exception as e:
            # 如果无法获取资源使用情况，不报错，保持静默
            pass
    
    def start_all_commands(self):
        """启动所有命令的执行（并行模式）"""
        if self.is_running:
            QMessageBox.warning(self, "警告", "程序正在运行中，请先停止当前运行")
            return
        
        # 重置状态
        self.is_running = True
        self.completed_commands = 0
        self.command_statuses = ["pending"] * len(self.commands)
        self.command_executors = []
        self.update_button_states()
        
        # 清空日志
        self.clear_logs()
        self.append_output("开始执行项目启动流程（并行模式）")
        
        # 开始时间跟踪
        self.start_time_tracking()
        
        # 并行启动所有命令
        for index, command in enumerate(self.commands):
            self.execute_command_in_parallel(index, command)
    
    def execute_command_in_parallel(self, index, command):
        """并行执行单个命令"""
        if not self.is_running:
            return
        
        # 更新命令状态为执行中
        self.command_statuses[index] = "running"
        self.update_command_status(index, "running")
        
        # 创建命令执行器，设置new_terminal=True以在新终端执行
        executor = CommandExecutor(
            command['cmd'],
            index,
            command['requires_sudo'],
            new_terminal=True
        )
        
        # 连接信号到槽函数
        executor.output_signal.connect(self.append_output)
        executor.error_signal.connect(self.append_error)
        executor.finished_signal.connect(lambda exit_code, idx=index: self.on_command_completed_parallel(idx, exit_code == 0))
        
        # 保存执行器实例
        self.command_executors.append(executor)
        
        # 启动命令执行
        executor.start()
        
        # 更新状态栏显示正在启动的命令
        self.current_command_label.setText(f"正在启动: {command['desc']}")
    
    def execute_next_command(self):
        """保留此方法以保持兼容性，但不再使用顺序执行逻辑"""
        pass
    
    def on_command_completed_parallel(self, index, success):
        """并行模式下命令执行完成后的回调"""
        # 更新命令状态
        status = "success" if success else "failed"
        self.command_statuses[index] = status
        self.update_command_status(index, status)
        
        # 增加已完成命令计数
        self.completed_commands += 1
        
        # 如果命令失败，记录错误信息但不中断其他命令
        if not success:
            self.append_error(f"命令 '{self.commands[index]['desc']}' 执行失败")
        else:
            self.append_output(f"命令 '{self.commands[index]['desc']}' 执行成功")
        
        # 检查是否所有命令都已执行完毕
        if self.completed_commands >= len(self.commands):
            self.is_running = False
            self.update_button_states()
            
            # 停止时间跟踪
            self.stop_time_tracking()
            
            # 检查是否有失败的命令
            has_failed = "failed" in self.command_statuses
            if has_failed:
                self.append_output("所有命令已执行完毕，但部分命令执行失败")
            else:
                self.append_output("所有命令执行完毕")
            
            self.current_command_label.setText("完成: 所有命令已执行")
    
    def on_command_completed(self, index, success):
        """保留此方法以保持兼容性，实际使用on_command_completed_parallel"""
        self.on_command_completed_parallel(index, success)
    
    def on_log_filter_changed(self):
        """处理日志过滤器变更事件"""
        filter_type = self.log_filter_combo.currentText()
        
        # 清空当前显示
        self.log_text.clear()
        
        # 根据过滤条件重新显示日志
        for log_entry in self.log_history:
            if filter_type == "全部日志" or \
               (filter_type == "仅错误" and log_entry["type"] == "error") or \
               (filter_type == "仅成功" and log_entry["type"] == "success") or \
               (filter_type == "仅信息" and log_entry["type"] == "info"):
                
                # 设置对应的颜色
                if log_entry["type"] == "error":
                    self.log_text.setTextColor(QColor(255, 0, 0))
                elif log_entry["type"] == "success":
                    self.log_text.setTextColor(QColor(0, 150, 0))
                else:  # info
                    self.log_text.setTextColor(QColor(0, 0, 0))
                
                # 添加日志条目
                self.log_text.append(log_entry["text"])
                
        # 恢复默认颜色
        self.log_text.setTextColor(QColor(0, 0, 0))
        
        # 滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
    
    def append_output(self, text):
        """添加输出文本到日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {text}"
        
        # 保存到日志历史
        self.log_history.append({"type": "info", "text": log_entry})
        
        # 根据当前过滤器显示日志
        if self.log_filter_combo.currentText() in ["全部日志", "仅信息"]:
            # 设置文本颜色
            self.log_text.setTextColor(QColor(0, 0, 0))  # 黑色
            self.log_text.append(log_entry)
            
            # 如果当前是详情标签页且有正在执行的命令，也添加到详情
            if self.tab_widget.currentWidget() == self.details_tab and self.current_command_index >= 0:
                self.details_text.setTextColor(QColor(0, 0, 0))
                self.details_text.append(log_entry)
        
        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
    
    def append_error(self, text):
        """添加错误文本到日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {text}"
        
        # 保存到日志历史
        self.log_history.append({"type": "error", "text": log_entry})
        
        # 根据当前过滤器显示日志
        if self.log_filter_combo.currentText() in ["全部日志", "仅错误"]:
            # 设置红色文本
            self.log_text.setTextColor(QColor(255, 0, 0))  # 红色
            self.log_text.append(log_entry)
            
            # 如果当前是详情标签页且有正在执行的命令，也添加到详情
            if self.tab_widget.currentWidget() == self.details_tab and self.current_command_index >= 0:
                self.details_text.setTextColor(QColor(255, 0, 0))
                self.details_text.append(log_entry)
        
        # 恢复默认文本颜色
        self.log_text.setTextColor(QColor(0, 0, 0))
        
        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
    
    def update_command_status(self, index, status):
        """更新命令的状态显示"""
        if index < 0 or index >= self.command_list.count():
            return
        
        item = self.command_list.item(index)
        if not item:
            return
        
        # 保存成功日志
        if status == "success":
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] 步骤 {index+1} '{self.commands[index]['desc']}' 执行成功"
            self.log_history.append({"type": "success", "text": log_entry})
            
            # 根据当前过滤器显示日志
            if self.log_filter_combo.currentText() in ["全部日志", "仅成功"]:
                self.log_text.setTextColor(QColor(0, 150, 0))
                self.log_text.append(log_entry)
                self.log_text.setTextColor(QColor(0, 0, 0))
        
        # 更新状态标签
        if status == "running":
            item.setForeground(QColor(0, 0, 255))  # 蓝色
            item.setText(f"[{index+1}] {self.commands[index]['desc']} - 执行中...")
            # 更新状态栏显示当前命令
            self.current_command_label.setText(f"{index+1}: {self.commands[index]['desc']}")
            # 清空详情面板并添加命令详情
            self.details_text.clear()
            self.details_text.append(f"命令详情 (步骤 {index+1}):")
            self.details_text.append(f"描述: {self.commands[index]['desc']}")
            self.details_text.append(f"命令: {self.commands[index]['cmd']}")
            self.details_text.append(f"需要管理员权限: {'是' if self.commands[index]['requires_sudo'] else '否'}")
            self.details_text.append("\n输出日志:")
        elif status == "success":
            item.setForeground(QColor(0, 150, 0))  # 绿色
            item.setText(f"[{index+1}] {self.commands[index]['desc']} - 成功")
        elif status == "failed":
            item.setForeground(QColor(200, 0, 0))  # 红色
            item.setText(f"[{index+1}] {self.commands[index]['desc']} - 失败")
    
    def command_finished(self, exit_code):
        """命令执行完成后的处理"""
        if exit_code == 0:
            # 命令执行成功，继续下一个
            QTimer.singleShot(500, self.execute_next_command)  # 短暂延迟后执行下一个
        else:
            # 命令执行失败，等待用户操作
            self.statusBar().showMessage(f"执行失败，请选择重试或跳过")
            self.update_button_states()
            # 显示消息框
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("执行失败")
            msg_box.setText(f"步骤 {self.current_command_index + 1} 执行失败")
            msg_box.setInformativeText("您可以选择重试该步骤或跳过它继续执行")
            msg_box.setStandardButtons(
                QMessageBox.StandardButton.Retry | 
                QMessageBox.StandardButton.Ignore | 
                QMessageBox.StandardButton.Cancel
            )
            
            result = msg_box.exec()
            if result == QMessageBox.StandardButton.Retry:
                self.retry_current_command()
            elif result == QMessageBox.StandardButton.Ignore:
                self.skip_current_command()
            else:  # Cancel
                self.stop_all()
    
    def retry_current_command(self):
        """重试当前命令"""
        if self.current_command_index >= 0 and self.current_command_index < len(self.commands):
            self.append_output(f"[{datetime.now().strftime('%H:%M:%S')}] 重新执行步骤 {self.current_command_index + 1}")
            self.execute_command(self.current_command_index)
    
    def skip_current_command(self):
        """跳过当前命令，执行下一个"""
        if self.current_command_index >= 0 and self.current_command_index < len(self.commands):
            self.append_output(f"[{datetime.now().strftime('%H:%M:%S')}] 跳过步骤 {self.current_command_index + 1}")
            # 更新当前命令状态为跳过
            item = self.command_list.item(self.current_command_index)
            if item:
                item.setForeground(QColor(255, 165, 0))  # 橙色
                item.setText(f"[{self.current_command_index+1}] {self.commands[self.current_command_index]['desc']} - 已跳过")
            # 继续执行下一个命令
            QTimer.singleShot(500, self.execute_next_command)
    
    def stop_current_command(self):
        """停止所有正在执行的命令"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 停止所有命令执行器
        for executor in self.command_executors:
            if executor and executor.isRunning():
                executor.stop()
        
        self.command_executors.clear()
        self.update_button_states()
        self.append_error("用户终止了所有命令的执行")
        self.current_command_label.setText("已终止")
        self.stop_time_tracking()
    
    def stop_execution(self):
        """停止命令执行（与stop_current_command功能相同）"""
        self.stop_current_command()

    def update_button_states(self):
        """更新按钮状态"""
        self.start_button.setEnabled(not self.is_running)
        self.stop_button.setEnabled(self.is_running)
        
        # 更新进度条
        if self.is_running and len(self.commands) > 0:
            progress = (self.current_command_index / len(self.commands)) * 100
            self.progress_bar.setValue(int(progress))
        elif not self.is_running and len(self.commands) > 0 and self.current_command_index >= len(self.commands):
            # 所有命令执行完毕
            self.progress_bar.setValue(100)
        else:
            self.progress_bar.setValue(0)

    def on_save_logs(self):
        """保存日志到文件"""
        if not self.log_history:
            QMessageBox.information(self, "提示", "没有可保存的日志")
            return
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"gello_launcher_log_{timestamp}.txt"
        default_path = os.path.join(self.log_folder, default_filename)
        
        # 打开文件对话框
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "保存日志",
            default_path,
            "文本文件 (*.txt);;所有文件 (*)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    for log_entry in self.log_history:
                        f.write(f"{log_entry['text']}\n")
                QMessageBox.information(self, "成功", f"日志已保存到: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存日志失败: {str(e)}")

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        if self.is_running:
            reply = QMessageBox.question(
                self, '确认退出',
                '程序仍在运行中，确定要退出吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_all()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

def main():
    # 确保中文显示正常
    QApplication.setApplicationName("Gello启动工具")
    
    # 检查是否在Windows上以管理员权限运行
    if sys.platform == 'win32':
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if not is_admin:
                print("警告: 程序需要管理员权限才能执行某些操作。")
                print("请尝试以管理员身份重新启动程序。")
        except:
            pass
    
    # 创建应用程序实例
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")  # 使用Fusion样式以获得更好的跨平台外观
    
    # 设置全局字体，确保中文显示正常
    font = QFont()
    font.setFamily("SimHei" if sys.platform == 'win32' else "WenQuanYi Micro Hei")
    app.setFont(font)
    
    # 创建并显示主窗口
    window = GelloLauncher()
    window.show()
    
    # 运行应用程序主循环
    sys.exit(app.exec())

if __name__ == "__main__":
    main()