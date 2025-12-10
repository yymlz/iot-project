# Communication Procedures - TinyTelemetry Protocol

This document describes the complete communication flow for the TinyTelemetry IoT protocol.

## 4. Communication Procedures

### 4.1 Session Start

**Step-by-step sequence:**

1. **Client Initialization**

   - Client creates UDP socket
   - Binds to ephemeral port
   - Sets sequence number to 0

2. **INIT Message Exchange**

   ```
   Client → Server: INIT (seq=0, device_id=1001)
   Server → Client: ACK (seq=0)
   Server: Logs new device, initializes state
   ```

3. **Client State Setup**
   - Starts ACK listener thread (receives on separate socket)
   - Starts retransmission timer thread
   - Initializes RTT estimation (500ms initial value)

**Example trace:**

```
[00:00:00.000] Client: Socket created (port 54321)
[00:00:00.100] Client: Sent INIT (seq=0, device_id=1001)
[00:00:00.150] Server: Received INIT from 127.0.0.1:54321
[00:00:00.151] Server: Sent ACK (seq=0)
[00:00:00.152] Client: Received ACK (seq=0), RTT=52ms
[00:00:00.153] Client: Session established
```

---

### 4.2 Normal Data Exchange

**Without Batch Mode (batch_size=0):**

1. **Client generates sensor reading**

   - Temperature, humidity values
   - Assigns sequence number (increments)

2. **DATA Message Transmission**

   ```
   Client → Server: DATA (seq=N, temp=22.5, hum=55.0)
   Client: Adds to pending_packets dictionary
   Client: Starts timeout timer (RTO = estimatedRTT + 4*devRTT)
   ```

3. **Server Processing**

   ```
   Server: Receives DATA packet
   Server: Validates sequence number
   Server: Checks for gaps/duplicates
   Server: Logs to CSV
   Server → Client: ACK (seq=N)
   ```

4. **Client ACK Handling**
   ```
   Client: Receives ACK (seq=N)
   Client: Calculates sampleRTT = current_time - send_time
   Client: Updates estimatedRTT = 0.875 * estimatedRTT + 0.125 * sampleRTT
   Client: Updates devRTT = 0.75 * devRTT + 0.25 * |sampleRTT - estimatedRTT|
   Client: Updates timeout = estimatedRTT + 4 * devRTT
   Client: Removes seq=N from pending_packets
   ```

**Example trace (single packet):**

```
[00:00:01.000] Client: Generated reading (temp=22.5, hum=55.0)
[00:00:01.001] Client: Sent DATA (seq=1, 51 bytes)
[00:00:01.002] Client: Added to pending (timeout=520ms)
[00:00:01.055] Server: Received DATA (seq=1)
[00:00:01.056] Server: Logged to CSV
[00:00:01.057] Server: Sent ACK (seq=1)
[00:00:01.058] Client: Received ACK (seq=1)
[00:00:01.059] Client: sampleRTT=58ms
[00:00:01.060] Client: Updated estimatedRTT=495ms → 489ms
[00:00:01.061] Client: Updated timeout=520ms → 515ms
[00:00:01.062] Client: Removed seq=1 from pending
```

---

**With Batch Mode (batch_size=3):**

1. **Client buffers readings**

   ```
   Client: Reading 1 → buffer (no send)
   Client: Reading 2 → buffer (no send)
   Client: Reading 3 → buffer → BATCH FULL
   ```

2. **BATCH Message Transmission**

   ```
   Client: Creates JSON array: [
       {seq_num: 1, temperature: 22.5, humidity: 55.0},
       {seq_num: 2, temperature: 23.1, humidity: 54.2},
       {seq_num: 3, temperature: 21.8, humidity: 56.3}
   ]
   Client: Compresses JSON (no spaces)
   Client: Checks payload ≤ 200 bytes
   Client → Server: BATCH (seq=3, payload=154 bytes)
   Client: Adds to pending_packets
   ```

