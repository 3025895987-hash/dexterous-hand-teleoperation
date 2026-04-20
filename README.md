# 基于手部姿态估计的五指灵巧手遥操作系统

一个结合 **MediaPipe、OpenCV、串口通信与 MicroPython 舵机控制** 的五指灵巧手项目：

- **上位机（PC）**：在 VS Code / Python 环境中运行，通过摄像头识别人手关键点并计算五根手指的关节角度；
- **下位机（Pico）**：在 Thonny / MicroPython 环境中运行，接收上位机发送的五指角度数据并驱动 5 路舵机；
- **系统目标**：实现人手动作到机械灵巧手动作的实时映射与同步跟随控制。

---

## 1. 项目亮点

- 基于摄像头的**手部关键点识别**
- 根据关键点计算**五根手指关节角度**
- 通过串口实现**上位机 / 下位机通信**
- 使用 MicroPython 控制 5 路舵机，实现**五指灵巧手实时跟随**
- 具备完整的 **感知 -> 映射 -> 执行** 系统链路
- 适合用于机器人、嵌入式、计算机视觉与人机交互方向的项目展示

---

## 2. 项目架构

```text
摄像头
  ↓
OpenCV 读取实时画面
  ↓
MediaPipe 提取手部关键点
  ↓
计算五根手指关节角度
  ↓
串口发送五指角度报文
  ↓
Pico / MicroPython 接收并解析数据
  ↓
PWM 驱动五路舵机
  ↓
机械灵巧手同步动作
3. 仓库结构
.
├── firmware/
│   ├── main.py
│   └── protocol_selfcheck.py
├── pc_controller/
│   └── hand_tracking_controller.py
├── docs/
│   ├── project_description_zh.md
│   └── setup_guide_zh.md
├── README.md
├── requirements.txt
└── .gitignore
4. 技术栈
上位机
Python
OpenCV
MediaPipe
PySerial
下位机
MicroPython
Raspberry Pi Pico / Pico W
PWM 舵机控制
5. 上位机功能说明

上位机主要负责：

读取摄像头实时画面；
使用 MediaPipe 检测手部关键点；
计算五根手指的关节角度；
将五指角度格式化为固定长度字符串；
通过串口发送给下位机；
在窗口中实时显示手部关键点与识别结果。
五指角度顺序

上位机默认按以下顺序发送角度：

拇指（Thumb）
食指（Index）
中指（Middle）
无名指（Ring）
小指（Pinky）
6. 下位机功能说明

下位机主要负责：

从串口接收上位机发送的五指角度数据；
解析固定格式的五指角度报文；
将每根手指角度映射为对应舵机的 PWM 输出；
驱动五路舵机完成同步动作；
支持对每根手指单独配置方向、限幅与舵机参数。
7. 串口通信协议

当前项目采用五指固定长度报文。

报文格式
TTTIIIMMMRRRPPP

其中：

TTT：拇指角度（3 位）
III：食指角度（3 位）
MMM：中指角度（3 位）
RRR：无名指角度（3 位）
PPP：小指角度（3 位）
示例
090045120060030

表示：

拇指 = 90°
食指 = 45°
中指 = 120°
无名指 = 60°
小指 = 30°
8. 环境配置
上位机环境

建议使用：

Python 3.10
VS Code

安装依赖：

pip install -r requirements.txt

requirements.txt 内容为：

opencv-python
mediapipe
pyserial
下位机环境

建议使用：

Thonny
MicroPython 固件
Raspberry Pi Pico / Pico W
9. 运行方式
9.1 上位机运行
安装 Python 依赖；
根据实际串口修改 pc_controller/hand_tracking_controller.py 中的串口号；
连接摄像头与单片机；
运行上位机程序：
python pc_controller/hand_tracking_controller.py
9.2 下位机运行
给 Pico 烧录 MicroPython 固件；
使用 Thonny 打开 firmware/main.py；
将文件保存到开发板中，命名为 main.py；
重启开发板；
等待上位机发送五指角度数据。
10. 接线说明

当前项目使用五路舵机分别控制五根手指。
具体 GPIO 引脚可在下位机程序中按实际接线进行修改。

示例配置思路：

拇指舵机：GPIO 12
食指舵机：GPIO 13
中指舵机：GPIO 14
无名指舵机：GPIO 15
小指舵机：GPIO 16

若不同手指的运动方向与实际需求不一致，可在下位机配置中单独调整反向映射与输出范围。

11. 我的工作
完成上位机的手部关键点识别与五指关节角度计算；
设计并实现上位机与下位机之间的五指串口通信协议；
编写下位机 MicroPython 固件，实现五指角度解析与五路舵机控制；
完成从视觉识别到机械执行的整体联调；
对项目进行整理与文档化，方便后续展示、归档与继续迭代。
12. 项目价值

这个项目不仅是一个简单的“舵机跟手”演示，更是一个完整的小型机器人系统原型。
它把计算机视觉、嵌入式控制、串口通信与机械执行结合到了一起，具备较强的展示性、交互性和扩展性。

它可以作为以下方向的入门与展示项目：

机器人控制
嵌入式系统开发
计算机视觉
人机交互
智能硬件原型设计
13. 可扩展方向
增加角度滤波与平滑处理，减少抖动
针对每根手指分别做更精细的运动映射
提高机械结构自由度，优化手部动作还原效果
加入抓取、捏合等动作模板
扩展为更完整的机械手 / 机械臂主从控制系统
