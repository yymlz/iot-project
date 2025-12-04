"""
TinyTelemetry Server (Collector)
Receives and logs telemetry data from IoT sensors
"""

import socket
import sys
import time
import csv
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
        self.csv_file = None
        self.csv_writer = None
        self.total_expected = 0
        self.total_received = 0
        self.total_lost = 0
        self.packet_buffer = []  # Buffer for reordering
        self.buffer_timeout = 2.0  # Wait 2 seconds before processing

    def start(self):
        """Start the UDP server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))
        print(f"[SERVER] TinyTelemetry Collector v1 started")
        print(f"[SERVER] Listening on {self.host}:{self.port}")
        print(f"[SERVER] Waiting for sensor data...")
        print("-" * 80)
        self.socket.settimeout(5.0)  # Timeout every 5 seconds
        

        # Create CSV file with timestamp
        csv_filename = f"telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.csv_file = open(csv_filename, 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        # Write header row
        self.csv_writer.writerow(['timestamp', 'device_id', 'seq_num', 'msg_type', 'temperature', 'humidity'])
        self.csv_file.flush()
        print(f"[SERVER] Logging to: {csv_filename}")

    def add_to_buffer(self, packet_info):
        """Add packet to buffer for reordering"""
        self.packet_buffer.append(packet_info)

    def process_buffer(self):
        """Process buffered packets in timestamp order"""
        if not self.packet_buffer:
            return
    
        current_time = time.time()
        
        # Find packets that have been in buffer long enough
        ready_packets = []
        remaining_packets = []
        
        for packet in self.packet_buffer:
            if current_time - packet['buffer_time'] >= self.buffer_timeout:
                ready_packets.append(packet)
            else:
                remaining_packets.append(packet)
        
        if ready_packets:
            # Simulate out-of-order arrival (shuffle before sorting)
            import random
            random.shuffle(ready_packets)
            print(f"\n[BUFFER] Received {len(ready_packets)} packets out of order:")
            for p in ready_packets:
                print(f"         Seq {p['seq']} (timestamp: {p['timestamp']})")
            
            # Sort ready packets by timestamp (THIS IS THE REORDERING!)
            ready_packets.sort(key=lambda p: p['timestamp'])
            print(f"[BUFFER] After sorting by timestamp:")
            for p in ready_packets:
                print(f"         Seq {p['seq']} (timestamp: {p['timestamp']})")
            print()
        
        # Process sorted packets
        for packet in ready_packets:
            self.display_packet(packet)
        
        # Keep remaining packets in buffer
        self.packet_buffer = remaining_packets

    # Bonus feature: Check for device timeouts
    def check_device_timeout(self, timeout=30):
        """Check for devices that have timed out"""
        current_time = time.time()
        for device_id, state in list(self.device_state.items()):
            if current_time - state['last_seen'] > timeout:
                print(f"[TIMEOUT] Device {device_id} has not sent data for {timeout} seconds. Marking as offline.")
                del self.device_state[device_id]

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
                    'packet_count': 0,
                    'last_seen': arrival_time,
                    'heartbeat_count': 0
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
                state['last_seen'] = arrival_time
                
                # Track heartbeat count
                if msg_type == MSG_HEARTBEAT:
                    state['heartbeat_count'] += 1
                    print(f"[{datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')}] Device {device_id}: Heartbeat received. Total heartbeats: {state['heartbeat_count']} | Seq {seq_num}")

            # Parse payload if DATA message
            payload_str = ""
            if msg_type == MSG_DATA and payload:
                try:
                    payload_str = payload.decode('utf-8')
                except:
                    payload_str = f"<binary:{len(payload)}bytes>"
            
            if gap_flag:
                self.total_lost += gap_size
            self.total_received += 1

            if self.total_received>0:
                losss_rate = (self.total_lost / (self.total_received + self.total_lost)) * 100
                print(f"[STATISTICS] Total Received: {self.total_received}, Total Lost: {self.total_lost}, Loss Rate: {losss_rate:.2f}%")
            
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
                print("          >> New sensor initialized")
            
            # Log detailed info for HEARTBEAT messages
            if msg_type == MSG_HEARTBEAT:
                print("          ♥ Device is still alive")

            # Write to CSV
            if msg_type == MSG_DATA and payload_str:
                try:
                    payload_json = json.loads(payload_str)
                    temperature = payload_json.get('temperature', '')
                    humidity = payload_json.get('humidity', '')
                except:
                    temperature = ''
                    humidity = ''

                self.csv_writer.writerow([
                    datetime.fromtimestamp(arrival_time).strftime('%Y-%m-%d %H:%M:%S'),
                    device_id,
                    seq_num,
                    msg_type_str,
                    temperature,
                    humidity
                ])
                self.csv_file.flush()

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

    def display_packet(self, packet_info):
        """Display packet information (called after reordering)"""
        device_id = packet_info['device_id']
        seq_num = packet_info['seq']
        timestamp = packet_info['timestamp']
        msg_type_str = packet_info['msg_type']
        payload_str = packet_info['payload']
        duplicate_flag = packet_info['duplicate_flag']
        gap_flag = packet_info['gap_flag']
        addr = packet_info['addr']
        arrival_time = packet_info['arrival_time']
        
        # Log to console
        flags_str = "[REORDERED] "
        if duplicate_flag:
            flags_str += "[DUPLICATE] "
        if gap_flag:
            flags_str += "[GAP] "
        
        print(f"[{datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')}] {flags_str}"
              f"Device {device_id} | Seq {seq_num} | Type: {msg_type_str} | "
              f"From {addr[0]}:{addr[1]}")
        
        if payload_str:
            print(f"          Payload: {payload_str}")
        
        # Write to CSV
        if msg_type_str == 'DATA' and payload_str:
            try:
                payload_json = json.loads(payload_str)
                temperature = payload_json.get('temperature', '')
                humidity = payload_json.get('humidity', '')
            except:
                temperature = ''
                humidity = ''

            self.csv_writer.writerow([
                datetime.fromtimestamp(arrival_time).strftime('%Y-%m-%d %H:%M:%S'),
                device_id,
                seq_num,
                msg_type_str,
                temperature,
                humidity
            ])
            self.csv_file.flush()

    def run(self):
        """Main server loop"""
        try:
            self.start()
            last_buffer_check = time.time()
            
            while True:
                try:
                    data, addr = self.socket.recvfrom(1024)
                    packet_info = self.process_packet(data, addr)
                    
                    # Add to buffer for reordering
                    if packet_info:
                        packet_info['buffer_time'] = time.time()
                        packet_info['addr'] = addr
                        self.add_to_buffer(packet_info)
                    
                    # Check buffer every 3 seconds even while receiving
                    if time.time() - last_buffer_check >= 3.0:
                        self.process_buffer()
                        last_buffer_check = time.time()
                    
                except socket.timeout:
                    # No packet received in 5 seconds, check for offline devices
                    self.check_device_timeout()
                    self.process_buffer()  # Process buffered packets
                    last_buffer_check = time.time()

        except KeyboardInterrupt:
            print("\n" + "-" * 80)
            print("[SERVER] Shutting down...")
            # Process any remaining buffered packets
            self.buffer_timeout = 0  # Force process all
            self.process_buffer()
            self.print_statistics()
        except Exception as e:
            print(f"[ERROR] Server error: {e}")
        finally:
            if self.csv_file:
                self.csv_file.close()
            if self.socket:
                self.socket.close()

    def print_statistics(self):
        """Print server statistics"""
        print("\n[STATISTICS]")
        for device_id, state in self.device_state.items():
            print(f"  Device {device_id}: {state['packet_count']} packets received, "
                  f"{state['heartbeat_count']} heartbeats, last seq: {state['last_seq']}")

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
