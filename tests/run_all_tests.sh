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
RESULTS_FILE="$LOG_DIR/test_results_$(date +%Y%m%d_%H%M%S).csv"

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
    local interval="${8:-1}"  # Default to 1s if not specified
    
    print_header "TEST: $test_name"
    
    # Apply netem rule
    if [ -n "$netem_cmd" ]; then
        echo -e "${YELLOW}Applying netem: $netem_cmd${NC}"
        eval "tc qdisc add dev $INTERFACE root netem $netem_cmd"
    else
        echo -e "${YELLOW}No network impairment (baseline)${NC}"
        netem_cmd="none"
    fi
    
    # Show current qdisc
    echo "Current qdisc:"
    tc qdisc show dev "$INTERFACE"
    echo ""
    
    # Run client
    echo -e "${GREEN}Running client (Device $device_id, Duration ${duration}s, Interval ${interval}s, Batch $batch_size)...${NC}"
    cd "$SERVER_DIR"
    python3 client.py "$device_id" "$interval" "$duration" "$loss" "$jitter" "$batch_size" 127.0.0.1
    
    # Log to CSV
    echo "\"$test_name\",$device_id,$duration,$batch_size,\"$netem_cmd\",\"$(date '+%Y-%m-%d %H:%M:%S')\"" >> "$RESULTS_FILE"
    
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

# Start logging with CSV header
{
    echo "test_name,device_id,duration,batch_size,netem_config,timestamp"
} > "$RESULTS_FILE"

# Clear any existing rules
clear_netem

# TEST 1: Baseline (no impairment) - Different intervals
run_test "Baseline - No Impairment (1s)" 1001 60 0 0 1 ""
run_test "Baseline - No Impairment (5s)" 1002 60 0 0 5 ""
run_test "Baseline - No Impairment (30s)" 1003 60 0 0 30 ""

# TEST 2: Packet Loss Tests (1s, 5s, 30s intervals)
run_test "Packet Loss 5% (1s)" 1004 60 0 0 1 "loss 5%"
run_test "Packet Loss 5% (5s)" 1005 60 0 0 5 "loss 5%"
run_test "Packet Loss 5% (30s)" 1006 60 0 0 30 "loss 5%"
run_test "Packet Loss 10% (1s)" 1007 60 0 0 1 "loss 10%"
run_test "Packet Loss 10% (5s)" 1008 60 0 0 5 "loss 10%"
run_test "Packet Loss 10% (30s)" 1009 60 0 0 30 "loss 10%"
run_test "Packet Loss 15% (1s)" 1010 60 0 0 1 "loss 15%"
run_test "Packet Loss 15% (5s)" 1011 60 0 0 5 "loss 15%"
run_test "Packet Loss 15% (30s)" 1012 60 0 0 30 "loss 15%"

# # TEST 3: Delay Tests (1s, 5s, 30s)
# run_test "Delay 50ms (1s)" 1013 1 0 0 3 "delay 50ms"
# run_test "Delay 50ms (5s)" 1014 5 0 0 3 "delay 50ms"
# run_test "Delay 50ms (30s)" 1015 30 0 0 3 "delay 50ms"
# run_test "Delay 100ms (1s)" 1016 1 0 0 3 "delay 100ms"
# run_test "Delay 100ms (5s)" 1017 5 0 0 3 "delay 100ms"
# run_test "Delay 100ms (30s)" 1018 30 0 0 3 "delay 100ms"
# run_test "Delay 200ms (1s)" 1019 1 0 0 3 "delay 200ms"
# run_test "Delay 200ms (5s)" 1020 5 0 0 3 "delay 200ms"
# run_test "Delay 200ms (30s)" 1021 30 0 0 3 "delay 200ms"

# TEST 4: Jitter Tests (1s, 5s, 30s intervals)
run_test "Jitter (100ms ± 10ms) (1s)" 1022 60 0 0 1 "delay 100ms 10ms"
run_test "Jitter (100ms ± 10ms) (5s)" 1023 60 0 0 5 "delay 100ms 10ms"
run_test "Jitter (100ms ± 10ms) (30s)" 1024 60 0 0 30 "delay 100ms 10ms"
# run_test "Jitter (100ms ± 50ms) (1s)" 1025 60 0 0 1 "delay 100ms 50ms"
# run_test "Jitter (100ms ± 50ms) (5s)" 1026 60 0 0 5 "delay 100ms 50ms"
# run_test "Jitter (100ms ± 50ms) (30s)" 1027 60 0 0 30 "delay 100ms 50ms"

