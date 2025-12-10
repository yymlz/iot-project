# Experimental Evaluation Plan - TinyTelemetry Protocol

## 6. Experimental Evaluation Plan

### 6.1 Test Objectives

Evaluate TinyTelemetry protocol performance under various network conditions:

- **Reliability:** Packet delivery rate with RDT retransmission
- **Efficiency:** Overhead from retransmissions and ACKs
- **Adaptability:** Timeout adjustment to network conditions
- **Scalability:** Batch mode vs. individual packet performance

---

### 6.2 Baseline Configuration

**Hardware/Software:**

- OS: Linux (Ubuntu/Debian) or Windows with WSL2
- Python: 3.8+
- Network: Localhost (loopback interface)
- Network Emulator: `tc` with `netem` module

**Default Test Parameters:**

- Device ID: 1001-1020 (unique per test)
- Interval: 1 second between readings
- Duration: 30 seconds (30 readings total)
- Batch Size: 3 (10 BATCH packets per test)
- Initial Timeout: 500ms
- Max Retries: 3

**Baseline Test (No Impairment):**

```bash
# Expected results:
- Packet loss: 0%
- Retransmissions: 0
- All packets acknowledged
- RTT: <5ms (localhost)
- Timeout stabilizes: ~200-300ms
```

---

### 6.3 Metrics to Measure

**Client-Side Metrics:**

1. `total_packets_sent` - Total DATA/BATCH packets transmitted
2. `ack_received_count` - Number of ACKs received
3. `retransmission_count` - Number of retransmissions sent
4. `retransmission_rate` - (retransmissions / total_packets_sent) \* 100%
5. `estimated_rtt` - Average round-trip time (ms)
6. `dev_rtt` - RTT deviation (ms)
7. `final_timeout` - Adapted timeout value (ms)
8. `unacknowledged_packets` - Packets lost after max retries

**Server-Side Metrics:**

1. `packets_received` - Total packets received
2. `bytes_per_report` - Average payload size
3. `duplicate_rate` - Percentage of duplicate packets
4. `sequence_gap_count` - Number of detected gaps
5. `packet_loss_rate` - (total_lost / (received + lost)) \* 100%
6. `cpu_ms_per_report` - Processing time per packet
7. `total_bytes_received` - Total bandwidth consumed

**Combined Metrics:**

1. **Delivery Success Rate** = (packets_received / packets_sent) \* 100%
2. **Effective Throughput** = total_bytes_received / duration
3. **Protocol Overhead** = (retransmissions + ACKs) / data_packets
4. **Recovery Efficiency** = recovered_packets / lost_packets

---

### 6.4 Test Scenarios

#### **Scenario 1: Packet Loss Tests**

**Purpose:** Evaluate retransmission mechanism effectiveness

| Test | Loss Rate | Expected Delivery | Expected Retrans |
| ---- | --------- | ----------------- | ---------------- |
| 1a   | 0%        | 100%              | 0                |
| 1b   | 5%        | >95%              | ~5-10%           |
| 1c   | 10%       | >95%              | ~10-15%          |
| 1d   | 15%       | >90%              | ~15-25%          |
| 1e   | 20%       | >85%              | ~25-35%          |

**Linux netem commands:**

```bash
# Test 1b: 5% packet loss
sudo tc qdisc add dev lo root netem loss 5%

# Test 1c: 10% packet loss
sudo tc qdisc add dev lo root netem loss 10%

# Test 1d: 15% packet loss
sudo tc qdisc add dev lo root netem loss 15%

# Test 1e: 20% packet loss
sudo tc qdisc add dev lo root netem loss 20%

# Clear rules
sudo tc qdisc del dev lo root
```

**Windows (requires Administrator PowerShell):**

```powershell
# No native Windows equivalent - use WSL2:
wsl sudo tc qdisc add dev lo root netem loss 10%
```

**macOS:**

```bash
# Use pfctl or dummynet (complex) - recommend WSL2 or Linux VM
```

---

#### **Scenario 2: Network Delay Tests**

**Purpose:** Evaluate timeout adaptation

| Test | Delay | Expected RTT | Expected Timeout |
| ---- | ----- | ------------ | ---------------- |
| 2a   | 50ms  | ~50ms        | ~250-300ms       |
| 2b   | 100ms | ~100ms       | ~400-500ms       |
| 2c   | 200ms | ~200ms       | ~800-1000ms      |
| 2d   | 500ms | ~500ms       | ~2000-2500ms     |

**Linux netem commands:**

```bash
# Test 2a: 50ms delay
sudo tc qdisc add dev lo root netem delay 50ms

# Test 2b: 100ms delay
sudo tc qdisc add dev lo root netem delay 100ms

# Test 2c: 200ms delay
sudo tc qdisc add dev lo root netem delay 200ms

# Test 2d: 500ms delay
sudo tc qdisc add dev lo root netem delay 500ms
```

---

#### **Scenario 3: Jitter (Delay Variation) Tests**

