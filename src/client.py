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
from protocol import TinyTelemetryProtocol, MSG_INIT, MSG_DATA, MSG_HEARTBEAT

class TelemetrySensor:
    def __init__(self, device_id, server_host=socket.gethostbyname(socket.gethostname()), server_port=5000):
        self.device_id = device_id
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.seq_num = 0
        self.packet_loss_rate = 0.0  # 0.0 = 0%, 0.1 = 10%, 0.15 = 15%
        self.jitter_max = 0.0  # Maximum jitter in seconds (e.g., 0.5 = 500ms)
        self.batch_size = 0  # Number of messages to batch before sending
        self.batch_buffer = []

    def connect(self):
        """Create UDP socket"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print("[SENSOR] TinyTelemetry Sensor v1")
        print(f"[SENSOR] Device ID: {self.device_id}")
        print(f"[SENSOR] Target server: {self.server_host}:{self.server_port}")
        print("-" * 80)

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
        
        self.seq_num += 1

    def send_batch(self):
        """Send all buffered readings as a single BATCH message"""
        if not self.batch_buffer:
            return
        
        # Use the last reading's seq_num as the batch packet seq
        last_seq = self.batch_buffer[-1]['seq_num']
        
        payload = json.dumps(self.batch_buffer).encode('utf-8')
        message = TinyTelemetryProtocol.create_message(
            msg_type=3,  # MSG_BATCH
            device_id=self.device_id,
            seq_num=last_seq,  # Use last reading's seq, not a new one
            payload=payload
        )
        self.socket.sendto(message, (self.server_host, self.server_port))
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [BATCH] Sent {len(self.batch_buffer)} readings (seq {self.batch_buffer[0]['seq_num']}-{last_seq})")
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

            print("-" * 80)
            print(f"[SENSOR] Transmission complete. Sent {self.seq_num} messages total.")

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
