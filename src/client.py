"""
TinyTelemetry Client (Sensor)
Simulates an IoT sensor sending telemetry data
"""

import socket
import sys
import time
import json
import random
from datetime import datetime
from protocol import TinyTelemetryProtocol, MSG_INIT, MSG_DATA

class TelemetrySensor:
    def __init__(self, device_id, server_host=socket.gethostbyname(socket.gethostname()), server_port=5000):
        self.device_id = device_id
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.seq_num = 0

    def connect(self):
        """Create UDP socket"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"[SENSOR] TinyTelemetry Sensor v1")
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
        """Send DATA message with sensor readings"""
        # Create JSON payload
        payload_dict = {
            'temperature': round(temperature, 2),
            'humidity': round(humidity, 2)
        }
        payload = json.dumps(payload_dict).encode('utf-8')

        # Create and send message
        message = TinyTelemetryProtocol.create_message(
            msg_type=MSG_DATA,
            device_id=self.device_id,
            seq_num=self.seq_num,
            payload=payload
        )

        self.socket.sendto(message, (self.server_host, self.server_port))
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent DATA (seq: {self.seq_num}): "
              f"temp={temperature:.1f}°C, humidity={humidity:.1f}%")
        self.seq_num += 1

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

            while time.time() - start_time < duration:
                current_time = time.time()

                if current_time >= next_send_time:
                    # Generate and send sensor data
                    temperature, humidity = self.simulate_sensor_readings()
                    self.send_data(temperature, humidity)

                    # Schedule next send
                    next_send_time += interval

                # Small sleep to prevent busy waiting
                time.sleep(0.01)

            print("-" * 80)
            print(f"[SENSOR] Transmission complete. Sent {self.seq_num} messages total.")

        except KeyboardInterrupt:
            print("\n[SENSOR] Interrupted by user")
        except Exception as e:
            print(f"[ERROR] Sensor error: {e}")
        finally:
            if self.socket:
                self.socket.close()

def main():
    """Main entry point"""
    device_id = 1001
    server_host = socket.gethostbyname(socket.gethostname())
    server_port = 5000
    interval = 1  # seconds
    duration = 60  # seconds

    # Parse command line arguments
    if len(sys.argv) > 1:
        device_id = int(sys.argv[1])
    if len(sys.argv) > 2:
        interval = float(sys.argv[2])
    if len(sys.argv) > 3:
        duration = int(sys.argv[3])

    sensor = TelemetrySensor(device_id, server_host, server_port)
    sensor.run(interval, duration)

if __name__ == '__main__':
    main()
