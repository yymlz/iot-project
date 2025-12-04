TinyTelemetry Protocol v1 - Phase 1 Prototype
==============================================

IoT Telemetry Protocol for Sensor Reporting over UDP
Computer Networks Project - Phase 1 Deliverable

Project Team: [Your Team Name]
Date: October 2025

---

OVERVIEW
--------
TinyTelemetry is a lightweight application-layer protocol designed for IoT sensors
to report telemetry data (temperature, humidity) to a central collector over UDP.

This Phase 1 prototype demonstrates:
- INIT message exchange (sensor initialization)
- DATA message exchange (periodic sensor readings)
- Compact binary header (10 bytes)
- UDP-based communication


PROTOCOL HEADER FORMAT
----------------------
Total size: 10 bytes

Field       | Size (bits) | Description
------------|-------------|------------------
Version     | 4           | Protocol version (currently 1)
MsgType     | 4           | Message type: 0=INIT, 1=DATA, 2=HEARTBEAT
DeviceID    | 16          | Unique device identifier (0-65535)
SeqNum      | 16          | Sequence number (0-65535)
Timestamp   | 32          | Unix epoch seconds
Flags       | 8           | Reserved for future use

Pack format: struct.pack('!BHHIB', version_type, device_id, seq_num, timestamp, flags)


MESSAGE TYPES (Phase 1)
-----------------------
- INIT (0):  Initial handshake from sensor to collector
- DATA (1):  Sensor reading with JSON payload {"temperature": X, "humidity": Y}


REQUIREMENTS
------------
- Python 3.7 or higher
- Standard library only (no external dependencies)
- Works on macOS, Linux, and Windows


DIRECTORY STRUCTURE
-------------------
iot-project/
├── README.txt              # This file
├── src/
│   ├── protocol.py        # Protocol header packing/unpacking
│   ├── server.py          # Collector (receives telemetry)
│   ├── client.py          # Sensor (sends telemetry)
├── tests/
│   └── baseline_test.sh   # Automated baseline test script
├── logs/                  # Test outputs (generated)
└── Docs/
    ├── proposal.pdf       # Project proposal
    └── mini_rfc_draft.pdf # Mini-RFC sections 1-3


HOW TO RUN LOCALLY
------------------

1. Start the server (collector):

   cd src
   python3 server.py

   The server will listen on 127.0.0.1:5000


2. In a separate terminal, start the client (sensor):

   cd src
   python3 client.py

   Default parameters:
   - Device ID: 1001
   - Reporting interval: 1 second
   - Duration: 60 seconds


3. Custom parameters:

   python3 client.py <device_id> <interval> <duration>

   Example (Device 2001, every 5 seconds, for 30 seconds):
   python3 client.py 2001 5 30


4. Stop the server:
   Press Ctrl+C


BASELINE TEST SCRIPT
--------------------

To run the automated baseline test:

   cd tests
   chmod +x baseline_test.sh
   ./baseline_test.sh

   using instead:
   run_baseline_test.py
   with same instructions:{
      cd tests
      python run_baseline_test.py
   }
   -seeing all server receiving packets at server_log.txt

===========================================================================================

This script will:
- Start the server
- Run the client for 60 seconds (1-second interval)
- Collect logs
- Verify ≥99% packet delivery
- Save results to logs/baseline_<timestamp>/

Expected output:
- Total packets: ~61 (1 INIT + 60 DATA)
- Success rate: ≥99%
- No sequence gaps (baseline has no network impairment)


EXAMPLE OUTPUT
--------------

Server output:
[SERVER] TinyTelemetry Collector v1 started
[SERVER] Listening on 127.0.0.1:5000
[SERVER] Waiting for sensor data...
[12:34:56] Device 1001 | Seq 0 | Type: INIT | From 127.0.0.1:54321
          >> New sensor initialized
[12:34:57] Device 1001 | Seq 1 | Type: DATA | From 127.0.0.1:54321
          Payload: {"temperature": 23.45, "humidity": 58.32}
[12:34:58] Device 1001 | Seq 2 | Type: DATA | From 127.0.0.1:54321
          Payload: {"temperature": 22.87, "humidity": 56.71}
...

Client output:
[SENSOR] TinyTelemetry Sensor v1
[SENSOR] Device ID: 1001
[SENSOR] Target server: 127.0.0.1:5000
[12:34:56] Sent INIT message (seq: 0)
[12:34:57] Sent DATA (seq: 1): temp=23.4°C, humidity=58.3%
[12:34:58] Sent DATA (seq: 2): temp=22.9°C, humidity=56.7%
...
[SENSOR] Transmission complete. Sent 61 messages total.


DEMO VIDEO
----------

A 5-minute demonstration video is available at:

[VIDEO LINK TO BE ADDED]

The video shows:
1. Protocol header format explanation
2. Running the server
3. Running the client
4. INIT and DATA message exchange
5. Server logs showing received packets
6. Baseline test script execution


FEATURES IMPLEMENTED (Phase 1)
-------------------------------
✓ Compact 10-byte binary header
✓ INIT message type
✓ DATA message type with JSON payload
✓ Device ID and sequence number tracking
✓ Timestamp field (Unix epoch)
✓ UDP socket communication
✓ Server logs all received packets
✓ Duplicate detection (server-side)
✓ Sequence gap detection (server-side)
✓ Automated baseline test script


FUTURE WORK (Phase 2 & 3)
--------------------------
- HEARTBEAT message implementation
- Batching mode (multiple readings per packet)
- Network impairment testing (loss, delay, jitter)
- Packet reordering by timestamp
- CSV logging for analysis
- PCAP capture for protocol inspection
- Performance metrics collection
- Enhanced error handling


TROUBLESHOOTING
---------------

Q: "Address already in use" error when starting server?
A: Another process is using port 5000. Either:
   - Kill the existing process: lsof -ti:5000 | xargs kill
   - Use a different port: python3 server.py 5001

Q: Client can't connect to server?
A: Ensure:
   - Server is running first
   - Firewall allows UDP on port 5000
   - Using correct server address (127.0.0.1 for local)

Q: Test script shows "command not found: bc"?
A: Install bc: brew install bc (macOS) or apt-get install bc (Linux)


CONTACT
-------
For questions about this project, contact:
[Your team members and emails]


---
End of README
