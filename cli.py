#!/usr/bin/env python3
"""
macOS TTS to Device - Main Entry Point

A Python utility for routing text-to-speech (TTS) audio to specific output devices on macOS.
Supports multiple TTS engines: macOS 'say' and Bark AI.
"""

import sys
import logging
import click

from src import TTSEngine, ProfileManager
from src.utils import setup_logging
import settings

# The engines are automatically loaded when importing from src
ENGINES = TTSEngine.get_registered_engines()
profile_manager = ProfileManager()


@click.command()
@click.option(
    "--profile",
    type=str,
    default=None,
    help="Load settings from a saved profile.",
)
@click.option(
    "--engine",
    type=click.Choice(list(ENGINES.keys()), case_sensitive=False),
    default=settings.DEFAULT_ENGINE,
    show_default=True,
    help="TTS engine to use.",
)
@click.option(
    "--devices",
    multiple=True,
    default=[settings.PREFERRED_DEFAULT_DEVICE],
    help="Output device name(s) - can be partial match. Can be specified multiple times.",
)
@click.option(
    "--voice",
    type=str,
    default=None,
    help="[Say engine] macOS voice name (e.g., 'Alex', 'Samantha'). Run 'say -v ?' to list available voices.",
)
@click.option(
    "--timeout",
    type=int,
    default=settings.SAY_ENGINE_TIMEOUT,
    show_default=True,
    help="[Say engine] Timeout in seconds for the 'say' command.",
)
@click.option(
    "--speaker",
    type=str,
    default=settings.DEFAULT_BARK_SPEAKER,
    show_default=True,
    help="[Bark engine] Bark voice preset. Try speaker_1 through speaker_9.",
)
@click.option(
    "--sample-rate",
    type=int,
    default=int(settings.DEFAULT_SAMPLE_RATE),
    show_default=True,
    help="[Bark engine] Bark output sample rate in Hz.",
)
@click.option(
    "--model",
    type=str,
    default=settings.PIPER_MODEL_PATH,
    show_default=True,
    help="[Piper engine] Path to Piper .onnx model file.",
)
@click.option(
    "--playback-speed",
    type=float,
    default=settings.DEFAULT_PLAYBACK_SPEED,
    show_default=True,
    help="Playback speed multiplier (0.5 = half speed, 2.0 = double speed).",
)
@click.option(
    "--volume",
    type=float,
    default=settings.DEFAULT_VOLUME,
    show_default=True,
    help="Volume multiplier (0.0 = silent, 1.0 = full volume).",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default=settings.LOG_LEVEL,
    show_default=True,
    help="Set logging level for debugging and detailed output.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output (equivalent to --log-level INFO).",
)
@click.option(
    "--text",
    "-t",
    type=str,
    default=None,
    help="Text to speak. If provided, speaks the text and exits. Otherwise, enters interactive mode.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Path to save the generated audio file (e.g., speech.wav).",
)
@click.option(
    "--no-play",
    is_flag=True,
    help="Do not play the audio on configured devices (useful with --output).",
)
@click.option(
    "--list-voices",
    is_flag=True,
    help="List all available voices for the selected engine and exit.",
)
@click.option(
    "--list-engines",
    is_flag=True,
    help="List all available TTS engines and exit.",
)
@click.option(
    "--list-devices",
    is_flag=True,
    help="List all available audio output devices and exit.",
)
def main(
    engine,
    devices,
    voice,
    timeout,
    speaker,
    sample_rate,
    playback_speed,
    volume,
    log_level,
    verbose,
    text,
    output,
    no_play,
    list_voices,
    list_engines,
    list_devices,
    model,
    profile,
):
    """Route TTS audio to specific output devices on macOS.

    \b
    Examples:
      # Load settings from a profile
      macos-tts --profile "Gaming" --text "Hello"
      # List available voices for the say engine
      macos-tts --engine say --list-voices

      # List available voices for the bark engine
      macos-tts --engine bark --list-voices

      # Speak text directly from command line
      macos-tts --text "Hello world"

      # Use macOS say with default voice (interactive mode)
      macos-tts --engine say --devices "BlackHole 16ch"

      # Use macOS say with specific voice and text
      macos-tts --engine say --devices "BlackHole 16ch" --voice "Samantha" --text "Hello"

      # Use Bark AI with custom speaker
      macos-tts --engine bark --devices "External Headphones" --speaker "v2/en_speaker_3"

      # Multiple devices (simultaneous playback)
      macos-tts --engine say --devices "BlackHole 16ch" --devices "External Headphones"

      # Adjust playback speed (faster or slower)
      macos-tts --engine say --devices "BlackHole 16ch" --playback-speed 1.5

      # Enable verbose logging for troubleshooting
      macos-tts --engine say --devices "BlackHole 16ch" --verbose

      # Enable debug logging for detailed output
      macos-tts --engine say --devices "BlackHole 16ch" --log-level DEBUG

    \b
    Interactive Slash Commands:
      /help         Show available commands
      /list-voices  List voices for current engine
      /clear        Clear history file
      /exit         Exit the program
    """
    # Configure logging
    setup_logging(level=log_level, verbose=verbose)
    logger = logging.getLogger(__name__)

    # Load profile if specified
    if profile:
        profile_data = profile_manager.get_profile(profile)
        if not profile_data:
            click.echo(f"Error: Profile '{profile}' not found.", err=True)
            sys.exit(1)

        # Override arguments with profile data
        engine = profile_data.get("engine", engine)
        devices = profile_data.get("devices", list(devices))
        voice = profile_data.get("voice", voice)
        playback_speed = profile_data.get("speed", playback_speed)
        sample_rate = int(profile_data.get("sample_rate", sample_rate))
        # For Bark engine, we might save speaker as voice in profile
        if engine == "bark":
            speaker = profile_data.get("voice", speaker)
        # For Piper engine
        if engine == "piper":
            model = profile_data.get("voice", model)

    # Get the engine class
    engine_class = ENGINES.get(engine)
    if not engine_class:
        click.echo(f"Unknown engine: {engine}", err=True)
        sys.exit(1)

    # Handle --list-engines flag
    if list_engines:
        try:
            TTSEngine.list_engines()
            sys.exit(0)
        except Exception as e:
            click.echo(f"Error listing engines: {e}", err=True)
            sys.exit(1)

    # Handle --list-voices flag
    if list_voices:
        try:
            engine_class.print_available_voices()
            sys.exit(0)
        except Exception as e:
            click.echo(f"Error listing voices: {e}", err=True)
            sys.exit(1)

    # Handle --list-devices flag
    if list_devices:
        try:
            TTSEngine.print_available_devices()
            sys.exit(0)
        except Exception as e:
            click.echo(f"Error listing devices: {e}", err=True)
            sys.exit(1)

    logger.info(f"Starting macOS TTS to Device with engine={engine}, devices={devices}")

    # Convert devices tuple to list
    devices = list(devices)

    # Validate playback speed
    if (
        playback_speed < settings.MIN_PLAYBACK_SPEED
        or playback_speed > settings.MAX_PLAYBACK_SPEED
    ):
        click.echo(
            f"Warning: Playback speed {playback_speed} is outside recommended range "
            f"({settings.MIN_PLAYBACK_SPEED}-{settings.MAX_PLAYBACK_SPEED}). "
            "Clamping to valid range.",
            err=True,
        )
        playback_speed = max(
            settings.MIN_PLAYBACK_SPEED,
            min(settings.MAX_PLAYBACK_SPEED, playback_speed),
        )

    # Engine-specific initialization parameters
    engine_params = {
        "say": {
            "output_devices": devices,
            "voice": voice,
            "timeout": timeout,
            "playback_speed": playback_speed,
            "volume": volume,
        },
        "bark": {
            "output_devices": devices,
            "voice_preset": speaker,
            "sample_rate": sample_rate,
            "playback_speed": playback_speed,
            "volume": volume,
        },
        "piper": {
            "output_devices": devices,
            "model_path": model,
            "playback_speed": playback_speed,
            "volume": volume,
        },
    }

    # Initialize the TTS engine
    try:
        tts_engine = engine_class(**engine_params[engine])

    except ImportError as e:
        if "bark" in str(e).lower():
            click.echo("\nError: Bark library not installed.", err=True)
            click.echo("Install it with: uv pip install .[bark]", err=True)
            click.echo(
                "Or use the 'say' engine instead: macos-tts --engine say", err=True
            )
        elif "piper" in str(e).lower():
            click.echo("\nError: Piper library not installed.", err=True)
            click.echo("Install it with: uv pip install .[piper]", err=True)
            click.echo(
                "Or use the 'say' engine instead: macos-tts --engine say", err=True
            )
        else:
            click.echo(f"\nImport error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"\nError initializing TTS engine: {e}", err=True)
        sys.exit(1)

    # Print configuration info
    tts_engine.print_info()

    # If text is provided via CLI, process it and exit
    if text:
        try:
            tts_engine.process_text(text, output_path=output, play_audio=not no_play)
            sys.exit(0)
        except Exception as e:
            click.echo(f"Error processing text: {e}", err=True)
            sys.exit(1)

    # Check if stdin is being piped
    if not sys.stdin.isatty():
        piped_text = sys.stdin.read().strip()
        if piped_text:
            try:
                tts_engine.process_text(
                    piped_text, output_path=output, play_audio=not no_play
                )
                sys.exit(0)
            except Exception as e:
                click.echo(f"Error processing piped text: {e}", err=True)
                sys.exit(1)
        else:
            sys.exit(0)

    # Otherwise, enter interactive mode
    click.echo("Interactive mode enabled. Type your text and press Enter.")
    if output:
        click.echo(f"Exporting all speech to: {output}")
    click.echo("Special commands: /help, /list-voices, /exit")
    try:
        while True:
            text = input("> ").strip()
            if not text:
                continue

            if text == "/exit" or text == "/quit":
                break
            elif text == "/help":
                click.echo("Special commands:")
                click.echo("  /help         Show this help message")
                click.echo("  /list-voices  List available voices for current engine")
                click.echo("  /clear        Clear the history file")
                click.echo("  /exit, /quit  Exit the program")
                continue
            elif text == "/clear":
                from src import HistoryManager

                HistoryManager().clear_history()
                click.echo("History cleared.")
                continue
            elif text == "/list-voices":
                engine_class.print_available_voices()
                continue

            try:
                tts_engine.process_text(
                    text, output_path=output, play_audio=not no_play
                )
            except KeyboardInterrupt:
                raise
            except Exception as e:
                click.echo(f"Error processing text: {e}", err=True)

    except KeyboardInterrupt:
        click.echo("\nExiting.")
        sys.exit(0)


if __name__ == "__main__":
    main()
