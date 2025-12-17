# macOS TTS to Device

A Python utility for routing text-to-speech (TTS) audio to specific output devices on macOS. Useful for streaming TTS to virtual audio devices like BlackHole, OBS, Discord, or any other audio destination.

## Features

- 🎯 **Device Selection**: Route TTS to any audio output device by name
- 🔊 **Multiple Device Output**: Play audio simultaneously on multiple devices
- 🎤 **Two TTS Engines**:
  - **macOS `say`**: Fast, built-in macOS TTS with multiple voice options
  - **Bark AI**: Natural-sounding AI-generated speech with realistic prosody
- 🔄 **Interactive CLI**: Type text and hear it immediately
- 🧹 **Auto-cleanup**: Temporary audio files are automatically removed
- ⚡ **Real-time**: Minimal latency from text input to audio output

## Use Cases

- Stream TTS to virtual meetings (Zoom, Discord, etc.)
- Create voiceovers for live streaming (OBS, Twitch)
- Route TTS to audio processing software
- Test audio device configurations
- Generate speech for accessibility purposes
- Output to multiple devices simultaneously (e.g., speakers + virtual device)

## Requirements

- macOS (uses macOS-specific audio features)
- Python 3.7+
- Audio output device (physical or virtual like BlackHole)

## Installation

1. Clone or download this repository:

```bash
git clone <repository-url>
cd macos_tts_to_device
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

**Note**: The Bark installation may take several minutes as it downloads AI models.

## Configuration

### Option 1: macOS `say` (main_say.py)

Edit the configuration at the top of `main_say.py`:

```python
OUTPUT_DEVICES = ["BlackHole 16ch"]  # List of target audio devices
VOICE = None                          # macOS voice name (e.g., "Alex", "Samantha")
```

**Multiple Device Output**: Add multiple devices to play audio simultaneously on all of them:

```python
OUTPUT_DEVICES = ["BlackHole 16ch", "External Headphones", "Built-in Output"]
```

To see available macOS voices, run:
```bash
say -v ?
```

### Option 2: Bark AI (main_bark.py)

Edit the configuration at the top of `main_bark.py`:

```python
OUTPUT_DEVICES = ["External Headphones"]  # List of target audio devices
VOICE_PRESET = "v2/en_speaker_6"          # Try speaker_1 through speaker_9
SAMPLE_RATE = 24000                       # Bark's output sample rate
```

**Multiple Device Output**: Same as `main_say.py`, you can add multiple devices:

```python
OUTPUT_DEVICES = ["BlackHole 16ch", "External Headphones"]
```

## Finding Your Output Device Name

To list all available audio output devices:

```python
import sounddevice as sd
print(sd.query_devices())
```

Or use a partial name match (e.g., "BlackHole", "External", "Headphones").

## Usage

### Using macOS `say` (Fast & Simple)

```bash
python main_say.py
```

Then type text and press Enter:

```
Live TTS → Multiple Devices
Output devices: ['BlackHole 16ch']
Temp files: /path/to/tts_tmp
Type a line and press Enter (Ctrl+C to quit)

> Hello, world!
> This is a test of the TTS system.
```

**Tip**: To hear the audio locally while routing to a virtual device, add your speakers to the device list:

```python
OUTPUT_DEVICES = ["BlackHole 16ch", "External Headphones"]
```

### Using Bark AI (Natural & Expressive)

```bash
python main_bark.py
```

**First run**: Bark will download model files (1-2 GB), which may take several minutes.

Then type text and press Enter:

```
Loading Bark models (first run takes a while)...
Live Bark TTS → Multiple Devices
Output devices: ['External Headphones']
Temp files: /path/to/tts_tmp
Voice preset: v2/en_speaker_6
Type a line and press Enter (Ctrl+C to quit)

> Hello! How are you today?
> [laughter] That's pretty cool!
```

**Bark Tips**:
- Try different speaker presets (speaker_1 to speaker_9) for different voices
- Bark supports emotional expressions: `[laughter]`, `[sighs]`, `[music]`
- Generation takes 5-15 seconds per sentence depending on length

## Exiting

Press `Ctrl+C` to exit either program.

## How It Works

1. **Text Input**: User enters text via stdin
2. **Audio Generation**: 
   - `main_say.py` calls macOS `say` command to generate AIFF
   - `main_bark.py` uses Bark AI to generate WAV
3. **Temporary Storage**: Audio saved to `tts_tmp/` directory
4. **Playback**: 
   - Audio streamed to specified output device(s) via `sounddevice`
   - For multiple devices, parallel threads ensure simultaneous playback
5. **Cleanup**: Temporary file deleted after playback

## Virtual Audio Setup (Optional)

To route TTS to applications like Zoom or OBS:

1. Install [BlackHole](https://github.com/ExistentialAudio/BlackHole) (free virtual audio driver)
2. Set `OUTPUT_DEVICE = "BlackHole 16ch"` in your chosen script
3. Configure your target application to use BlackHole as its audio input
4. (Optional) Use Audio MIDI Setup to create a Multi-Output Device to hear audio locally

## Troubleshooting

### "Device not found" error

Check available devices:
```python
import sounddevice as sd
print(sd.query_devices())
```

Ensure `OUTPUT_DEVICE` matches a device name (substring matching is supported).

### Bark is too slow

- Use `main_say.py` for faster (but less natural) TTS
- Bark's first generation per session is slower (model loading)
- Consider using shorter sentences

### No audio output

- Verify the output device is not muted
- Check that the device is properly configured in System Settings → Sound
- For virtual devices, ensure they're properly installed and visible

### One device works but others don't (multiple device mode)

- Check error messages for specific device failures
- Verify all device names are correct (run the device query script)
- Some devices may not support simultaneous playback - test individually
- Ensure all devices are active and not in use by other applications

## Dependencies

- `sounddevice`: Python bindings for PortAudio (audio I/O)
- `soundfile`: Audio file reading/writing
- `bark` (optional): Suno's Bark AI TTS model

## License

[Specify your license here]

## Contributing

Contributions welcome! Feel free to open issues or submit pull requests.

## Acknowledgments

- [Bark](https://github.com/suno-ai/bark) by Suno AI for the neural TTS engine
- [BlackHole](https://github.com/ExistentialAudio/BlackHole) for virtual audio routing on macOS
