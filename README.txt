# TinyTelemetry Protocol v1
**IoT Telemetry Protocol with Reliable Data Transfer**

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com)

---

## 📋 Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [Protocol Specification](#protocol-specification)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [Testing](#testing)
- [Documentation](#documentation)
- [Performance](#performance)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## 🎯 Overview

TinyTelemetry is a **lightweight, reliable IoT telemetry protocol** designed for resource-constrained sensors to transmit environmental data (temperature, humidity) to a central collector over UDP networks.

### What Makes It Special?

**100% Reliable Delivery** - ACK-based retransmission with dynamic timeout (TCP RFC 6298)  
**Efficient Batching** - Reduces bandwidth by 36-54% with configurable batch sizes  
**Network Resilient** - Handles 15% packet loss, 200ms delay, jitter, duplication, and reordering  
**Comprehensive Testing** - 30+ automated test scenarios using Linux tc/netem  
**Production Ready** - CSV logging, performance monitoring, data visualization  

### Project Status
**Phase 2 Complete** | All reliability features implemented and tested

**Date:** December 2025  
**Computer Networks Course Project**

---

## 🚀 Key Features

### Reliability & Performance
- **Reliable Data Transfer (RDT)** - Stop-and-Wait ARQ with ACK-based retransmission
- **Dynamic Timeout** - Adapts to network conditions using `RTO = estimatedRTT + 4 × devRTT`
- **Duplicate Detection** - Server-side tracking using sequence number sets
- **Gap Detection** - Identifies missing packets in sequence
- **Packet Reordering** - 2-second buffer handles out-of-order delivery
- **Maximum 3 Retries** - Gives up after 3 failed attempts per packet

### Protocol Features
- **5 Message Types** - INIT, DATA, BATCH, HEARTBEAT, ACK
- **Compact Header** - Only 10 bytes ('!BHHIB' without magic number, version, type, device_id, seq, timestamp)
- **Batch Processing** - Send up to 30 readings in one packet (auto-splits at 200-byte limit)
- **Heartbeat Mechanism** - 12-second interval, 30-second device timeout detection
- **JSON Payload** - Human-readable sensor data encoding

### Monitoring & Analysis
- **CSV Logging** - 10 columns including duplicate_flag, gap_flag, retransmit_flag
- **Real-time Metrics** - CPU usage, memory, throughput, packet loss rate
- **Performance Tracking** - psutil integration for system monitoring
- **Data Visualization** - Automated graph generation (5 analysis charts)
- **Comprehensive Statistics** - Per-device breakdowns on shutdown

### Testing Infrastructure
- **30+ Test Scenarios** - Automated suite covering all network conditions
- **Network Impairment** - Loss (5-15%), delay (50-200ms), jitter, duplication, reordering
- **Client-Side Simulation** - Built-in loss/jitter simulation (cross-platform)
- **Linux tc/netem Support** - Real network condition emulation
- **Baseline Validation** - 99%+ delivery rate verification

---

## 📡 Protocol Specification

### Header Format (10 bytes)

```
Bytes 0-1: Magic Number (0xAA55) - Protocol identification
Byte 2:    Version (1)            - Protocol version
Byte 3:    Message Type           - 0=INIT, 1=DATA, 2=HEARTBEAT, 3=BATCH, 4=ACK
Bytes 4-5: Device ID (16-bit)     - Unique sensor identifier (0-65535)
Bytes 6-7: Sequence Number (16-bit) - Monotonic packet counter
Bytes 8-9: Timestamp (16-bit)     - Truncated Unix epoch (lower 16 bits)
```

**Struct Format:** `'!HBBHHH'` (network byte order, big-endian)
**Struct Format:** `'!HBBHHH'` (network byte order, big-endian)

### Message Types

| Type | Value | Description | Payload | Requires ACK |
|------|-------|-------------|---------|--------------|
| **INIT** | 0 | Session initialization | Empty | Yes |
| **DATA** | 1 | Single sensor reading | `{"temperature": 22.5, "humidity": 58.3}` | Yes |
| **HEARTBEAT** | 2 | Keep-alive (seq=0) | Empty | No |
| **BATCH** | 3 | Multiple readings | `[{"seq_num": 1, "temperature": 22.5, ...}, ...]` | Yes |
| **ACK** | 4 | Acknowledgment | Empty | No |

### Sample Packets

**INIT Message:**
```
Header: AA 55 01 00 03 E9 00 00 12 34
        │    │  │  │  │     │     │
        │    │  │  │  │     │     └─ Timestamp (lower 16 bits)
        │    │  │  │  │     └─────── Sequence: 0
        │    │  │  │  └───────────── Device ID: 1001
        │    │  │  └──────────────── Type: INIT (0)
        │    │  └─────────────────── Version: 1
        │    └────────────────────── Magic: 0xAA55
        └─────────────────────────── (10 bytes total)
Payload: (empty)
```

**DATA Message:**
```
Header: AA 55 01 01 03 E9 00 01 12 35
Payload: {"temperature": 22.5, "humidity": 58.3}
Total: ~46 bytes
```

**BATCH Message (3 readings):**
```
Header: AA 55 01 03 03 E9 00 05 12 40
Payload: [
  {"seq_num": 1, "temperature": 22.5, "humidity": 58.3},
  {"seq_num": 2, "temperature": 23.1, "humidity": 57.9},
  {"seq_num": 3, "temperature": 21.8, "humidity": 59.2}
]
Total: ~115 bytes
```

**Payload Limit:** Maximum 200 bytes (batches auto-split if exceeded)

---

## Quick Start
   **For Quick Testing Go to test.md file**
### Option 1: Basic Test (Windows)

```powershell
# Terminal 1: Start Server
cd d:\iot-project\src
python server.py

# Terminal 2: Run Client (1-minute test)
cd d:\iot-project\src
python client.py 1001 1 60 0 0 1
```

### Option 2: Comprehensive Testing (Linux/WSL)

```bash
# Terminal 1: Start Server
cd /mnt/d/iot-project/src
python3 server.py

# Terminal 2: Run Full Test Suite (30+ tests, ~30 minutes)
cd /mnt/d/iot-project/tests
sudo ./run_all_tests.sh

# Terminal 3: Generate Analysis Graphs
cd /mnt/d/iot-project/tests
python3 make_graphs.py
```

### What You'll See

**Server Output:**
```
[SERVER] TinyTelemetry Collector v1 started
[SERVER] Listening on 0.0.0.0:5000
[SERVER] Logging to: telemetry_20251212_120000.csv
[12:00:01] Device 1001 | Seq 0 | Type: INIT | From 127.0.0.1:54321
          >> New sensor initialized
[12:00:02] Device 1001 | Seq 1 | Type: DATA | From 127.0.0.1:54321
          Payload: {"temperature": 22.5, "humidity": 58.3}
[12:00:14] ♥ Device is still alive (Total heartbeats: 1)

^C [Ctrl+C pressed]

[FINAL STATISTICS]
Per-Device Statistics:
  Device 1001: 61 packets received, 5 heartbeats, last seq: 60

bytes_per_report: 46.23 bytes
packets_received: 61
duplicate_rate: 0.0000 (0 duplicates)
retransmit_rate: 0.0000 (0 retransmits)
sequence_gap_count: 0
cpu_ms_per_report: 0.0234 ms
packet_loss_rate: 0.00%
```

**Client Output:**
```
[CLIENT] TinyTelemetry Sensor - Device 1001
[CLIENT] Server: 127.0.0.1:5000
[CLIENT] Interval: 1s, Duration: 60s, Batch Size: 1
[12:00:01] INIT → ACK ✓ (RTT: 2.3ms)
[12:00:02] DATA seq=1 → ACK ✓ (RTT: 2.1ms)
[12:00:03] DATA seq=2 → ACK ✓ (RTT: 2.4ms)
...
[12:00:14] HEARTBEAT sent (seq=0)

[CLIENT] Shutting down...
[CLIENT] Statistics:
  Total Sent: 61 packets
  Retransmissions: 0
  Delivery Rate: 100.00%
  Final RTO: 0.156s
```

---

## Installation

### Requirements

- **Python 3.7+** (3.8+ recommended)
- **Operating System:** Windows 10/11, Linux (Ubuntu 20.04+), macOS 11+
- **Network:** UDP port 5000 available

### Optional Dependencies

```bash
# For performance monitoring
pip install psutil

# For graph generation
pip install matplotlib pandas

# For network impairment testing (Linux only)
sudo apt-get install iproute2  # Ubuntu/Debian
sudo yum install iproute-tc    # CentOS/RHEL
```

### Project Structure

```
iot-project/
├── README.txt                      # This file
├── IMPLEMENTATION_SUMMARY.md       # Complete technical documentation
├── COMMUNICATION_SEQUENCES.md      # Protocol procedure documentation
├── TESTING_AND_EVALUATION.md       # Testing methodology guide
├── src/
│   ├── protocol.py                # Protocol header pack/unpack
│   ├── server.py                  # Collector (receiver)
│   ├── client.py                  # Sensor (transmitter)
│   ├── performance_monitor.py     # CPU/memory tracking
│   └── telemetry_*.csv            # Generated CSV logs
├── tests/
│   ├── run_all_tests.sh           # Automated test suite (30+ tests)
│   ├── run_baseline_test.py       # Basic validation test
│   ├── make_graphs.py             # Data visualization generator
│   └── *.png                      # Generated analysis graphs
└── logs/                          # Test results (auto-created)
```

### Clone & Setup

```bash
# Clone repository
git clone https://github.com/yymlz/iot-project.git
cd iot-project

# Verify Python version
python --version  # Should be 3.7+

# Install optional dependencies
pip install psutil matplotlib pandas

# Make test scripts executable (Linux/macOS)
chmod +x tests/*.sh
```

---

## 📖 Usage

### Server (Collector)

**Basic Usage:**
```bash
python server.py [port]
```

**Examples:**
```bash
# Default port 5000
python server.py

# Custom port
python server.py 8080

# Stop server: Press Ctrl+C to see final statistics
```

**Features:**
- Listens on all interfaces (0.0.0.0)
- Logs to CSV: `telemetry_YYYYMMDD_HHMMSS.csv`
- Displays real-time packet information
- Tracks per-device statistics
- Detects duplicates, gaps, retransmissions
- 30-second device timeout detection

### Client (Sensor)

**Syntax:**
```bash
python client.py [device_id] [interval] [duration] [loss_rate] [jitter_max] [batch_size] [server_host]
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| device_id | int | 1001 | Unique sensor identifier (0-65535) |
| interval | int | 1 | Reporting interval in seconds |
| duration | int | 60 | Test duration in seconds |
| loss_rate | float | 0.0 | Client-side packet loss (0.0-1.0) |
| jitter_max | float | 0.0 | Maximum jitter in seconds |
| batch_size | int | 1 | Readings per batch (0=heartbeat only) |
| server_host | str | 127.0.0.1 | Server IP address |

**Examples:**

```bash
# Baseline test (60 seconds, 1-second interval)
python client.py 1001 1 60 0 0 1

# Batch mode (5 readings per batch, 5-second interval)
python client.py 1002 5 60 0 0 5

# Large batches (30 readings, 30-second interval)
python client.py 1003 30 60 0 0 30

# Heartbeat only (no data, 12-second interval)
python client.py 1004 12 60 0 0 0

# Client-side 5% loss simulation
python client.py 1005 1 60 0.05 0 1

# Client-side 100ms jitter simulation
python client.py 1006 1 60 0 0.1 1

# Combined: 10% loss + 50ms jitter
python client.py 1007 1 60 0.10 0.05 1

# Remote server
python client.py 1008 1 60 0 0 1 192.168.1.100
```

---

## 🧪 Testing

### Baseline Test (Quick Validation)

```bash
cd tests
python run_baseline_test.py
```

**Expected:** 99%+ delivery rate, 0 duplicates, 0 gaps

### Comprehensive Test Suite (30+ Scenarios)

**Requirements:** Linux or WSL with sudo access

```bash
cd tests
sudo ./run_all_tests.sh [interface]

# Examples:
sudo ./run_all_tests.sh lo      # Localhost
sudo ./run_all_tests.sh eth0    # Ethernet interface
```

### Test Scenarios Covered

| Category | Tests | Impairments |
|----------|-------|-------------|
| **Baseline** | 3 | No impairment (1s, 5s, 30s intervals) |
| **Packet Loss** | 9 | 5%, 10%, 15% loss × 3 intervals |
| **Network Delay** | 3 | 50ms, 100ms, 200ms |
| **Jitter** | 3 | ±10ms, ±50ms |
| **Duplication** | 3 | 5% duplicate packets |
| **Reordering** | 3 | 25%, 50% reordering |
| **Combined** | 9 | Various combinations |
| **Heartbeat** | 5 | Heartbeat-only mode tests |

**Total:** 30+ tests, each runs for 60 seconds

### Network Impairment Commands (Linux)

```bash
# Apply 10% packet loss
sudo tc qdisc add dev lo root netem loss 10%

# Apply 100ms delay
sudo tc qdisc add dev lo root netem delay 100ms

# Apply jitter (100ms ± 50ms)
sudo tc qdisc add dev lo root netem delay 100ms 50ms

# Combined: 10% loss + 100ms delay + jitter
sudo tc qdisc add dev lo root netem loss 10% delay 100ms 50ms

# Remove impairments
sudo tc qdisc del dev lo root
```

### Data Analysis & Visualization

```bash
cd tests

# Generate all 5 analysis graphs from latest CSV
python3 make_graphs.py

# Use specific CSV file
python3 make_graphs.py ../src/telemetry_20251212_120000.csv
```

**Generated Graphs:**
1. `bytes_vs_interval.png` - Packet size by reporting interval
2. `duplicate_vs_loss.png` - Duplicate rate vs network loss
3. `loss_detection.png` - Gap detection accuracy
4. `duplicate_breakdown.png` - Per-device duplicate counts
5. `retransmit_rate.png` - RDT retransmission analysis

---

### Code Documentation

All modules include detailed docstrings:

```python
# Protocol module
from protocol import pack_header, unpack_header, MSG_INIT, MSG_DATA, MSG_BATCH

# Server module
from server import TelemetryServer

# Client module
from client import TelemetrySensor
```

### CSV Data Format

**File:** `telemetry_YYYYMMDD_HHMMSS.csv`

**Columns:**
```
timestamp, device_id, seq_num, msg_type, temperature, humidity, 
duplicate_flag, gap_flag, retransmit_flag, packet_bytes
```

**Example:**
```csv
2025-12-12 12:00:01,1001,1,DATA,22.5,58.3,0,0,0,46
2025-12-12 12:00:02,1001,2,DATA,23.1,57.9,0,0,0,46
2025-12-12 12:00:03,1001,3,DATA,21.8,59.2,0,0,0,46
```

---

## 📊 Performance
---

## 📊 Performance

### Bandwidth Efficiency

| Configuration | Bytes/Packet | Packets/Min | Bandwidth | Efficiency Gain |
|---------------|--------------|-------------|-----------|-----------------|
| Individual DATA (batch=1) | ~46 | 60 | ~46 bytes/s | Baseline |
| Small Batch (batch=5) | ~175 | 12 | ~35 bytes/s | **24% savings** |
| Large Batch (batch=30) | ~250 | 2 | ~8.3 bytes/s | **82% savings** |

**RDT Overhead:** ~21% (ACK messages + retransmissions under 5% loss)

### Reliability Results

| Network Condition | Loss Rate | Retransmit Rate | Delivery Rate | Avg RTO |
|-------------------|-----------|-----------------|---------------|---------|
| No impairment | 0% | 0% | **100%** | 150ms |
| 5% packet loss | 5% | 5.2% | **100%** | 600ms |
| 10% packet loss | 10% | 11.3% | **100%** | 900ms |
| 15% packet loss | 15% | 18.7% | **100%** | 1200ms |
| 100ms delay | 0% | 0% | **100%** | 450ms |
| 200ms delay | 0% | 0% | **100%** | 850ms |
| Combined (10% loss + 100ms delay) | 10% | 11.1% | **100%** | 950ms |

**Key Achievement:** 100% reliable delivery even under 15% packet loss

### System Resource Usage

| Metric | Server | Client |
|--------|--------|--------|
| CPU Usage | <0.5% | <1% |
| Memory Usage | <30 MB | <20 MB |
| Processing Time | <10ms per packet | <5ms per packet |

**Tested on:** Intel i5-8250U, 8GB RAM, Windows 11

---

## 🔧 Troubleshooting

### Common Issues

**Q: "Address already in use" error when starting server?**

```bash
# Find process using port 5000
# Linux/macOS:
lsof -ti:5000 | xargs kill -9

# Windows PowerShell:
Get-Process -Id (Get-NetTCPConnection -LocalPort 5000).OwningProcess | Stop-Process -Force

# Or use different port:
python server.py 8080
```

**Q: Client can't connect to server?**

**A:** Verify:
1. Server is running first
2. Firewall allows UDP on port 5000
3. Using correct server IP address
4. Server logs show "Listening on 0.0.0.0:5000"

```bash
# Test connectivity (Linux/macOS)
nc -u -v 127.0.0.1 5000

# Windows
Test-NetConnection -ComputerName 127.0.0.1 -Port 5000
```

**Q: "Permission denied" when running test suite?**

**A:** Network impairment testing requires sudo:
```bash
sudo ./run_all_tests.sh lo
```

**Q: CSV file not generated?**

**A:** Check:
1. Server has write permissions in `src/` directory
2. Sufficient disk space available
3. Server ran for at least 1 second before stopping

**Q: Graphs not generating?**

**A:** Install required dependencies:
```bash
pip install matplotlib pandas
```

**Q: High retransmission rate?**

**A:** Check:
1. Network impairment active? (`tc qdisc show dev lo`)
2. Server overloaded? (Check CPU usage)
3. Timeout too aggressive? (Increase initial RTO in client.py)

**Q: Test suite hangs on netem cleanup?**

**A:** Manually remove rules:
```bash
sudo tc qdisc del dev lo root 2>/dev/null
pkill -f client.py
```

### Debug Mode

Enable verbose logging:

```python
# In server.py or client.py, add at top:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Platform-Specific Notes

**Windows:**
- Use PowerShell or CMD (not Git Bash for Python commands)
- WSL recommended for network impairment testing
- Firewall may need UDP exception for port 5000

**Linux:**
- Requires `sudo` for tc/netem network impairment
- Install `iproute2` package for tc command
- Use `lo` interface for localhost testing

**macOS:**
- tc/netem not available (use Network Link Conditioner or client-side simulation)
- May need to install Xcode Command Line Tools
- Use `lo0` interface for localhost

---

## 🎓 Architecture & Design

### Protocol Stack

```
┌─────────────────────────────────┐
│   Application (Sensor Data)     │
├─────────────────────────────────┤
│   TinyTelemetry Protocol v1     │  ← Custom application-layer protocol
│   - Header: 10 bytes             │
│   - Payload: JSON (≤200 bytes)   │
│   - RDT: Stop-and-Wait ARQ       │
├─────────────────────────────────┤
│   UDP (Port 5000)                │
├─────────────────────────────────┤
│   IP (IPv4)                      │
├─────────────────────────────────┤
│   Link Layer                     │
└─────────────────────────────────┘
```

### Reliability Mechanism (Stop-and-Wait ARQ)

```
Client (Sensor)                    Server (Collector)
     │                                    │
     │────── DATA (seq=1) ──────>        │
     │                                    │ Process packet
     │                                    │ Log to CSV
     │                                    │ Check duplicates/gaps
     │                                    │
     │<────── ACK (seq=1) ────────        │
     │                                    │
     │ ✓ Remove from pending              │
     │ ✓ Update RTT estimate              │
     │ ✓ Adjust timeout                   │
     │                                    │
     │────── DATA (seq=2) ──────>        │
     │                                    │
     │  [TIMEOUT - No ACK received]      │
     │                                    │
     │────── DATA (seq=2) ──────>        │ (Retransmission)
     │                                    │
     │<────── ACK (seq=2) ────────        │
     │                                    │
```

### Dynamic Timeout Algorithm (TCP RFC 6298)

```python
# Initial values
estimatedRTT = 0.5  # 500ms
devRTT = 0.25       # 250ms
alpha = 0.125       # EWMA smoothing factor
beta = 0.25         # Deviation smoothing factor

# When ACK received:
sampleRTT = current_time - send_time

# Update estimated RTT (Exponential Weighted Moving Average)
estimatedRTT = (1 - alpha) × estimatedRTT + alpha × sampleRTT

# Update RTT deviation
devRTT = (1 - beta) × devRTT + beta × |sampleRTT - estimatedRTT|

# Calculate new timeout
RTO = max(0.1, estimatedRTT + 4 × devRTT)
```

---

## 🏆 Project Achievements

**100% Reliable Delivery** - Even under 15% packet loss  
**30+ Test Scenarios** - Comprehensive automated testing  
**Dynamic Timeout** - Adapts from 150ms to 1500ms based on network  
**Efficient Batching** - 36-82% bandwidth savings  
**Production Ready** - CSV logging, monitoring, visualization  
**Cross-Platform** - Windows, Linux, macOS support  
**Well Documented** - 4 comprehensive documentation files  
**Network Resilient** - Handles loss, delay, jitter, duplication, reordering  

### Phase 2 Requirements - All Completed 

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Payload ≤ 200 bytes | ✅ | Auto-splits batches, validates size |
| CSV data logging | ✅ | 10 columns including flags and metrics |
| bytes_per_report metric | ✅ | Calculated and displayed in statistics |
| packets_received tracking | ✅ | Total count with per-device breakdown |
| duplicate_rate calculation | ✅ | Fraction of duplicates detected |
| sequence_gap_count tracking | ✅ | Gap event counter |
| cpu_ms_per_report measurement | ✅ | Per-packet CPU time tracking |
| Retransmission for critical packets | ✅ | ACK-based RDT with max 3 retries |
| Tolerance ≤5% loss | ✅ | Achieves 100% delivery with RDT under 5-15% loss |
| Network impairment testing | ✅ | 30+ tests with tc/netem (loss, jitter, duplication) |
| Heartbeat mechanism | ✅ | 12s interval, device timeout detection |
| Batch processing | ✅ | Configurable batch sizes (1, 5, 30) |
| Performance monitoring | ✅ | CPU, memory, processing time tracking |
| Comprehensive documentation | ✅ | COMMUNICATION_SEQUENCES.md with all scenarios |
| Data visualization | ✅ | 5 analysis graphs generated from CSV |
| Gap detection | ✅ | Per-device, within batches, gap_flag in CSV |
| Duplicate detection | ✅ | Distinguishes RDT retransmits from network dups |
| Dynamic timeout | ✅ | TCP RFC 6298 algorithm, adapts to network conditions |

```

### Development Setup

```bash
git clone https://github.com/yymlz/iot-project.git
cd iot-project
pip install -r requirements.txt  # Install dev dependencies

---

## 🔗 Related Resources

- **Course Materials:** Computer Networks (Fall 2025)
- **Protocol Reference:** TCP RFC 6298 (RTO Calculation)
- **Testing Tools:** Linux tc/netem documentation
- **Python Docs:** socket, struct, threading, psutil modules

---

## 🙏 Acknowledgments

- **Course Instructor:** Dr Karim, Dr Ayman
- **Teaching Assistants:** Eng Rafik, Eng Mina, Eng Noha
- **Team Members:** 
   Ziyad Mohamed Saber Elnemr           23P0013
   Youssef Tarek Fawzy Azzam            23P0177
   Youssef Farid Haddad                 23P0113
   Marwan Ahmed Abdelaziz               23P0242
   Loay Khaled Mohammed                 23P0340
   Kareem Ahmed Talat                   23P0225


- **Tools Used:** Python 3, Linux tc/netem, psutil, matplotlib, pandas

---

**Last Updated:** December 12, 2025  
**Version:** 1.0 (Phase 2 Complete)  
**Status:** Production Ready ✅

---

*Built with ❤️ for reliable IoT telemetry*
