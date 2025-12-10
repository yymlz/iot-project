# Example Use Case Walkthrough - TinyTelemetry Protocol

## 7. Example Use Case Walkthrough

### Scenario Description

**Context:** Temperature/humidity sensor monitoring server room conditions

- **Device:** Sensor ID 1001
- **Location:** Server room (simulated on localhost)
- **Network:** 10% packet loss, 100ms latency (poor WiFi conditions)
- **Configuration:** Batch mode (batch_size=3), 30-second monitoring session

---

### Complete Session Trace

#### **Phase 1: Session Initialization (0-500ms)**

```
[Timestamp]       [Source]  [Event]                                    [Details]
[00:00:00.000]    Client    Socket created                             Port: 54321
[00:00:00.001]    Client    ACK socket created                         Port: 54322
[00:00:00.002]    Client    Threads started                            ACK listener, Retrans timer
[00:00:00.003]    Client    Initial timeout set                        RTO = 500ms
[00:00:00.100]    Client    → INIT (seq=0)                            10 bytes, device_id=1001
[00:00:00.150]    Network   Delay applied                              +50ms (jitter)
[00:00:00.200]    Server    ← INIT received                            From 127.0.0.1:54321
[00:00:00.201]    Server    Device 1001 registered                     last_seq=-1, state initialized
[00:00:00.202]    Server    → ACK (seq=0)                             10 bytes
[00:00:00.252]    Network   Delay applied                              +50ms (jitter)
[00:00:00.302]    Client    ← ACK (seq=0) received                    sampleRTT = 202ms
[00:00:00.303]    Client    RTT updated                                estimatedRTT = 487ms
[00:00:00.304]    Client    Timeout updated                            RTO = 487 + 4*103 = 899ms
[00:00:00.305]    Client    Session established                        Ready for data transmission
```

**Analysis:**

- Initial RTT sample: 202ms (includes network delay)
- Timeout adapted from 500ms → 899ms
- INIT/ACK exchange successful

---

#### **Phase 2: Normal Data Exchange (1-4 seconds)**

**Reading 1-3 (Buffered):**

```
[00:01:000]       Client    Reading 1 generated                        Temp=22.5°C, Hum=55.0%
[00:01:001]       Client    Added to batch buffer                      Buffer size: 1/3
[00:01:002]       Client    seq_num incremented                        seq_num = 1

[00:02:000]       Client    Reading 2 generated                        Temp=23.1°C, Hum=54.2%
[00:02:001]       Client    Added to batch buffer                      Buffer size: 2/3
[00:02:002]       Client    seq_num incremented                        seq_num = 2

[00:03:000]       Client    Reading 3 generated                        Temp=21.8°C, Hum=56.3%
[00:03:001]       Client    Added to batch buffer                      Buffer size: 3/3 → FULL
[00:03:002]       Client    Creating BATCH packet                      3 readings
[00:03:003]       Client    JSON payload created
                              Payload: [
                                {"seq_num":1,"temperature":22.5,"humidity":55.0},
                                {"seq_num":2,"temperature":23.1,"humidity":54.2},
                                {"seq_num":3,"temperature":21.8,"humidity":56.3}
                              ]
                              Compact JSON: 154 bytes (≤200 ✓)
[00:03:004]       Client    → BATCH (seq=3)                           164 bytes total
[00:03:005]       Client    Added to pending_packets                   timeout = 899ms
[00:03:055]       Network   Delay applied                              +50ms
[00:03:105]       Server    ← BATCH received                           seq=3, 3 readings
[00:03:106]       Server    Parsing reading 1                          seq=1
[00:03:107]       Server    CSV write                                  timestamp, device_id, seq_num=1, ...
[00:03:108]       Server    Parsing reading 2                          seq=2
[00:03:109]       Server    CSV write                                  seq_num=2
[00:03:110]       Server    Parsing reading 3                          seq=3
[00:03:111]       Server    CSV write                                  seq_num=3
[00:03:112]       Server    → ACK (seq=3)                             10 bytes
[00:03:162]       Network   Delay applied                              +50ms
[00:03:212]       Client    ← ACK (seq=3) received                    sampleRTT = 208ms
[00:03:213]       Client    RTT updated                                estimatedRTT = 461ms, devRTT=104ms
[00:03:214]       Client    Timeout updated                            RTO = 461 + 4*104 = 877ms
[00:03:215]       Client    Removed from pending                       pending_packets now empty
```

**CSV Entries Created:**

