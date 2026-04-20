"""上位机：基于 MediaPipe 的手部姿态识别与串口发送。

运行环境：Windows + VS Code + Python 3.10
作用：
1. 通过摄像头捕获手部画面；
2. 使用 MediaPipe 提取手部关键点；
3. 计算拇指、食指等手指关节角度；
4. 通过串口把角度发送给下位机，驱动灵巧手同步动作。

当前仓库默认采用“双指演示模式”：
- 只发送拇指、食指两个角度；
- 报文格式为：TTTIII\n，例如 090045\n。
这样可以和当前下位机固件稳定配合，避免连续裸字节导致的串口粘包/错位。
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import List, Sequence

import cv2
import mediapipe as mp
import serial
from serial import SerialException

# =========================
# 可按自己设备修改的配置项
# =========================
CAMERA_INDEX = 0
SERIAL_PORT = "COM5"
BAUDRATE = 9600
SERIAL_TIMEOUT = 1
SEND_INTERVAL_S = 0.03  # 最快约 33Hz，避免串口打印过快
DISPLAY_WINDOW_NAME = "Dexterous Hand Teleoperation"
FLIP_DISPLAY = True
TWO_FINGER_MODE = True  # True: 只发送拇指+食指；False: 发送五指

# MediaPipe 初始化
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles


@dataclass(frozen=True)
class FingerAngles:
    """保存一只手五根手指的关节角。"""

    thumb: int
    index: int
    middle: int
    ring: int
    pinky: int

    def as_list(self) -> List[int]:
        return [self.thumb, self.index, self.middle, self.ring, self.pinky]


# =========================
# 角度计算相关函数
# =========================
def calculate_joint_angle(a, b, c) -> float:
    """计算 ∠ABC 的夹角（单位：度）。

    MediaPipe 手部关键点坐标是归一化坐标，这里只使用 x、y 平面信息。
    对于视觉演示项目，这样已经可以较稳定地反映手指弯曲程度。
    """
    ba = (a.x - b.x, a.y - b.y)
    bc = (c.x - b.x, c.y - b.y)

    dot_product = ba[0] * bc[0] + ba[1] * bc[1]
    len_ba = math.sqrt(ba[0] ** 2 + ba[1] ** 2)
    len_bc = math.sqrt(bc[0] ** 2 + bc[1] ** 2)

    if len_ba == 0 or len_bc == 0:
        return 90.0

    cosine = dot_product / (len_ba * len_bc)
    cosine = max(-1.0, min(1.0, cosine))
    return math.degrees(math.acos(cosine))


def extract_finger_angles(hand_landmarks) -> FingerAngles:
    """从 MediaPipe 的 21 个关键点中提取五指关节角度。"""
    points = hand_landmarks.landmark

    thumb = int(calculate_joint_angle(points[1], points[2], points[3]))
    index = int(calculate_joint_angle(points[5], points[6], points[7]))
    middle = int(calculate_joint_angle(points[9], points[10], points[11]))
    ring = int(calculate_joint_angle(points[13], points[14], points[15]))
    pinky = int(calculate_joint_angle(points[17], points[18], points[19]))

    return FingerAngles(thumb, index, middle, ring, pinky)


def clamp_angle(angle: int) -> int:
    """把角度限制在 0~180。"""
    return max(0, min(180, int(angle)))


def format_packet(angles: FingerAngles, two_finger_mode: bool = True) -> str:
    """把角度打包成串口报文。

    双指模式：TTTIII\n
    五指模式：TTTIIIMMMRRRPPP\n
    每个角度固定 3 位，不足前补零，方便下位机解析。
    """
    values: Sequence[int]
    if two_finger_mode:
        values = [angles.thumb, angles.index]
    else:
        values = angles.as_list()

    return "".join(f"{clamp_angle(value):03d}" for value in values) + "\n"


def draw_angle_overlay(frame, angles: FingerAngles) -> None:
    """在画面左上角叠加当前角度，便于调试和录制演示视频。"""
    lines = [
        f"Thumb : {angles.thumb:03d}",
        f"Index : {angles.index:03d}",
        f"Middle: {angles.middle:03d}",
        f"Ring  : {angles.ring:03d}",
        f"Pinky : {angles.pinky:03d}",
    ]

    for i, line in enumerate(lines):
        cv2.putText(
            frame,
            line,
            (20, 35 + i * 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )


# =========================
# 主流程
# =========================
def main() -> None:
    try:
        serial_port = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=SERIAL_TIMEOUT)
    except SerialException as exc:
        raise SystemExit(f"无法打开串口 {SERIAL_PORT}：{exc}") from exc

    camera = cv2.VideoCapture(CAMERA_INDEX)
    if not camera.isOpened():
        serial_port.close()
        raise SystemExit("无法打开摄像头，请检查设备是否被占用。")

    last_packet = ""
    last_send_time = 0.0

    print("上位机已启动。")
    print(f"串口：{SERIAL_PORT} @ {BAUDRATE}")
    print(f"发送模式：{'双指模式' if TWO_FINGER_MODE else '五指模式'}")
    print("按 q 或 ESC 退出。")

    with mp_hands.Hands(
        model_complexity=0,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as hands_model:
        try:
            while camera.isOpened():
                success, frame = camera.read()
                if not success:
                    print("摄像头读帧失败，跳过当前帧。")
                    continue

                frame.flags.writeable = False
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands_model.process(rgb_frame)
                frame.flags.writeable = True
                frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)

                current_angles = None
                if results.multi_hand_landmarks:
                    # 当前版本只取第一只检测到的手，避免多手时控制源混乱。
                    hand_landmarks = results.multi_hand_landmarks[0]
                    mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style(),
                    )

                    current_angles = extract_finger_angles(hand_landmarks)
                    draw_angle_overlay(frame, current_angles)

                    packet = format_packet(current_angles, TWO_FINGER_MODE)
                    now = time.time()

                    # 只在内容变化、且满足最小发送间隔时发一次，减少串口刷屏。
                    if packet != last_packet and (now - last_send_time) >= SEND_INTERVAL_S:
                        serial_port.write(packet.encode("utf-8"))
                        last_packet = packet
                        last_send_time = now
                        print(f"发送报文: {packet.strip()}")

                if FLIP_DISPLAY:
                    frame = cv2.flip(frame, 1)

                cv2.imshow(DISPLAY_WINDOW_NAME, frame)
                key = cv2.waitKey(5) & 0xFF
                if key == ord("q") or key == 27:
                    print("用户请求退出程序。")
                    break
        finally:
            camera.release()
            serial_port.close()
            cv2.destroyAllWindows()
            print("资源已释放，程序安全退出。")


if __name__ == "__main__":
    main()
