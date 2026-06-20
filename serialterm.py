#!/usr/bin/env python3
"""
Cross-platform Serial Terminal
- Optional baudrate (-b, default 115200)
- Optional timestamps (-t), default HH:MM:SS, supports 'iso8601'
- Real-time incoming serial display
- Carriage-return line endings (\r)
- Clean command history without duplicates
- Works on Linux, macOS, Windows
Requirements: pip install pyserial
"""

import sys
import time
import threading
import argparse
import serial
from datetime import datetime

try:
    import readline  # optional, enables history/editing on Linux/macOS
except ImportError:
    readline = None


def format_timestamp(fmt):
    if fmt:
        if fmt.lower() == "iso8601":
            return datetime.now().isoformat()
        else:
            return datetime.now().strftime(fmt)
    return ""


def serial_reader(ser, stop_event, timestamp_fmt=None):
    """Background thread for reading serial data."""
    while not stop_event.is_set():
        try:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                text = data.decode(errors="replace")
                if timestamp_fmt:
                    lines = text.splitlines(keepends=True)
                    text = "".join(f"[{format_timestamp(timestamp_fmt)}] {line}" for line in lines)

                # Print incoming data without breaking prompt
                buffer = readline.get_line_buffer()
                print(f"\r{' ' * (len(buffer) + 2)}\r{text}\n", end="", flush=True)
                print(f"> {buffer}", end="", flush=True)

            else:
                time.sleep(0.01)
        except serial.SerialException as e:
            print(f"\n[ERROR] Serial exception: {e}")
            break
        except Exception as e:
            print(f"\n[ERROR] Reader thread: {e}")
            break


def main():
    parser = argparse.ArgumentParser(description="Simple Serial Terminal")
    parser.add_argument("port", help="Serial port (e.g., COM3 or /dev/ttyUSB0)")
    parser.add_argument("-b", "--baudrate", type=int, default=115200,
                        help="Baudrate (default: 115200)")
    parser.add_argument("-t", "--timestamp", nargs="?", const="%H:%M:%S",
                        help="Enable timestamps. Default format HH:MM:SS. Use 'iso8601' for ISO8601.")
    args = parser.parse_args()

    port = args.port
    baudrate = args.baudrate
    timestamp_fmt = args.timestamp

    try:
        ser = serial.Serial(port, baudrate, timeout=0)
    except serial.SerialException as e:
        print(f"[ERROR] Could not open port {port}: {e}")
        sys.exit(1)

    print(f"[INFO] Connected to {port} at {baudrate} baud.")
    print("[INFO] Press Ctrl+C to exit.")

    stop_event = threading.Event()
    reader_thread = threading.Thread(target=serial_reader,
                                     args=(ser, stop_event, timestamp_fmt),
                                     daemon=True)
    reader_thread.start()

    try:
        while True:
            try:
                line = input("> ")
            except EOFError:
                break

            if not line.strip():
                continue

            # Send command with carriage return
            ser.write((line + "\r").encode())

            # Add to history without duplicates
            if readline and line.strip():
                last_index = readline.get_current_history_length()
                last_item = readline.get_history_item(last_index) if last_index > 0 else None
                if last_item != line:
                    readline.add_history(line)

    except KeyboardInterrupt:
        print("\n[INFO] Exiting...")
    finally:
        stop_event.set()
        ser.close()


if __name__ == "__main__":
    main()