3. **Server BATCH Processing**
   ```
   Server: Receives BATCH packet
   Server: Parses JSON array
   Server: Checks for gaps between readings
   Server: Logs each reading to CSV individually
   Server → Client: ACK (seq=3)
   ```

**Example trace (batch):**

```
[00:00:02.000] Client: Reading 1 buffered
[00:00:03.000] Client: Reading 2 buffered
[00:00:04.000] Client: Reading 3 buffered → BATCH FULL
[00:00:04.001] Client: Sent BATCH (seq=1-3, 154 bytes)
[00:00:04.055] Server: Received BATCH (3 readings)
[00:00:04.056] Server: Logged seq=1 to CSV
[00:00:04.057] Server: Logged seq=2 to CSV
[00:00:04.058] Server: Logged seq=3 to CSV
[00:00:04.059] Server: Sent ACK (seq=3)
[00:00:04.060] Client: Received ACK, removed from pending
```

---

### 4.3 Error Recovery

**Scenario 1: Packet Loss (No ACK Received)**

```
[00:00:05.000] Client: Sent DATA (seq=4)
[00:00:05.001] Client: Added to pending, timeout=515ms
[00:00:05.100] Network: Packet LOST (simulated 10% loss)
[00:00:05.515] Client: Timeout! No ACK for seq=4
[00:00:05.516] Client: Retry 1/3 - Resending DATA (seq=4)
[00:00:05.570] Server: Received DATA (seq=4)
[00:00:05.571] Server: Sent ACK (seq=4)
[00:00:05.572] Client: Received ACK, recovery successful
```

**Scenario 2: ACK Lost**

```
[00:00:06.000] Client: Sent DATA (seq=5)
[00:00:06.050] Server: Received DATA (seq=5)
[00:00:06.051] Server: Sent ACK (seq=5)
[00:00:06.052] Network: ACK LOST
[00:00:06.515] Client: Timeout! Retry 1/3
[00:00:06.516] Client: Resending DATA (seq=5)
[00:00:06.570] Server: Received DATA (seq=5) - DUPLICATE!
[00:00:06.571] Server: Sets duplicate_flag=1
[00:00:06.572] Server: Sent ACK (seq=5) anyway
[00:00:06.573] Client: Received ACK, removed from pending
```

**Scenario 3: Multiple Retries Fail**

```
[00:00:07.000] Client: Sent DATA (seq=6)
[00:00:07.515] Client: Timeout! Retry 1/3
[00:00:07.516] Client: Resending...
[00:00:08.031] Client: Timeout! Retry 2/3
[00:00:08.032] Client: Resending...
[00:00:08.547] Client: Timeout! Retry 3/3
[00:00:08.548] Client: Resending...
[00:00:09.063] Client: Timeout! Max retries exceeded
[00:00:09.064] Client: Giving up on seq=6 (packet lost)
[00:00:09.065] Client: Removed from pending, continues with seq=7
```

**Scenario 4: Sequence Gap Detection**

```
[00:00:10.000] Server: Received DATA (seq=7)
[00:00:10.001] Server: Expected seq=7, but last was seq=5
[00:00:10.002] Server: Gap detected! Missing seq=6
[00:00:10.003] Server: Sets gap_flag=1 for seq=7
[00:00:10.004] Server: sequence_gap_count += 1
[00:00:10.005] Server: total_lost += 1
[00:00:10.006] Server: Logs to CSV with gap_flag=1
```

---

### 4.4 Heartbeat Mechanism

**Purpose:** Keep-alive to detect offline devices

**Flow:**

```
[Every 10 seconds with no DATA transmission]
Client → Server: HEARTBEAT (seq=0, no payload)
Server: Updates last_seen timestamp
Server: Does NOT send ACK (heartbeat is unreliable by design)
```

**Timeout Detection:**

```
[00:05:00.000] Server: Last packet from device 1001 at 00:04:30
[00:05:00.001] Server: Current time - last_seen = 30 seconds
[00:05:00.002] Server: Threshold = 30 seconds
[00:05:00.003] Server: Marks device 1001 OFFLINE
[00:05:00.004] Server: Logs: "[TIMEOUT] Device 1001 offline"
```

