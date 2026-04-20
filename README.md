# 基于手部姿态估计的灵巧手遥操作系统

一个基于 **MediaPipe + OpenCV + 串口通信 + MicroPython 舵机控制** 的双端项目：
- **上位机（PC）**：在 VS Code / Python 环境中运行，通过摄像头识别人手关键点并计算关节角；
- **下位机（Pico）**：在 Thonny / MicroPython 环境中运行，接收串口角度报文并驱动舵机；
- **演示目标**：实现“人手动作 -> 机械灵巧手动作”的实时跟随控制。

> 当前仓库整理为 **双指演示版**：默认控制拇指与食指，便于比赛演示、代码展示和 GitHub 归档。后续可以继续扩展到五指版本。

---

## 1. 项目亮点

- 基于摄像头的 **手部关键点识别**
- 根据关键点计算 **手指关节角度**
- 通过串口实现 **上位机 / 下位机通信**
- 使用 MicroPython 控制舵机，实现 **灵巧手实时跟随**
- 具备清晰的“感知 -> 映射 -> 执行”系统链路

---

## 2. 项目架构

```text
摄像头
  ↓
OpenCV 读取画面
  ↓
MediaPipe 提取手部关键点
  ↓
计算拇指 / 食指关节角度
  ↓
串口发送报文（如 090045）
  ↓
Pico / MicroPython 解析报文
  ↓
PWM 驱动舵机
  ↓
机械手同步动作
```

---

## 3. 仓库结构

```text
.
├── firmware/
│   └── main.py                      # 下位机固件（Thonny / MicroPython）
├── pc_controller/
│   └── hand_tracking_controller.py  # 上位机程序（VS Code / Python）
├── docs/
│   ├── project_description_zh.md    # 可直接复用到作品集 / 报名表的项目说明
│   └── setup_guide_zh.md            # 环境搭建与运行说明
├── assets/                          # 放演示截图、GIF、视频封面
├── requirements.txt                 # 上位机依赖
├── .gitignore
└── README.md
```

---

## 4. 快速开始

### 4.1 上位机环境

建议使用 **Python 3.10**。

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

运行前，请先打开 `pc_controller/hand_tracking_controller.py`，按自己的设备修改：

- `SERIAL_PORT`：例如 `COM5`
- `CAMERA_INDEX`：默认 0
- `TWO_FINGER_MODE`：当前默认 `True`

运行：

```bash
python pc_controller/hand_tracking_controller.py
```

### 4.2 下位机环境

1. 给 Pico 烧录 MicroPython 固件；
2. 用 Thonny 打开 `firmware/main.py`；
3. 选择对应串口；
4. 另存为板载 `main.py`；
5. 重启板子，等待串口输入。

---

## 5. 串口协议

当前默认协议为 **双指模式**：

```text
TTTIII\n
TTT = 拇指角度（3 位）
III = 食指角度（3 位）
\n  = 一帧结束
```

示例：

```text
090045
```

表示：
- 拇指 = 90°
- 食指 = 45°

> 为什么要加换行？
>
> 因为串口连续发送时，如果不做帧分隔，固定长度读取很容易产生粘包或错位。加入换行以后，下位机按“整行”解析，稳定很多。

---

## 6. 我的工作（可直接复用到作品集）

- 搭建上位机视觉识别流程，完成摄像头读取、MediaPipe 手部关键点检测与关节角计算；
- 设计上位机与下位机之间的串口通信格式；
- 编写下位机 MicroPython 固件，实现角度解析与舵机控制；
- 完成从“视觉识别 -> 串口传输 -> 舵机执行”的整套联调；
- 将项目整理为适合 GitHub 展示的结构，方便继续扩展和作品集展示。

---

## 7. 演示素材建议

你把仓库上传到 GitHub 后，建议再补这些内容：

- `assets/demo-cover.png`：项目封面图
- `assets/hand-demo.gif`：短 GIF 演示
- 一个视频链接：放在 README 顶部或项目说明里

推荐写法：

```md
## Demo Video
- [演示视频链接](在这里替换成你的链接)
```

---

## 8. 后续可扩展方向

- 从双指扩展到五指控制
- 加入更稳定的角度滤波 / 平滑处理
- 加入左右手识别
- 增加抓取动作模板
- 替换为更高自由度的灵巧手机构

---

## 9. 适合简历 / 报名表的一句话介绍

**基于手部姿态估计的灵巧手遥操作系统**：通过视觉识别人手关键点并计算关节角度，再通过串口将角度映射到下位机舵机，实现机械灵巧手对人手动作的实时跟随控制。
