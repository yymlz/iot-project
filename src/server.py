"""
TinyTelemetry Server (Collector)
Receives and logs telemetry data from IoT sensors
"""

import socket
import sys
import time
import json
from datetime import datetime
from protocol import TinyTelemetryProtocol, MSG_INIT, MSG_DATA, MSG_HEARTBEAT

class TelemetryCollector:
    def __init__(self, host=socket.gethostbyname(socket.gethostname()), port=5000):
        self.host = host
        self.port = port
        self.socket = None
        # Per-device state
        self.device_state = {}  # device_id -> {'last_seq': num, 'last_timestamp': ts}

    def start(self):
        """Start the UDP server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))
        print(f"[SERVER] TinyTelemetry Collector v1 started")
        print(f"[SERVER] Listening on {self.host}:{self.port}")
        print(f"[SERVER] Waiting for sensor data...")
        print("-" * 80)

    def process_packet(self, data, addr):
        """Process received packet"""
        try:
            # Parse message
            header, payload = TinyTelemetryProtocol.parse_message(data)
            arrival_time = time.time()

            device_id = header['device_id']
            seq_num = header['seq_num']
            timestamp = header['timestamp']
            msg_type = header['msg_type']
            msg_type_str = TinyTelemetryProtocol.msg_type_to_string(msg_type)

            # Initialize device state if new
            if device_id not in self.device_state:
                self.device_state[device_id] = {
                    'last_seq': -1,
                    'last_timestamp': 0,
                    'packet_count': 0
                }

            state = self.device_state[device_id]
            duplicate_flag = False
            gap_flag = False

            # Check for duplicate
            if seq_num == state['last_seq']:
                duplicate_flag = True

            # Check for sequence gap
            if state['last_seq'] != -1 and seq_num > state['last_seq'] + 1:
                gap_flag = True
                gap_size = seq_num - state['last_seq'] - 1
                print(f"[WARNING] Device {device_id}: Sequence gap detected! "
                      f"Missing {gap_size} packet(s) between seq {state['last_seq']} and {seq_num}")

            # Update state
            if not duplicate_flag:
                state['last_seq'] = seq_num
                state['last_timestamp'] = timestamp
                state['packet_count'] += 1

            # Parse payload if DATA message
            payload_str = ""
            if msg_type == MSG_DATA and payload:
                try:
                    payload_str = payload.decode('utf-8')
                except:
                    payload_str = f"<binary:{len(payload)}bytes>"

            # Log to console
            flags_str = ""
            if duplicate_flag:
                flags_str += "[DUPLICATE] "
            if gap_flag:
                flags_str += "[GAP] "

            print(f"[{datetime.now().strftime('%H:%M:%S')}] {flags_str}"
                  f"Device {device_id} | Seq {seq_num} | Type: {msg_type_str} | "
                  f"From {addr[0]}:{addr[1]}")

            if payload_str:
                print(f"          Payload: {payload_str}")

            # Log detailed info for INIT messages
            if msg_type == MSG_INIT:
                print(f"          >> New sensor initialized")

            return {
                'device_id': device_id,
                'seq': seq_num,
                'timestamp': timestamp,
                'arrival_time': arrival_time,
                'duplicate_flag': duplicate_flag,
                'gap_flag': gap_flag,
                'msg_type': msg_type_str,
                'payload': payload_str
            }

        except Exception as e:
            print(f"[ERROR] Failed to process packet from {addr}: {e}")
            return None

    def run(self):
        """Main server loop"""
        try:
            self.start()
            while True:
                data, addr = self.socket.recvfrom(1024)
                self.process_packet(data, addr)

        except KeyboardInterrupt:
            print("\n" + "-" * 80)
            print("[SERVER] Shutting down...")
            self.print_statistics()
        except Exception as e:
            print(f"[ERROR] Server error: {e}")
        finally:
            if self.socket:
                self.socket.close()

    def print_statistics(self):
        """Print server statistics"""
        print("\n[STATISTICS]")
        for device_id, state in self.device_state.items():
            print(f"  Device {device_id}: {state['packet_count']} packets received, "
                  f"last seq: {state['last_seq']}")

def main():
    """Main entry point"""
    host = socket.gethostbyname(socket.gethostname())
    port = 5000

    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    collector = TelemetryCollector(host, port)
    collector.run()

if __name__ == '__main__':
    main()
