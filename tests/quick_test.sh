#!/bin/bash
#
# TinyTelemetry - Quick Test Script (Essential Tests Only)
# Runs 5 key tests in ~3 minutes
#
# Usage: sudo ./quick_test.sh [interface]
#

INTERFACE="${1:-lo}"

echo "════════════════════════════════════════════════════════"
echo "TinyTelemetry Quick Test Suite"
echo "Interface: $INTERFACE"
echo "════════════════════════════════════════════════════════"
echo ""
echo "IMPORTANT: Make sure server is running!"
echo "  Terminal 1: cd src && python3 server.py"
echo ""
read -p "Press Enter to start tests..."

# Clear existing rules
sudo tc qdisc del dev "$INTERFACE" root 2>/dev/null || true

cd ../src

# Test 1: Baseline
echo ""
echo "=== Test 1/5: Baseline (No Impairment) ==="
python3 client.py 2001 1 20 0 0 3 127.0.0.1
sleep 2

# Test 2: Packet Loss
echo ""
echo "=== Test 2/5: Packet Loss 10% ==="
sudo tc qdisc add dev "$INTERFACE" root netem loss 10%
python3 client.py 2002 1 20 0 0 3 127.0.0.1
sudo tc qdisc del dev "$INTERFACE" root
sleep 2

# Test 3: Delay + Jitter
echo ""
echo "=== Test 3/5: Delay 100ms + Jitter ±20ms ==="
sudo tc qdisc add dev "$INTERFACE" root netem delay 100ms 20ms
python3 client.py 2003 1 20 0 0 3 127.0.0.1
sudo tc qdisc del dev "$INTERFACE" root
sleep 2

# Test 4: Packet Reordering
echo ""
echo "=== Test 4/5: Packet Reordering ==="
sudo tc qdisc add dev "$INTERFACE" root netem delay 10ms reorder 25% 50%
python3 client.py 2004 1 20 0 0 3 127.0.0.1
sudo tc qdisc del dev "$INTERFACE" root
sleep 2

# Test 5: Combined (Loss + Delay + Reorder)
echo ""
echo "=== Test 5/5: Combined Impairments ==="
sudo tc qdisc add dev "$INTERFACE" root netem loss 10% delay 100ms reorder 25% 50%
python3 client.py 2005 1 20 0 0 3 127.0.0.1
sudo tc qdisc del dev "$INTERFACE" root

echo ""
echo "════════════════════════════════════════════════════════"
echo "Quick test suite complete!"
echo "Check server output for metrics and logs/ for CSV files"
echo "════════════════════════════════════════════════════════"
