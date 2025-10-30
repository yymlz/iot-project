# Mini-RFC: TinyTelemetry Protocol v1
## Lightweight Telemetry Protocol for IoT Sensor Networks

**Protocol Name:** TinyTelemetry
**Version:** 1.0
**Authors:** [Your Team Names]
**Date:** October 2025
**Status:** Phase 1 Draft (Sections 1-3)

---

## 1. Introduction

### 1.1 Purpose and Scope

TinyTelemetry is a custom application-layer protocol designed for constrained IoT sensors to efficiently report periodic telemetry data (e.g., temperature, humidity, voltage) to a central collector over unreliable networks. The protocol operates over UDP and prioritizes compactness, simplicity, and loss tolerance over guaranteed delivery.

### 1.2 Motivation

Existing protocols like MQTT or CoAP introduce overhead unsuitable for resource-constrained devices with limited bandwidth and power. TinyTelemetry addresses these constraints by:

- Using a **compact binary header** (10 bytes) instead of text-based formats
- Operating **directly over UDP** without connection establishment overhead
- Supporting **loss-tolerant telemetry** where occasional packet loss is acceptable
- Enabling **efficient batching** of multiple readings (future enhancement)

### 1.3 Use Case

**Scenario:** Environmental monitoring network with 100+ battery-powered sensors reporting temperature and humidity every 1-30 seconds to a central collector over a lossy wireless network.

**Requirements:**
- Minimize header overhead to conserve bandwidth and power
- Tolerate up to 5% packet loss without retransmission
- Support device identification and sequence tracking
- Enable simple duplicate detection and gap analysis

### 1.4 Assumptions and Constraints

| Parameter | Value/Constraint |
|-----------|------------------|
| Transport layer | UDP only |
| Maximum packet size | 200 bytes (header + payload) |
| Header size | 10 bytes (fixed) |
| Maximum payload | 190 bytes |
| Supported loss rate | 0-5% (without recovery) |
| Time synchronization | Sensors have approximate UTC time (±5 min acceptable) |
| Device ID space | 0-65535 (16-bit unsigned) |
| Sequence number space | 0-65535 (16-bit unsigned, wraps around) |

---

## 2. Protocol Architecture

### 2.1 Entities

The protocol defines two primary entities:

1. **Sensor (Client)**
   - Battery-powered or resource-constrained device
   - Periodically measures environmental data
   - Sends telemetry messages to collector
   - Does not expect acknowledgments (fire-and-forget)

2. **Collector (Server)**
   - Centralized receiver with stable network connection
   - Listens on a well-known UDP port (default: 5000)
   - Maintains per-device state (last sequence number, timestamp)
   - Performs duplicate suppression and gap detection
   - Logs received data for analysis

### 2.2 Communication Model

TinyTelemetry uses a **sessionless, unidirectional push model**:

```
Sensor                          Collector
  |                                |
  |------ INIT (seq=0) ----------->|  (Initial handshake)
  |                                |
  |------ DATA (seq=1) ----------->|  (Telemetry reading)
  |                                |
  |------ DATA (seq=2) ----------->|  (Telemetry reading)
  |                                |
  |         (1-30 seconds)         |
  |                                |
  |------ DATA (seq=3) ----------->|  (Telemetry reading)
  |                                |
```

**No acknowledgments or responses** are sent by the collector. Sensors transmit at fixed intervals regardless of reception.

### 2.3 Finite State Machine (Sensor)

```
┌─────────┐
│  IDLE   │
└────┬────┘
     │ Start sensor
     ▼
┌─────────┐
│  INIT   │──── Send INIT message
└────┬────┘
     │ Timer started
     ▼
┌─────────┐
│ ACTIVE  │◄─── Send DATA periodically (interval: 1-30s)
└────┬────┘
     │ Stop/shutdown
     ▼
┌─────────┐
│ STOPPED │
└─────────┘
```

### 2.4 Finite State Machine (Collector)

```
┌─────────┐
│  IDLE   │
└────┬────┘
     │ Bind UDP socket
     ▼
┌──────────┐
│ LISTENING│◄─── Receive packets, process headers
└──────────┘
     │ Parse message
     ├─── INIT: Initialize device state
     ├─── DATA: Log reading, check duplicates/gaps
     └─── Unknown: Log warning
```

The collector remains in the LISTENING state indefinitely, processing each incoming packet independently.

---

## 3. Message Formats

### 3.1 Header Structure

