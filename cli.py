#!/usr/bin/env python3
"""
macOS TTS to Device - Main Entry Point

A Python utility for routing text-to-speech (TTS) audio to specific output devices on macOS.
Supports multiple TTS engines: macOS 'say' and Bark AI.
"""

import sys
import logging
import click

from src import SayTTSEngine, BarkTTSEngine
import settings

# Engine registry for cleaner code
ENGINES = {
    "say": SayTTSEngine,
    "bark": BarkTTSEngine,
}


@click.command()
@click.option(
    "--engine",
    type=click.Choice(["say", "bark"], case_sensitive=False),
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
    "--list-voices",
    is_flag=True,
    help="List all available voices for the selected engine and exit.",
)
def main(
    engine,
    devices,
    voice,
    timeout,
    speaker,
    sample_rate,
    log_level,
    verbose,
    text,
    list_voices,
):
    """Route TTS audio to specific output devices on macOS.

    \b
    Examples:
      # List available voices for the say engine
      python main.py --engine say --list-voices

      # List available voices for the bark engine
      python main.py --engine bark --list-voices

      # Speak text directly from command line
      python main.py --text "Hello world"

      # Use macOS say with default voice (interactive mode)
      python main.py --engine say --devices "BlackHole 16ch"

      # Use macOS say with specific voice and text
      python main.py --engine say --devices "BlackHole 16ch" --voice "Samantha" --text "Hello"

      # Use Bark AI with custom speaker
      python main.py --engine bark --devices "External Headphones" --speaker "v2/en_speaker_3"

      # Multiple devices (simultaneous playback)
      python main.py --engine say --devices "BlackHole 16ch" --devices "External Headphones"

      # Enable verbose logging for troubleshooting
      python main.py --engine say --devices "BlackHole 16ch" --verbose

      # Enable debug logging for detailed output
      python main.py --engine say --devices "BlackHole 16ch" --log-level DEBUG
    """
    # Configure logging
    if verbose:
        log_level = "INFO"

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=settings.LOG_FORMAT,
        datefmt=settings.LOG_DATE_FORMAT,
    )

    logger = logging.getLogger(__name__)

    # Get the engine class
    engine_class = ENGINES.get(engine)
    if not engine_class:
        click.echo(f"Unknown engine: {engine}", err=True)
        sys.exit(1)

    # Handle --list-voices flag
    if list_voices:
        try:
            engine_class.print_available_voices()
            sys.exit(0)
        except Exception as e:
            click.echo(f"Error listing voices: {e}", err=True)
            sys.exit(1)

    logger.info(f"Starting macOS TTS to Device with engine={engine}, devices={devices}")

    # Convert devices tuple to list
    devices = list(devices)

    # Engine-specific initialization parameters
    engine_params = {
        "say": {"output_devices": devices, "voice": voice, "timeout": timeout},
        "bark": {
            "output_devices": devices,
            "voice_preset": speaker,
            "sample_rate": sample_rate,
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
                "Or use the 'say' engine instead: python main.py --engine say", err=True
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
            tts_engine.process_text(text)
            sys.exit(0)
        except Exception as e:
            click.echo(f"Error processing text: {e}", err=True)
            sys.exit(1)

    # Otherwise, enter interactive mode
    try:
        while True:
            text = input("> ").strip()
            if not text:
                continue

            try:
                tts_engine.process_text(text)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                click.echo(f"Error processing text: {e}", err=True)

    except KeyboardInterrupt:
        click.echo("\nExiting.")
        sys.exit(0)


if __name__ == "__main__":
    main()
