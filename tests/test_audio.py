import numpy as np

from callbridge.audio import AI_RATE, BLOCK, DEV_RATE, Recorder, RingGate, resample


def tone(hz, n=BLOCK, amp=0.1):
    return (amp * np.sin(2 * np.pi * hz * np.arange(n) / DEV_RATE)).astype(np.float32)


def test_resample_changes_length_by_rate():
    assert len(resample(np.zeros(DEV_RATE // 50, np.float32), DEV_RATE, AI_RATE)) == AI_RATE // 50
    assert len(resample(np.zeros(0, np.float32), DEV_RATE, AI_RATE)) == 0


def test_ring_gate_stays_shut_on_ring_tones():
    for hz in (400, 425, 440, 480):           # IL/EU/US ring-back tones
        g = RingGate()
        assert not any(g.feed(tone(hz)) for _ in range(50)), hz


def test_ring_gate_stays_shut_on_silence():
    g = RingGate()
    assert not any(g.feed(np.zeros(BLOCK, np.float32)) for _ in range(50))


def test_ring_gate_opens_on_speech_like_sound():
    g = RingGate()
    voice = lambda: tone(180) + tone(900, amp=0.05) + tone(2300, amp=0.03)
    results = [g.feed(voice()) for _ in range(10)]
    assert results[6] is False and results[7] is True    # ~160 ms of voice, not one click


def test_ring_gate_disabled_for_inbound_calls():
    assert RingGate(enabled=False).feed(np.zeros(BLOCK, np.float32))


def test_recorder_writes_stereo_wav(tmp_path):
    import wave
    r = Recorder()
    r.left.append(np.full(160, 0.5, np.float32))
    r.right.append(np.full(320, -0.5, np.float32))
    p = r.save(tmp_path / "x.wav")
    with wave.open(str(p)) as w:
        assert (w.getnchannels(), w.getframerate(), w.getnframes()) == (2, AI_RATE, 320)