```csv
timestamp,device_id,seq_num,msg_type,temperature,humidity,duplicate_flag,gap_flag,packet_bytes
2025-12-10 00:03:07,1001,1,BATCH_DATA,22.5,55.0,0,0,164
2025-12-10 00:03:09,1001,2,BATCH_DATA,23.1,54.2,0,0,164
2025-12-10 00:03:11,1001,3,BATCH_DATA,21.8,56.3,0,0,164
```

---

#### **Phase 3: Packet Loss & Retransmission (4-7 seconds)**

**Readings 4-6 (Batch Lost):**

```
[00:04:000]       Client    Reading 4 generated                        Temp=22.0°C, Hum=58.1%
[00:05:000]       Client    Reading 5 generated                        Temp=23.5°C, Hum=52.7%
[00:06:000]       Client    Reading 6 generated                        Temp=21.2°C, Hum=59.4%
[00:06:001]       Client    Buffer full → BATCH
[00:06:002]       Client    → BATCH (seq=6)                           156 bytes
[00:06:003]       Client    Added to pending_packets                   timeout = 877ms
[00:06:053]       Network   ⚠ PACKET LOST (10% loss)                  Batch never reaches server
[00:06:880]       Client    ⏰ TIMEOUT! No ACK for seq=6
[00:06:881]       Client    Retry 1/3                                  retransmission_count++
[00:06:882]       Client    → BATCH (seq=6) [RETRANS]                156 bytes
[00:06:932]       Network   Delay applied                              +50ms
[00:06:982]       Server    ← BATCH received                           seq=6 (first time server sees it)
[00:06:983]       Server    Gap detected!                              Expected seq=4, got seq=6
[00:06:984]       Server    gap_flag = 1                               Missing readings 4, 5
[00:06:985]       Server    sequence_gap_count++                       Now = 1
[00:06:986]       Server    total_lost += 2                            Lost 2 readings
[00:06:987]       Server    CSV write reading 4                        (missing - not written)
[00:06:988]       Server    CSV write reading 5                        (missing - not written)
[00:06:989]       Server    CSV write reading 6                        gap_flag=1
[00:06:990]       Server    → ACK (seq=6)
[00:07:040]       Client    ← ACK (seq=6) received                    sampleRTT = 158ms (retrans time)
[00:07:041]       Client    RTT updated                                estimatedRTT = 423ms
[00:07:042]       Client    Removed from pending
```

**Statistics After This Phase:**

- Client: retransmission_count = 1
- Server: sequence_gap_count = 1, total_lost = 2
- Effective loss: 2/6 readings = 33% (batch amplification)

---

#### **Phase 4: ACK Loss (7-10 seconds)**

**Readings 7-9 (ACK Lost):**

```
[00:07:000]       Client    Readings 7-9 buffered
[00:09:001]       Client    → BATCH (seq=9)                           155 bytes
[00:09:002]       Client    Added to pending
[00:09:052]       Server    ← BATCH received                           No gap (seq continuous)
[00:09:053]       Server    CSV writes for seq=7,8,9                   duplicate_flag=0, gap_flag=0
[00:09:054]       Server    → ACK (seq=9)
[00:09:104]       Network   ⚠ ACK LOST (10% loss)                     Client never receives ACK
[00:09:878]       Client    ⏰ TIMEOUT! No ACK for seq=9
[00:09:879]       Client    Retry 1/3
[00:09:880]       Client    → BATCH (seq=9) [RETRANS]                Retransmitting
[00:09:930]       Server    ← BATCH received (seq=9)                  🔄 DUPLICATE!
[00:09:931]       Server    Duplicate detected                         seq=9 == last_seq=9
[00:09:932]       Server    duplicate_flag = 1
[00:09:933]       Server    total_duplicates++
[00:09:934]       Server    CSV writes for seq=7,8,9 AGAIN            duplicate_flag=1
[00:09:935]       Server    → ACK (seq=9)                             Send ACK anyway
[00:09:985]       Client    ← ACK (seq=9) received
[00:09:986]       Client    Removed from pending
```

**Analysis:**

- ACK lost → Client retransmits
- Server receives duplicate → Sets duplicate_flag=1
- CSV now has duplicate entries (by design, shows all received packets)

**CSV Entries:**

```csv
2025-12-10 00:09:05,1001,7,BATCH_DATA,22.3,57.2,0,0,155
2025-12-10 00:09:05,1001,8,BATCH_DATA,21.9,54.8,0,0,155
2025-12-10 00:09:05,1001,9,BATCH_DATA,23.2,56.1,0,0,155
2025-12-10 00:09:93,1001,7,BATCH_DATA,22.3,57.2,1,0,155  ← duplicate_flag=1
2025-12-10 00:09:93,1001,8,BATCH_DATA,21.9,54.8,1,0,155  ← duplicate_flag=1
2025-12-10 00:09:93,1001,9,BATCH_DATA,23.2,56.1,1,0,155  ← duplicate_flag=1
```

