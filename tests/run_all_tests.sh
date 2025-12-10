#!/bin/bash
#
# TinyTelemetry Protocol - Comprehensive Test Suite
# This script runs all network impairment tests automatically
#
# Usage: sudo ./run_all_tests.sh [interface]
#   interface: network interface (default: lo for localhost)
#

set -e

# Configuration
INTERFACE="${1:-lo}"
SERVER_DIR="../src"
LOG_DIR="../logs"
RESULTS_FILE="$LOG_DIR/test_results_$(date +%Y%m%d_%H%M%S).txt"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root (sudo)${NC}"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Clear any existing netem rules
clear_netem() {
    tc qdisc del dev "$INTERFACE" root 2>/dev/null || true
    echo -e "${GREEN}Cleared netem rules on $INTERFACE${NC}"
}

# Print header
print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Run a test
run_test() {
    local test_name="$1"
    local device_id="$2"
    local duration="$3"
    local loss="$4"
    local jitter="$5"
    local batch_size="$6"
    local netem_cmd="$7"
    
    print_header "TEST: $test_name"
    
    # Apply netem rule
    if [ -n "$netem_cmd" ]; then
        echo -e "${YELLOW}Applying netem: $netem_cmd${NC}"
        eval "tc qdisc add dev $INTERFACE root netem $netem_cmd"
    else
        echo -e "${YELLOW}No network impairment (baseline)${NC}"
    fi
    
    # Show current qdisc
    echo "Current qdisc:"
    tc qdisc show dev "$INTERFACE"
    echo ""
    
    # Run client
    echo -e "${GREEN}Running client (Device $device_id, Duration ${duration}s, Batch $batch_size)...${NC}"
    cd "$SERVER_DIR"
    python3 client.py "$device_id" 1 "$duration" "$loss" "$jitter" "$batch_size" 127.0.0.1
    
    # Clear netem
    clear_netem
    
    # Wait between tests
    echo -e "${GREEN}Test complete. Waiting 3 seconds...${NC}"
    sleep 3
}

# Main test suite
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     TinyTelemetry Comprehensive Test Suite                ║${NC}"
echo -e "${BLUE}║     Interface: $INTERFACE                                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}IMPORTANT: Make sure the server is running in another terminal!${NC}"
echo -e "${YELLOW}Command: python3 src/server.py${NC}"
echo ""
read -p "Press Enter to start tests (or Ctrl+C to cancel)..."

# Start logging
{
    echo "TinyTelemetry Test Suite Results"
    echo "Date: $(date)"
    echo "Interface: $INTERFACE"
    echo "=========================================="
    echo ""
} > "$RESULTS_FILE"

# Clear any existing rules
clear_netem

# TEST 1: Baseline (no impairment)
run_test "Baseline - No Impairment" 1001 30 0 0 3 ""

# TEST 2: Packet Loss Tests
run_test "Packet Loss 5%" 1002 30 0 0 3 "loss 5%"
run_test "Packet Loss 10%" 1003 30 0 0 3 "loss 10%"
run_test "Packet Loss 15%" 1004 30 0 0 3 "loss 15%"

# TEST 3: Delay Tests
run_test "Delay 50ms" 1005 30 0 0 3 "delay 50ms"
run_test "Delay 100ms" 1006 30 0 0 3 "delay 100ms"
run_test "Delay 200ms" 1007 30 0 0 3 "delay 200ms"

# TEST 4: Jitter Tests
run_test "Jitter (100ms ± 20ms)" 1008 30 0 0 3 "delay 100ms 20ms"
run_test "Jitter (100ms ± 50ms)" 1009 30 0 0 3 "delay 100ms 50ms"

# TEST 5: Packet Reordering
run_test "Reordering 25%" 1010 30 0 0 3 "delay 10ms reorder 25% 50%"
run_test "Reordering 50%" 1011 30 0 0 3 "delay 10ms reorder 50% 50%"

# TEST 6: Packet Duplication
run_test "Duplication 5%" 1012 30 0 0 3 "duplicate 5%"

# TEST 7: Combined Impairments
run_test "Combined Light (5% loss + 50ms delay)" 1013 30 0 0 3 "loss 5% delay 50ms"
run_test "Combined Medium (10% loss + 100ms delay + jitter)" 1014 30 0 0 3 "loss 10% delay 100ms 20ms"
run_test "Combined Harsh (15% loss + 200ms + reorder)" 1015 30 0 0 3 "loss 15% delay 200ms reorder 25% 50%"

# TEST 8: Batch Size Tests (with 10% loss)
run_test "Batch Size 1 (10% loss)" 1016 30 0 0 1 "loss 10%"
run_test "Batch Size 5 (10% loss)" 1017 30 0 0 5 "loss 10%"
run_test "Batch Size 10 (10% loss)" 1018 30 0 0 10 "loss 10%"

# TEST 9: Client-side Loss + Network Loss
run_test "Client Loss 5% + Network Loss 5%" 1019 30 0.05 0 3 "loss 5%"

# TEST 10: Client-side Jitter + Network Delay
run_test "Client Jitter 0.1s + Network Delay 100ms" 1020 30 0 0.1 3 "delay 100ms"

# Final cleanup
clear_netem

# Summary
print_header "TEST SUITE COMPLETE"
echo -e "${GREEN}All tests completed successfully!${NC}"
echo -e "${YELLOW}Results logged to: $RESULTS_FILE${NC}"
echo ""
echo -e "${BLUE}Check the server output for detailed metrics including:${NC}"
echo "  - packets_received"
echo "  - bytes_per_report"
echo "  - duplicate_rate"
echo "  - sequence_gap_count"
echo "  - cpu_ms_per_report"
echo "  - packet_loss_rate"
echo ""
echo -e "${BLUE}Check CSV files in logs/ directory for detailed data${NC}"
echo ""
