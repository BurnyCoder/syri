#!/usr/bin/env python3
import os
import tempfile
import wave
import pyaudio
import threading
import argparse
import time

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', type=int, default=5)
    parser.add_argument('--list-devices', action='store_true')
    parser.add_argument('--device', type=int)
    args = parser.parse_args()
    
    p = pyaudio.PyAudio()
    
    if args.list_devices:
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if dev.get('maxInputChannels') > 0:
                print(f"{i}: {dev.get('name')}")
        return
    
    chunk = 1024
    format = pyaudio.paInt16
    channels = 1
    rate = 44100
    
    device_idx = args.device
    if device_idx is None:
        device_idx = p.get_default_input_device_info()['index']
        print(f"Using device {device_idx}: {p.get_device_info_by_index(device_idx)['name']}")
    
    stream = p.open(format=format,
                  channels=channels,
                  rate=rate,
                  input=True,
                  input_device_index=device_idx,
                  frames_per_buffer=chunk)
    
    print(f"Recording {args.duration} seconds...")
    frames = []
    
    for i in range(0, int(rate / chunk * args.duration)):
        data = stream.read(chunk, exception_on_overflow=False)
        frames.append(data)
        
    stream.stop_stream()
    stream.close()
    
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_filename = temp_file.name
    temp_file.close()
    
    with wave.open(temp_filename, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(format))
        wf.setframerate(rate)
        wf.writeframes(b''.join(frames))
    
    p.terminate()
    print(f"Saved to {temp_filename}")
    
    # Play back the recording
    print("Playing recording...")
    play_audio(temp_filename)

def play_audio(file_path):
    chunk = 1024
    
    wf = wave.open(file_path, 'rb')
    p = pyaudio.PyAudio()
    
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                  channels=wf.getnchannels(),
                  rate=wf.getframerate(),
                  output=True)
    
    data = wf.readframes(chunk)
    
    while data:
        stream.write(data)
        data = wf.readframes(chunk)
        
    stream.stop_stream()
    stream.close()
    p.terminate()

if __name__ == "__main__":
    main() 