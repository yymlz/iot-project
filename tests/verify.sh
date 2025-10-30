#!/bin/bash

# Quick verification script - tests protocol module and basic functionality
# Run this before recording demo video

echo "========================================="
echo "TinyTelemetry Quick Verification"
echo "========================================="
echo ""

cd "$(dirname "$0")/../src" || exit 1

echo "1. Testing protocol module..."
python3 -c "
import protocol
print('   ✓ Protocol module imports successfully')

# Test header packing
header = protocol.TinyTelemetryProtocol.pack_header(
    msg_type=protocol.MSG_INIT,
    device_id=1001,
    seq_num=0
)
print(f'   ✓ Header packing works: {len(header)} bytes')

# Test header unpacking
parsed = protocol.TinyTelemetryProtocol.unpack_header(header)
print(f'   ✓ Header unpacking works: device_id={parsed[\"device_id\"]}, seq={parsed[\"seq_num\"]}')

# Test message creation
msg = protocol.TinyTelemetryProtocol.create_message(
    msg_type=protocol.MSG_DATA,
    device_id=1001,
    seq_num=1,
    payload=b'{\"temp\":23.5}'
)
print(f'   ✓ Message creation works: {len(msg)} bytes total')
print('')
"

if [ $? -ne 0 ]; then
    echo "❌ Protocol module test failed!"
    exit 1
fi

echo "2. Testing server script syntax..."
python3 -m py_compile server.py
if [ $? -eq 0 ]; then
    echo "   ✓ server.py syntax OK"
else
    echo "   ❌ server.py has syntax errors"
    exit 1
fi

echo ""
echo "3. Testing client script syntax..."
python3 -m py_compile client.py
if [ $? -eq 0 ]; then
    echo "   ✓ client.py syntax OK"
else
    echo "   ❌ client.py has syntax errors"
    exit 1
fi

echo ""
echo "========================================="
echo "All checks passed! ✅"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Run server: cd src && python3 server.py"
echo "2. Run client: cd src && python3 client.py"
echo "3. Run baseline test: cd tests && ./baseline_test.sh"
echo ""
