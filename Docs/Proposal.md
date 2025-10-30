# Project Proposal: TinyTelemetry Protocol v1

**Team Name:** [Your Team Name]
**Team Members:** [Names and IDs]
**Date:** October 2025
**Project:** IoT Telemetry Protocol (Sensor Reporting)

---

## 1. Project Scenario

We have selected **Project 1: IoT Telemetry Protocol (Sensor Reporting)** from the available options. This project involves designing and implementing a custom lightweight telemetry protocol for constrained IoT sensors that periodically send small readings to a central collector over UDP.

---

## 2. Motivation

### 2.1 Problem Statement

Modern IoT deployments face a critical challenge: **resource-constrained sensors must transmit telemetry data efficiently over unreliable networks while minimizing power consumption and bandwidth usage.** Existing protocols introduce unnecessary overhead:

- **MQTT:** Requires TCP connection establishment, adds significant header overhead, and maintains session state
- **CoAP:** While lightweight, still carries REST-style overhead and implements complex retransmission logic
- **HTTP/REST:** Completely unsuitable for battery-powered sensors due to connection overhead

### 2.2 Our Approach

We propose **TinyTelemetry**, a purpose-built protocol that:

1. **Minimizes overhead:** 10-byte fixed header vs. MQTT's variable headers + topic strings
2. **Embraces UDP:** No connection overhead, lower latency, acceptable for loss-tolerant telemetry
3. **Fire-and-forget design:** Sensors transmit without waiting for acknowledgments, saving power
4. **Simple duplicate detection:** Server-side sequence tracking without client complexity

### 2.3 Target Use Case

**Environmental monitoring network:**
- 100+ battery-powered temperature/humidity sensors
- Wireless mesh network with 2-5% typical packet loss
- Reporting intervals: 1-30 seconds
- 5+ year battery life requirement
- Central collector aggregates data for analysis

---

## 3. Proposed Protocol Approach

### 3.1 Core Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Simplicity** | Fixed header format, minimal state machine |
| **Efficiency** | 10-byte header, binary encoding, no acknowledgments |
| **Loss tolerance** | Accept 0-5% loss without retransmission |
| **Scalability** | Stateless transmission, collector handles 1000+ devices |

### 3.2 Protocol Header (10 bytes)

```
Field           | Bits | Purpose
----------------|------|------------------------------------
Version         | 4    | Protocol version (currently 1)
Message Type    | 4    | INIT, DATA, HEARTBEAT
Device ID       | 16   | Unique sensor identifier (0-65535)
Sequence Number | 16   | Monotonic counter for duplicate/gap detection
Timestamp       | 32   | Unix epoch seconds (UTC)
Flags           | 8    | Reserved for batching, priority, compression
```

**Total:** 10 bytes (vs. MQTT-SN minimum 5 bytes + topic overhead)

### 3.3 Message Types

**Phase 1 Implementation:**

1. **INIT (0x0):** Sensor startup handshake
   - Purpose: Signal collector that device is online
   - Payload: Empty or device metadata
   - Frequency: Once per sensor boot

2. **DATA (0x1):** Telemetry reading
   - Purpose: Deliver sensor measurements
   - Payload: JSON (Phase 1) or binary-packed (Phase 2+)
   - Frequency: Every 1-30 seconds based on application

**Phase 2 Enhancement:**

3. **HEARTBEAT (0x2):** Keep-alive when no data available
   - Purpose: Prove liveness without wasting bandwidth on duplicate data
   - Payload: Empty
   - Frequency: Only when readings unchanged for >5 minutes

### 3.4 Communication Flow

```
Sensor                               Collector
  |                                      |
  |---- INIT (seq=0) ------------------>|  Initialize device state
  |                                      |  (Store device_id, seq=0)
  |                                      |
  |---- DATA (seq=1, temp=23.5) ------->|  Log reading, expect seq=1 ✓
  |                                      |
  |---- DATA (seq=2, temp=23.8) ------->|  Log reading, expect seq=2 ✓
  |                                      |
  |  X  DATA (seq=3) lost in network    |
  |                                      |
  |---- DATA (seq=4, temp=24.1) ------->|  Gap detected! Missing seq=3
  |                                      |  (Log gap but no recovery)
```

### 3.5 Server Responsibilities

The collector (server) performs:

1. **Per-device state tracking:**
   - Last sequence number received
   - Last timestamp received
   - Total packets received

2. **Duplicate suppression:**
   - Ignore packets with seq ≤ last_seq for same device
   - Useful if network causes duplicates

3. **Gap detection:**
   - Alert when seq_new > last_seq + 1
   - Log missing sequence numbers for analysis

4. **Logging:**
   - CSV output: `device_id, seq, timestamp, arrival_time, duplicate_flag, gap_flag`
   - Enable post-experiment analysis

### 3.6 Why No Retransmission?

