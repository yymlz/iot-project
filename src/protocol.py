import struct
import time

# Protocol constants
PROTOCOL_VERSION = 1
HEADER_SIZE = 10  # bytes

# Message types
MSG_INIT = 0
MSG_DATA = 1
MSG_HEARTBEAT = 2
MSG_BATCH = 3
MSG_ACK = 4

class TinyTelemetryProtocol:

    @staticmethod
    def pack_header(msg_type, device_id, seq_num, timestamp=None, flags=0):
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
        header = TinyTelemetryProtocol.pack_header(
            msg_type, device_id, seq_num, timestamp, flags
        )
        return header + payload

    @staticmethod
    def parse_message(data):
        header = TinyTelemetryProtocol.unpack_header(data)
        payload = data[HEADER_SIZE:]
        return header, payload

    @staticmethod
    def msg_type_to_string(msg_type):
        """Convert message type code to string"""
        types = {MSG_INIT: 'INIT', MSG_DATA: 'DATA', MSG_HEARTBEAT: 'HEARTBEAT', MSG_BATCH: 'BATCH', MSG_ACK: 'ACK'}
        return types.get(msg_type, f'UNKNOWN({msg_type})')
