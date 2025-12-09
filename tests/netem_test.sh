#!/bin/bash
#
# TinyTelemetry Protocol - Network Impairment Test Script using netem
# This script uses Linux Traffic Control (tc) with netem to simulate network conditions
#
# REQUIREMENTS:
#   - Linux with root/sudo access
#   - iproute2 package (tc command)
#   - Run this on the SERVER machine (receiver)
#
# Usage: sudo ./netem_test.sh <scenario> [interface]
#   Scenarios: baseline, loss5, loss10, delay50, delay100, jitter, reorder, combined
#   Interface: network interface (default: eth0, use 'lo' for localhost testing)
#

set -e

# Configuration
INTERFACE="${2:-eth0}"  # Default interface, change to lo for localhost
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOGS_DIR="$SCRIPT_DIR/../logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}========================================${NC}"
}

print_warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

print_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (sudo)"
        exit 1
    fi
}

# Clear any existing netem rules
clear_netem() {
    echo "[INFO] Clearing existing netem rules on $INTERFACE..."
    tc qdisc del dev $INTERFACE root 2>/dev/null || true
}

# Apply netem rules based on scenario
apply_netem() {
    local scenario=$1
    
    case $scenario in
        baseline)
            echo "[INFO] Baseline test - no impairment"
            # No netem rules, clean network
            ;;
        
        loss5)
            echo "[INFO] Applying 5% packet loss..."
            tc qdisc add dev $INTERFACE root netem loss 5%
            ;;
        
        loss10)
            echo "[INFO] Applying 10% packet loss..."
            tc qdisc add dev $INTERFACE root netem loss 10%
            ;;
        
        loss15)
            echo "[INFO] Applying 15% packet loss..."
            tc qdisc add dev $INTERFACE root netem loss 15%
            ;;
        
        delay50)
            echo "[INFO] Applying 50ms delay..."
            tc qdisc add dev $INTERFACE root netem delay 50ms
            ;;
        
        delay100)
            echo "[INFO] Applying 100ms delay..."
            tc qdisc add dev $INTERFACE root netem delay 100ms
            ;;
        
        delay200)
            echo "[INFO] Applying 200ms delay..."
            tc qdisc add dev $INTERFACE root netem delay 200ms
            ;;
        
        jitter)
            echo "[INFO] Applying 50ms delay with 25ms jitter (normal distribution)..."
            tc qdisc add dev $INTERFACE root netem delay 50ms 25ms distribution normal
            ;;
        
        jitter_high)
            echo "[INFO] Applying 100ms delay with 10ms jitter..."
            tc qdisc add dev $INTERFACE root netem delay 100ms 10ms distribution normal
            ;;
        
        reorder)
            echo "[INFO] Applying packet reordering (25% reorder, 50% correlation)..."
            tc qdisc add dev $INTERFACE root netem delay 10ms reorder 25% 50%
            ;;
        
        reorder_high)
            echo "[INFO] Applying high packet reordering (50% reorder)..."
            tc qdisc add dev $INTERFACE root netem delay 20ms reorder 50% 25%
            ;;
        
        duplicate)
            echo "[INFO] Applying 5% packet duplication..."
            tc qdisc add dev $INTERFACE root netem duplicate 5%
            ;;
        
        combined)
            echo "[INFO] Applying combined impairment (5% loss, 50ms delay, 25ms jitter, 10% reorder)..."
            tc qdisc add dev $INTERFACE root netem loss 5% delay 50ms 25ms reorder 10% 25%
            ;;
        
        combined_harsh)
            echo "[INFO] Applying harsh combined impairment (10% loss, 100ms delay, 50ms jitter, 25% reorder)..."
            tc qdisc add dev $INTERFACE root netem loss 10% delay 100ms 50ms reorder 25% 50%
            ;;
        
        *)
            print_error "Unknown scenario: $scenario"
            echo "Available scenarios:"
            echo "  baseline     - No impairment (clean network)"
            echo "  loss5        - 5% packet loss"
            echo "  loss10       - 10% packet loss"
            echo "  loss15       - 15% packet loss"
            echo "  delay50      - 50ms delay"
            echo "  delay100     - 100ms delay"
            echo "  delay200     - 200ms delay"
            echo "  jitter       - 50ms delay with 25ms jitter"
            echo "  jitter_high  - 100ms delay with 50ms jitter"
            echo "  reorder      - 25% packet reordering"
            echo "  reorder_high - 50% packet reordering"
            echo "  duplicate    - 5% packet duplication"
            echo "  combined     - 5% loss + 50ms delay + jitter + 10% reorder"
            echo "  combined_harsh - 10% loss + 100ms delay + jitter + 25% reorder"
            exit 1
            ;;
    esac
}

