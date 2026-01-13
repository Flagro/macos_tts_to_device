#!/usr/bin/env python3
"""
macOS TTS to Device - GUI Application

A minimalistic Tkinter-based GUI for routing text-to-speech audio to specific devices.
"""

import logging
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Optional, Union, Any

from src import SayTTSEngine, BarkTTSEngine
from src.tts_base import TTSEngine
import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT,
    datefmt=settings.LOG_DATE_FORMAT,
)

logger = logging.getLogger(__name__)


class TTSApp:
    """Minimalistic TTS GUI Application."""

    def __init__(self, root: tk.Tk) -> None:
        self.root: tk.Tk = root
        self.root.title(settings.WINDOW_TITLE)
        self.root.geometry(f"{settings.WINDOW_WIDTH}x{settings.WINDOW_HEIGHT}")
        self.root.resizable(True, True)

        # State
        self.tts_engine: Optional[Union[SayTTSEngine, BarkTTSEngine]] = None
        self.is_processing: bool = False
        self.processing_lock: threading.Lock = threading.Lock()
        self.cancel_event: threading.Event = threading.Event()
        self.current_engine_type: str = settings.DEFAULT_ENGINE

        # Available engines
        self.engines: dict[str, dict[str, Any]] = {
            "say": {
                "class": SayTTSEngine,
                "name": settings.ENGINE_METADATA["say"]["name"],
            },
            "bark": {
                "class": BarkTTSEngine,
                "name": settings.ENGINE_METADATA["bark"]["name"],
            },
        }

        # Available audio devices
        self.available_devices: list[str] = []
        self.device_vars: dict[str, tk.BooleanVar] = {}  # Device name -> BooleanVar

        # UI Elements (will be initialized in _create_widgets)
        self.engine_var: tk.StringVar
        self.device_frame: ttk.Frame
        self.device_checkboxes: list[ttk.Checkbutton] = []
        self.sample_rate_var: tk.StringVar
        self.sample_rate_combo: ttk.Combobox
        self.sample_rate_label: ttk.Label
        self.playback_speed_var: tk.DoubleVar
        self.playback_speed_scale: ttk.Scale
        self.playback_speed_label: ttk.Label
        self.playback_speed_value_label: ttk.Label
        self.voice_var: tk.StringVar
        self.voice_help: ttk.Label
        self.voice_combo: ttk.Combobox
        self.available_voices: list[str] = []
        self.text_input: scrolledtext.ScrolledText
        self.speak_button: ttk.Button
        self.stop_button: ttk.Button
        self.status_var: tk.StringVar
        self.progress_bar: ttk.Progressbar

        # Create UI
        self._create_widgets()
        self._load_audio_devices()
        self._load_voices_for_engine()  # Load voices for initial engine
        self._update_ui_for_engine()  # Hide/show elements based on initial engine
        self._initialize_default_engine()

    def _create_widgets(self) -> None:
        """Create all UI widgets."""

        # Main container with padding
        main_frame: ttk.Frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights for responsiveness
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)  # Updated from 5 to 6 for playback speed row

        # ===== Engine Selection =====
        ttk.Label(main_frame, text="Engine:").grid(row=0, column=0, sticky=tk.W, pady=5)

        self.engine_var = tk.StringVar(value=settings.DEFAULT_ENGINE)
        engine_frame: ttk.Frame = ttk.Frame(main_frame)
        engine_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)

        ttk.Radiobutton(
            engine_frame,
            text=settings.ENGINE_METADATA["say"]["name"],
            variable=self.engine_var,
            value="say",
            command=self._on_engine_change,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(
            engine_frame,
            text=settings.ENGINE_METADATA["bark"]["name"],
            variable=self.engine_var,
            value="bark",
            command=self._on_engine_change,
        ).pack(side=tk.LEFT, padx=5)

        # ===== Output Devices =====
        device_label_frame = ttk.Frame(main_frame)
        device_label_frame.grid(row=1, column=0, sticky=(tk.W, tk.N), pady=5)

        ttk.Label(device_label_frame, text="Output Devices:").pack(anchor=tk.W)
        ttk.Button(
            device_label_frame,
            text="↻ Refresh",
            command=self._on_refresh_devices,
            width=10,
        ).pack(anchor=tk.W, pady=(2, 0))

        # Frame for device checkboxes (will be populated by _load_audio_devices)
        self.device_frame = ttk.Frame(main_frame)
        self.device_frame.grid(
            row=1, column=1, sticky=(tk.W, tk.E, tk.N), pady=5, padx=5
        )

        # ===== Sample Rate Selection =====
        self.sample_rate_label = ttk.Label(main_frame, text="Sample Rate:")
        self.sample_rate_label.grid(row=2, column=0, sticky=tk.W, pady=5)

        self.sample_rate_var = tk.StringVar(value=settings.DEFAULT_SAMPLE_RATE)
        self.sample_rate_combo = ttk.Combobox(
            main_frame,
            textvariable=self.sample_rate_var,
            values=settings.AVAILABLE_SAMPLE_RATES,
            width=37,
            state="readonly",
        )
        self.sample_rate_combo.grid(
            row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=5
        )

        # ===== Playback Speed Control =====
        self.playback_speed_label = ttk.Label(main_frame, text="Playback Speed:")
        self.playback_speed_label.grid(row=3, column=0, sticky=tk.W, pady=5)

        playback_speed_frame = ttk.Frame(main_frame)
        playback_speed_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)

        self.playback_speed_var = tk.DoubleVar(value=settings.DEFAULT_PLAYBACK_SPEED)
        self.playback_speed_scale = ttk.Scale(
            playback_speed_frame,
            from_=settings.MIN_PLAYBACK_SPEED,
            to=settings.MAX_PLAYBACK_SPEED,
            variable=self.playback_speed_var,
            orient=tk.HORIZONTAL,
            command=self._on_playback_speed_change,
        )
        self.playback_speed_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.playback_speed_value_label = ttk.Label(
            playback_speed_frame, text="1.0x", width=6
        )
        self.playback_speed_value_label.pack(side=tk.LEFT, padx=(5, 0))

        # ===== Voice Selection (Engine-specific) =====
        ttk.Label(main_frame, text="Voice/Speaker:").grid(
            row=4, column=0, sticky=tk.W, pady=5
        )

        self.voice_var = tk.StringVar(value=settings.DEFAULT_SAY_VOICE)
        self.voice_combo = ttk.Combobox(
            main_frame,
            textvariable=self.voice_var,
            width=37,
            state="readonly",
        )
        self.voice_combo.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)

        # Help text for voice
        self.voice_help = ttk.Label(
            main_frame,
            text=settings.VOICE_HELP_SAY,
            font=("", settings.HELP_TEXT_FONT_SIZE),
            foreground="gray",
        )
        self.voice_help.grid(row=5, column=1, sticky=tk.W, padx=5)

        # ===== Text Input =====
        ttk.Label(main_frame, text="Text to Speak:").grid(
            row=6, column=0, sticky=(tk.W, tk.N), pady=5
        )

        self.text_input = scrolledtext.ScrolledText(
            main_frame,
            height=settings.TEXT_INPUT_HEIGHT,
            width=settings.TEXT_INPUT_WIDTH,
            wrap=tk.WORD,
            font=("", settings.TEXT_INPUT_FONT_SIZE),
        )
        self.text_input.grid(
            row=6, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=5
        )
        self.text_input.focus()

        # Bind Enter key (with modifier) to speak
        self.text_input.bind("<Command-Return>", lambda e: self._on_speak())
        self.text_input.bind("<Control-Return>", lambda e: self._on_speak())

        # ===== Buttons =====
        button_frame: ttk.Frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=10)

        self.speak_button = ttk.Button(
            button_frame,
            text="Speak (⌘+Enter)",
            command=self._on_speak,
            width=20,
        )
        self.speak_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(
            button_frame,
            text="⏹ Stop",
            command=self._on_stop,
            width=15,
            state="disabled",
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Clear", command=self._on_clear, width=15).pack(
            side=tk.LEFT, padx=5
        )

        # ===== Progress Bar =====
        self.progress_bar = ttk.Progressbar(
            main_frame,
            mode="indeterminate",
            length=300,
        )
        self.progress_bar.grid(
            row=8, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0), padx=10
        )
        self.progress_bar.grid_remove()  # Hidden by default

        # ===== Status Bar =====
        self.status_var = tk.StringVar(value="Ready")
        status_bar: ttk.Label = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2),
        )
        status_bar.grid(row=9, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

    def _initialize_default_engine(self) -> None:
        """Initialize the default TTS engine."""
        self._update_engine()

    def _load_audio_devices(self) -> None:
        """Load available audio devices and create checkboxes."""
        try:
            # Clear all existing widgets in device frame (checkboxes and any error labels)
            for widget in self.device_frame.winfo_children():
                widget.destroy()
            self.device_checkboxes.clear()
            self.device_vars.clear()

            devices = TTSEngine.list_available_devices()
            self.available_devices = [device["name"] for device in devices]

            if self.available_devices:

                # Create a checkbox for each device
                for device_name in self.available_devices:
                    var = tk.BooleanVar(value=False)
                    self.device_vars[device_name] = var

                    checkbox = ttk.Checkbutton(
                        self.device_frame, text=device_name, variable=var
                    )
                    checkbox.pack(anchor=tk.W, pady=2)
                    self.device_checkboxes.append(checkbox)

                # Try to select preferred device by default if available
                if settings.PREFERRED_DEFAULT_DEVICE in self.available_devices:
                    self.device_vars[settings.PREFERRED_DEFAULT_DEVICE].set(True)
                elif self.available_devices:
                    # Select first device by default
                    self.device_vars[self.available_devices[0]].set(True)
            else:
                ttk.Label(
                    self.device_frame, text="No devices found", foreground="red"
                ).pack(anchor=tk.W)
                self._set_status("Warning: No audio output devices found")

        except Exception as e:
            logger.error(f"Failed to load audio devices: {e}", exc_info=True)
            ttk.Label(
                self.device_frame, text=f"Error loading devices: {e}", foreground="red"
            ).pack(anchor=tk.W)
            self._set_status(f"Error loading devices: {e}")

    def _on_refresh_devices(self) -> None:
        """Refresh the list of available audio devices."""
        # Save currently selected devices
        previously_selected = self._get_selected_devices()

        # Reload devices
        self._load_audio_devices()

        # Restore previously selected devices if they still exist
        for device_name in previously_selected:
            if device_name in self.device_vars:
                self.device_vars[device_name].set(True)

        # Update status
        device_count = len(self.available_devices)
        self._set_status(
            f"Refreshed - Found {device_count} device{'s' if device_count != 1 else ''}"
        )

        # If engine is already initialized and selected devices changed, update it
        selected_devices = self._get_selected_devices()
        if (
            self.tts_engine
            and selected_devices
            and set(self.tts_engine.output_devices) != set(selected_devices)
        ):
            self._update_engine()

    def _on_engine_change(self) -> None:
        """Handle engine selection change."""
        self._load_voices_for_engine()  # Load voices before updating UI
        self._update_ui_for_engine()

        new_engine: str = self.engine_var.get()
        if new_engine != self.current_engine_type:
            self._update_engine()

    def _load_voices_for_engine(self) -> None:
        """Load available voices for the currently selected engine."""
        engine_type: str = self.engine_var.get()

        try:
            if engine_type == "bark":
                # Load Bark voices
                from settings import BARK_VOICES

                self.available_voices = ["Default"] + list(BARK_VOICES.keys())

                # Set default if current value is not valid for Bark
                current_voice = self.voice_var.get()
                if (
                    not current_voice
                    or current_voice == "Default"
                    or not current_voice.startswith("v2/")
                ):
                    self.voice_var.set(settings.DEFAULT_BARK_SPEAKER)
            else:  # say
                # Load Say voices
                try:
                    voices = SayTTSEngine.list_available_voices()
                    self.available_voices = ["Default"] + [voice[0] for voice in voices]

                    # Set default if current value is not valid for Say
                    current_voice = self.voice_var.get()
                    if not current_voice or current_voice.startswith("v2/"):
                        self.voice_var.set("Default")
                except Exception as e:
                    logger.error(f"Failed to load Say voices: {e}")
                    self.available_voices = ["Default", "Alex", "Samantha", "Victoria"]
                    self.voice_var.set("Default")

            # Update combobox values
            self.voice_combo["values"] = self.available_voices

        except Exception as e:
            logger.error(
                f"Failed to load voices for engine '{engine_type}': {e}", exc_info=True
            )
            self.available_voices = ["Default"]
            self.voice_combo["values"] = self.available_voices
            self.voice_var.set("Default")

    def _update_ui_for_engine(self) -> None:
        """Update UI elements based on selected engine."""
        engine_type: str = self.engine_var.get()

        if engine_type == "bark":
            # Update voice help for Bark
            self.voice_help.config(text=settings.VOICE_HELP_BARK)
            # Show sample rate for Bark
            self.sample_rate_label.grid()
            self.sample_rate_combo.grid()
        else:
            # Update voice help for Say
            self.voice_help.config(text=settings.VOICE_HELP_SAY)
            # Hide sample rate for Say (not applicable)
            self.sample_rate_label.grid_remove()
            self.sample_rate_combo.grid_remove()

    def _get_selected_devices(self) -> list[str]:
        """Get list of currently selected devices."""
        return [
            device_name for device_name, var in self.device_vars.items() if var.get()
        ]

    def _on_playback_speed_change(self, value: str) -> None:
        """Handle playback speed slider change."""
        speed = float(value)
        self.playback_speed_value_label.config(text=f"{speed:.1f}x")

    def _update_engine(self) -> None:
        """Recreate the TTS engine with current settings."""
        engine_type: str = self.engine_var.get()
        selected_devices: list[str] = self._get_selected_devices()
        voice: str = self.voice_var.get().strip()
        sample_rate: int = int(self.sample_rate_var.get())
        playback_speed: float = self.playback_speed_var.get()

        if not selected_devices:
            self._set_status("Error: Please select at least one output device")
            return

        try:
            self._set_status("Initializing engine...")

            engine_class: type[TTSEngine] = self.engines[engine_type]["class"]

            if engine_type == "say":
                # Handle "Default" option
                voice_to_use = None if voice == "Default" or not voice else voice
                self.tts_engine = engine_class(
                    output_devices=selected_devices,
                    voice=voice_to_use,
                    timeout=settings.SAY_ENGINE_TIMEOUT,
                    playback_speed=playback_speed,
                )
            else:  # bark
                # Handle "Default" option
                voice_to_use = (
                    settings.DEFAULT_BARK_SPEAKER
                    if voice == "Default" or not voice
                    else voice
                )
                self.tts_engine = engine_class(
                    output_devices=selected_devices,
                    voice_preset=voice_to_use,
                    sample_rate=sample_rate,
                    playback_speed=playback_speed,
                )

            self.current_engine_type = engine_type
            engine_name: str = self.engines[engine_type]["name"]
            device_count: str = (
                f"{len(selected_devices)} device{'s' if len(selected_devices) > 1 else ''}"
            )
            speed_info: str = f" @ {playback_speed:.1f}x" if playback_speed != 1.0 else ""
            self._set_status(f"Ready - Using {engine_name} ({device_count}){speed_info}")

        except ImportError as e:
            if "bark" in str(e).lower():
                self._set_status(
                    "Error: Bark not installed. Install with: uv pip install .[bark]"
                )
                # Fall back to say
                self.engine_var.set("say")
                self._update_engine()
            else:
                self._set_status(f"Error: {e}")
        except Exception as e:
            self._set_status(f"Error initializing engine: {e}")

    def _on_speak(self) -> None:
        """Handle speak button click."""
        # Check and set processing flag atomically
        with self.processing_lock:
            if self.is_processing:
                self._set_status("Already processing...")
                return
            self.is_processing = True

        try:
            text: str = self.text_input.get("1.0", tk.END).strip()
            if not text:
                self._set_status("Please enter some text")
                with self.processing_lock:
                    self.is_processing = False
                return

            # Get selected devices
            selected_devices: list[str] = self._get_selected_devices()
            if not selected_devices:
                self._set_status("Error: Please select at least one output device")
                with self.processing_lock:
                    self.is_processing = False
                return

            # Update engine if settings changed
            voice: str = self.voice_var.get().strip()

            # Check if we need to reinitialize
            needs_reinit = False

            if not self.tts_engine:
                needs_reinit = True
            elif set(self.tts_engine.output_devices) != set(selected_devices):
                needs_reinit = True
            elif isinstance(self.tts_engine, SayTTSEngine):
                # Check if Say voice changed
                voice_to_check = None if voice == "Default" or not voice else voice
                if self.tts_engine.voice != voice_to_check:
                    needs_reinit = True
            elif isinstance(self.tts_engine, BarkTTSEngine):
                # Check if Bark settings changed
                current_sample_rate = int(self.sample_rate_var.get())
                voice_to_check = (
                    settings.DEFAULT_BARK_SPEAKER
                    if voice == "Default" or not voice
                    else voice
                )
                if (
                    self.tts_engine.voice_preset != voice_to_check
                    or self.tts_engine.sample_rate != current_sample_rate
                ):
                    needs_reinit = True

            # Check if playback speed changed
            current_speed = self.playback_speed_var.get()
            if abs(self.tts_engine.playback_speed - current_speed) > 0.01:
                needs_reinit = True

            if needs_reinit:
                self._update_engine()

            # Clear any previous cancel flag and update buttons
            self.cancel_event.clear()
            self.speak_button.config(state="disabled")
            self.stop_button.config(state="normal")

            # Speak in background thread
            threading.Thread(
                target=self._speak_threaded, args=(text,), daemon=True
            ).start()
        except Exception as e:
            # If any error occurs before thread starts, reset processing flag
            with self.processing_lock:
                self.is_processing = False
            raise

    def _on_stop(self) -> None:
        """Handle stop button click."""
        with self.processing_lock:
            if not self.is_processing:
                return

        # Signal cancellation
        self.cancel_event.set()
        self._set_status("Stopping...")
        logger.info("Stop requested by user")

    def _speak_threaded(self, text: str) -> None:
        """Speak text in a background thread."""
        # Show progress bar if using Bark
        is_bark = isinstance(self.tts_engine, BarkTTSEngine)
        if is_bark:
            self.root.after(0, lambda: self._show_progress())
            self.root.after(
                0,
                lambda: self._set_status(
                    "Generating speech with Bark AI (this may take 5-15 seconds)..."
                ),
            )
        else:
            self.root.after(0, lambda: self._set_status("Generating speech..."))

        try:
            self.tts_engine.process_text(text, self.cancel_event)  # type: ignore[union-attr]

            # Check if cancelled
            if self.cancel_event.is_set():
                self.root.after(0, lambda: self._set_status("Stopped"))
            else:
                self.root.after(0, lambda: self._set_status("Playback complete"))
        except Exception as e:
            error_msg: str = f"Error: {str(e)}"
            self.root.after(0, lambda: self._set_status(error_msg))
            logger.error(f"Error during TTS processing: {e}", exc_info=True)
        finally:
            # Hide progress bar
            if is_bark:
                self.root.after(0, lambda: self._hide_progress())

            with self.processing_lock:
                self.is_processing = False
            self.root.after(0, lambda: self.speak_button.config(state="normal"))
            self.root.after(0, lambda: self.stop_button.config(state="disabled"))

    def _on_clear(self) -> None:
        """Clear the text input."""
        self.text_input.delete("1.0", tk.END)
        self.text_input.focus()

    def _show_progress(self) -> None:
        """Show and start the progress bar animation."""
        self.progress_bar.grid()
        self.progress_bar.start(10)  # Update every 10ms

    def _hide_progress(self) -> None:
        """Stop and hide the progress bar."""
        self.progress_bar.stop()
        self.progress_bar.grid_remove()

    def _set_status(self, message: str) -> None:
        """Update the status bar."""
        self.status_var.set(message)
        logger.info(f"Status: {message}")


def main() -> None:
    """Main entry point for the GUI application."""
    root: tk.Tk = tk.Tk()

    # Tkinter on macOS already uses native appearance by default
    app = TTSApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