---

#### **Phase 5: Session Shutdown (30 seconds)**

```
[00:30:000]       Client    Duration elapsed (30s)
[00:30:001]       Client    Flushing batch buffer                      2 remaining readings
[00:30:002]       Client    → BATCH (seq=29-30)                       105 bytes (2 readings)
[00:30:052]       Server    ← BATCH received
[00:30:053]       Server    → ACK (seq=30)
[00:30:103]       Client    ← ACK (seq=30) received
[00:30:104]       Client    Waiting for final ACKs...                 2 second grace period
[00:32:104]       Client    Checking pending_packets                   Empty (all ACKed)
[00:32:105]       Client    Displaying RDT statistics
                              =====================================
                              [RDT STATISTICS]
                              =====================================
                              Total packets sent:       10
                              ACKs received:            10
                              Retransmissions:          2
                              Retransmission rate:      20.00%
                              Estimated RTT:            398.50 ms
                              RTT deviation:            89.23 ms
                              Current timeout (RTO):    755.42 ms
                              Timeout calculation:      RTO = estimatedRTT + 4 * devRTT
                                                        = 398.50 + 4 * 89.23
                                                        = 755.42 ms
                              Unacknowledged packets:   0 (100% delivery success!)
                              =====================================
[00:32:106]       Client    Closing sockets
[00:32:107]       Client    Session terminated

[00:32:200]       Server    Timeout check                              Device 1001 last_seen 2s ago
[01:02:200]       Server    Device 1001 marked OFFLINE                 No data for 30 seconds
```

---

### Network-Level Analysis (Wireshark pcap)

**Packet Capture Excerpt:** (See appendix for full pcap)

```
No.   Time        Source          Destination     Protocol  Length  Info
1     0.100000    127.0.0.1:54321 127.0.0.1:5000  UDP       10      INIT (seq=0)
2     0.202000    127.0.0.1:5000  127.0.0.1:54322 UDP       10      ACK (seq=0)
3     3.004000    127.0.0.1:54321 127.0.0.1:5000  UDP       164     BATCH (seq=3)
4     3.112000    127.0.0.1:5000  127.0.0.1:54322 UDP       10      ACK (seq=3)
5     6.002000    127.0.0.1:54321 127.0.0.1:5000  UDP       156     BATCH (seq=6) [LOST]
6     6.882000    127.0.0.1:54321 127.0.0.1:5000  UDP       156     BATCH (seq=6) [RETRANS]
7     6.990000    127.0.0.1:5000  127.0.0.1:54322 UDP       10      ACK (seq=6)
8     9.001000    127.0.0.1:54321 127.0.0.1:5000  UDP       155     BATCH (seq=9)
9     9.054000    127.0.0.1:5000  127.0.0.1:54322 UDP       10      ACK (seq=9) [LOST]
10    9.880000    127.0.0.1:54321 127.0.0.1:5000  UDP       155     BATCH (seq=9) [RETRANS]
11    9.935000    127.0.0.1:5000  127.0.0.1:54322 UDP       10      ACK (seq=9)
...
```

**Wireshark Filters Used:**

```
# All TinyTelemetry traffic
udp.port == 5000

# Only BATCH packets
udp.port == 5000 && udp.length > 100

# Only ACKs
udp.port == 5000 && udp.length == 10

# Retransmissions (identify by timing)
udp.port == 5000 && frame.time_delta > 0.5
```

---

### Message Format Examples

**INIT Message (Hex Dump):**

```
Offset  Hex                                          ASCII
0000    01 00 03 E9 00 00 00 00 00 00               ..ù.......

Fields:
  Byte 0:    01           = MSG_INIT
  Bytes 1-2: 00 03        = Reserved (0)
  Bytes 3-4: E9 03        = Device ID 1001 (little-endian)
  Bytes 5-6: 00 00        = Sequence number 0
  Bytes 7-10: 00 00 00 00 = Timestamp 0 (INIT doesn't need timestamp)
  Payload: (empty)
```

**BATCH Message (Hex Dump):**