**Purpose:** Test timeout stability with variable latency

| Test | Delay ± Jitter | Expected Behavior  |
| ---- | -------------- | ------------------ |
| 3a   | 100ms ± 10ms   | Timeout stable     |
| 3b   | 100ms ± 50ms   | Moderate variation |
| 3c   | 100ms ± 100ms  | High variation     |

**Linux netem commands:**

```bash
# Test 3a: Low jitter
sudo tc qdisc add dev lo root netem delay 100ms 10ms

# Test 3b: Medium jitter
sudo tc qdisc add dev lo root netem delay 100ms 50ms

# Test 3c: High jitter
sudo tc qdisc add dev lo root netem delay 100ms 100ms
```

**Jitter distribution:**

```bash
# Normal distribution (default)
sudo tc qdisc add dev lo root netem delay 100ms 20ms

# Uniform distribution
sudo tc qdisc add dev lo root netem delay 100ms 20ms distribution uniform

# Pareto distribution (long tail)
sudo tc qdisc add dev lo root netem delay 100ms 20ms distribution pareto
```

---

#### **Scenario 4: Packet Reordering Tests**

**Purpose:** Verify server reorder buffer functionality

| Test | Reorder % | Correlation | Expected Behavior |
| ---- | --------- | ----------- | ----------------- |
| 4a   | 25%       | 50%         | Some reordering   |
| 4b   | 50%       | 50%         | Heavy reordering  |

**Linux netem commands:**

```bash
# Test 4a: 25% reordering (need base delay)
sudo tc qdisc add dev lo root netem delay 10ms reorder 25% 50%

# Test 4b: 50% reordering
sudo tc qdisc add dev lo root netem delay 10ms reorder 50% 50%
```

**Explanation:**

- `delay 10ms` - Base delay needed for reordering
- `reorder 25%` - 25% of packets reordered
- `50%` - Correlation (how likely consecutive packets reorder)

---

#### **Scenario 5: Packet Duplication Tests**

**Purpose:** Test duplicate detection and handling

| Test | Duplication % | Expected duplicate_rate |
| ---- | ------------- | ----------------------- |
| 5a   | 5%            | ~5%                     |
| 5b   | 10%           | ~10%                    |

**Linux netem commands:**

```bash
# Test 5a: 5% duplication
sudo tc qdisc add dev lo root netem duplicate 5%

# Test 5b: 10% duplication
sudo tc qdisc add dev lo root netem duplicate 10%
```

---

#### **Scenario 6: Combined Impairments (Realistic Networks)**

**Purpose:** Simulate real-world adverse conditions

| Test | Configuration                   | Simulates   |
| ---- | ------------------------------- | ----------- |
| 6a   | 5% loss + 50ms delay            | Good WiFi   |
| 6b   | 10% loss + 100ms + jitter 20ms  | Poor WiFi   |
| 6c   | 15% loss + 200ms + reorder 25%  | Cellular 3G |
| 6d   | 20% loss + 500ms + jitter 100ms | Satellite   |

**Linux netem commands:**

```bash
# Test 6a: Good WiFi
sudo tc qdisc add dev lo root netem loss 5% delay 50ms

# Test 6b: Poor WiFi
sudo tc qdisc add dev lo root netem loss 10% delay 100ms 20ms

# Test 6c: Cellular 3G
sudo tc qdisc add dev lo root netem loss 15% delay 200ms reorder 25% 50%

# Test 6d: Satellite
sudo tc qdisc add dev lo root netem loss 20% delay 500ms 100ms
```

---

#### **Scenario 7: Batch Size Comparison**

**Purpose:** Evaluate batch mode efficiency vs. packet loss amplification

| Test | Batch Size | Loss Rate | Expected Behavior                   |
| ---- | ---------- | --------- | ----------------------------------- |
| 7a   | 1          | 10%       | ~10% reading loss                   |
| 7b   | 3          | 10%       | ~30% reading loss                   |
| 7c   | 5          | 10%       | ~50% reading loss                   |
| 7d   | 10         | 10%       | ~100% reading loss (may need split) |

**Commands:**

```bash
# Apply 10% loss
sudo tc qdisc add dev lo root netem loss 10%

# Test different batch sizes
python3 client.py 1001 1 30 0 0 1 127.0.0.1   # batch_size=1
python3 client.py 1002 1 30 0 0 3 127.0.0.1   # batch_size=3
python3 client.py 1003 1 30 0 0 5 127.0.0.1   # batch_size=5
python3 client.py 1004 1 30 0 0 10 127.0.0.1  # batch_size=10
```

---

### 6.5 Measurement Methods

#### **Manual Testing:**

```bash
# Terminal 1: Start server
cd /mnt/d/iot-project/src
python3 server.py

# Terminal 2: Apply network impairment
sudo tc qdisc add dev lo root netem loss 10% delay 100ms

# Terminal 3: Run client
python3 client.py 1001 1 30 0 0 3 127.0.0.1

# Terminal 2: Clear impairment
sudo tc qdisc del dev lo root

# Collect results from console output + CSV files
```

