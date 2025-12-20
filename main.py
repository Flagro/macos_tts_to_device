#!/usr/bin/env python3
"""
macOS TTS to Device - Main Entry Point

A Python utility for routing text-to-speech (TTS) audio to specific output devices on macOS.
Supports multiple TTS engines: macOS 'say' and Bark AI.
"""

import sys
import click

from src import SayTTSEngine, BarkTTSEngine


@click.command()
@click.option(
    "--engine",
    type=click.Choice(["say", "bark"], case_sensitive=False),
    default="say",
    show_default=True,
    help="TTS engine to use.",
)
@click.option(
    "--devices",
    multiple=True,
    default=["BlackHole 16ch"],
    help="Output device name(s) - can be partial match. Can be specified multiple times.",
)
@click.option(
    "--voice",
    type=str,
    default=None,
    help="[Say engine] macOS voice name (e.g., 'Alex', 'Samantha'). Run 'say -v ?' to list available voices.",
)
@click.option(
    "--speaker",
    type=str,
    default="v2/en_speaker_6",
    show_default=True,
    help="[Bark engine] Bark voice preset. Try speaker_1 through speaker_9.",
)
@click.option(
    "--sample-rate",
    type=int,
    default=24000,
    show_default=True,
    help="[Bark engine] Bark output sample rate in Hz.",
)
def main(engine, devices, voice, speaker, sample_rate):
    """Route TTS audio to specific output devices on macOS.

    \b
    Examples:
      # Use macOS say with default voice
      python main.py --engine say --devices "BlackHole 16ch"

      # Use macOS say with specific voice
      python main.py --engine say --devices "BlackHole 16ch" --voice "Samantha"

      # Use Bark AI with custom speaker
      python main.py --engine bark --devices "External Headphones" --speaker "v2/en_speaker_3"

      # Multiple devices (simultaneous playback)
      python main.py --engine say --devices "BlackHole 16ch" --devices "External Headphones"
    """
    # Convert devices tuple to list
    devices = list(devices)

    # Initialize the appropriate TTS engine
    try:
        if engine == "say":
            tts_engine = SayTTSEngine(output_devices=devices, voice=voice)
        elif engine == "bark":
            tts_engine = BarkTTSEngine(
                output_devices=devices,
                voice_preset=speaker,
                sample_rate=sample_rate,
            )
        else:
            click.echo(f"Unknown engine: {engine}", err=True)
            sys.exit(1)

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

    # Main loop
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
