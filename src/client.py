"""
TinyTelemetry Client (Sensor)
Simulates an IoT sensor sending telemetry data
"""

import socket
import sys
import time
import json
import random
import threading
from datetime import datetime
from protocol import TinyTelemetryProtocol, MSG_INIT, MSG_DATA, MSG_HEARTBEAT, MSG_ACK

class TelemetrySensor:
    def __init__(self, device_id, server_host=socket.gethostbyname(socket.gethostname()), server_port=5000):
        self.device_id = device_id
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.ack_socket = None  # Separate socket for receiving ACKs
        self.seq_num = 0
        self.packet_loss_rate = 0.0  # 0.0 = 0%, 0.1 = 10%, 0.15 = 15%
        self.jitter_max = 0.0  # Maximum jitter in seconds (e.g., 0.5 = 500ms)
        self.batch_size = 0  # Number of messages to batch before sending
        self.batch_buffer = []
        self.pending_packets = {}
        # Dynamic timeout calculation (RTO = estimatedRTT + 4 * devRTT)
        self.estimated_rtt = 0.5  # Initial estimate: 500ms
        self.dev_rtt = 0.1  # Initial deviation: 100ms
        self.ack_timeout = 0.5  # Will be updated dynamically
        self.alpha = 0.125  # RTT estimation weight
        self.beta = 0.25  # Deviation estimation weight
        self.max_retries = 3
        self.retransmission_count = 0
        self.ack_received_count = 0
        self.total_rtt_samples = 0
        self.ack_lock = threading.Lock()

    def ack_listener_thread(self):
        """Thread to listen for ACK messages from server"""
        while True:
            try:
                data, _ = self.ack_socket.recvfrom(1024)
                header, _ = TinyTelemetryProtocol.parse_message(data)
                msg_type = header['msg_type']
                seq_num = header['seq_num']

                if msg_type == MSG_ACK:
                    current_time = time.time()
                    with self.ack_lock:
                        if seq_num in self.pending_packets:
                            # Calculate sample RTT
                            send_time = self.pending_packets[seq_num]['send_time']
                            sample_rtt = current_time - send_time
                            
                            # Update RTT estimates (TCP-style)
                            # estimatedRTT = (1-α) * estimatedRTT + α * sampleRTT
                            self.estimated_rtt = (1 - self.alpha) * self.estimated_rtt + self.alpha * sample_rtt
                            # devRTT = (1-β) * devRTT + β * |sampleRTT - estimatedRTT|
                            self.dev_rtt = (1 - self.beta) * self.dev_rtt + self.beta * abs(sample_rtt - self.estimated_rtt)
                            # RTO = estimatedRTT + 4 * devRTT
                            self.ack_timeout = self.estimated_rtt + 4 * self.dev_rtt
                            
                            # Track metrics
                            self.ack_received_count += 1
                            self.total_rtt_samples += 1
                            
                            # Remove from pending
                            del self.pending_packets[seq_num]
            except socket.timeout:
                continue  # Normal timeout, keep listening
            except Exception:
                break  # Socket closed, exit thread
    
    def retransmission_timer_thread(self):
        """Thread to check for timed-out packets and retransmit"""
        while True:
            try:
                time.sleep(0.1)  # Check every 100ms
                current_time = time.time()
                
                with self.ack_lock:
                    for seq_num, packet_info in list(self.pending_packets.items()):
                        time_elapsed = current_time - packet_info['send_time']
                        
                        if time_elapsed > self.ack_timeout:
                            if packet_info['retry_count'] < self.max_retries:
                                # Retransmit
                                self.socket.sendto(packet_info['packet'], packet_info['addr'])
                                packet_info['send_time'] = current_time
                                packet_info['retry_count'] += 1
                                self.retransmission_count += 1
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] [RETRANSMIT] seq {seq_num} (attempt {packet_info['retry_count']}/{self.max_retries})")
                            else:
                                # Max retries exceeded, give up
                                del self.pending_packets[seq_num]
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] [LOST] seq {seq_num} after {self.max_retries} retries")
            except Exception:
                break  # Exit on error

    def connect(self):
        """Create UDP socket"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Create separate socket for receiving ACKs (bound to receive responses)
        self.ack_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ack_socket.bind(('', 0))  # Bind to any available port
        self.ack_socket.settimeout(0.1)  # Non-blocking with timeout
        
        # Get the local port for sending (so server knows where to send ACKs)
        self.socket = self.ack_socket  # Use same socket for send/receive
        
        print("[SENSOR] TinyTelemetry Sensor v1")
        print(f"[SENSOR] Device ID: {self.device_id}")
        print(f"[SENSOR] Target server: {self.server_host}:{self.server_port}")
        print("-" * 80)
        
        # Start ACK listener and retransmission timer threads
        ack_thread = threading.Thread(target=self.ack_listener_thread, daemon=True)
        ack_thread.start()
        
        timer_thread = threading.Thread(target=self.retransmission_timer_thread, daemon=True)
        timer_thread.start()

    def send_init(self):
        """Send INIT message to server"""
        message = TinyTelemetryProtocol.create_message(
            msg_type=MSG_INIT,
            device_id=self.device_id,
            seq_num=self.seq_num
        )

        self.socket.sendto(message, (self.server_host, self.server_port))
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent INIT message (seq: {self.seq_num})")
        self.seq_num += 1

    def send_data(self, temperature, humidity):
        # Simulate packet loss
        if random.random() < self.packet_loss_rate:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [SIMULATED LOSS] Packet seq {self.seq_num} dropped!")
            self.seq_num += 1  # Still increment seq so server detects gap
            return  # Don't send the packet

        if self.batch_size > 0:
            """Buffer reading for batch sending"""
            reading = {
                'seq_num': self.seq_num,
                'temperature': round(temperature, 2),
                'humidity': round(humidity, 2)
            }
            self.batch_buffer.append(reading)
            self.seq_num += 1
            if len(self.batch_buffer) >= self.batch_size:
                self.send_batch()
            return

        """Send DATA message with sensor readings"""
        # Create JSON payload
        payload_dict = {
            'temperature': round(temperature, 2),
            'humidity': round(humidity, 2)
        }
        payload = json.dumps(payload_dict).encode('utf-8')

        # Create message
        message = TinyTelemetryProtocol.create_message(
            msg_type=MSG_DATA,
            device_id=self.device_id,
            seq_num=self.seq_num,
            payload=payload
        )
        
        current_seq = self.seq_num  # Capture for logging
        
        # Simulate network jitter using threading (packets can overtake each other)
        if self.jitter_max > 0:
            delay = random.uniform(0, self.jitter_max)
            # Create a thread that waits, then sends
            def delayed_send(msg, seq, delay_time, temp, hum):
                time.sleep(delay_time)
                self.socket.sendto(msg, (self.server_host, self.server_port))
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent DATA (seq: {seq}, delay: {delay_time*1000:.0f}ms): "
                      f"temp={temp:.1f}°C, humidity={hum:.1f}%")
            
            thread = threading.Thread(target=delayed_send, args=(message, current_seq, delay, temperature, humidity))
            thread.daemon = True
            thread.start()
        else:
            # No jitter - send immediately
            self.socket.sendto(message, (self.server_host, self.server_port))
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent DATA (seq: {self.seq_num}): "
                  f"temp={temperature:.1f}°C, humidity={humidity:.1f}%")
            
            # Add to pending packets for ACK tracking
            with self.ack_lock:
                self.pending_packets[current_seq] = {
                    'packet': message,
                    'retry_count': 0,
                    'send_time': time.time(),
                    'addr': (self.server_host, self.server_port)
                }
        
        self.seq_num += 1

    def send_batch(self):
        """Send all buffered readings as a single BATCH message"""
        if not self.batch_buffer:
            return
        
        # Use the last reading's seq_num as the batch packet seq
        last_seq = self.batch_buffer[-1]['seq_num']
        
        # Create compact JSON (no spaces, 2 decimal places for floats)
        compact_buffer = [
            {
                'seq_num': r['seq_num'],
                'temperature': round(r['temperature'], 2),
                'humidity': round(r['humidity'], 2)
            }
            for r in self.batch_buffer
        ]
        payload = json.dumps(compact_buffer, separators=(',', ':')).encode('utf-8')
        
        # Check payload size (max 200 bytes for Phase 2)
        if len(payload) > 200:
            print(f"[WARNING] Batch payload {len(payload)} bytes exceeds 200 byte limit! Splitting batch...")
            # Split batch in half and send separately
            mid = len(self.batch_buffer) // 2
            first_half = self.batch_buffer[:mid]
            second_half = self.batch_buffer[mid:]
            self.batch_buffer = first_half
            self.send_batch()  # Recursive call for first half
            self.batch_buffer = second_half
            self.send_batch()  # Recursive call for second half
            return
        
        message = TinyTelemetryProtocol.create_message(
            msg_type=3,  # MSG_BATCH
            device_id=self.device_id,
            seq_num=last_seq,  # Use last reading's seq, not a new one
            payload=payload
        )
        self.socket.sendto(message, (self.server_host, self.server_port))
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [BATCH] Sent {len(self.batch_buffer)} readings (seq {self.batch_buffer[0]['seq_num']}-{last_seq}) | {len(payload)} bytes")
        
        # Add to pending packets for ACK tracking
        with self.ack_lock:
            self.pending_packets[last_seq] = {
                'packet': message,
                'retry_count': 0,
                'send_time': time.time(),
                'addr': (self.server_host, self.server_port)
            }
        
        # Don't increment seq_num - readings already have their seq numbers
        self.batch_buffer = []  # Clear buffer

    def simulate_sensor_readings(self):
        """Generate realistic sensor readings"""
        # Simulate temperature: 18-28°C with small variations
        base_temp = 22.0
        temp_variation = random.uniform(-3.0, 3.0)
        temperature = base_temp + temp_variation

        # Simulate humidity: 40-70% with small variations
        base_humidity = 55.0
        humidity_variation = random.uniform(-10.0, 10.0)
        humidity = base_humidity + humidity_variation

        return temperature, humidity

    def run(self, interval=1, duration=60):
        """
        Run sensor simulation

        Args:
            interval: Reporting interval in seconds (default: 1s)
            duration: Total duration in seconds (default: 60s)
        """
        try:
            self.connect()

            # Send INIT message
            self.send_init()
            time.sleep(0.5)

            # Send DATA messages periodically
            start_time = time.time()
            next_send_time = start_time + interval

            print(f"\n[SENSOR] Starting data transmission (interval: {interval}s, duration: {duration}s)")
            print("-" * 80)

            # Send HEARTBEAT messages periodically
            last_heartbeat_time = start_time
            heartbeat_interval = 10  # seconds

            while time.time() - start_time < duration:
                current_time = time.time()

                if current_time >= next_send_time:
                    # Generate and send sensor data
                    temperature, humidity = self.simulate_sensor_readings()
                    self.send_data(temperature, humidity)

                    # Schedule next send
                    next_send_time += interval
                    last_heartbeat_time = current_time
                
                #send HEARTBEAT if no data has been sent recently
                if current_time - last_heartbeat_time >= heartbeat_interval:
                    self.send_heartbeat()
                    last_heartbeat_time = current_time

                # Small sleep to prevent busy waiting
                time.sleep(0.01)

            # Flush any remaining readings in batch buffer
            if self.batch_buffer:
                print(f"[SENSOR] Flushing {len(self.batch_buffer)} remaining readings from batch buffer...")
                self.send_batch()

            # Wait for final ACKs
            print("[SENSOR] Waiting for final ACKs...")
            time.sleep(2)
            
            print("-" * 80)
            print(f"[SENSOR] Transmission complete. Sent {self.seq_num} messages total.")
            
            # Display RDT statistics
            print("\n" + "=" * 80)
            print("[RDT STATISTICS]")
            print("=" * 80)
            print(f"  Total packets sent:       {self.seq_num}")
            print(f"  ACKs received:            {self.ack_received_count}")
            print(f"  Retransmissions:          {self.retransmission_count}")
            if self.seq_num > 0:
                print(f"  Retransmission rate:      {(self.retransmission_count / self.seq_num * 100):.2f}%")
            print(f"  Estimated RTT:            {self.estimated_rtt * 1000:.2f} ms")
            print(f"  RTT deviation:            {self.dev_rtt * 1000:.2f} ms")
            print(f"  Current timeout (RTO):    {self.ack_timeout * 1000:.2f} ms")
            print(f"  Timeout calculation:      RTO = estimatedRTT + 4 * devRTT")
            print(f"                            = {self.estimated_rtt * 1000:.2f} + 4 * {self.dev_rtt * 1000:.2f}")
            print(f"                            = {self.ack_timeout * 1000:.2f} ms")
            
            with self.ack_lock:
                unacked = len(self.pending_packets)
            if unacked > 0:
                print(f"  Unacknowledged packets:   {unacked} (lost after {self.max_retries} retries)")
            else:
                print(f"  Unacknowledged packets:   0 (100% delivery success!)")
            print("=" * 80)

        except KeyboardInterrupt:
            print("\n[SENSOR] Interrupted by user")
        except Exception as e:
            print(f"[ERROR] Sensor error: {e}")
        finally:
            if self.socket:
                self.socket.close()

    def send_heartbeat(self):
        """Send HEARTBEAT message to server (doesn't consume sequence number)"""
        message = TinyTelemetryProtocol.create_message(
            msg_type=MSG_HEARTBEAT,
            device_id=self.device_id,
            seq_num=0  # Heartbeats don't need sequence tracking
        )

        self.socket.sendto(message, (self.server_host, self.server_port))
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent HEARTBEAT message")
        # Don't increment seq_num - heartbeats are just status signals


def main():
    """Main entry point"""
    # Default values
    device_id = 1001
    server_host = socket.gethostbyname(socket.gethostname())  # Default: localhost
    server_port = 5000
    interval = 1  # seconds
    duration = 60  # seconds
    packet_loss_rate = 0.0
    jitter_max = 0.0
    batch_size = 0

    # Parse command line arguments
    # Usage: python client.py <device_id> <interval> <duration> <loss_rate> <jitter_max> <batch_size> [server_ip]
    if len(sys.argv) > 1:
        device_id = int(sys.argv[1])
    if len(sys.argv) > 2:
        interval = float(sys.argv[2])
    if len(sys.argv) > 3:
        duration = int(sys.argv[3])
    if len(sys.argv) > 4:
        packet_loss_rate = float(sys.argv[4])
    if len(sys.argv) > 5:
        jitter_max = float(sys.argv[5])
    if len(sys.argv) > 6:
        batch_size = int(sys.argv[6])
    if len(sys.argv) > 7:
        server_host = sys.argv[7]  # Remote server IP
    
    # Print configuration
    print(f"[CONFIG] Server: {server_host}:{server_port}")
    print(f"[CONFIG] Device ID: {device_id}, Interval: {interval}s, Duration: {duration}s")
    print(f"[CONFIG] Loss Rate: {packet_loss_rate*100}%, Jitter Max: {jitter_max}s, Batch Size: {batch_size}")
    print("-" * 80)
    
    # Create and configure sensor
    sensor = TelemetrySensor(device_id, server_host, server_port)
    sensor.packet_loss_rate = packet_loss_rate
    sensor.jitter_max = jitter_max
    sensor.batch_size = batch_size
    sensor.run(interval, duration)

if __name__ == '__main__':
    main()
