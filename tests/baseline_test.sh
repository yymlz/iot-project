#!/bin/bash

# TinyTelemetry Baseline Test Script
# Tests: Baseline (no impairment), 1s interval, 60s duration
# Acceptance: ≥99% of reports received, sequence numbers in order

echo "========================================"
echo "TinyTelemetry Baseline Test"
echo "========================================"
echo "Test parameters:"
echo "  - Interval: 1 second"
echo "  - Duration: 60 seconds"
echo "  - Expected packets: ~61 (1 INIT + 60 DATA)"
echo "========================================"
echo ""

# Configuration
DEVICE_ID=1001
INTERVAL=1
DURATION=60
SERVER_PORT=5000
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="../logs/baseline_$TIMESTAMP"

# Create log directory
mkdir -p "$LOG_DIR"

echo "[TEST] Creating log directory: $LOG_DIR"
echo ""

# Change to src directory
cd "$(dirname "$0")/../src" || exit 1

echo "[TEST] Starting server..."
# Start server in background and capture output
python3 server.py $SERVER_PORT > "$LOG_DIR/server.log" 2>&1 &
SERVER_PID=$!

# Wait for server to initialize
sleep 2

echo "[TEST] Server started (PID: $SERVER_PID)"
echo "[TEST] Starting client..."
echo ""

# Run client (this will run for 60 seconds)
python3 client.py $DEVICE_ID $INTERVAL $DURATION > "$LOG_DIR/client.log" 2>&1

echo ""
echo "[TEST] Client finished"
echo "[TEST] Waiting 2 seconds for final packets..."
sleep 2

echo "[TEST] Stopping server..."
# Stop server
kill -INT $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null

echo ""
echo "========================================"
echo "Test Results"
echo "========================================"

# Analyze results
echo ""
echo "Server log excerpt (first 20 lines):"
echo "--------------------------------------"
head -20 "$LOG_DIR/server.log"
echo ""
echo "..."
echo ""
echo "Server log excerpt (last 10 lines):"
echo "--------------------------------------"
tail -10 "$LOG_DIR/server.log"

echo ""
echo "========================================"
echo "Statistics:"
echo "========================================"

# Count received packets (excluding header lines and warnings)
TOTAL_PACKETS=$(grep -c "Device $DEVICE_ID" "$LOG_DIR/server.log" || echo "0")
INIT_PACKETS=$(grep -c "Type: INIT" "$LOG_DIR/server.log" || echo "0")
DATA_PACKETS=$(grep -c "Type: DATA" "$LOG_DIR/server.log" || echo "0")
DUPLICATE_COUNT=$(grep -c "\[DUPLICATE\]" "$LOG_DIR/server.log" || echo "0")
GAP_COUNT=$(grep -c "\[GAP\]" "$LOG_DIR/server.log" || echo "0")

echo "Total packets received: $TOTAL_PACKETS"
echo "  - INIT packets: $INIT_PACKETS"
echo "  - DATA packets: $DATA_PACKETS"
echo "Duplicates detected: $DUPLICATE_COUNT"
echo "Sequence gaps detected: $GAP_COUNT"
echo ""

# Calculate success rate (expected: 1 INIT + 60 DATA = 61 total)
EXPECTED=61
if [ $TOTAL_PACKETS -ge 60 ]; then
    SUCCESS_RATE=$(awk "BEGIN {printf \"%.1f\", ($TOTAL_PACKETS/$EXPECTED)*100}")
    echo "Success rate: $SUCCESS_RATE% (≥99% required)"

    if (( $(echo "$SUCCESS_RATE >= 99.0" | bc -l) )); then
        echo "✓ PASS: Baseline test criteria met"
        TEST_RESULT="PASS"
    else
        echo "✗ FAIL: Success rate below 99%"
        TEST_RESULT="FAIL"
    fi
else
    echo "✗ FAIL: Received $TOTAL_PACKETS packets, expected ~$EXPECTED"
    TEST_RESULT="FAIL"
fi

echo ""
echo "========================================"
echo "Logs saved to: $LOG_DIR"
echo "  - server.log: Server output"
echo "  - client.log: Client output"
echo "========================================"
echo ""
echo "Test Result: $TEST_RESULT"
echo ""

# Exit with appropriate code
if [ "$TEST_RESULT" = "PASS" ]; then
    exit 0
else
    exit 1
fi
