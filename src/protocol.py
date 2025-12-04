"""
TinyTelemetry Protocol v1
Compact IoT telemetry protocol for sensor reporting over UDP
"""

import struct
import time

# Protocol constants
PROTOCOL_VERSION = 1
HEADER_SIZE = 10  # bytes

# Message types
MSG_INIT = 0
MSG_DATA = 1
MSG_HEARTBEAT = 2

class TinyTelemetryProtocol:
    """
    Header Format (10 bytes):
    +---------+---------+----------+--------+-----------+-------+
    | Ver+Msg | DeviceID| SeqNum   | Timestamp          | Flags |
    | (1B)    | (2B)    | (2B)     | (4B)               | (1B)  |
    +---------+---------+----------+--------+-----------+-------+

    Field breakdown:
    - Version (4 bits) + MsgType (4 bits) = 1 byte
    - DeviceID: 16 bits = 2 bytes
    - SeqNum: 16 bits = 2 bytes
    - Timestamp: 32 bits = 4 bytes (Unix epoch seconds)
    - Flags: 8 bits = 1 byte (reserved for future use)

    Pack format: '!BHHIB'
    ! = network byte order (big-endian)
    B = unsigned char (1 byte)
    H = unsigned short (2 bytes)
    I = unsigned int (4 bytes)
    """

    @staticmethod
    def pack_header(msg_type, device_id, seq_num, timestamp=None, flags=0):
        """
        Pack protocol header into bytes

        Args:
            msg_type: Message type (MSG_INIT, MSG_DATA, MSG_HEARTBEAT)
            device_id: Unique device identifier (0-65535)
            seq_num: Sequence number (0-65535)
            timestamp: Unix timestamp (auto-generated if None)
            flags: Optional flags byte (default 0)

        Returns:
            bytes: 10-byte packed header
        """
        if timestamp is None:
            timestamp = int(time.time())

        # Combine version (4 bits) and msg_type (4 bits) into 1 byte
        version_and_type = (PROTOCOL_VERSION << 4) | (msg_type & 0x0F)

        # Pack: version+type, device_id, seq_num, timestamp, flags
        header = struct.pack('!BHHIB',
                           version_and_type,
                           device_id,
                           seq_num,
                           timestamp,
                           flags)
        return header

    @staticmethod
    def unpack_header(data):
        """
        Unpack protocol header from bytes

        Args:
            data: bytes containing at least 10-byte header

        Returns:
            dict: Parsed header fields
        """
        if len(data) < HEADER_SIZE:
            raise ValueError(f"Data too short: {len(data)} bytes, need {HEADER_SIZE}")

        # Unpack header
        version_and_type, device_id, seq_num, timestamp, flags = struct.unpack(
            '!BHHIB', data[:HEADER_SIZE]
        )

        # Extract version and msg_type
        version = (version_and_type >> 4) & 0x0F
        msg_type = version_and_type & 0x0F

        return {
            'version': version,
            'msg_type': msg_type,
            'device_id': device_id,
            'seq_num': seq_num,
            'timestamp': timestamp,
            'flags': flags
        }

    @staticmethod
    def create_message(msg_type, device_id, seq_num, payload=b'', timestamp=None, flags=0):
        """
        Create a complete protocol message (header + payload)

        Args:
            msg_type: Message type
            device_id: Device ID
            seq_num: Sequence number
            payload: Message payload (bytes)
            timestamp: Unix timestamp
            flags: Flags byte

        Returns:
            bytes: Complete message
        """
        header = TinyTelemetryProtocol.pack_header(
            msg_type, device_id, seq_num, timestamp, flags
        )
        return header + payload

    @staticmethod
    def parse_message(data):
        """
        Parse a complete protocol message

        Args:
            data: bytes containing message

        Returns:
            tuple: (header_dict, payload_bytes)
        """
        header = TinyTelemetryProtocol.unpack_header(data)
        payload = data[HEADER_SIZE:]
        return header, payload

    @staticmethod
    def msg_type_to_string(msg_type):
        """Convert message type code to string"""
        types = {MSG_INIT: 'INIT', MSG_DATA: 'DATA', MSG_HEARTBEAT: 'HEARTBEAT'}
        return types.get(msg_type, f'UNKNOWN({msg_type})')
