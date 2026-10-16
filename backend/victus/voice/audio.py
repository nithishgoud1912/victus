"""PCM conversion/resampling without an audio device or model dependency."""

import math
import struct
from array import array


def pcm16_mono(data: bytes, channels: int = 1) -> array:
    if channels not in (1, 2) or len(data) % (2 * channels):
        raise ValueError("Invalid PCM frame")
    samples = [v[0] for v in struct.iter_unpack("<h", data)]
    if channels == 2:
        samples = [round((samples[i] + samples[i + 1]) / 2) for i in range(0, len(samples), 2)]
    return array("h", samples)


def float32_to_pcm16(values) -> bytes:
    samples = []
    for value in values:
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("Non-finite audio sample")
        samples.append(round(max(-1.0, min(1.0, value)) * 32767))
    return b"".join(struct.pack("<h", value) for value in samples)


def resample_pcm16(
    data: bytes, source_rate: int, target_rate: int = 16000, channels: int = 1
) -> bytes:
    if not 8000 <= source_rate <= 192000 or not 8000 <= target_rate <= 192000:
        raise ValueError("Unsupported sample rate")
    samples = pcm16_mono(data, channels)
    if source_rate == target_rate and channels == 1:
        return data
    if not samples:
        return b""
    count = round(len(samples) * target_rate / source_rate)
    output = bytearray()
    for i in range(count):
        position = min(i * source_rate / target_rate, len(samples) - 1)
        left = int(position)
        right = min(left + 1, len(samples) - 1)
        value = round(samples[left] + (samples[right] - samples[left]) * (position - left))
        output.extend(struct.pack("<h", value))
    return bytes(output)


def rms(data: bytes) -> float:
    samples = pcm16_mono(data)
    return math.sqrt(sum(float(x) ** 2 for x in samples) / len(samples)) / 32768 if samples else 0
