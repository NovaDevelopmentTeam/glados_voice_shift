# -*- coding: utf-8 -*-
import random
import time
from pydub import AudioSegment
import numpy as np
from librosa.effects import pitch_shift
import librosa

def pitch_shift_librosa(sound_array, sample_rate, n_steps):
    # n_steps = Halbtöne, z.B. +3 oder -5
    return pitch_shift(sound_array, sr=sample_rate, n_steps=n_steps)

def voice_shifter(
    input_path,
    output_path,
    min_shift=-5,          # Minimaler Halbtone Shift
    max_shift=5,           # Maximaler Halbtone Shift
    segment_length_sec=1,  # Länge der kleinen Segmente in Sekunden
    hold_time_sec=3,       # Dauer, wie lange ein Shift gehalten wird
    sample_rate=44100
):
    # Audio laden
    y, sr = librosa.load(input_path, sr=sample_rate)
    duration = librosa.get_duration(y=y, sr=sr)

    output_audio = np.array([], dtype=np.float32)
    
    current_pos = 0.0
    shifting = False
    shift_end_time = 0.0
    current_shift = 0.0

    while current_pos < duration:
        seg_len = min(segment_length_sec, duration - current_pos)

        start_sample = int(current_pos * sr)
        end_sample = int((current_pos + seg_len) * sr)
        segment = y[start_sample:end_sample]

        if not shifting:
            # Entscheidung, ob Shift startet
            do_shift = random.choice([True, False])
            if do_shift:
                current_shift = random.uniform(min_shift, max_shift)
                shift_end_time = current_pos + hold_time_sec
                shifting = True
            else:
                current_shift = 0.0

        if shifting and current_pos >= shift_end_time:
            # Shift vorbei
            shifting = False
            current_shift = 0.0

        if current_shift != 0.0:
            shifted_segment = pitch_shift_librosa(segment, sr, current_shift)
            output_audio = np.concatenate((output_audio, shifted_segment))
        else:
            output_audio = np.concatenate((output_audio, segment))

        current_pos += seg_len

    # Ausgabe als WAV speichern
    shifted_audio = AudioSegment(
        (output_audio * 32767).astype(np.int16).tobytes(),
        frame_rate=sr,
        sample_width=2,
        channels=1
    )

    shifted_audio.export(output_path, format="wav")
    print(f"Gespeichert: {output_path}")

# Beispiel-Aufruf
if __name__ == "__main__":
    voice_shifter(
        "Cave_Johnson_fifties_waiting01.wav",
        "ok-Cave_Johnson_fifties_waiting01.wav",
        min_shift=-3,
        max_shift=3,
        segment_length_sec=1,
        hold_time_sec=3,
        sample_rate=44100
    )