```
Offset  Hex                                          ASCII
0000    03 00 03 E9 00 03 5B 7B 22 73 65 71 5F 6E   ..ù..[{"seq_n
0010    75 6D 22 3A 31 2C 22 74 65 6D 70 65 72 61   um":1,"tempera
0020    74 75 72 65 22 3A 32 32 2E 35 2C 22 68 75   ture":22.5,"hu
0030    6D 69 64 69 74 79 22 3A 35 35 2E 30 7D ...  midity":55.0}...

Fields:
  Byte 0:    03              = MSG_BATCH (3)
  Bytes 1-2: 00 00           = Reserved
  Bytes 3-4: E9 03           = Device ID 1001
  Bytes 5-6: 03 00           = Sequence number 3
  Bytes 7-10: (timestamp)
  Payload: [{"seq_num":1,"temperature":22.5,"humidity":55.0}...]
```

**ACK Message (Hex Dump):**

```
Offset  Hex                                          ASCII
0000    04 00 03 E9 00 03                            ..ù..

Fields:
  Byte 0:    04        = MSG_ACK
  Bytes 1-2: 00 00     = Reserved
  Bytes 3-4: E9 03     = Device ID 1001
  Bytes 5-6: 03 00     = Acknowledging sequence number 3
  Payload: (empty)
```

---

### Final Statistics Summary

**Client Metrics:**

```
Total packets sent:       10 BATCH packets (30 readings)
ACKs received:            10
Retransmissions:          2 (seq=6, seq=9)
Retransmission rate:      20% (higher than network loss due to ACK loss)
Estimated RTT:            398ms (adapted from initial 500ms)
Final timeout:            755ms (dynamically calculated)
Unacknowledged:           0 (100% eventual delivery)
```

**Server Metrics:**

```
Packets received:         12 (10 unique + 2 duplicates)
Total readings:           30 original + 6 duplicates = 36 in CSV
Gaps detected:            1 gap (readings 4-5 lost)
Duplicates detected:      2 duplicate packets (seq=9 received twice)
Sequence gap count:       1
Total lost readings:      2 (6.67% of 30)
Duplicate rate:           16.67% (2/12 packets)
Effective delivery:       93.33% (28/30 original readings received)
```

**Network Metrics:**

```
Actual packet loss:       10% (1 DATA + 1 ACK lost)
Retransmissions sent:     2
Recovery success:         100% (all retransmissions succeeded)
Protocol overhead:        10 ACKs + 2 retrans = 12 extra packets for 10 data packets = 120%
```

---

### Key Observations

1. **RDT Effectiveness:**

   - Despite 10% network loss, achieved 93.33% reading delivery
   - Retransmissions successfully recovered lost batch (seq=6)
   - ACK loss handled gracefully (duplicate detection)

2. **Timeout Adaptation:**

   - Started at 500ms (initial estimate)
   - Adapted to 755ms based on network conditions
   - Formula: RTO = 398ms + 4 × 89ms = 755ms
   - Prevented premature timeouts

3. **Batch Mode Impact:**

   - Batch loss amplified: 1 lost packet = 3 lost readings
   - But: Reduced total packets by 3x (efficiency)
   - Trade-off: Efficiency vs. loss amplification

4. **Gap Detection:**

   - Server correctly identified missing readings 4-5
   - Set gap_flag=1 in CSV
   - Logged to statistics (sequence_gap_count=1)

5. **Duplicate Handling:**
   - ACK loss caused client retransmission
   - Server detected duplicate (seq=9 == last_seq)
   - Set duplicate_flag=1 in CSV
   - Both copies logged (shows full packet history)

---

## Appendix: Full pcap Analysis

_See separate file: `logs/example_session_capture.pcap`_

**How to view:**

```bash
# Command line
tcpdump -r logs/example_session_capture.pcap -v

# Wireshark GUI
wireshark logs/example_session_capture.pcap

# Filter for retransmissions
tshark -r logs/example_session_capture.pcap -Y "udp.length > 150" -T fields -e frame.number -e frame.time_delta -e udp.length
```

**Expected pcap statistics:**

- Total packets: 22 (10 DATA + 10 ACK + 2 retrans)
- Average packet size: ~87 bytes
- Session duration: 30 seconds
- Packets per second: 0.73 pps (low rate - 1s interval)

---

## Conclusion

This walkthrough demonstrates:
✅ Complete session lifecycle (INIT → DATA → SHUTDOWN)
✅ RDT retransmission mechanism in action
✅ Timeout adaptation (500ms → 755ms)
✅ Loss recovery (seq=6 retransmitted successfully)
✅ Duplicate detection (seq=9 flagged)
✅ Gap detection (readings 4-5 identified as lost)
✅ CSV logging with flags (duplicate_flag, gap_flag)
✅ Final statistics showing 93.33% effective delivery despite 10% network loss
