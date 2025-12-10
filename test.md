wsl
cd /mnt/d/iot-project/tests

# Make executable
chmod +x netem_test.sh

# Test each scenario (use 'lo' for localhost testing):

# 1. Baseline (no impairment)
sudo ./netem_test.sh test baseline lo

# 2. Packet Loss Tests
sudo ./netem_test.sh test loss5 lo
sudo ./netem_test.sh test loss10 lo
sudo ./netem_test.sh test loss15 lo

# 3. Delay Tests
sudo ./netem_test.sh test delay50 lo
sudo ./netem_test.sh test delay100 lo
sudo ./netem_test.sh test delay200 lo

# 4. Jitter Tests
sudo ./netem_test.sh test jitter lo
sudo ./netem_test.sh test jitter_high lo

# 5. Reordering Tests
sudo ./netem_test.sh test reorder lo
sudo ./netem_test.sh test reorder_high lo

# 6. Duplication Test
sudo ./netem_test.sh test duplicate lo

# 7. Combined Tests
sudo ./netem_test.sh test combined lo
sudo ./netem_test.sh test combined_harsh lo


wsl
cd /mnt/d/iot-project

# Terminal 2 - Apply impairment
sudo tc qdisc add dev lo root netem loss 10%

# Terminal 3 - Run client
python3 src/client.py 1001 1 60 0 0 5 127.0.0.1

# Check status
tc qdisc show dev lo

# Clear when done
sudo tc qdisc del dev lo root

# Terminal 1: Server
cd /mnt/d/iot-project/src
python3 server.py

# Terminal 2: Client tests
cd /mnt/d/iot-project/src

# Test 1: See timeout adapt to localhost (should go down to ~200-300ms)
python3 client.py 1001 1 30 0 0 3 127.0.0.1

# Test 2: See timeout adapt to network delay
sudo tc qdisc add dev lo root netem delay 100ms
python3 client.py 1002 1 30 0 0 3 127.0.0.1
# Expected: timeout adapts to ~500-800ms
sudo tc qdisc del dev lo root

# Test 3: See retransmission in action
sudo tc qdisc add dev lo root netem loss 10%
python3 client.py 1003 1 30 0 0 3 127.0.0.1
# Expected: retransmissions > 0, but all packets eventually delivered
sudo tc qdisc del dev lo root

# showing wireshark result
sudo tcpdump -i lo -w /mnt/d/iot-project/logs/capture_$(date +%Y%m%d_%H%M%S).pcap port 5000
wireshark /mnt/d/iot-project/logs/capture_*.pcap

# test all 
cd /mnt/d/iot-project/tests && sudo bash run_all_tests.sh