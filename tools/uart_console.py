#!/usr/bin/env python3
"""Console UART 2 chiều (gõ lệnh + xem log), không cần pyserial/picocom.

Dùng:  tools/uart_console.py [/dev/ttyUSB0] -l work/pi-uart7.log
Thoát: Ctrl-]

Lưu ý: chỉ MỘT tiến trình được đọc /dev/ttyUSB0; nếu work/wait-pi.py hoặc
`cat /dev/ttyUSB0` đang chạy thì dữ liệu sẽ bị chia đôi cho cả hai.
"""
import argparse
import os
import select
import sys
import termios
import tty

SPEEDS = {
    "9600": termios.B9600,
    "57600": termios.B57600,
    "115200": termios.B115200,
    "1500000": getattr(termios, "B1500000", termios.B115200),
}


def configure(fd, baud):
    (iflag, oflag, cflag, lflag, _ispeed, _ospeed, cc) = termios.tcgetattr(fd)
    iflag &= ~(
        termios.IGNBRK | termios.BRKINT | termios.PARMRK | termios.ISTRIP
        | termios.INLCR | termios.IGNCR | termios.ICRNL | termios.IXON | termios.IXOFF
    )
    oflag &= ~termios.OPOST
    lflag &= ~(
        termios.ECHO | termios.ECHONL | termios.ICANON | termios.ISIG | termios.IEXTEN
    )
    cflag &= ~(termios.CSIZE | termios.PARENB | termios.CSTOPB)
    cflag |= termios.CS8 | termios.CREAD | termios.CLOCAL
    cc[termios.VMIN] = 1
    cc[termios.VTIME] = 0
    speed = SPEEDS.get(str(baud), termios.B115200)
    termios.tcsetattr(fd, termios.TCSANOW,
                      [iflag, oflag, cflag, lflag, speed, speed, cc])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dev", nargs="?", default="/dev/ttyUSB0")
    ap.add_argument("-b", "--baud", default="115200")
    ap.add_argument("-l", "--log", default=None, help="ghi toàn bộ dữ liệu nhận được ra file")
    args = ap.parse_args()

    fd = os.open(args.dev, os.O_RDWR | os.O_NOCTTY)
    configure(fd, args.baud)

    log = open(args.log, "ab", buffering=0) if args.log else None
    sys.stderr.write(f"[uart-console] {args.dev} @ {args.baud}"
                     + (f" -> {args.log}" if args.log else "")
                     + " (Ctrl-] để thoát)\n")
    sys.stderr.flush()

    stdin = sys.stdin.fileno()
    stdin_state = termios.tcgetattr(stdin) if os.isatty(stdin) else None
    if stdin_state is not None:
        tty.setraw(stdin)
    try:
        while True:
            ready, _, _ = select.select([fd, stdin], [], [], 1.0)
            if fd in ready:
                data = os.read(fd, 4096)
                if not data:
                    continue
                if log:
                    log.write(data)
                sys.stdout.write(data.decode("utf-8", "replace"))
                sys.stdout.flush()
            if stdin in ready:
                chunk = os.read(stdin, 1024)
                if not chunk:
                    break
                if b"\x1d" in chunk:  # Ctrl-]
                    chunk = chunk.split(b"\x1d")[0]
                    if chunk:
                        os.write(fd, chunk)
                    break
                os.write(fd, chunk)
    except KeyboardInterrupt:
        pass
    finally:
        if stdin_state is not None:
            termios.tcsetattr(stdin, termios.TCSANOW, stdin_state)
        if log:
            log.close()
        os.close(fd)


if __name__ == "__main__":
    main()
