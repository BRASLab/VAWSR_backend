import struct
from io import BytesIO

def byte2wav(b: BytesIO):
    _b = b.getvalue()
    chunk_size = struct.pack('<I', len(_b) + 44 - 8)
    subchunk_size = struct.pack('<I', len(_b))

    chunk_descriptor =  b'RIFF' + chunk_size + b'WAVE'
    # detail: http://soundfile.sapp.org/doc/WaveFormat
    # channel:1 samplerate:16000
    fmt_subchunk = bytes.fromhex('666d74201000000001000100803e0000007d000002001000')
    data_subchunk = b'data' + subchunk_size + _b

    return BytesIO(chunk_descriptor + fmt_subchunk + data_subchunk)
