#!/bin/bash

# Demo helper script - Run this to quickly test the system
# Perfect for showing during video recording

echo "╔════════════════════════════════════════════╗"
echo "║   TinyTelemetry Protocol v1 Demo          ║"
echo "║   Phase 1 - INIT + DATA Exchange          ║"
echo "╚════════════════════════════════════════════╝"
echo ""
echo "This demo will:"
echo "  1. Start the server (collector)"
echo "  2. Wait 2 seconds"
echo "  3. Start the client (sensor) for 10 seconds"
echo "  4. Show the results"
echo ""
read -p "Press ENTER to start..."
echo ""

cd "$(dirname "$0")/../src" || exit 1

echo "Starting server in background..."
python3 server.py > /tmp/tinytelemetry_demo_server.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"
echo ""

sleep 2

echo "Starting client (will run for 10 seconds)..."
echo "════════════════════════════════════════════"
echo ""

# Run client for just 10 seconds to keep demo short
python3 client.py 1001 1 10

echo ""
echo "════════════════════════════════════════════"
echo "Client finished. Stopping server..."
sleep 1

kill -INT $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null

echo ""
echo "════════════════════════════════════════════"
echo "Server Output:"
echo "════════════════════════════════════════════"
cat /tmp/tinytelemetry_demo_server.log
echo ""

echo "════════════════════════════════════════════"
echo "Demo complete!"
echo ""
echo "You should see:"
echo "  ✓ 1 INIT message (seq 0)"
echo "  ✓ ~10 DATA messages (seq 1-10)"
echo "  ✓ No errors or gaps"
echo "════════════════════════════════════════════"
echo ""
