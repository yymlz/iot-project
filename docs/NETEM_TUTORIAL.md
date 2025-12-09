# TinyTelemetry - Network Impairment Testing with netem

This guide explains how to use Linux `netem` (Network Emulator) to test the TinyTelemetry protocol under various network conditions.

## What is netem?

`netem` is a Linux kernel module that provides network emulation functionality for testing protocols under impaired network conditions. It can simulate:

- **Packet loss** - Drop packets randomly
- **Delay** - Add latency to packets
- **Jitter** - Variable delay (delay variation)
- **Packet reordering** - Deliver packets out of order
- **Packet duplication** - Send duplicate packets
- **Packet corruption** - Corrupt packet data

## Prerequisites

### On Linux (Ubuntu/Debian):

```bash
# Install iproute2 (usually pre-installed)
sudo apt-get install iproute2

# Verify tc command is available
tc -V
```

### On Windows with WSL:

```powershell
# Open WSL
wsl

# Inside WSL, you have access to tc command
# Note: Some functionality requires WSL2 with proper networking
```

## Quick Start

### 1. Identify Your Network Interface

```bash
# List all network interfaces
ip link show

# Common interfaces:
# - eth0: Ethernet adapter
# - wlan0: WiFi adapter
# - lo: Localhost (loopback)
# - enp0s3: VirtualBox/VM ethernet
```

### 2. Basic netem Commands

```bash
# Add packet loss (5%)
sudo tc qdisc add dev eth0 root netem loss 5%

# Add delay (100ms)
sudo tc qdisc add dev eth0 root netem delay 100ms

# Add jitter (100ms delay with 50ms variation)
sudo tc qdisc add dev eth0 root netem delay 100ms 10ms

# View current rules
tc qdisc show dev eth0

# Remove all rules
sudo tc qdisc del dev eth0 root
```

## Test Scenarios for TinyTelemetry

### Scenario 1: Baseline (No Impairment)

```bash
# Clear any existing rules
sudo tc qdisc del dev eth0 root 2>/dev/null

# Run test - expect 0% loss, ordered packets
```

### Scenario 2: Packet Loss (5%, 10%, 15%)

```bash
# 5% packet loss
sudo tc qdisc add dev eth0 root netem loss 5%

# 10% packet loss
sudo tc qdisc add dev eth0 root netem loss 10%

# 15% packet loss
sudo tc qdisc add dev eth0 root netem loss 15%

# Clear when done
sudo tc qdisc del dev eth0 root
```

### Scenario 3: Network Delay

```bash
# Fixed 50ms delay
sudo tc qdisc add dev eth0 root netem delay 50ms

# Fixed 100ms delay
sudo tc qdisc add dev eth0 root netem delay 100ms

# Fixed 200ms delay
sudo tc qdisc add dev eth0 root netem delay 200ms
```

### Scenario 4: Jitter (Delay Variation)

```bash
# 50ms delay with 25ms jitter (uniform distribution)
sudo tc qdisc add dev eth0 root netem delay 50ms 25ms

# 100ms delay with 50ms jitter (normal distribution - more realistic)
sudo tc qdisc add dev eth0 root netem delay 100ms 50ms distribution normal

# High jitter for stress testing
sudo tc qdisc add dev eth0 root netem delay 200ms 100ms distribution normal
```

### Scenario 5: Packet Reordering

```bash
# 25% of packets will be reordered
sudo tc qdisc add dev eth0 root netem delay 10ms reorder 25% 50%

# Higher reordering (50%)
sudo tc qdisc add dev eth0 root netem delay 20ms reorder 50% 25%

# Note: reorder requires some delay to work
```

### Scenario 6: Packet Duplication

```bash
# 5% of packets will be duplicated
sudo tc qdisc add dev eth0 root netem duplicate 5%

# 10% duplication
sudo tc qdisc add dev eth0 root netem duplicate 10%
```

### Scenario 7: Combined Impairments (Real-World Simulation)

```bash
# Moderate: 5% loss + 50ms delay + 25ms jitter + 10% reorder
sudo tc qdisc add dev eth0 root netem loss 5% delay 50ms 25ms reorder 10% 25%

# Harsh: 10% loss + 100ms delay + 50ms jitter + 25% reorder
sudo tc qdisc add dev eth0 root netem loss 10% delay 100ms 50ms reorder 25% 50%

# Very harsh (stress test)
sudo tc qdisc add dev eth0 root netem loss 15% delay 200ms 100ms reorder 50% 50%
```

## Step-by-Step Testing Procedure

### Step 1: Set Up Two Machines (or VMs)

**Machine A (Server - Linux with netem):**

- Runs the TinyTelemetry server
- Has netem rules applied

**Machine B (Client - Windows or Linux):**

- Runs the TinyTelemetry client
- Sends data to Machine A

