#!/usr/bin/env python3
"""
macOS TTS to Device - Main Entry Point

A Python utility for routing text-to-speech (TTS) audio to specific output devices on macOS.
Supports multiple TTS engines: macOS 'say' and Bark AI.
"""

import sys
import argparse

from src import SayTTSEngine, BarkTTSEngine


def main():
    """Main entry point for TTS to Device utility."""
    parser = argparse.ArgumentParser(
        description="Route TTS audio to specific output devices on macOS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use macOS say with default voice
  python main.py --engine say --devices "BlackHole 16ch"
  
  # Use macOS say with specific voice
  python main.py --engine say --devices "BlackHole 16ch" --voice "Samantha"
  
  # Use Bark AI with custom speaker
  python main.py --engine bark --devices "External Headphones" --speaker "v2/en_speaker_3"
  
  # Multiple devices (simultaneous playback)
  python main.py --engine say --devices "BlackHole 16ch" "External Headphones"
        """,
    )

    parser.add_argument(
        "--engine",
        choices=["say", "bark"],
        default="say",
        help="TTS engine to use (default: say)",
    )

    parser.add_argument(
        "--devices",
        nargs="+",
        default=["BlackHole 16ch"],
        help="Output device name(s) - can be partial match (default: BlackHole 16ch)",
    )

    # Say-specific options
    say_group = parser.add_argument_group("macOS say options")
    say_group.add_argument(
        "--voice",
        type=str,
        default=None,
        help="macOS voice name (e.g., 'Alex', 'Samantha'). Run 'say -v ?' to list available voices.",
    )

    # Bark-specific options
    bark_group = parser.add_argument_group("Bark AI options")
    bark_group.add_argument(
        "--speaker",
        type=str,
        default="v2/en_speaker_6",
        help="Bark voice preset (default: v2/en_speaker_6). Try speaker_1 through speaker_9.",
    )
    bark_group.add_argument(
        "--sample-rate",
        type=int,
        default=24000,
        help="Bark output sample rate in Hz (default: 24000)",
    )

    args = parser.parse_args()

    # Initialize the appropriate TTS engine
    try:
        if args.engine == "say":
            engine = SayTTSEngine(output_devices=args.devices, voice=args.voice)
        elif args.engine == "bark":
            engine = BarkTTSEngine(
                output_devices=args.devices,
                voice_preset=args.speaker,
                sample_rate=args.sample_rate,
            )
        else:
            print(f"Unknown engine: {args.engine}")
            sys.exit(1)

    except ImportError as e:
        if "bark" in str(e).lower():
            print("\nError: Bark library not installed.")
            print(
                "Install it with: pip install git+https://github.com/suno-ai/bark.git"
            )
            print("Or use the 'say' engine instead: python main.py --engine say")
        else:
            print(f"\nImport error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nError initializing TTS engine: {e}")
        sys.exit(1)

    # Print configuration info
    engine.print_info()

    # Main loop
    try:
        while True:
            text = input("> ").strip()
            if not text:
                continue

            try:
                engine.process_text(text)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"Error processing text: {e}")

    except KeyboardInterrupt:
        print("\nExiting.")
        sys.exit(0)


if __name__ == "__main__":
    main()
