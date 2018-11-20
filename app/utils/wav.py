import struct
from io import BytesIO

def byte2wav(b: BytesIO, rate = 16000, channel = 1):
    _b = b.getvalue()
    chunk_size = struct.pack('<I', len(_b) + 44 - 8)
    subchunk_size = struct.pack('<I', len(_b))
    sample_rate = struct.pack('<I', rate)
    byte_rate = struct.pack('<I', rate * channel * 2)
    chunk_descriptor =  b'RIFF' + chunk_size + b'WAVE'
    channel = struct.pack('<H', channel)
    # detail: http://soundfile.sapp.org/doc/WaveFormat
    # channel:1 samplerate:16000
    fmt_subchunk = bytes.fromhex('666d7420100000000100')
    fmt_subchunk += channel
    fmt_subchunk += sample_rate
    fmt_subchunk += byte_rate
    fmt_subchunk += bytes.fromhex('02001000')
    
    data_subchunk = b'data' + subchunk_size + _b

    return BytesIO(chunk_descriptor + fmt_subchunk + data_subchunk)