### Step 2: Apply netem Rules on Server

```bash
# On Machine A (Server)
# Clear existing rules first
sudo tc qdisc del dev eth0 root 2>/dev/null

# Apply desired scenario (e.g., 10% loss)
sudo tc qdisc add dev eth0 root netem loss 10%

# Verify
tc qdisc show dev eth0
```

### Step 3: Start the Server

```bash
# On Machine A
cd /path/to/iot-project/src
python3 server.py
```

### Step 4: Start the Client

```powershell
# On Machine B (Windows) - replace <server_ip> with actual IP
cd d:\iot-project\src
python client.py 1001 1 60 0 0 5 <server_ip>

# Parameters: device_id=1001, interval=1s, duration=60s,
#             no client-side loss, no jitter, batch_size=5
```

### Step 5: Collect Results

After the test:

1. Stop the server (Ctrl+C)
2. Review the CSV file generated
3. Check the Phase 2 metrics printed at shutdown
4. Clear netem rules:
   ```bash
   sudo tc qdisc del dev eth0 root
   ```

## Testing on Localhost (Same Machine)

For testing on the same machine, use the loopback interface (`lo`):

```bash
# Apply loss to loopback
sudo tc qdisc add dev lo root netem loss 5%

# Start server (binds to 127.0.0.1)
python3 server.py

# Start client (connects to 127.0.0.1)
python3 client.py 1001 1 60 0 0 5 127.0.0.1

# Clear when done
sudo tc qdisc del dev lo root
```

**Note:** Localhost testing has limitations - packets don't actually traverse a real network path. For accurate testing, use separate machines.

## Expected Results by Scenario

| Scenario  | Expected Behavior                                     |
| --------- | ----------------------------------------------------- |
| Baseline  | 0% loss, packets in order                             |
| loss5     | ~5% packets missing, sequence gaps detected           |
| loss10    | ~10% packets missing, more gaps                       |
| delay100  | All packets arrive, with ~100ms latency               |
| jitter    | Packets may arrive out of order due to variable delay |
| reorder   | Some packets processed out of sequence                |
| duplicate | Duplicate packets detected and logged                 |
| combined  | Mix of all effects                                    |

## Interpreting TinyTelemetry Metrics

After each test, the server prints Phase 2 metrics:

```
[Phase 2 Metrics]
----------------------------------------
  bytes_per_report:     47.00 bytes     # Avg packet size
  packets_received:     57              # Successfully received
  duplicate_rate:       0.0175          # 1.75% duplicates
  sequence_gap_count:   3               # 3 gap events detected
  total_lost_packets:   5               # 5 packets never arrived
  cpu_ms_per_report:    0.0234 ms       # Processing time per packet
```

## Troubleshooting

### "RTNETLINK answers: Operation not permitted"

```bash
# Must run as root
sudo tc qdisc add dev eth0 root netem loss 5%
```

### "Cannot find device eth0"

```bash
# Check available interfaces
ip link show

# Use correct interface name
sudo tc qdisc add dev enp0s3 root netem loss 5%
```

### "RTNETLINK answers: File exists"

```bash
# Delete existing rules first
sudo tc qdisc del dev eth0 root
```

### Netem not affecting traffic

```bash
# Make sure you're applying to the correct interface
# For localhost: use 'lo'
# For external traffic: use your network interface (eth0, enp0s3, etc.)

# Verify rules are applied
tc qdisc show dev eth0
```

## Quick Reference Commands

```bash
# View all interfaces
ip link show

# View current rules on interface
tc qdisc show dev eth0

# Add rules
sudo tc qdisc add dev eth0 root netem <options>

# Change existing rules
sudo tc qdisc change dev eth0 root netem <options>

# Delete rules
sudo tc qdisc del dev eth0 root

# Helpful options:
#   loss X%              - Drop X% of packets
#   delay Xms            - Add X milliseconds delay
#   delay Xms Yms        - X ms delay with Y ms jitter
#   reorder X% Y%        - X% reorder with Y% correlation
#   duplicate X%         - Duplicate X% of packets
#   corrupt X%           - Corrupt X% of packets
```

## Using the Provided Test Script

We've included a test script that automates netem configuration:

```bash
# Make script executable
chmod +x tests/netem_test.sh

# Apply a scenario
sudo ./tests/netem_test.sh apply loss10 eth0

# Clear all rules
sudo ./tests/netem_test.sh clear eth0

# Show status
sudo ./tests/netem_test.sh status eth0

# Run full automated test
sudo ./tests/netem_test.sh test combined eth0
```

## Recording Results

For each test run, record:

1. Scenario name and parameters
2. Test duration
3. CSV file from server
4. Final metrics from server output
5. Any observed anomalies

This data will be used for Phase 2 analysis and protocol performance evaluation.