TinyTelemetry uses a **fixed 10-byte binary header** for all message types:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Ver |MsgType|       Device ID       |      Sequence Number      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          Timestamp                            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     Flags     |
+-+-+-+-+-+-+-+-+
```

### 3.2 Header Field Definitions

| Field | Size (bits) | Offset (bytes) | Description |
|-------|-------------|----------------|-------------|
| **Version** | 4 | 0 (upper nibble) | Protocol version (currently 1) |
| **MsgType** | 4 | 0 (lower nibble) | Message type code (see 3.3) |
| **Device ID** | 16 | 1-2 | Unique device identifier (0-65535) |
| **Sequence Number** | 16 | 3-4 | Monotonically increasing packet counter (wraps at 65535) |
| **Timestamp** | 32 | 5-8 | Unix epoch time in seconds (UTC) |
| **Flags** | 8 | 9 | Reserved for future use (set to 0 in v1) |

**Total header size:** 10 bytes

### 3.3 Message Types

| Code | Name | Description |
|------|------|-------------|
| 0x0 | INIT | Initial handshake; sent once when sensor starts |
| 0x1 | DATA | Sensor reading with payload |
| 0x2 | HEARTBEAT | Keep-alive message (reserved for Phase 2) |
| 0x3-0xF | Reserved | For future protocol extensions |

### 3.4 Header Encoding

The header is encoded using **network byte order (big-endian)** to ensure cross-platform compatibility.

**Python `struct` format string:**
```python
'!BHHIB'
```

Where:
- `!` = Network byte order (big-endian)
- `B` = Unsigned char (1 byte) – Version (4 bits) + MsgType (4 bits)
- `H` = Unsigned short (2 bytes) – Device ID
- `H` = Unsigned short (2 bytes) – Sequence Number
- `I` = Unsigned int (4 bytes) – Timestamp
- `B` = Unsigned char (1 byte) – Flags

**Example encoding (Python):**
```python
import struct

version = 1
msg_type = 1  # DATA
device_id = 1001
seq_num = 42
timestamp = 1698765432
flags = 0

# Combine version and msg_type into one byte
version_and_type = (version << 4) | (msg_type & 0x0F)

header = struct.pack('!BHHIB',
                     version_and_type,  # 0x11
                     device_id,         # 1001
                     seq_num,           # 42
                     timestamp,         # 1698765432
                     flags)             # 0

# Result: 10-byte binary header
```

### 3.5 Sample Messages

#### 3.5.1 INIT Message

**Header (hex representation):**
```
10 03 E9 00 00 65 4A 2F 38 00
```

**Interpretation:**
- `0x10` → Version=1, MsgType=0 (INIT)
- `0x03E9` → Device ID = 1001
- `0x0000` → Sequence Number = 0
- `0x654A2F38` → Timestamp = 1698765432 (2023-10-31 12:30:32 UTC)
- `0x00` → Flags = 0

**Total size:** 10 bytes (no payload for INIT)

#### 3.5.2 DATA Message

**Header (hex representation):**
```
11 03 E9 00 01 65 4A 2F 39 00
```

**Interpretation:**
- `0x11` → Version=1, MsgType=1 (DATA)
- `0x03E9` → Device ID = 1001
- `0x0001` → Sequence Number = 1
- `0x654A2F39` → Timestamp = 1698765433
- `0x00` → Flags = 0

**Payload (JSON, 37 bytes):**
```json
{"temperature": 23.5, "humidity": 58.2}
```

**Total packet size:** 10 (header) + 37 (payload) = **47 bytes**

### 3.6 Payload Format

**Phase 1:** Payload is UTF-8 encoded JSON for simplicity and debugging:
```json
{
  "temperature": <float>,
  "humidity": <float>
}
```

**Future (Phase 2):** Binary-packed payload for efficiency:
```
temperature (16-bit signed int, scaled by 100)
humidity    (16-bit unsigned int, scaled by 100)
Total: 4 bytes vs 37 bytes JSON
```

### 3.7 Byte Offsets Summary

For packet parsing:

| Byte Range | Field | Type |
|------------|-------|------|
| 0 | Version + MsgType | uint8 |
| 1-2 | Device ID | uint16 (big-endian) |
| 3-4 | Sequence Number | uint16 (big-endian) |
| 5-8 | Timestamp | uint32 (big-endian) |
| 9 | Flags | uint8 |
| 10+ | Payload | Variable (max 190 bytes) |

---

## Sections 4-7: Reserved for Phase 2

The following sections will be completed in Phase 2:
- **Section 4:** Communication Procedures
- **Section 5:** Reliability & Performance Features
- **Section 6:** Experimental Evaluation Plan
- **Section 7:** Example Use Case Walkthrough

---

## Appendix A: Design Rationale

### A.1 Why 10-byte Header?

We chose a 10-byte fixed header to balance:
- **Compactness:** Minimal overhead for small payloads
- **Functionality:** Essential fields (device ID, sequence, timestamp)
- **Alignment:** 10 bytes avoid padding issues on most platforms

### A.2 Why UDP?

UDP was selected because:
- No connection setup/teardown overhead
- Lower latency for time-sensitive telemetry
- Acceptable for loss-tolerant sensor data
- Simpler implementation on constrained devices

### A.3 Differences from MQTT-SN

| Feature | MQTT-SN | TinyTelemetry |
|---------|---------|---------------|
| Transport | UDP (with optional reliability) | UDP (no reliability) |
| Header size | Variable (min 5 bytes + topic) | Fixed 10 bytes |
| QoS levels | 3 levels (0, 1, 2) | None (fire-and-forget) |
| Publish/Subscribe | Yes | No (direct push) |
| Complexity | Moderate | Minimal |

TinyTelemetry sacrifices features for simplicity and minimal overhead.

---

## References

1. RFC 768 – User Datagram Protocol (UDP)
2. RFC 8259 – The JavaScript Object Notation (JSON) Data Interchange Format
3. MQTT-SN Specification v1.2 (for comparison)

---

**End of Phase 1 Mini-RFC Draft**
**Sections 4-7 will be completed in Phase 2**
