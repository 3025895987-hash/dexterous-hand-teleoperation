# 环境搭建与运行说明

这份说明基于原始实践指导书整理而来，适合直接放进 GitHub 仓库。

## 1. 软件准备

### 上位机
- Python 3.10
- VS Code
- 上位机依赖：OpenCV、MediaPipe、PySerial

### 下位机
- Thonny
- MicroPython 固件
- Raspberry Pi Pico / Pico W（或兼容开发板）

## 2. 上位机环境配置

### 2.1 创建虚拟环境
```bash
py -3.10 -m venv .venv
```

### 2.2 激活虚拟环境
```bash
.\.venv\Scripts\activate
```

### 2.3 安装依赖
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2.4 选择解释器
在 VS Code 中：
- `Ctrl + Shift + P`
- 搜索 `Python: Select Interpreter`
- 选择刚刚创建的虚拟环境

## 3. 下位机配置

1. 插上开发板；
2. 按住 `BOOT`，再按一下 `RUN` / `RESET`；
3. 电脑上会出现一个 U 盘；
4. 把 MicroPython 的 `.uf2` 固件拖进去；
5. 开发板重启后，打开 Thonny；
6. 右下角选择对应串口；
7. 打开 `firmware/main.py`，另存为板载 `main.py`。

## 4. 运行顺序

1. 先连接好开发板与舵机；
2. 启动 Thonny，让下位机 `main.py` 运行起来；
3. 在 VS Code 中运行 `pc_controller/hand_tracking_controller.py`；
4. 确保上位机里的 `SERIAL_PORT` 改成你的实际串口；
5. 摄像头捕捉到手后，机械手开始同步动作。

## 5. 接线说明

当前仓库为双指版：
- 拇指舵机：`GP12`
- 食指舵机：`GP13`

如果你后续只保留一根手指进行演示，也可以只接对应舵机。
