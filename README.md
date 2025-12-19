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
- [uv](https://github.com/astral-sh/uv) package installer (install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Audio output device (physical or virtual like BlackHole)

## Installation

1. Clone or download this repository:

```bash
git clone <repository-url>
cd macos_tts_to_device
```

2. Install dependencies:

**For macOS `say` engine only (lightweight)**:

```bash
uv pip install .
```

**For Bark AI support (includes all features)**:

```bash
uv pip install .[bark]
```

**Or install everything**:

```bash
uv pip install .[all]
```

**Note**: The Bark installation may take several minutes as it downloads AI models and dependencies.

## Project Structure

```
macos_tts_to_device/
├── main.py              # Single entry point with CLI
├── src/
│   ├── __init__.py
│   ├── tts_base.py      # Base class for TTS engines
│   ├── tts_say.py       # macOS 'say' implementation
│   └── tts_bark.py      # Bark AI implementation
├── pyproject.toml       # Dependencies and project config
└── README.md
```

## Configuration & Usage

The utility uses command-line arguments for configuration. No code editing required!

### Basic Usage

**Using macOS `say` (Fast & Simple)**:

```bash
python main.py --engine say --devices "BlackHole 16ch"
```

**Using Bark AI (Natural & Expressive)**:

```bash
python main.py --engine bark --devices "External Headphones"
```

### Multiple Device Output

Play audio simultaneously on multiple devices:

```bash
python main.py --engine say --devices "BlackHole 16ch" "External Headphones"
```

### Advanced Options

**macOS say with specific voice**:

```bash
python main.py --engine say --devices "BlackHole 16ch" --voice "Samantha"
```

To see available macOS voices:
```bash
say -v ?
```

**Bark AI with custom speaker**:

```bash
python main.py --engine bark --devices "External Headphones" --speaker "v2/en_speaker_3"
```

Try different speaker presets: `v2/en_speaker_1` through `v2/en_speaker_9`

### Finding Your Output Device Name

To list all available audio output devices:

```python
import sounddevice as sd
print(sd.query_devices())
```

Or use a partial name match (e.g., "BlackHole", "External", "Headphones").

### Command-Line Help

For all available options:

```bash
python main.py --help
```

## Interactive Mode

After starting the program, type text and press Enter:

```
Live TTS (macOS say) → Multiple Devices
Output devices: ['BlackHole 16ch']
Temp files: /path/to/tts_tmp
Voice: Default
Type a line and press Enter (Ctrl+C to quit)

> Hello, world!
> This is a test of the TTS system.
```

**With Bark AI** (first run will download model files ~1-2 GB):

```
Loading Bark models (first run takes a while)...
Live Bark TTS → Multiple Devices
Output devices: ['External Headphones']
Temp files: /path/to/tts_tmp
Voice preset: v2/en_speaker_6
Sample rate: 24000 Hz
Type a line and press Enter (Ctrl+C to quit)

> Hello! How are you today?
> [laughter] That's pretty cool!
```

**Bark Tips**:
- Try different speaker presets (speaker_1 to speaker_9) for different voices
- Bark supports emotional expressions: `[laughter]`, `[sighs]`, `[music]`
- Generation takes 5-15 seconds per sentence depending on length

**Exiting**: Press `Ctrl+C` to quit.

## How It Works

1. **Text Input**: User enters text via stdin
2. **Engine Selection**: Choose between macOS `say` or Bark AI via `--engine` flag
3. **Audio Generation**: 
   - `SayTTSEngine` calls macOS `say` command to generate AIFF
   - `BarkTTSEngine` uses Bark AI to generate WAV
4. **Temporary Storage**: Audio saved to `tts_tmp/` directory
5. **Playback**: 
   - Audio streamed to specified output device(s) via `sounddevice`
   - For multiple devices, parallel threads ensure simultaneous playback
6. **Cleanup**: Temporary file deleted after playback

### Architecture

- **`main.py`**: CLI entry point with argument parsing
- **`src/tts_base.py`**: Abstract base class defining the TTS engine interface
- **`src/tts_say.py`**: Implementation using macOS `say` command
- **`src/tts_bark.py`**: Implementation using Bark AI model
- All engines support multi-device playback with automatic cleanup

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

- Use `--engine say` for faster (but less natural) TTS
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
