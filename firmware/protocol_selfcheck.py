"""桌面端自检脚本：用于验证五指报文解析逻辑。

这个脚本不依赖 machine 模块，可在普通 Python 上运行。
它不能替代真实硬件测试，但可以验证：
1. 15 位报文拆分是否正确；
2. 连续字节流切帧是否正确；
3. 多帧连续输入时，能否稳定拿到最后一帧。
"""

PACKET_LENGTH = 15


def parse_packet(packet):
    if len(packet) != PACKET_LENGTH:
        raise ValueError("bad len")
    if not packet.isdigit():
        raise ValueError("non-digit")
    return [int(packet[i:i+3]) for i in range(0, PACKET_LENGTH, 3)]


class PacketReceiver:
    def __init__(self):
        self.buffer = ""

    def feed(self, data):
        for ch in data:
            if '0' <= ch <= '9':
                self.buffer += ch

    def get_packets(self):
        packets = []
        while len(self.buffer) >= PACKET_LENGTH:
            packets.append(self.buffer[:PACKET_LENGTH])
            self.buffer = self.buffer[PACKET_LENGTH:]
        return packets


def main():
    # 1) 单帧解析
    p1 = "090045120060030"
    assert parse_packet(p1) == [90, 45, 120, 60, 30]

    # 2) 分段送入，验证缓冲拼接
    receiver = PacketReceiver()
    receiver.feed("090045")
    assert receiver.get_packets() == []
    receiver.feed("120060030")
    packets = receiver.get_packets()
    assert packets == [p1]
    assert parse_packet(packets[0]) == [90, 45, 120, 60, 30]

    # 3) 连续两帧，验证切帧正确
    p2 = "180170160150140"
    receiver.feed(p1 + p2)
    packets = receiver.get_packets()
    assert packets == [p1, p2]
    assert parse_packet(packets[1]) == [180, 170, 160, 150, 140]

    # 4) 混入换行、空格等非数字字符，也能剔除
    receiver.feed("\n090045120060030\r\n")
    packets = receiver.get_packets()
    assert packets == [p1]

    print("protocol self-check passed")


if __name__ == "__main__":
    main()
