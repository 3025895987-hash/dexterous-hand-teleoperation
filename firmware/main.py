"""五指灵巧手下位机固件（MicroPython）。

适用场景：
- Raspberry Pi Pico / Pico W（或兼容 MicroPython 的板子）
- 上位机保持不变，继续发送 15 位纯数字角度串
- 角度顺序：拇指 / 食指 / 中指 / 无名指 / 小指

和当前上位机代码的协议完全对应：
- 上位机会把 5 个角度格式化为固定 15 位字符串，例如：
  090045120060030
- 下位机持续从串口字节流中提取数字，并按 15 位一帧解析
- 每 3 位代表一个手指角度，范围默认按 0~180 处理

说明：
1. 这个版本优先保证“协议对齐 + 五指解析 + 五路舵机输出”正确；
2. 如果你的某根手指运动方向反了，只改 SERVO_CONFIGS 里的 invert 即可；
3. 如果某根手指机械行程不一致，只改对应 finger 的 input/output 范围即可。
"""

from machine import Pin, PWM
import sys
import time
import uselect

# ============================================================
# 1) 基础配置
# ============================================================
PWM_FREQUENCY = 50          # 舵机常用 50Hz
PACKET_LENGTH = 15          # 5 根手指 * 每根 3 位角度
SERIAL_POLL_INTERVAL = 0.01 # 主循环空转等待时间（秒）
SERIAL_READ_CHUNK = 32      # 每次尽量多读一点，减少缓冲堆积
DEADBAND = 1                # 小于该角度差值时不更新舵机，减少抖动
VERBOSE = True              # True: 打印调试信息；False: 更安静

# ============================================================
# 2) 五指配置（按实际接线修改）
# ============================================================
# pin       : 舵机信号线接到的 GPIO
# invert    : True 表示把输入角度 angle 映射成 180-angle
# input_min : 接收角度下限（来自上位机）
# input_max : 接收角度上限（来自上位机）
# output_min/output_max : 映射到舵机的角度范围
# min_duty/max_duty      : 该舵机 PWM 脉宽范围（按你的舵机自行校准）
SERVO_CONFIGS = [
    {"name": "thumb",  "pin": 12, "invert": False, "input_min": 0, "input_max": 180, "output_min": 0, "output_max": 180, "min_duty": 1000, "max_duty": 9000},
    {"name": "index",  "pin": 13, "invert": False, "input_min": 0, "input_max": 180, "output_min": 0, "output_max": 180, "min_duty": 1000, "max_duty": 9000},
    {"name": "middle", "pin": 14, "invert": False, "input_min": 0, "input_max": 180, "output_min": 0, "output_max": 180, "min_duty": 1000, "max_duty": 9000},
    {"name": "ring",   "pin": 15, "invert": False, "input_min": 0, "input_max": 180, "output_min": 0, "output_max": 180, "min_duty": 1000, "max_duty": 9000},
    {"name": "pinky",  "pin": 16, "invert": False, "input_min": 0, "input_max": 180, "output_min": 0, "output_max": 180, "min_duty": 1000, "max_duty": 9000},
]

FINGER_NAMES = [cfg["name"] for cfg in SERVO_CONFIGS]

# ============================================================
# 3) 工具函数
# ============================================================
def log(message):
    """统一日志输出，便于后续整体关闭调试信息。"""
    if VERBOSE:
        print(message)


def clamp(value, low, high):
    """把数值限制在指定区间内。"""
    if value < low:
        return low
    if value > high:
        return high
    return value


# 注意：这里不用 Python 内置 map，避免和常见变量名冲突。
def linear_map(value, in_min, in_max, out_min, out_max):
    """线性映射。

    例：把输入角度 30~170 映射到舵机输出 10~150。
    若输入范围异常（in_min == in_max），直接返回 out_min。
    """
    if in_max == in_min:
        return out_min

    value = clamp(value, in_min, in_max)
    ratio = (value - in_min) / (in_max - in_min)
    return int(out_min + ratio * (out_max - out_min))


