# TinyTelemetry Protocol - Complete Learning Guide

**For Students New to Network Programming**

This guide explains everything you need to understand the TinyTelemetry Protocol project, from basic networking concepts to the actual implementation.

---

## Table of Contents

1. [Networking Fundamentals](#1-networking-fundamentals)
2. [Understanding Protocols](#2-understanding-protocols)
3. [UDP vs TCP](#3-udp-vs-tcp)
4. [Binary Data and Encoding](#4-binary-data-and-encoding)
5. [Understanding Our Protocol](#5-understanding-our-protocol)
6. [Code Walkthrough](#6-code-walkthrough)
7. [Testing and Validation](#7-testing-and-validation)
8. [Common Pitfalls](#8-common-pitfalls)

---

## 1. Networking Fundamentals

### What is a Network?

A **network** is a group of computers connected together that can communicate with each other. Think of it like a postal system where computers send "letters" (data packets) to each other.

### Key Concepts

#### IP Address
- **What it is**: A unique identifier for a device on a network
- **Example**: `192.168.1.100` or `127.0.0.1` (localhost - your own computer)
- **Analogy**: Like a street address for your house

#### Port
- **What it is**: A number (0-65535) that identifies a specific application/service
- **Example**: Port 80 for websites, Port 5000 for our server
- **Analogy**: Like an apartment number - the IP is the building, the port is which door to knock on

#### Packet
- **What it is**: A chunk of data sent over the network
- **Contains**: Header (instructions) + Payload (actual data)
- **Analogy**: An envelope (header) containing a letter (payload)

### How Computers Communicate

```
Sensor (Client)                   Collector (Server)
    |                                    |
    | "I want to send data to           |
    |  IP: 127.0.0.1, Port: 5000"       |
    |                                    |
    |------------ Packet --------------->|
    |  [Header: who, what, when]        |
    |  [Payload: temperature=23.5]      |
    |                                    |
    |                                    | "Got it! Processing..."
```

---

## 2. Understanding Protocols

### What is a Protocol?

A **protocol** is a set of rules for how computers communicate. It's like a language both sides agree to speak.

**Real-world analogy**: When you mail a letter, you follow a protocol:
1. Write recipient's address on front
2. Put return address on back
3. Add postage stamp
4. Everyone knows where to look for what

### Common Protocols You Use Every Day

| Protocol | What It Does | Example |
|----------|--------------|---------|
| HTTP | Loading web pages | Visiting google.com |
| SMTP | Sending email | Gmail sending a message |
| DNS | Converting names to IP addresses | www.google.com → 142.250.185.46 |
| **TinyTelemetry** | IoT sensor reporting | Temperature sensor → Collector |

### Why Create a Custom Protocol?

**Question**: Why not just use HTTP?

**Answer**: Different needs require different solutions:

| Need | HTTP | TinyTelemetry |
|------|------|---------------|
| Battery-powered sensors | ❌ Too much overhead | ✅ Minimal overhead |
| Tiny packets (10 bytes) | ❌ Headers are ~200 bytes | ✅ Header is 10 bytes |
| Fire-and-forget | ❌ Expects response | ✅ No response needed |
| Works on unreliable networks | ❌ Requires TCP connection | ✅ Tolerates 5% loss |

---

## 3. UDP vs TCP

### The Two Main Transport Protocols

Think of sending packages:

#### TCP (Transmission Control Protocol)
- **Like**: Registered mail with tracking
- **Guarantees**: Package arrives, in order, no duplicates
- **Process**:
  1. Establish connection ("Hello, I want to send you something")
  2. Send data with acknowledgments ("Got package 1?" "Yes!" "Got package 2?" "Yes!")
  3. Close connection ("Done sending, goodbye")
- **Overhead**: High (lots of back-and-forth)
- **Use when**: You need 100% reliability (file downloads, web pages)

#### UDP (User Datagram Protocol)
- **Like**: Dropping postcards in a mailbox
- **Guarantees**: NONE - might get lost, might arrive out of order
- **Process**: Just send it!
- **Overhead**: Minimal (no handshakes, no acknowledgments)
- **Use when**: Speed matters more than perfection (video calls, gaming, sensor data)

### Why We Use UDP for TinyTelemetry

```python
# Sensor sending temperature readings:

# With TCP (slow, power-hungry):
1. Connect to server           # Takes time, uses battery
2. Wait for "connected" response
3. Send reading
4. Wait for acknowledgment
5. Send next reading
6. Wait for acknowledgment
... (lots of waiting)

# With UDP (fast, efficient):
1. Send reading                # Just send it!
2. Send next reading           # Keep sending!
3. Send next reading
... (no waiting, save battery!)
```

**Trade-off**: If network drops a packet, we lose that temperature reading. But we get a new one in 1 second anyway, so who cares? 🤷‍♂️

---

## 4. Binary Data and Encoding

### Why Binary Instead of Text?

**Text (JSON) - What humans like:**
```json
{"device": 1001, "seq": 42, "temp": 23.5}
```
**Size**: 43 bytes

**Binary - What computers like:**
```
\x11\x03\xe9\x00\x2a\x65\x4a\x2f\x38\x00
```
**Size**: 10 bytes

**Savings**: 76% smaller! Critical for battery-powered sensors.

### Understanding Binary Encoding

#### Bits and Bytes
- **Bit**: A single 0 or 1
- **Byte**: 8 bits (e.g., `10110011`)
- **Hex**: Easier way to write bytes (e.g., `0xB3` = `10110011`)

#### Common Data Types

| Type | Size | Range | Example Use |
|------|------|-------|-------------|
| `uint8` | 1 byte (8 bits) | 0 to 255 | Message type, flags |
| `uint16` | 2 bytes (16 bits) | 0 to 65,535 | Device ID, sequence number |
| `uint32` | 4 bytes (32 bits) | 0 to 4,294,967,295 | Timestamp (Unix epoch) |

### Byte Order (Endianness)

**Problem**: Different computers store bytes in different orders.

**Example**: The number 1001 (0x03E9)

```
Big-Endian (Network byte order):
   Byte 1    Byte 2
   [0x03]    [0xE9]

Little-Endian (Some computers):
   Byte 1    Byte 2
   [0xE9]    [0x03]
```

**Solution**: Always use **network byte order (big-endian)** for network communication.

In Python: `struct.pack('!H', 1001)` - The `!` means "network byte order"

### Bit Packing

Sometimes we pack multiple values into one byte to save space.

**Example**: Our first byte contains both version and message type

```
Byte 0: Version (4 bits) + MsgType (4 bits)

        7  6  5  4  3  2  1  0  (bit positions)
       ┌──┬──┬──┬──┬──┬──┬──┬──┐
       │ 0│ 0│ 0│ 1│ 0│ 0│ 0│ 1│
       └──┴──┴──┴──┴──┴──┴──┴──┘
          Version=1    MsgType=1
         (bits 7-4)   (bits 3-0)

Hex: 0x11
```

**How to create this in code:**
```python
version = 1
msg_type = 1

# Shift version left by 4 bits, then OR with msg_type
combined = (version << 4) | msg_type
# Result: 0x11

# To extract:
version = (combined >> 4) & 0x0F      # Get upper 4 bits
msg_type = combined & 0x0F             # Get lower 4 bits
```

---

## 5. Understanding Our Protocol

### The Big Picture

**Goal**: Send temperature/humidity readings from battery-powered sensors to a central server.

**Constraints**:
- Sensors have limited power (battery life matters!)
- Network might drop 5% of packets (unreliable WiFi)
- Bandwidth is limited (save bytes = save money/power)
- Don't need 100% delivery (missing one reading is OK)

### Our Solution: TinyTelemetry

```
┌─────────────────────────────────────────────┐
│          TinyTelemetry Packet              │
├──────────────────┬──────────────────────────┤
│  Header (10 B)   │  Payload (0-190 B)      │
├──────────────────┴──────────────────────────┤
│  Total: Max 200 bytes                       │
└─────────────────────────────────────────────┘
```

### Header Breakdown (10 bytes)

```
Byte:  0      1-2        3-4       5-6-7-8      9
     ┌───┬─────────┬──────────┬────────────┬──────┐
     │V+T│DeviceID │ SeqNum   │ Timestamp  │Flags │
     └───┴─────────┴──────────┴────────────┴──────┘
      1B     2B         2B         4B         1B
```

**Field by field:**

#### Byte 0: Version + Message Type
- **Version** (4 bits): Protocol version = 1
  - Why? So we can make TinyTelemetry v2 later without breaking v1 devices
- **Message Type** (4 bits): What kind of message?
  - 0 = INIT (sensor starting up)
  - 1 = DATA (sensor reading)
  - 2 = HEARTBEAT (reserved for later)

#### Bytes 1-2: Device ID (16 bits)
- **Range**: 0 to 65,535
- **Purpose**: Which sensor sent this?
- **Example**: Sensor 1001 in the kitchen, 1002 in the bedroom
- **Why 16 bits?** Supports up to 65,536 sensors (enough for most buildings)

#### Bytes 3-4: Sequence Number (16 bits)
- **Range**: 0 to 65,535 (then wraps back to 0)
- **Purpose**: Detect lost packets and duplicates
- **Example**:
  - Sensor sends: 0, 1, 2, 3, 4, 5...
  - Server receives: 0, 1, 2, 4 (missing 3!), 5
  - Server: "Gap detected! Missing sequence 3"

#### Bytes 5-8: Timestamp (32 bits)
- **Format**: Unix epoch time (seconds since Jan 1, 1970)
- **Range**: 0 to 4.2 billion (valid until year 2106)
- **Purpose**: When was this reading taken?
- **Example**: 1698765432 = October 31, 2023, 12:30:32 UTC
- **Why?** Server can reorder delayed packets, detect old data

#### Byte 9: Flags (8 bits)
- **Current use**: Reserved (set to 0)
- **Future use**: Could indicate batching, priority, compression
- **Why include it?** Planning ahead for Phase 2 enhancements

### Message Types Explained

#### INIT Message
```
Purpose: "Hello! I'm a sensor, I'm starting up"
When:    Sent once when sensor boots up
Payload: Empty (just the header)
Example:
  Device 1001 starts → sends INIT (seq=0)
  Server: "OK, device 1001 is online, expecting seq=1 next"
```

#### DATA Message
```
Purpose: "Here's my latest reading"
When:    Every 1-30 seconds (configurable)
Payload: JSON with temperature and humidity
Example:
  Device 1001 every second:
    - INIT (seq=0)
    - DATA (seq=1): {"temperature": 23.5, "humidity": 58.2}
    - DATA (seq=2): {"temperature": 23.6, "humidity": 58.1}
    - ...
```

### Why This Design?

| Decision | Reason |
|----------|--------|
| Fixed 10-byte header | Predictable, easy to parse, no variable-length complexity |
| Separate INIT message | Server knows when sensors restart |
| Sequence numbers | Detect loss without retransmission |
| Timestamps | Handle network delays, reorder packets |
| JSON payload (Phase 1) | Easy to debug, human-readable |
| Binary header | Save bytes on overhead |

---

## 6. Code Walkthrough

### File Structure

```
src/
├── protocol.py    # Header packing/unpacking (the "language")
├── server.py      # Collector (listens and logs)
└── client.py      # Sensor (sends readings)
```

### protocol.py - The Language

**Purpose**: Define how to pack/unpack the 10-byte header.

#### Key Concept: struct Module

Python's `struct` module converts between Python values and binary bytes.

```python
import struct

# Pack: Python values → binary bytes
header = struct.pack('!BHHIB',
                     version_and_type,  # 1 byte
                     device_id,         # 2 bytes (H = unsigned short)
                     seq_num,           # 2 bytes
                     timestamp,         # 4 bytes (I = unsigned int)
                     flags)             # 1 byte
# Result: 10 bytes of binary data

# Unpack: binary bytes → Python values
version_and_type, device_id, seq_num, timestamp, flags = \
    struct.unpack('!BHHIB', header_bytes)
```

**Format string breakdown:**
- `!` = Network byte order (big-endian)
- `B` = Unsigned char (1 byte)
- `H` = Unsigned short (2 bytes)
- `I` = Unsigned int (4 bytes)

#### Walking Through pack_header()

```python
def pack_header(msg_type, device_id, seq_num, timestamp=None, flags=0):
    # 1. Get current time if not provided
    if timestamp is None:
        timestamp = int(time.time())  # Unix epoch seconds

    # 2. Combine version (1) and msg_type (0-2) into one byte
    #    Version in upper 4 bits, msg_type in lower 4 bits
    version_and_type = (PROTOCOL_VERSION << 4) | (msg_type & 0x0F)
    #    Example: (1 << 4) | 1 = 0x10 | 0x01 = 0x11

    # 3. Pack all fields into 10 bytes
    header = struct.pack('!BHHIB',
                        version_and_type,  # 1 byte
                        device_id,         # 2 bytes
                        seq_num,           # 2 bytes
                        timestamp,         # 4 bytes
                        flags)             # 1 byte

    return header  # Returns bytes object, length = 10
```

#### Walking Through unpack_header()

```python
def unpack_header(data):
    # 1. Check we have enough bytes
    if len(data) < HEADER_SIZE:  # HEADER_SIZE = 10
        raise ValueError("Data too short")

    # 2. Unpack the 10-byte header
    version_and_type, device_id, seq_num, timestamp, flags = \
        struct.unpack('!BHHIB', data[:HEADER_SIZE])

    # 3. Extract version and msg_type from combined byte
    version = (version_and_type >> 4) & 0x0F   # Upper 4 bits
    msg_type = version_and_type & 0x0F          # Lower 4 bits

    # 4. Return as dictionary
    return {
        'version': version,
        'msg_type': msg_type,
        'device_id': device_id,
        'seq_num': seq_num,
        'timestamp': timestamp,
        'flags': flags
    }
```

### server.py - The Collector

**Purpose**: Listen on UDP port 5000, receive packets, log them.

#### UDP Server Setup

```python
# Create a UDP socket
socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#                      AF_INET = IPv4, SOCK_DGRAM = UDP

# Bind to address and port
socket.bind(('127.0.0.1', 5000))
#           IP address    port

# Now we're listening!
```

#### Main Loop

```python
while True:
    # Wait for a packet (blocks until one arrives)
    data, addr = socket.recvfrom(1024)
    #     ^           ^                ^
    #     |           |                |
    #  packet      sender's        max bytes
    #  bytes      IP & port        to receive

    # Process the packet
    process_packet(data, addr)
```

#### Processing Packets

```python
def process_packet(data, addr):
    # 1. Parse the header
    header, payload = TinyTelemetryProtocol.parse_message(data)

    # 2. Extract fields
    device_id = header['device_id']
    seq_num = header['seq_num']
    msg_type = header['msg_type']

    # 3. Check for duplicates
    if seq_num == last_seq_for_this_device:
        print("[DUPLICATE]")

    # 4. Check for gaps
    if seq_num > last_seq + 1:
        gap_size = seq_num - last_seq - 1
        print(f"[WARNING] Missing {gap_size} packets")

    # 5. Log the packet
    print(f"Device {device_id} | Seq {seq_num} | Type: {msg_type}")
```

#### Why Track Per-Device State?

Multiple sensors can send to the same server:

```
Server state = {
    1001: {'last_seq': 42, 'count': 43},  # Kitchen sensor
    1002: {'last_seq': 15, 'count': 16},  # Bedroom sensor
    1003: {'last_seq': 8, 'count': 9}     # Garage sensor
}
```

Each sensor has independent sequence numbers.

### client.py - The Sensor

**Purpose**: Send INIT once, then send DATA every N seconds.

#### UDP Client Setup

```python
# Create a UDP socket
socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# No bind() needed! We're just sending, not receiving.
```

#### Sending Messages

```python
# 1. Create the message
message = TinyTelemetryProtocol.create_message(
    msg_type=MSG_DATA,
    device_id=1001,
    seq_num=42,
    payload=b'{"temperature": 23.5, "humidity": 58.2}'
)

# 2. Send it to the server
socket.sendto(message, ('127.0.0.1', 5000))
#                       server IP    server port

# That's it! Fire and forget!
```

#### Timing Loop

```python
interval = 1  # Send every 1 second
duration = 60  # Run for 60 seconds

start_time = time.time()
next_send_time = start_time + interval

while time.time() - start_time < duration:
    if time.time() >= next_send_time:
        # Time to send!
        send_data(temperature, humidity)

        # Schedule next send
        next_send_time += interval

    # Small sleep to avoid busy-waiting
    time.sleep(0.01)
```

**Why this approach?**
- Doesn't drift over time (unlike `time.sleep(interval)` in a loop)
- Precise timing even if `send_data()` takes a few milliseconds

---

## 7. Testing and Validation

### baseline_test.sh - Automated Testing

**Purpose**: Verify the system works without human intervention.

#### What It Does

```bash
1. Start server in background
2. Wait 2 seconds for server to initialize
3. Run client for 60 seconds
4. Stop server
5. Analyze logs
6. Report PASS or FAIL
```

#### Key Bash Concepts

```bash
# Start process in background (& at end)
python3 server.py > server.log 2>&1 &
SERVER_PID=$!  # Save the process ID

# Redirect output:
#   > server.log     (stdout to file)
#   2>&1             (stderr to stdout)

# Run client (foreground - script waits)
python3 client.py 1001 1 60

# Kill background process
kill -INT $SERVER_PID  # Send interrupt signal (Ctrl+C)
```

#### Log Analysis

```bash
# Count lines matching a pattern
TOTAL_PACKETS=$(grep -c "Device 1001" server.log)

# Expected: 1 INIT + 60 DATA = 61 packets
# Accept ≥99% = at least 60 packets

if [ $TOTAL_PACKETS -ge 60 ]; then
    echo "PASS"
else
    echo "FAIL"
fi
```

### What "Baseline" Means

**Baseline test**: Testing on a perfect local network (no packet loss, no delay).

**Purpose**: Verify the code works before testing with network problems.

**Later (Phase 2)**: Add artificial problems:
- 5% packet loss (use `netem`)
- 100ms delay
- Jitter (random delays)

---

## 8. Common Pitfalls and How to Avoid Them

### 1. Byte Order Confusion

**Problem**: Computer A sends 1001, Computer B receives 59395.

**Why?**
```
Little-endian sends: E9 03
Big-endian reads:    E9 03 = 0xE903 = 59395 ❌

Should be:           03 E9 = 0x03E9 = 1001 ✓
```

**Solution**: Always use `!` in struct format strings.

```python
# ✅ CORRECT
struct.pack('!H', 1001)  # Network byte order

# ❌ WRONG
struct.pack('H', 1001)   # Native byte order (varies by computer)
```

### 2. Forgetting to Increment Sequence Numbers

**Problem**: All packets have seq=0.

```python
# ❌ WRONG
seq_num = 0
while running:
    send_data(seq_num)  # Always sending 0!

# ✅ CORRECT
seq_num = 0
while running:
    send_data(seq_num)
    seq_num += 1  # Increment!
```

### 3. Server Crashes on Malformed Packets

**Problem**: Random network data crashes the server.

```python
# ❌ WRONG
header = unpack_header(data)  # Crashes if data is too short

# ✅ CORRECT
try:
    header = unpack_header(data)
except Exception as e:
    print(f"Invalid packet: {e}")
    return  # Skip this packet
```

### 4. Port Already in Use

**Problem**: Can't start server - "Address already in use"

**Why**: Old server process still running.

**Solution**:
```bash
# Find process using port 5000
lsof -ti:5000

# Kill it
lsof -ti:5000 | xargs kill -9
```

### 5. Wrong Directory

**Problem**: "Module not found: protocol"

**Why**: Python can't find protocol.py

**Solution**:
```bash
# Make sure you're in the src/ directory
cd /path/to/iot-project/src
python3 server.py  # Now it works!
```

### 6. Timestamp Errors

**Problem**: Timestamps look wrong or are in the future.

```python
# ✅ CORRECT
timestamp = int(time.time())  # Unix epoch seconds

# ❌ WRONG
timestamp = time.time()  # Float, wastes bytes
timestamp = datetime.now()  # Not a number!
```

### 7. JSON Encoding

**Problem**: "TypeError: a bytes-like object is required"

```python
# ✅ CORRECT
payload = json.dumps(data).encode('utf-8')  # str → bytes

# ❌ WRONG
payload = json.dumps(data)  # Still a string!
```

---

## Quick Reference

### Python Socket Cheat Sheet

```python
import socket

# Create UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Server: bind to port
sock.bind(('127.0.0.1', 5000))
data, addr = sock.recvfrom(1024)  # Receive (blocks)

# Client: just send
sock.sendto(b'hello', ('127.0.0.1', 5000))  # Send
```

### Struct Format Strings

```python
'!'   # Network byte order (big-endian) - ALWAYS USE THIS
'B'   # unsigned char (1 byte): 0-255
'H'   # unsigned short (2 bytes): 0-65535
'I'   # unsigned int (4 bytes): 0-4294967295
'f'   # float (4 bytes)

# Example: pack two shorts
struct.pack('!HH', 1001, 42)  # → b'\x03\xe9\x00\x2a'
```

### Bit Operations

```python
# Combine two 4-bit values into one byte
upper = 1  # Version
lower = 1  # Message type
combined = (upper << 4) | lower  # 0x11

# Extract from combined byte
upper = (combined >> 4) & 0x0F   # Get upper 4 bits
lower = combined & 0x0F           # Get lower 4 bits
```

### Time Functions

```python
import time

time.time()              # Current time (float, seconds since 1970)
int(time.time())         # Unix timestamp (integer)
time.sleep(1)            # Sleep for 1 second
```

---

## Practice Exercises

### Exercise 1: Understanding Headers

**Task**: What does this header represent?

```
Hex: 10 03 E9 00 05 67 2C 8A 50 00
```

<details>
<summary>Answer</summary>

```
Byte 0: 0x10 = 0001 0000
  Version = 0001 = 1
  MsgType = 0000 = 0 (INIT)

Bytes 1-2: 0x03E9 = 1001 (Device ID)
Bytes 3-4: 0x0005 = 5 (Sequence Number)
Bytes 5-8: 0x672C8A50 = 1731008080 (Timestamp: ~Nov 7, 2024)
Byte 9: 0x00 (Flags)

This is an INIT message from device 1001, sequence 5.
```
</details>

### Exercise 2: Code the Opposite

**Task**: If we have `pack_header()`, write `create_init_message()` for a sensor.

<details>
<summary>Answer</summary>

```python
def create_init_message(device_id):
    """Send INIT with seq=0"""
    return TinyTelemetryProtocol.create_message(
        msg_type=MSG_INIT,
        device_id=device_id,
        seq_num=0,  # INIT is always seq 0
        payload=b''  # No payload
    )
```
</details>

### Exercise 3: Detect Problems

**Task**: What's wrong with this code?

```python
seq = 0
for i in range(10):
    msg = pack_header(MSG_DATA, 1001, seq)
    sock.sendto(msg, ('127.0.0.1', 5000))
```

<details>
<summary>Answer</summary>

Two problems:
1. `seq` never increments - all messages have seq=0
2. No payload attached - just sending header

**Fix**:
```python
seq = 0
for i in range(10):
    payload = json.dumps({"temp": 23.5}).encode('utf-8')
    msg = create_message(MSG_DATA, 1001, seq, payload)
    sock.sendto(msg, ('127.0.0.1', 5000))
    seq += 1  # Increment!
```
</details>

---

## Additional Resources

### Learn More About:

1. **Network Programming**
   - [Python Socket Programming HOWTO](https://docs.python.org/3/howto/sockets.html)
   - [Beej's Guide to Network Programming](https://beej.us/guide/bgnet/)

2. **Binary Data**
   - [Python struct documentation](https://docs.python.org/3/library/struct.html)
   - Understanding hex: Each hex digit = 4 bits (0-F = 0-15)

3. **UDP vs TCP**
   - Watch: "UDP vs TCP" on YouTube
   - Try: `wireshark` to see actual packets

4. **Protocol Design**
   - Read real RFCs: RFC 768 (UDP), RFC 793 (TCP)
   - Our Mini-RFC is based on the same format

### Debugging Tools

```bash
# See if server is running
lsof -i :5000

# Check network connectivity
ping 127.0.0.1

# Capture packets (advanced)
tcpdump -i lo0 port 5000

# Monitor Python processes
ps aux | grep python
```

---

## Summary

**You now understand**:
- ✅ How networks and protocols work
- ✅ Why UDP is perfect for IoT sensors
- ✅ How binary encoding saves bandwidth
- ✅ The complete TinyTelemetry protocol design
- ✅ Every line of code in protocol.py, server.py, client.py
- ✅ How to test and validate the system

**Next steps**:
1. Run the code yourself (see `NEXT_STEPS.md`)
2. Try modifying it (change port, device ID, interval)
3. Break it and fix it (best way to learn!)
4. Read the Mini-RFC for formal specification

**Remember**: Every expert was once a beginner. Take your time, experiment, and don't be afraid to ask questions!

---

**Questions?** Review these files:
- `Docs/Mini_RFC_Draft.md` - Formal specification
- `Docs/Proposal.md` - Why we designed it this way
- `IMPLEMENTATION_SUMMARY.md` - What was built
- `README.txt` - How to run everything

Good luck! 🚀