#### **Automated Testing (Quick Test):**

```bash
cd /mnt/d/iot-project/tests
chmod +x quick_test.sh
sudo ./quick_test.sh lo
```

Runs 5 essential tests automatically:

1. Baseline
2. 10% packet loss
3. Delay + jitter
4. Reordering
5. Combined impairments

#### **Comprehensive Test Suite:**

```bash
cd /mnt/d/iot-project/tests
chmod +x run_all_tests.sh
sudo ./run_all_tests.sh lo
```

Runs 20 complete tests covering all scenarios.

---

### 6.6 Data Collection

**Automated collection:**

1. **Console Output Capture:**

   ```bash
   python3 server.py 2>&1 | tee logs/server_test1.log
   python3 client.py 1001 1 30 0 0 3 127.0.0.1 2>&1 | tee logs/client_test1.log
   ```

2. **CSV Files:**

   - Automatically saved to `logs/telemetry_YYYYMMDD_HHMMSS.csv`
   - Contains per-reading data with flags

3. **Packet Capture (Wireshark):**

   ```bash
   sudo tcpdump -i lo -w logs/capture_test1.pcap port 5000
   ```

4. **Results Analysis Script:**
   ```bash
   # Parse logs and generate statistics
   python3 tests/analyze_results.py logs/
   ```

---

### 6.7 Success Criteria

**Phase 1 (Basic Reliability):**

- ✅ 0% loss → 100% delivery
- ✅ 5% loss → ≥95% delivery (with retransmission)
- ✅ 10% loss → ≥95% delivery
- ✅ 15% loss → ≥90% delivery

**Phase 2 (Timeout Adaptation):**

- ✅ RTT adapts to network delay within 5-10 packets
- ✅ Timeout = estimatedRTT + 4\*devRTT
- ✅ No premature timeouts in stable networks

**Phase 3 (Efficiency):**

- ✅ Retransmission rate ≤ 2x network loss rate
- ✅ Protocol overhead (ACKs + retrans) ≤ 30% of data
- ✅ CPU usage ≤ 1ms per packet

**Phase 4 (Edge Cases):**

- ✅ Handles duplicates correctly (duplicate_flag=1)
- ✅ Detects gaps (gap_flag=1, sequence_gap_count)
- ✅ Survives extreme conditions (20% loss + 500ms delay)

---

### 6.8 Comparison Matrix

| Metric        | Baseline | 5% Loss | 10% Loss | 15% Loss | 200ms Delay |
| ------------- | -------- | ------- | -------- | -------- | ----------- |
| Delivery Rate | 100%     | ≥95%    | ≥95%     | ≥90%     | 100%        |
| Retrans Rate  | 0%       | ~5%     | ~10%     | ~15%     | 0%          |
| Avg RTT       | <5ms     | <10ms   | <10ms    | <10ms    | ~200ms      |
| Timeout       | ~300ms   | ~350ms  | ~400ms   | ~450ms   | ~1000ms     |
| CPU/packet    | <0.5ms   | <1ms    | <1ms     | <1.5ms   | <0.5ms      |

---

### 6.9 Test Execution Checklist

**Before Testing:**

- [ ] Install tcpdump: `sudo apt install tcpdump`
- [ ] Install netem: `sudo apt install iproute2`
- [ ] Create logs directory: `mkdir -p logs`
- [ ] Clear existing netem rules: `sudo tc qdisc del dev lo root 2>/dev/null`

**During Testing:**

- [ ] Start server first
- [ ] Apply netem rules before client
- [ ] Wait for test completion
- [ ] Clear netem rules after test
- [ ] Save console output
- [ ] Copy CSV files

**After Testing:**

- [ ] Verify CSV has expected number of rows
- [ ] Check RDT statistics match expectations
- [ ] Compare metrics against success criteria
- [ ] Generate graphs/charts if needed

---

### 6.10 Alternative Testing Tools

**If netem unavailable:**

1. **Clumsy (Windows):**

   - GUI tool for packet manipulation
   - Download: https://jagt.github.io/clumsy/
   - Can simulate loss, delay, duplication, reordering

2. **Network Link Conditioner (macOS):**

   - Built into Xcode
   - Limited compared to netem

3. **Python Simulation:**

   - Use client-side loss/jitter parameters:
     ```bash
     python3 client.py 1001 1 30 0.1 0.05 3 127.0.0.1
     #                               ^^^  ^^^^
     #                               10%  50ms jitter
     ```

4. **Docker Containers:**
   - Use tc inside containers
   - Isolate network testing

---

## Summary

**Testing time estimates:**

- Quick test (5 scenarios): ~3 minutes
- Comprehensive test (20 scenarios): ~15 minutes
- Full evaluation with analysis: ~30-45 minutes

**Key takeaway:** Automated scripts ensure reproducible results and comprehensive coverage of all network conditions.