# # TEST 5: Packet Reordering (1s, 5s, 30s)
# run_test "Reordering 25% (1s)" 1028 1 0 0 3 "delay 10ms reorder 25% 50%"
# run_test "Reordering 25% (5s)" 1029 5 0 0 3 "delay 10ms reorder 25% 50%"
# run_test "Reordering 25% (30s)" 1030 30 0 0 3 "delay 10ms reorder 25% 50%"
# run_test "Reordering 50% (1s)" 1031 1 0 0 3 "delay 10ms reorder 50% 50%"
# run_test "Reordering 50% (5s)" 1032 5 0 0 3 "delay 10ms reorder 50% 50%"
# run_test "Reordering 50% (30s)" 1033 30 0 0 3 "delay 10ms reorder 50% 50%"

# TEST 6: Packet Duplication (1s, 5s, 30s intervals)
run_test "Duplication 5% (1s)" 1034 60 0 0 1 "duplicate 5%"
run_test "Duplication 5% (5s)" 1035 60 0 0 5 "duplicate 5%"
run_test "Duplication 5% (30s)" 1036 60 0 0 30 "duplicate 5%"

# TEST 7: Combined Impairments (1s, 5s, 30s intervals)
run_test "Combined Light (5% loss + 50ms delay) (1s)" 1037 60 0 0 1 "loss 5% delay 50ms"
run_test "Combined Light (5% loss + 50ms delay) (5s)" 1038 60 0 0 5 "loss 5% delay 50ms"
run_test "Combined Light (5% loss + 50ms delay) (30s)" 1039 60 0 0 30 "loss 5% delay 50ms"
run_test "Combined Medium (10% loss + 100ms delay + jitter) (1s)" 1040 60 0 0 1 "loss 10% delay 100ms 10ms"
run_test "Combined Medium (10% loss + 100ms delay + jitter) (5s)" 1041 60 0 0 5 "loss 10% delay 100ms 10ms"
run_test "Combined Medium (10% loss + 100ms delay + jitter) (30s)" 1042 60 0 0 30 "loss 10% delay 100ms 10ms"
run_test "Combined Harsh (15% loss + 200ms + reorder) (1s)" 1043 60 0 0 1 "loss 15% delay 200ms reorder 25% 50%"
run_test "Combined Harsh (15% loss + 200ms + reorder) (5s)" 1044 60 0 0 5 "loss 15% delay 200ms reorder 25% 50%"
run_test "Combined Harsh (15% loss + 200ms + reorder) (30s)" 1045 60 0 0 30 "loss 15% delay 200ms reorder 25% 50%"

# # TEST 8: Batch Size Tests (with 10% loss) (1s, 5s, 30s)
# run_test "Batch Size 1 (10% loss) (1s)" 1046 1 0 0 1 "loss 10%"
# run_test "Batch Size 1 (10% loss) (5s)" 1047 5 0 0 1 "loss 10%"
# run_test "Batch Size 1 (10% loss) (30s)" 1048 30 0 0 1 "loss 10%"
# run_test "Batch Size 5 (10% loss) (1s)" 1049 1 0 0 5 "loss 10%"
# run_test "Batch Size 5 (10% loss) (5s)" 1050 5 0 0 5 "loss 10%"
# run_test "Batch Size 5 (10% loss) (30s)" 1051 30 0 0 5 "loss 10%"
# run_test "Batch Size 10 (10% loss) (1s)" 1052 1 0 0 10 "loss 10%"
# run_test "Batch Size 10 (10% loss) (5s)" 1053 5 0 0 10 "loss 10%"
# run_test "Batch Size 10 (10% loss) (30s)" 1054 30 0 0 10 "loss 10%"

# TEST 9: Client-side Loss + Network Loss (1s, 5s, 30s intervals)
run_test "Client Loss 5% + Network Loss 5% (1s)" 1055 60 0.05 0 1 "loss 5%"
run_test "Client Loss 5% + Network Loss 5% (5s)" 1056 60 0.05 0 5 "loss 5%"
run_test "Client Loss 5% + Network Loss 5% (30s)" 1057 60 0.05 0 30 "loss 5%"

# TEST 10: Client-side Jitter + Network Delay (1s, 5s, 30s intervals)
run_test "Client Jitter 0.1s + Network Delay 100ms (1s)" 1058 60 0 0.1 1 "delay 100ms"
run_test "Client Jitter 0.1s + Network Delay 100ms (5s)" 1059 60 0 0.1 5 "delay 100ms"
run_test "Client Jitter 0.1s + Network Delay 100ms (30s)" 1060 60 0 0.1 30 "delay 100ms"

# TEST 11: Heartbeat Tests (batch_size=0 sends only heartbeats, interval=12s)
run_test "Heartbeat Only - No Impairment" 1061 60 0 0 0 "" 12
run_test "Heartbeat Only - 5% Loss" 1062 60 0 0 0 "loss 5%" 12
run_test "Heartbeat Only - 10% Loss" 1063 60 0 0 0 "loss 10%" 12
run_test "Heartbeat Only - Network Delay 100ms" 1064 60 0 0 0 "delay 100ms" 12
run_test "Heartbeat Only - Combined (5% loss + 50ms delay)" 1065 60 0 0 0 "loss 5% delay 50ms" 12

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
