import socket
import sys
import time
import csv
import json
from datetime import datetime
from protocol import TinyTelemetryProtocol, MSG_INIT, MSG_DATA, MSG_HEARTBEAT, MSG_ACK
from performance_monitor import PerformanceMonitor

# Maximum UDP application payload size (excluding header)
MAX_UDP_PAYLOAD = 200  # bytes

class TelemetryCollector:
    def __init__(self, host=socket.gethostbyname(socket.gethostname()), port=5000):
        self.host = host
        self.port = port
        self.socket = None
        # Per-device state
        self.device_state = {}  # device_id -> {'last_seq': num, 'last_timestamp': ts}
        self.received_sequences = {}  # Track all received seq nums per device for duplicate detection
        self.csv_file = None
        self.csv_writer = None
        self.total_expected = 0
        self.total_received = 0
        self.total_lost = 0
        self.packet_buffer = []  # Buffer for reordering
        self.buffer_timeout = 2.0  # Wait 2 seconds before processing
        
        # Phase 2 Metrics
        self.total_duplicates = 0        # Count of duplicate messages
        self.total_retransmits = 0       # Count of retransmissions (duplicates due to RDT)
        self.sequence_gap_count = 0      # Number of gap events (not total missing)
        self.total_bytes_received = 0    # Total bytes (header + payload)
        self.total_cpu_time_ms = 0       # Total CPU time spent processing
        self.performance_monitor = PerformanceMonitor()

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
        # Write header row with duplicate_flag, gap_flag, retransmit_flag columns
        self.csv_writer.writerow(['timestamp', 'device_id', 'seq_num', 'msg_type', 'temperature', 'humidity', 'duplicate_flag', 'gap_flag', 'retransmit_flag', 'packet_bytes'])
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

    # feature: Check for device timeouts
    def check_device_timeout(self, timeout=30):
        """Check for devices that have timed out"""
        current_time = time.time()
        for device_id, state in list(self.device_state.items()):
            if current_time - state['last_seen'] > timeout:
                print(f"[TIMEOUT] Device {device_id} has not sent data for {timeout} seconds. Marking as offline.")
                del self.device_state[device_id]

    def process_packet(self, data, addr):
        """Process received packet"""
        cpu_start = time.perf_counter()  # Start CPU timing
        
        try:
            # Track total bytes received (header + payload)
            packet_bytes = len(data)
            self.total_bytes_received += packet_bytes
            
            # Parse message
            header, payload = TinyTelemetryProtocol.parse_message(data)
            arrival_time = time.time()
            
            device_id = header['device_id']
            seq_num = header['seq_num']
            timestamp = header['timestamp']
            msg_type = header['msg_type']
            msg_type_str = TinyTelemetryProtocol.msg_type_to_string(msg_type)
            
            # Send ACK for DATA and BATCH messages (not INIT or HEARTBEAT)
            if msg_type in [MSG_DATA, 3]:  # MSG_DATA or MSG_BATCH
                ack_packet = TinyTelemetryProtocol.create_message(MSG_ACK, device_id, seq_num, timestamp=0, payload=b'')
                self.socket.sendto(ack_packet, addr)

            # Check payload size constraint (Phase 2 requirement: <= 200 bytes)
            payload_size = len(payload) if payload else 0
            if payload_size > MAX_UDP_PAYLOAD:
                print(f"[WARNING] Payload size {payload_size} exceeds max {MAX_UDP_PAYLOAD} bytes!")

            # Initialize device state if new
            if device_id not in self.device_state:
                self.device_state[device_id] = {
                    'last_seq': -1,
                    'last_timestamp': 0,
                    'packet_count': 0,
                    'last_seen': arrival_time,
                    'heartbeat_count': 0
                }
                self.received_sequences[device_id] = set()

            state = self.device_state[device_id]
            duplicate_flag = False
            retransmit_flag = False
            gap_flag = False

            # Check for duplicate/retransmission (skip for heartbeats - they all use seq 0)
            if msg_type != MSG_HEARTBEAT and seq_num in self.received_sequences[device_id]:
                duplicate_flag = True
                retransmit_flag = True  # Assume duplicate is a retransmission from RDT
                self.total_duplicates += 1
                self.total_retransmits += 1

            # Check for sequence gap (skip for HEARTBEAT messages)
            if msg_type not in [3, MSG_HEARTBEAT] and state['last_seq'] != -1 and seq_num > state['last_seq'] + 1:
                gap_flag = True
                gap_size = seq_num - state['last_seq'] - 1
                self.sequence_gap_count += 1  # Track gap event count
                print(f"[WARNING] Device {device_id}: Sequence gap detected! "
                      f"Missing {gap_size} packet(s) between seq {state['last_seq']} and {seq_num}")

            if gap_flag:
                self.total_lost += gap_size
            
            # DON'T log to console here - will be done in display_packet() after reordering
            # to prevent double-logging

            # Update state and handle message type specifics
            if not duplicate_flag:
                # Don't update last_seq for heartbeats (they don't have real sequence numbers)
                if msg_type != MSG_HEARTBEAT:
                    state['last_seq'] = seq_num
                state['last_timestamp'] = timestamp
                state['packet_count'] += 1
                state['last_seen'] = arrival_time
                
                # Track heartbeat count (display immediately - not buffered)
                if msg_type == MSG_HEARTBEAT:
                    state['heartbeat_count'] += 1
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Device {device_id} | Seq {seq_num} | Type: {msg_type_str} | From {addr[0]}:{addr[1]}")
                    print(f"          ♥ Device is still alive (Total heartbeats: {state['heartbeat_count']})")
                    self.total_received += 1  # Count heartbeat as 1 reading
                    if self.total_received > 0:
                        loss_rate = (self.total_lost / (self.total_received + self.total_lost)) * 100
                        print(f"[STATISTICS] Total Received: {self.total_received}, Total Lost: {self.total_lost}, Loss Rate: {loss_rate:.2f}%")
                elif msg_type == 3:  # BATCH
                    # Display BATCH header immediately (not buffered)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Device {device_id} | Seq {seq_num} | Type: BATCH | From {addr[0]}:{addr[1]}")
                    readings = json.loads(payload.decode('utf-8'))
                    print(f"          [BATCH] {len(readings)} readings:")
                    
                    # Track last reading seq to detect gaps within batch
                    # Initialize to 0 (INIT seq), so first DATA reading should be seq 1
                    last_reading_seq = state.get('last_reading_seq', 0)
                    
                    for reading in readings:
                        reading_seq = reading.get('seq_num', 0)
                        reading_gap_flag = False
                        reading_duplicate_flag = False
                        
                        # Check for duplicate reading
                        if reading_seq in self.received_sequences[device_id]:
                            reading_duplicate_flag = True
                            print(f"            [DUPLICATE] Seq {reading_seq} already received")
                        
                        # Check for gap within batch (detect if first reading isn't seq 1, or any subsequent gap)
                        if reading_seq > last_reading_seq + 1:
                            gap_size = reading_seq - last_reading_seq - 1
                            reading_gap_flag = True
                            print(f"            [LOST] Missing {gap_size} reading(s) between seq {last_reading_seq} and {reading_seq}")
                            self.total_lost += gap_size
                            self.sequence_gap_count += 1
                        
                        # Display each reading
                        print(f"            Seq {reading_seq} | Temp: {reading.get('temperature')}, Hum: {reading.get('humidity')}")
                        
                        # Log to CSV with duplicate_flag and gap_flag
                        if self.csv_writer:
                            self.csv_writer.writerow([
                                datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                                device_id,
                                reading_seq,
                                'BATCH_DATA',
                                reading.get('temperature'),
                                reading.get('humidity'),
                                1 if reading_duplicate_flag else 0,  # duplicate_flag
                                1 if reading_gap_flag else 0,  # gap_flag
                                1 if retransmit_flag else 0,  # retransmit_flag (batch-level retransmission)
                                packet_bytes  # bytes for this packet
                            ])
                        
                        # Track this reading sequence as received
                        if not reading_duplicate_flag:
                            self.received_sequences[device_id].add(reading_seq)
                        
                        last_reading_seq = reading_seq
                    
                    # Save last reading seq for next batch
                    state['last_reading_seq'] = last_reading_seq
                    self.csv_file.flush()
                    self.total_received += len(readings)  # Count each reading in batch
                    # Display statistics after batch
                    if self.total_received > 0:
                        loss_rate = (self.total_lost / (self.total_received + self.total_lost)) * 100
                        print(f"[STATISTICS] Total Received: {self.total_received}, Total Lost: {self.total_lost}, Loss Rate: {loss_rate:.2f}%")
                elif msg_type == MSG_INIT:
                    # Display INIT immediately (not buffered)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Device {device_id} | Seq {seq_num} | Type: {msg_type_str} | From {addr[0]}:{addr[1]}")
                    print("          >> New sensor initialized")
                    self.total_received += 1  # Count INIT as 1
                    if self.total_received > 0:
                        loss_rate = (self.total_lost / (self.total_received + self.total_lost)) * 100
                        print(f"[STATISTICS] Total Received: {self.total_received}, Total Lost: {self.total_lost}, Loss Rate: {loss_rate:.2f}%")
                elif msg_type == MSG_DATA:
                    self.total_received += 1  # Count single DATA as 1 reading
            
            # Parse payload if DATA message
            payload_str = ""
            if msg_type == MSG_DATA and payload:
                try:
                    payload_str = payload.decode('utf-8')
                except:
                    payload_str = f"<binary:{len(payload)}bytes>"

            # DON'T print payload or statistics here - will be done in display_packet()
            
            # Track this sequence number as received (for duplicate/retransmit detection)
            # Do this BEFORE adding to buffer so buffer can detect duplicates
            if msg_type != MSG_HEARTBEAT and not duplicate_flag:
                self.received_sequences[device_id].add(seq_num)
            
            # Record CPU time for this packet
            cpu_end = time.perf_counter()
            cpu_time_ms = (cpu_end - cpu_start) * 1000
            self.total_cpu_time_ms += cpu_time_ms

            return {
                'device_id': device_id,
                'seq': seq_num,
                'timestamp': timestamp,
                'arrival_time': arrival_time,
                'duplicate_flag': duplicate_flag,
                'retransmit_flag': retransmit_flag,
                'gap_flag': gap_flag,
                'msg_type': msg_type_str,
                'payload': payload_str,
                'packet_bytes': packet_bytes,
                'addr': addr  # Include addr here
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
        packet_bytes = packet_info.get('packet_bytes', 0)
        
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
        
        # Write to CSV with duplicate_flag and gap_flag (only for non-BATCH DATA)
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
                humidity,
                1 if duplicate_flag else 0,
                1 if gap_flag else 0,
                1 if packet_info.get('retransmit_flag', False) else 0,
                packet_bytes
            ])
            self.csv_file.flush()
        
        # Print statistics after each packet display
        if self.total_received > 0:
            loss_rate = (self.total_lost / (self.total_received + self.total_lost)) * 100
            print(f"[STATISTICS] Total Received: {self.total_received}, Total Lost: {self.total_lost}, Loss Rate: {loss_rate:.2f}%")

    def run(self):
        """Main server loop"""
        try:
            self.start()
            last_buffer_check = time.time()
            
            while True:
                try:
                    data, addr = self.socket.recvfrom(1024)
                    packet_info = self.process_packet(data, addr)
                    
                    # Add to buffer for reordering (skip BATCH, HEARTBEAT, INIT, and DUPLICATE packets)
                    # Duplicates have already been counted/tracked, no need to buffer them
                    # INIT (seq 0) is displayed immediately and should not be buffered
                    if (packet_info and 
                        packet_info['msg_type'] not in ['BATCH', 'HEARTBEAT', 'INIT'] and 
                        not packet_info['duplicate_flag']):
                        packet_info['buffer_time'] = time.time()
                        self.add_to_buffer(packet_info)
                    elif packet_info and packet_info['duplicate_flag']:
                        # Display duplicates immediately (don't reorder them)
                        flags_str = "[DUPLICATE] "
                        if packet_info['gap_flag']:
                            flags_str += "[GAP] "
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] {flags_str}"
                              f"Device {packet_info['device_id']} | Seq {packet_info['seq']} | "
                              f"Type: {packet_info['msg_type']} | From {packet_info['addr'][0]}:{packet_info['addr'][1]}")
                        if packet_info['payload']:
                            print(f"          Payload: {packet_info['payload']}")
                        if self.total_received > 0:
                            loss_rate = (self.total_lost / (self.total_received + self.total_lost)) * 100
                            print(f"[STATISTICS] Total Received: {self.total_received}, Total Lost: {self.total_lost}, Loss Rate: {loss_rate:.2f}%")
                    
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
        """Print server statistics including Phase 2 metrics"""
        print("\n" + "=" * 80)
        print("[FINAL STATISTICS]")
        print("=" * 80)
        
        # Per-device stats
        print("\n[Per-Device Statistics]")
        for device_id, state in self.device_state.items():
            print(f"  Device {device_id}: {state['packet_count']} packets received, "
                  f"{state['heartbeat_count']} heartbeats, last seq: {state['last_seq']}")
        
        # Phase 2 Required Metrics
        # getting CPU and memory stats
        perf_stats = self.performance_monitor.get_stats()
        print("-" * 40)
        
        # bytes_per_report: Average total bytes (payload + header) per reading
        bytes_per_report = self.total_bytes_received / self.total_received if self.total_received > 0 else 0
        print(f"  bytes_per_report:     {bytes_per_report:.2f} bytes")
        
        # packets_received: Count of successfully received packets
        print(f"  packets_received:     {self.total_received}")
        
        # duplicate_rate: Fraction of duplicate messages detected
        total_packets = self.total_received + self.total_duplicates
        duplicate_rate = self.total_duplicates / total_packets if total_packets > 0 else 0
        print(f"  duplicate_rate:       {duplicate_rate:.4f} ({self.total_duplicates} duplicates)")
        
        # retransmit_rate: Fraction of packets that were retransmissions
        retransmit_rate = self.total_retransmits / total_packets if total_packets > 0 else 0
        print(f"  retransmit_rate:      {retransmit_rate:.4f} ({self.total_retransmits} retransmits)")
        
        # sequence_gap_count: Number of missing sequences detected (gap events)
        print(f"  sequence_gap_count:   {self.sequence_gap_count}")
        print(f"  total_lost_packets:   {self.total_lost}")
        
        # cpu_ms_per_report: CPU time per reading processed
        cpu_ms_per_report = self.total_cpu_time_ms / self.total_received if self.total_received > 0 else 0
        print(f"  cpu_ms_per_report:    {cpu_ms_per_report:.4f} ms")
        
        # Additional useful metrics
        print("\n[Additional Metrics]")
        print("-" * 40)
        loss_rate = (self.total_lost / (self.total_received + self.total_lost)) * 100 if (self.total_received + self.total_lost) > 0 else 0
        print(f"  packet_loss_rate:     {loss_rate:.2f}%")
        print(f"  total_bytes:          {self.total_bytes_received} bytes")
        print(f"  total_cpu_time:       {self.total_cpu_time_ms:.2f} ms")
        print("=" * 80)
        print("[PERFORMANCE]")
        print(f"  CPU Usage:     {perf_stats['cpu_percent']:.2f}%")
        print(f"  Memory Usage:  {perf_stats['memory_mb']:.2f} MB")
        print(f"  CPU Time:      {perf_stats['cpu_time_ms']:.2f} ms")

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