Environmental telemetry tolerates occasional loss because:
- Readings are **temporal samples** (missing one of 60/hour is acceptable)
- **Redundancy:** Next reading arrives within seconds
- **Trends matter:** One lost packet doesn't invalidate trend analysis
- **Power savings:** Retransmission requires listening, draining battery

If critical data (e.g., alarm events) needs reliability, we reserve Flags field for future "priority" mode with optional acknowledgments.

---

## 4. Implementation Plan (Phase 1)

### 4.1 Deliverables

| Item | Description | Status |
|------|-------------|--------|
| Mini-RFC (Sections 1-3) | Protocol spec: intro, architecture, message formats | In progress |
| Prototype | Working server + client over UDP | In progress |
| Baseline test | Automated script: 1s interval, 60s, ≥99% delivery | Planned |
| Demo video | 5-min demonstration of INIT/DATA exchange | Planned |

### 4.2 Technology Stack

- **Language:** Python 3.7+ (cross-platform, rapid prototyping)
- **Networking:** Standard library `socket` module (UDP)
- **Encoding:** `struct` module for binary packing
- **Payload:** JSON (Phase 1), binary (Phase 2)

### 4.3 Testing Approach

**Phase 1 (Baseline):**
- Run client for 60 seconds at 1-second intervals
- Verify ≥99% packet delivery on localhost (no impairment)
- Validate sequence numbers are monotonic and ordered

**Phase 2 (Network Impairments):**
- Use Linux `netem` to simulate:
  - 5% packet loss
  - 100ms ±10ms delay/jitter
- Measure duplicate rate, gap detection accuracy
- Collect pcap traces for analysis

---

## 5. Expected Outcomes

### 5.1 Phase 1 Success Criteria

- [x] Working INIT and DATA message exchange
- [x] Compact 10-byte binary header
- [x] Server logs received packets with metadata
- [x] Baseline test achieves ≥99% delivery (local)
- [x] Code runs on macOS and Linux without modification
- [x] Demo video shows protocol in action

### 5.2 Protocol Efficiency Analysis

**Example DATA packet:**
- Header: 10 bytes
- Payload (JSON): `{"temperature":23.5,"humidity":58.2}` = 37 bytes
- **Total: 47 bytes**

**Comparison with MQTT:**
- MQTT fixed header: 2 bytes
- Topic: `sensor/1001/data` = 16 bytes
- Payload: Same 37 bytes
- **Total: 55 bytes**

**Savings: 15% reduction** (more significant with binary payload in Phase 2)

### 5.3 Future Enhancements (Phase 2-3)

1. **Batching mode:** Group up to N readings per packet
   - Flags field: bits 0-2 indicate count (1-8 readings)
   - Reduces packets/sec by 4-8x for low-update-rate sensors

2. **Binary payload encoding:**
   - Temperature: 16-bit signed int (scaled by 100) = 2 bytes
   - Humidity: 16-bit unsigned int (scaled by 100) = 2 bytes
   - **Total payload: 4 bytes vs. 37 bytes JSON (9x reduction)**

3. **Timestamp compression:**
   - Use 16-bit delta from previous timestamp instead of full 32-bit epoch
   - Saves 2 bytes when readings are frequent

---

## 6. Challenges and Mitigation

| Challenge | Risk | Mitigation |
|-----------|------|------------|
| Packet loss exceeds 5% | Protocol doesn't handle recovery | Document acceptable loss range; Phase 2 explores heartbeat/batching |
| Clock drift on sensors | Timestamps become unreliable | Document ±5 min tolerance; suggest NTP sync for production |
| Sequence number wrap-around | After 65535 packets, seq resets to 0 | Server detects wrap (seq_new < last_seq - threshold); reset state |
| Binary encoding bugs | Cross-platform compatibility issues | Use Python `struct` with explicit byte order (`!`); test on Mac/Linux |

---

## 7. Conclusion

TinyTelemetry addresses the need for an ultra-lightweight, loss-tolerant telemetry protocol optimized for resource-constrained IoT sensors. By embracing UDP's simplicity and designing a compact fixed header, we achieve:

- **Minimal overhead:** 10-byte header enables efficient use of limited bandwidth
- **Low complexity:** Simple state machine reduces implementation cost on sensors
- **Power efficiency:** Fire-and-forget design minimizes radio-on time
- **Practical loss tolerance:** Acceptable for temporal sampling applications

**Phase 1 will deliver a working prototype demonstrating INIT and DATA exchanges**, forming the foundation for enhanced features (batching, binary payloads, network impairment testing) in subsequent phases.

---

**Project Team Signatures:**

[Team Member 1 - Name & ID]
[Team Member 2 - Name & ID]
[Team Member 3 - Name & ID]
[Team Member 4 - Name & ID]

---

**Proposal Submission Date:** [Date]
**Target Phase 1 Completion:** Week 7
