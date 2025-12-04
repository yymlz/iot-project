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
        
        # Update buffer immediately to prevent re-processing
        self.packet_buffer = remaining_packets
        
        if ready_packets:
            # Sort ready packets by timestamp (THIS IS THE REORDERING!)
            print(f"\n[BUFFER] Processing {len(ready_packets)} buffered packets...")
            ready_packets.sort(key=lambda p: p['timestamp'])
        
            # Process sorted packets
            for packet in ready_packets:
                self.display_packet(packet)

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

            # Check for duplicate (skip for heartbeats - they all use seq 0)
            if msg_type != MSG_HEARTBEAT and seq_num == state['last_seq']:
                duplicate_flag = True

            # Check for sequence gap (skip for BATCH and HEARTBEAT messages)
            if msg_type not in [3, MSG_HEARTBEAT] and state['last_seq'] != -1 and seq_num > state['last_seq'] + 1:
                gap_flag = True
                gap_size = seq_num - state['last_seq'] - 1
                print(f"[WARNING] Device {device_id}: Sequence gap detected! "
                      f"Missing {gap_size} packet(s) between seq {state['last_seq']} and {seq_num}")

            if gap_flag:
                self.total_lost += gap_size
            
            # Log to console - packet header first
            flags_str = ""
            if duplicate_flag:
                flags_str += "[DUPLICATE] "
            if gap_flag:
                flags_str += "[GAP] "

            print(f"[{datetime.now().strftime('%H:%M:%S')}] {flags_str}"
                  f"Device {device_id} | Seq {seq_num} | Type: {msg_type_str} | "
                  f"From {addr[0]}:{addr[1]}")

            # Update state and handle message type specifics
            if not duplicate_flag:
                # Don't update last_seq for heartbeats (they don't have real sequence numbers)
                if msg_type != MSG_HEARTBEAT:
                    state['last_seq'] = seq_num
                state['last_timestamp'] = timestamp
                state['packet_count'] += 1
                state['last_seen'] = arrival_time
                
                # Track heartbeat count
                if msg_type == MSG_HEARTBEAT:
                    state['heartbeat_count'] += 1
                    print(f"          ♥ Device is still alive (Total heartbeats: {state['heartbeat_count']})")
                    self.total_received += 1  # Count heartbeat as 1 reading
                elif msg_type == 3:  # BATCH
                    readings = json.loads(payload.decode('utf-8'))
                    print(f"          [BATCH] {len(readings)} readings:")
                    
                    # Track last reading seq to detect gaps within batch
                    last_reading_seq = state.get('last_reading_seq', 0)
                    
                    for reading in readings:
                        reading_seq = reading.get('seq_num', 0)
                        
                        # Check for gap within batch
                        if last_reading_seq > 0 and reading_seq > last_reading_seq + 1:
                            gap_size = reading_seq - last_reading_seq - 1
                            print(f"            [LOST] Missing {gap_size} reading(s) between seq {last_reading_seq} and {reading_seq}")
                            self.total_lost += gap_size
                        
                        # Display each reading
                        print(f"            Seq {reading_seq} | Temp: {reading.get('temperature')}, Hum: {reading.get('humidity')}")
                        
                        # Log to CSV
                        if self.csv_writer:
                            self.csv_writer.writerow([
                                datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                                device_id,
                                reading_seq,
                                'BATCH_DATA',
                                reading.get('temperature'),
                                reading.get('humidity')
                            ])
                        
                        last_reading_seq = reading_seq
                    
                    # Save last reading seq for next batch
                    state['last_reading_seq'] = last_reading_seq
                    self.csv_file.flush()
                    self.total_received += len(readings)  # Count each reading in batch
                elif msg_type == MSG_INIT:
                    print("          >> New sensor initialized")
                    self.total_received += 1  # Count INIT as 1
                elif msg_type == MSG_DATA:
                    self.total_received += 1  # Count single DATA as 1 reading
            
            # Parse payload if DATA message
            payload_str = ""
            if msg_type == MSG_DATA and payload:
                try:
                    payload_str = payload.decode('utf-8')
                except:
                    payload_str = f"<binary:{len(payload)}bytes>"

            if payload_str:
                print(f"          Payload: {payload_str}")

            # Statistics at the end
            if self.total_received > 0:
                loss_rate = (self.total_lost / (self.total_received + self.total_lost)) * 100
                print(f"[STATISTICS] Total Received: {self.total_received}, Total Lost: {self.total_lost}, Loss Rate: {loss_rate:.2f}%")

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
                    
                    # Add to buffer for reordering (skip BATCH and HEARTBEAT packets)
                    if packet_info and packet_info['msg_type'] not in ['BATCH', 'HEARTBEAT']:
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
    # Use 0.0.0.0 to listen on all interfaces (needed for cross-platform)
    host = '0.0.0.0'
    port = 5000

    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    if len(sys.argv) > 2:
        host = sys.argv[2]  # Optional: specify host

    collector = TelemetryCollector(host, port)
    collector.run()

if __name__ == '__main__':
    main()