class ServoController:
    """单个舵机的控制封装。"""

    def __init__(self, config):
        self.name = config["name"]
        self.pin = config["pin"]
        self.invert = config.get("invert", False)
        self.input_min = config.get("input_min", 0)
        self.input_max = config.get("input_max", 180)
        self.output_min = config.get("output_min", 0)
        self.output_max = config.get("output_max", 180)
        self.min_duty = config.get("min_duty", 1000)
        self.max_duty = config.get("max_duty", 9000)

        self.pwm = PWM(Pin(self.pin))
        self.pwm.freq(PWM_FREQUENCY)
        self.last_output_angle = None

    def input_to_output_angle(self, input_angle):
        """把上位机传来的角度转换成当前舵机实际应输出的角度。"""
        input_angle = clamp(int(input_angle), self.input_min, self.input_max)

        if self.invert:
            input_angle = self.input_max - (input_angle - self.input_min)

        output_angle = linear_map(
            input_angle,
            self.input_min,
            self.input_max,
            self.output_min,
            self.output_max,
        )
        return clamp(output_angle, 0, 180)

    def angle_to_duty_u16(self, angle):
        """把 0~180 度舵机角度转成 Pico 的 16 位 PWM 占空比。"""
        angle = clamp(int(angle), 0, 180)
        return self.min_duty + int((self.max_duty - self.min_duty) * angle / 180)

    def set_angle(self, input_angle, force=False):
        """根据输入角度控制舵机。

        force=True 用于初始化，忽略死区。
        """
        output_angle = self.input_to_output_angle(input_angle)

        if (not force) and self.last_output_angle is not None:
            if abs(output_angle - self.last_output_angle) <= DEADBAND:
                return False

        duty = self.angle_to_duty_u16(output_angle)
        self.pwm.duty_u16(duty)
        self.last_output_angle = output_angle
        return True


# ============================================================
# 4) 串口协议解析
# ============================================================
def parse_packet(packet):
    """把 15 位字符串解析成 5 个角度。

    例如：
        "090045120060030" -> [90, 45, 120, 60, 30]
    """
    if len(packet) != PACKET_LENGTH:
        raise ValueError("报文长度错误: {}".format(len(packet)))

    if not packet.isdigit():
        raise ValueError("报文存在非数字字符: {!r}".format(packet))

    angles = []
    for i in range(0, PACKET_LENGTH, 3):
        angles.append(int(packet[i:i + 3]))
    return angles


class PacketReceiver:
    """从 sys.stdin 的连续字节流中提取 15 位纯数字报文。"""

    def __init__(self):
        self.buffer = ""

    def read_available(self):
        """读取当前可读串口数据，并只保留数字字符。

        上位机当前发送的是连续的 15 位数字，不带换行。
        因此这里采用“缓冲区 + 固定长度切帧”的方式。
        """
        while uselect.select([sys.stdin], [], [], 0)[0]:
            chunk = sys.stdin.read(SERIAL_READ_CHUNK)
            if not chunk:
                break

            # 只保留数字。这样即便串口里混入 \r\n 或杂字符，也不会污染主缓冲区。
            for ch in chunk:
                if '0' <= ch <= '9':
                    self.buffer += ch

            # 防止极端情况下缓冲区无限增长：保留最后 4 帧即可。
            if len(self.buffer) > PACKET_LENGTH * 4:
                self.buffer = self.buffer[-PACKET_LENGTH * 4:]

    def get_packets(self):
        """尽可能多地从缓冲区中取出完整报文。"""
        packets = []
        while len(self.buffer) >= PACKET_LENGTH:
            packets.append(self.buffer[:PACKET_LENGTH])
            self.buffer = self.buffer[PACKET_LENGTH:]
        return packets


# ============================================================
# 5) 主程序
# ============================================================
log("下位机程序启动：五指灵巧手控制")
log("等待上位机发送 15 位角度串：TTTIIIMMMRRRPPP")

servos = [ServoController(cfg) for cfg in SERVO_CONFIGS]
receiver = PacketReceiver()

# 初始化到 0 度，给舵机一个明确起点。
log("初始化舵机位置...")
for servo in servos:
    servo.set_angle(0, force=True)
    log("{} -> init 000° (GPIO{})".format(servo.name, servo.pin))
time.sleep(1.0)

last_input_angles = [None, None, None, None, None]

while True:
    receiver.read_available()
    packets = receiver.get_packets()

    # 如果本轮收到多帧，只处理最后一帧，减少延迟堆积。
    if packets:
        packet = packets[-1]

        try:
            input_angles = parse_packet(packet)

            changed = []
            for i in range(5):
                angle = clamp(input_angles[i], 0, 180)
                updated = servos[i].set_angle(angle)
                if updated:
                    changed.append("{}={:03d}".format(FINGER_NAMES[i], angle))
                last_input_angles[i] = angle

            if changed:
                log("收到报文: {} | 更新: {}".format(packet, ", ".join(changed)))
        except Exception as exc:
            log("解析失败: {} | packet={!r}".format(exc, packet))

    time.sleep(SERIAL_POLL_INTERVAL)