---

### 4.5 Session Shutdown

**Normal Shutdown (Duration Expired):**

```
[00:01:00.000] Client: Duration (60s) elapsed
[00:01:00.001] Client: Flushing batch buffer (2 readings)
[00:01:00.002] Client: Sent final BATCH (seq=58-59)
[00:01:00.055] Server: Received final BATCH
[00:01:00.056] Server: Sent ACK
[00:01:00.057] Client: Received ACK
[00:01:00.058] Client: Waiting 2s for any remaining ACKs...
[00:01:02.058] Client: Checking pending_packets
[00:01:02.059] Client: All packets acknowledged (pending=0)
[00:01:02.060] Client: Displays RDT statistics
[00:01:02.061] Client: Closes sockets
[00:01:02.062] Client: Session terminated
```

**User Interrupt (Ctrl+C):**

```
[00:00:30.000] User: Presses Ctrl+C
[00:00:30.001] Client: Catches KeyboardInterrupt
[00:00:30.002] Client: Flushes batch buffer if not empty
[00:00:30.003] Client: Waits 2s for pending ACKs
[00:00:30.004] Client: Displays partial statistics
[00:00:30.005] Client: Closes sockets
[00:00:30.006] Client: Exits gracefully
```

**Server Shutdown:**

```
[00:10:00.000] User: Presses Ctrl+C on server
[00:10:00.001] Server: Processes remaining buffered packets
[00:10:00.002] Server: Displays final statistics
[00:10:00.003] Server: Closes CSV file
[00:10:00.004] Server: Closes socket
[00:10:00.005] Server: Exits
```

---

## Summary Table

| Phase         | Client            | Server           | Network Messages     |
| ------------- | ----------------- | ---------------- | -------------------- |
| **Start**     | Send INIT         | Log device       | INIT → ACK           |
| **Normal**    | Send DATA/BATCH   | Process + ACK    | DATA → ACK           |
| **Error**     | Timeout → Retry   | Detect gap/dup   | Retransmit → ACK     |
| **Heartbeat** | Send every 10s    | Update last_seen | HEARTBEAT (no ACK)   |
| **Shutdown**  | Flush + Wait ACKs | Final stats      | Final packets → ACKs |

---

## RDT State Machine

**Client States:**

- **IDLE:** No pending packets
- **WAITING_ACK:** Packet sent, timer running
- **RETRANSMIT:** Timeout occurred, retry < max_retries
- **GIVE_UP:** Max retries exceeded, accept loss

**Transitions:**

```
IDLE → [send packet] → WAITING_ACK
WAITING_ACK → [ACK received] → IDLE
WAITING_ACK → [timeout] → RETRANSMIT
RETRANSMIT → [retry < max] → WAITING_ACK
RETRANSMIT → [retry >= max] → GIVE_UP → IDLE
```

---

## Timeout Calculation Details

**Initial values:**

- `estimatedRTT = 500ms` (conservative estimate)
- `devRTT = 100ms` (initial deviation)
- `timeout = 500 + 4*100 = 900ms`

**After each ACK:**

```python
sampleRTT = current_time - send_time
estimatedRTT = (1 - α) * estimatedRTT + α * sampleRTT    # α = 0.125
devRTT = (1 - β) * devRTT + β * |sampleRTT - estimatedRTT|  # β = 0.25
timeout = estimatedRTT + 4 * devRTT
```

**Example evolution:**

```
Packet 1: sampleRTT=50ms  → estimatedRTT=494ms, devRTT=121ms, timeout=978ms
Packet 2: sampleRTT=55ms  → estimatedRTT=489ms, devRTT=130ms, timeout=1009ms
Packet 3: sampleRTT=48ms  → estimatedRTT=484ms, devRTT=139ms, timeout=1040ms
[Network delay increases]
Packet 10: sampleRTT=200ms → estimatedRTT=520ms, devRTT=85ms, timeout=860ms
[Timeout adapts to network conditions]
```
