# Gello 项目启动自动化工具使用说明

## 1. 工具介绍

Gello项目启动自动化工具是一个基于PyQt6开发的图形界面应用程序，旨在简化Gello项目的启动过程。该工具提供了一键式的启动功能，可以自动按顺序执行项目所需的各种命令，并实时显示执行状态和日志信息，大大提高了开发和测试效率。

## 2. 功能特性

### 2.1 直观的用户界面
- 清晰的执行步骤列表，实时显示每个命令的执行状态
- 详细的运行日志显示区域，支持日志过滤和保存功能
- 运行状态监控面板，显示总运行时间、当前步骤时间、CPU和内存使用率
- 命令详情标签页，展示当前执行命令的详细信息

### 2.2 自动化命令执行
- 一键启动功能，自动按顺序执行预设的所有命令
- 支持需要管理员/root权限的命令执行
- 跨平台兼容性，自动适应Windows和Linux/Mac系统

### 2.3 完善的状态监控
- 实时显示每个命令的执行状态（等待中、执行中、成功、失败、已跳过）
- 运行时间统计，包括总运行时间和当前步骤运行时间
- 系统资源监控，实时显示CPU使用率和内存使用量
- 进度条显示整体执行进度

### 2.4 强大的日志管理
- 带时间戳的日志记录
- 日志类型过滤（全部日志、仅错误、仅成功、仅信息）
- 日志保存功能，支持自定义保存路径
- 日志清空功能

### 2.5 智能错误处理
- 详细的错误信息捕获和显示
- 命令超时检测机制（默认5分钟）
- 失败时提供重试、跳过或终止选项
- 自动保存错误日志便于问题排查

## 3. 系统要求

### 3.1 软件要求
- Python 3.7 或更高版本
- PyQt6 库
- psutil 库
- 对于Windows系统：需要管理员权限执行某些命令
- 对于Linux/Mac系统：需要sudo权限执行某些命令

### 3.2 依赖安装

```bash
pip install PyQt6 psutil
```

## 4. 使用说明

### 4.1 启动工具

在项目根目录下执行以下命令启动工具：

```bash
python scripts/gello_launcher.py
```

> **注意**：在Windows系统上，请右键选择"以管理员身份运行"命令提示符或PowerShell，然后执行上述命令。

### 4.2 主要功能操作

#### 4.2.1 一键启动
点击界面上的"一键启动"按钮，系统将按照预设顺序自动执行所有命令。

#### 4.2.2 停止运行
在任何时候，您都可以点击"停止运行"按钮中断当前正在执行的命令。

#### 4.2.3 重试当前步骤
当某个命令执行失败时，您可以点击"重试当前步骤"按钮重新执行该命令。

#### 4.2.4 跳过当前步骤
如果您希望跳过当前失败的步骤并继续执行后续命令，可以点击"跳过当前步骤"按钮。

#### 4.2.5 日志过滤
使用日志过滤下拉菜单，您可以选择查看全部日志、仅错误日志、仅成功日志或仅信息日志。

#### 4.2.6 保存日志
点击"保存日志"按钮，您可以将当前的所有日志保存到文件中，便于后续分析和问题排查。

#### 4.2.7 清除日志
点击"清除日志"按钮，您可以清空当前显示的所有日志内容。

### 4.3 命令执行流程

1. 系统按照预设顺序依次执行每个命令
2. 对于需要特殊权限的命令，系统会自动尝试获取权限
3. 实时显示命令的输出和错误信息
4. 命令执行完成后，自动更新状态显示
5. 如果命令执行成功，继续执行下一个命令
6. 如果命令执行失败，弹出对话框提供重试、跳过或终止选项

## 5. 配置说明

工具会根据您的操作系统自动配置不同的命令列表：

### 5.1 Windows系统

```python
self.commands = [
    {"cmd": "echo 设置USB权限 (Windows)", "desc": "设置USB权限", "requires_sudo": True},
    {"cmd": "conda activate gello", "desc": "激活conda环境", "requires_sudo": False},
    {"cmd": "python d:\\WorkSpace\\gello_software\\experiments\\launch_camera_nodes.py", "desc": "启动相机节点", "requires_sudo": False},
    {"cmd": "python d:\\WorkSpace\\gello_software\\experiments\\launch_nodes.py", "desc": "启动机器人节点", "requires_sudo": False},
    {"cmd": "python d:\\WorkSpace\\gello_software\\experiments\\run_env_with_footpedal.py --agent=gello", "desc": "启动带脚踏板的环境", "requires_sudo": False}
]
```

### 5.2 Linux/Mac系统

```python
self.commands = [
    {"cmd": "sudo chmod 777 /dev/ttyCH343USB0", "desc": "设置USB0权限", "requires_sudo": True},
    {"cmd": "sudo chmod 777 /dev/ttyCH343USB2", "desc": "设置USB2权限", "requires_sudo": True},
    {"cmd": "conda activate gello", "desc": "激活conda环境", "requires_sudo": False},
    {"cmd": "python /home/ju/Workspace/gello_software/experiments/launch_camera_nodes.py", "desc": "启动相机节点", "requires_sudo": False},
    {"cmd": "python /home/ju/Workspace/gello_software/experiments/launch_nodes.py", "desc": "启动机器人节点", "requires_sudo": False},
    {"cmd": "python experiments/run_env_with_footpedal.py --agent=gello", "desc": "启动带脚踏板的环境", "requires_sudo": False}
]
```

> **注意**：如果您需要修改命令列表，请编辑`gello_launcher.py`文件中的相应部分。

## 6. 常见问题解答

### 6.1 为什么某些命令需要管理员/root权限？

设置USB设备权限等操作需要系统级别的权限，因此这些命令需要以管理员或root身份执行。

### 6.2 如何在Linux系统上配置免密码sudo？

编辑sudoers文件（使用`sudo visudo`命令），添加以下行（将`username`替换为您的用户名）：

```
username ALL=(ALL) NOPASSWD: ALL
```

或仅为特定命令授权：

```
username ALL=(ALL) NOPASSWD: /bin/chmod 777 /dev/ttyCH343USB*
```

### 6.3 命令执行超时怎么办？

默认的超时时间为5分钟。如果您的命令需要更长时间执行，可以在`CommandExecutor`类的`__init__`方法中修改`self.timeout_seconds`的值。

### 6.4 日志保存在哪里？

默认情况下，日志文件会保存在用户目录下的`gello_logs`文件夹中，文件名为`gello_launcher_log_时间戳.txt`格式。您也可以在保存日志时选择自定义的保存路径。

## 7. 故障排除

### 7.1 程序无法启动

- 确保已安装所有必要的依赖库（PyQt6、psutil）
- 检查Python版本是否满足要求（3.7或更高）
- 在Windows系统上，确保以管理员身份运行

### 7.2 命令执行失败

- 检查命令的语法是否正确
- 确认相关文件和目录是否存在
- 验证是否有足够的权限执行命令
- 查看详细的错误日志以获取更多信息

### 7.3 权限错误

- Windows：确保以管理员身份运行程序
- Linux/Mac：确保正确配置了sudo权限，或直接以root用户运行

### 7.4 找不到文件或目录

- 检查文件路径是否正确，特别是在不同操作系统之间的路径分隔符差异
- 确保相关的Python脚本文件存在于指定位置

## 8. 联系与支持

如果您在使用过程中遇到任何问题或有改进建议，请联系开发团队。

---

*本文档由Gello项目团队编写，最后更新时间：2024年*