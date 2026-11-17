"""Audio between the phone call and the voice agent, over two virtual cables (no speaker, no microphone, no echo).

  caller -> Mac default output = call cable -> CableAudio.on_in  -> agent (16 kHz PCM)
  agent  -> CableAudio.on_out -> agent cable = Mac default input -> caller
"""
from __future__ import annotations

import queue
import threading
import time
import wave
from pathlib import Path

import numpy as np

DEV_RATE, AI_RATE = 48000, 16000      # the cables run at 48 kHz; the agent speaks and listens at 16 kHz PCM
BLOCK = DEV_RATE // 50                # 20 ms blocks keep the round trip short


def resample(x: np.ndarray, src: int, dst: int) -> np.ndarray:
    if src == dst or not len(x):
        return x.astype(np.float32)
    n = int(len(x) * dst / src)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


class RingGate:
    """Holds the agent's ears shut until someone picks up, so it never talks to the ring-back tone.
    Open after ~160 ms of sound that is not the 400-450 Hz ring tone."""

    def __init__(self, enabled: bool = True, blocks_needed: int = 8):
        self.open = not enabled
        self.blocks = 0
        self.needed = blocks_needed

    def feed(self, block: np.ndarray) -> bool:
        if self.open:
            return True
        if np.sqrt(np.mean(block ** 2)) > 0.001:
            spec = np.abs(np.fft.rfft(block)) ** 2
            total = spec[2:].sum()
            bin_hz = DEV_RATE / len(block)
            lo, hi = int(350 / bin_hz), int(500 / bin_hz) + 1      # where the ring tone lives
            if total > 0 and spec[lo:hi].sum() / total < 0.7:
                self.blocks += 1
                self.open = self.blocks >= self.needed
        return self.open


class Recorder:
    """Optional stereo WAV of the call: caller on the left, agent on the right, 16 kHz."""

    def __init__(self) -> None:
        self.left: list[np.ndarray] = []
        self.right: list[np.ndarray] = []

    def save(self, path: Path) -> Path:
        caller, agent = np.concatenate(self.left or [np.zeros(0)]), np.concatenate(self.right or [np.zeros(0)])
        n = max(len(caller), len(agent))
        caller, agent = np.pad(caller, (0, n - len(caller))), np.pad(agent, (0, n - len(agent)))
        pcm = (np.clip(np.stack([caller, agent], axis=1), -1, 1) * 32767).astype("<i2")
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as w:
            w.setnchannels(2), w.setsampwidth(2), w.setframerate(AI_RATE)
            w.writeframes(pcm.tobytes())
        return path


try:  # the ElevenLabs SDK's audio interface; a stub keeps the pure parts importable in tests
    from elevenlabs.conversational_ai.conversation import AudioInterface
except ImportError:  # pragma: no cover
    AudioInterface = object  # type: ignore[assignment,misc]


class CableAudio(AudioInterface):
    def __init__(self, call_in: str, agent_out: str, gain: float = 12.0, ring_gate: bool = True,
                 recorder: Recorder | None = None) -> None:
        self.call_in, self.agent_out, self.gain = call_in, agent_out, gain
        self.gate = RingGate(enabled=ring_gate)
        self.rec = recorder
        self.out_q: queue.Queue[np.ndarray] = queue.Queue()
        self.buf = np.zeros(0, dtype=np.float32)
        self.lock = threading.Lock()
        self.last_sound = 0.0        # a live line is never pure digital zeros; a hung-up one is

    def start(self, input_callback):
        import sounddevice as sd

        def on_in(indata, frames, t, status):
            mono = indata[:, 0]
            if np.any(mono):
                self.last_sound = time.time()
            heard = mono * self.gain if self.gate.feed(mono) else np.zeros_like(mono)
            x = np.clip(resample(heard, DEV_RATE, AI_RATE), -1, 1)
            if self.rec is not None:
                self.rec.left.append(x)
            input_callback((x * 32767).astype("<i2").tobytes())

        def on_out(outdata, frames, t, status):
            with self.lock:
                while len(self.buf) < frames and not self.out_q.empty():
                    self.buf = np.concatenate([self.buf, self.out_q.get_nowait()])
                chunk, self.buf = self.buf[:frames], self.buf[frames:]
            outdata[:] = 0
            outdata[:len(chunk), 0] = chunk
            outdata[:len(chunk), 1] = chunk
            if self.rec is not None:
                self.rec.right.append(resample(outdata[:, 0].copy(), DEV_RATE, AI_RATE))

        self.inp = sd.InputStream(device=self.call_in, samplerate=DEV_RATE, channels=2, dtype="float32",
                                  blocksize=BLOCK, latency="low", callback=on_in)
        self.out = sd.OutputStream(device=self.agent_out, samplerate=DEV_RATE, channels=2, dtype="float32",
                                   blocksize=BLOCK, latency="low", callback=on_out)
        self.inp.start(), self.out.start()

    def stop(self):
        for s in (getattr(self, "inp", None), getattr(self, "out", None)):
            if s:
                s.stop(), s.close()

    def output(self, audio: bytes):
        x = np.frombuffer(audio, dtype="<i2").astype(np.float32) / 32768
        self.out_q.put(resample(x, AI_RATE, DEV_RATE))

    def interrupt(self):   # the caller spoke over the agent: drop what it hasn't said yet
        with self.lock:
            self.buf = np.zeros(0, dtype=np.float32)
            while not self.out_q.empty():
                self.out_q.get_nowait()
