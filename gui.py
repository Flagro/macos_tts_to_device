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
        self.voice_var: tk.StringVar
        self.voice_help: ttk.Label
        self.voice_entry: ttk.Entry
        self.text_input: scrolledtext.ScrolledText
        self.speak_button: ttk.Button
        self.status_var: tk.StringVar

        # Create UI
        self._create_widgets()
        self._load_audio_devices()
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
        main_frame.rowconfigure(5, weight=1)  # Updated from 4 to 5 for sample rate row

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

        # ===== Voice Selection (Engine-specific) =====
        ttk.Label(main_frame, text="Voice/Speaker:").grid(
            row=3, column=0, sticky=tk.W, pady=5
        )

        self.voice_var = tk.StringVar(value=settings.DEFAULT_SAY_VOICE)
        self.voice_entry = ttk.Entry(main_frame, textvariable=self.voice_var, width=40)
        self.voice_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)

        # Help text for voice
        self.voice_help = ttk.Label(
            main_frame,
            text=settings.VOICE_HELP_SAY,
            font=("", settings.HELP_TEXT_FONT_SIZE),
            foreground="gray",
        )
        self.voice_help.grid(row=4, column=1, sticky=tk.W, padx=5)

        # ===== Text Input =====
        ttk.Label(main_frame, text="Text to Speak:").grid(
            row=5, column=0, sticky=(tk.W, tk.N), pady=5
        )

        self.text_input = scrolledtext.ScrolledText(
            main_frame,
            height=settings.TEXT_INPUT_HEIGHT,
            width=settings.TEXT_INPUT_WIDTH,
            wrap=tk.WORD,
            font=("", settings.TEXT_INPUT_FONT_SIZE),
        )
        self.text_input.grid(
            row=5, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=5
        )
        self.text_input.focus()

        # Bind Enter key (with modifier) to speak
        self.text_input.bind("<Command-Return>", lambda e: self._on_speak())
        self.text_input.bind("<Control-Return>", lambda e: self._on_speak())

        # ===== Buttons =====
        button_frame: ttk.Frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=10)

        self.speak_button = ttk.Button(
            button_frame,
            text="Speak (⌘+Enter)",
            command=self._on_speak,
            width=20,
        )
        self.speak_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Clear", command=self._on_clear, width=15).pack(
            side=tk.LEFT, padx=5
        )

        # ===== Status Bar =====
        self.status_var = tk.StringVar(value="Ready")
        status_bar: ttk.Label = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2),
        )
        status_bar.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

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
        self._update_ui_for_engine()

        new_engine: str = self.engine_var.get()
        if new_engine != self.current_engine_type:
            self._update_engine()

    def _update_ui_for_engine(self) -> None:
        """Update UI elements based on selected engine."""
        engine_type: str = self.engine_var.get()

        if engine_type == "bark":
            # Update voice help for Bark
            self.voice_help.config(text=settings.VOICE_HELP_BARK)
            if not self.voice_var.get() or self.voice_var.get() in [
                "",
                "Alex",
                "Samantha",
            ]:
                self.voice_var.set(settings.DEFAULT_BARK_SPEAKER)
            # Show sample rate for Bark
            self.sample_rate_label.grid()
            self.sample_rate_combo.grid()
        else:
            # Update voice help for Say
            self.voice_help.config(text=settings.VOICE_HELP_SAY)
            if self.voice_var.get().startswith("v2/"):
                self.voice_var.set(settings.DEFAULT_SAY_VOICE)
            # Hide sample rate for Say (not applicable)
            self.sample_rate_label.grid_remove()
            self.sample_rate_combo.grid_remove()

    def _get_selected_devices(self) -> list[str]:
        """Get list of currently selected devices."""
        return [
            device_name for device_name, var in self.device_vars.items() if var.get()
        ]

    def _update_engine(self) -> None:
        """Recreate the TTS engine with current settings."""
        engine_type: str = self.engine_var.get()
        selected_devices: list[str] = self._get_selected_devices()
        voice: str = self.voice_var.get().strip()
        sample_rate: int = int(self.sample_rate_var.get())

        if not selected_devices:
            self._set_status("Error: Please select at least one output device")
            return

        try:
            self._set_status("Initializing engine...")

            engine_class: type[TTSEngine] = self.engines[engine_type]["class"]

            if engine_type == "say":
                self.tts_engine = engine_class(
                    output_devices=selected_devices,
                    voice=voice if voice else None,
                    timeout=settings.SAY_ENGINE_TIMEOUT,
                )
            else:  # bark
                self.tts_engine = engine_class(
                    output_devices=selected_devices,
                    voice_preset=voice if voice else settings.DEFAULT_BARK_SPEAKER,
                    sample_rate=sample_rate,
                )

            self.current_engine_type = engine_type
            engine_name: str = self.engines[engine_type]["name"]
            device_count: str = (
                f"{len(selected_devices)} device{'s' if len(selected_devices) > 1 else ''}"
            )
            self._set_status(f"Ready - Using {engine_name} ({device_count})")

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
                if self.tts_engine.voice != (voice if voice else None):
                    needs_reinit = True
            elif isinstance(self.tts_engine, BarkTTSEngine):
                # Check if Bark settings changed
                current_sample_rate = int(self.sample_rate_var.get())
                if (
                    self.tts_engine.voice_preset != voice
                    or self.tts_engine.sample_rate != current_sample_rate
                ):
                    needs_reinit = True

            if needs_reinit:
                self._update_engine()

            # Disable button in main thread
            self.speak_button.config(state="disabled")

            # Speak in background thread
            threading.Thread(
                target=self._speak_threaded, args=(text,), daemon=True
            ).start()
        except Exception as e:
            # If any error occurs before thread starts, reset processing flag
            with self.processing_lock:
                self.is_processing = False
            raise

    def _speak_threaded(self, text: str) -> None:
        """Speak text in a background thread."""
        self.root.after(0, lambda: self._set_status("Generating speech..."))

        try:
            self.tts_engine.process_text(text)  # type: ignore[union-attr]
            self.root.after(0, lambda: self._set_status("Playback complete"))
        except Exception as e:
            error_msg: str = f"Error: {str(e)}"
            self.root.after(0, lambda: self._set_status(error_msg))
            logger.error(f"Error during TTS processing: {e}", exc_info=True)
        finally:
            with self.processing_lock:
                self.is_processing = False
            self.root.after(0, lambda: self.speak_button.config(state="normal"))

    def _on_clear(self) -> None:
        """Clear the text input."""
        self.text_input.delete("1.0", tk.END)
        self.text_input.focus()

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