# Show current netem status
show_status() {
    echo ""
    echo "[INFO] Current tc qdisc status on $INTERFACE:"
    tc qdisc show dev $INTERFACE
    echo ""
}

# Run a test with the server
run_test() {
    local scenario=$1
    local duration=${3:-60}
    
    print_header "Running test: $scenario"
    
    # Create logs directory
    mkdir -p "$LOGS_DIR/netem_${scenario}_${TIMESTAMP}"
    local LOG_DIR="$LOGS_DIR/netem_${scenario}_${TIMESTAMP}"
    
    # Clear and apply netem
    clear_netem
    apply_netem $scenario
    show_status
    
    echo "[INFO] Test will run for ${duration} seconds"
    echo "[INFO] Logs will be saved to: $LOG_DIR"
    echo ""
    echo "[INSTRUCTIONS]"
    echo "  1. Start the server on this machine:"
    echo "     cd $SCRIPT_DIR/../src && python3 server.py"
    echo ""
    echo "  2. In another terminal, start the client:"
    echo "     cd $SCRIPT_DIR/../src && python3 client.py 1001 1 $duration 0 0 0 <server_ip>"
    echo ""
    echo "  3. Wait for the test to complete, then press Ctrl+C on the server"
    echo ""
    echo "Press Enter when ready to start the server automatically, or Ctrl+C to cancel..."
    read
    
    # Start server in background
    cd "$SCRIPT_DIR/../src"
    python3 server.py > "$LOG_DIR/server.log" 2>&1 &
    SERVER_PID=$!
    echo "[INFO] Server started with PID: $SERVER_PID"
    echo "[INFO] Server log: $LOG_DIR/server.log"
    echo ""
    echo "Now start the client on the OTHER machine. Press Enter when client is done..."
    read
    
    # Stop server
    kill $SERVER_PID 2>/dev/null || true
    
    # Clear netem rules
    clear_netem
    
    # Copy CSV file to logs
    mv "$SCRIPT_DIR/../src"/telemetry_*.csv "$LOG_DIR/" 2>/dev/null || true
    
    echo ""
    print_header "Test Complete: $scenario"
    echo "[INFO] Results saved to: $LOG_DIR"
    echo ""
}

# Main
main() {
    local scenario="${1:-help}"
    
    if [ "$scenario" == "help" ] || [ "$scenario" == "-h" ] || [ "$scenario" == "--help" ]; then
        echo "TinyTelemetry netem Test Script"
        echo ""
        echo "Usage: sudo $0 <command> [interface]"
        echo ""
        echo "Commands:"
        echo "  apply <scenario>  - Apply a netem scenario"
        echo "  clear             - Clear all netem rules"
        echo "  status            - Show current netem status"
        echo "  test <scenario>   - Run a full test with server"
        echo "  help              - Show this help"
        echo ""
        echo "Examples:"
        echo "  sudo $0 apply loss5 eth0     # Apply 5% loss on eth0"
        echo "  sudo $0 apply jitter lo      # Apply jitter on localhost"
        echo "  sudo $0 clear eth0           # Clear rules on eth0"
        echo "  sudo $0 test combined eth0   # Run combined test"
        exit 0
    fi
    
    check_root
    
    case $scenario in
        apply)
            apply_netem "$2"
            show_status
            ;;
        clear)
            clear_netem
            echo "[INFO] All netem rules cleared on $INTERFACE"
            ;;
        status)
            show_status
            ;;
        test)
            run_test "$2" "$INTERFACE"
            ;;
        *)
            # Assume it's a scenario name, apply it
            apply_netem "$scenario"
            show_status
            ;;
    esac
}

main "$@"
