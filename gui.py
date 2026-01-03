#!/usr/bin/env python3
"""
macOS TTS to Device - GUI Application

A minimalistic Tkinter-based GUI for routing text-to-speech audio to specific devices.
"""

import logging
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Optional, Union, Dict, Any

from src import SayTTSEngine, BarkTTSEngine
from src.tts_base import TTSEngine

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


class TTSApp:
    """Minimalistic TTS GUI Application."""

    def __init__(self, root: tk.Tk) -> None:
        self.root: tk.Tk = root
        self.root.title("macOS TTS to Device")
        self.root.geometry("600x500")
        self.root.resizable(True, True)

        # State
        self.tts_engine: Optional[Union[SayTTSEngine, BarkTTSEngine]] = None
        self.is_processing: bool = False
        self.current_engine_type: str = "say"

        # Available engines
        self.engines: Dict[str, Dict[str, Any]] = {
            "say": {"class": SayTTSEngine, "name": "macOS Say (Fast)"},
            "bark": {"class": BarkTTSEngine, "name": "Bark AI (Natural)"},
        }

        # Available audio devices
        self.available_devices: list[str] = []

        # UI Elements (will be initialized in _create_widgets)
        self.engine_var: tk.StringVar
        self.device_var: tk.StringVar
        self.device_combo: ttk.Combobox
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

        self.engine_var = tk.StringVar(value="say")
        engine_frame: ttk.Frame = ttk.Frame(main_frame)
        engine_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)

        ttk.Radiobutton(
            engine_frame,
            text="macOS Say (Fast)",
            variable=self.engine_var,
            value="say",
            command=self._on_engine_change,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(
            engine_frame,
            text="Bark AI (Natural)",
            variable=self.engine_var,
            value="bark",
            command=self._on_engine_change,
        ).pack(side=tk.LEFT, padx=5)

        # ===== Output Device =====
        ttk.Label(main_frame, text="Output Device:").grid(
            row=1, column=0, sticky=tk.W, pady=5
        )

        self.device_var = tk.StringVar(value="BlackHole 16ch")
        self.device_combo = ttk.Combobox(
            main_frame, textvariable=self.device_var, width=37, state="readonly"
        )
        self.device_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)

        # ===== Sample Rate Selection =====
        self.sample_rate_label = ttk.Label(main_frame, text="Sample Rate:")
        self.sample_rate_label.grid(row=2, column=0, sticky=tk.W, pady=5)

        self.sample_rate_var = tk.StringVar(value="24000")
        self.sample_rate_combo = ttk.Combobox(
            main_frame,
            textvariable=self.sample_rate_var,
            values=["16000", "22050", "24000", "44100", "48000"],
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

        self.voice_var = tk.StringVar(value="")
        self.voice_entry = ttk.Entry(main_frame, textvariable=self.voice_var, width=40)
        self.voice_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)

        # Help text for voice
        self.voice_help = ttk.Label(
            main_frame,
            text="(Optional) e.g., 'Alex', 'Samantha' - leave empty for default",
            font=("", 9),
            foreground="gray",
        )
        self.voice_help.grid(row=4, column=1, sticky=tk.W, padx=5)

        # ===== Text Input =====
        ttk.Label(main_frame, text="Text to Speak:").grid(
            row=5, column=0, sticky=(tk.W, tk.N), pady=5
        )

        self.text_input = scrolledtext.ScrolledText(
            main_frame, height=10, width=50, wrap=tk.WORD, font=("", 11)
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
        """Load available audio devices into the dropdown."""
        try:
            devices = TTSEngine.list_available_devices()
            self.available_devices = [device["name"] for device in devices]

            if self.available_devices:
                self.device_combo["values"] = self.available_devices

                # Try to select BlackHole 16ch if available, otherwise first device
                if "BlackHole 16ch" in self.available_devices:
                    self.device_var.set("BlackHole 16ch")
                else:
                    self.device_var.set(self.available_devices[0])
            else:
                self.device_combo["values"] = ["No devices found"]
                self.device_var.set("No devices found")
                self._set_status("Warning: No audio output devices found")

        except Exception as e:
            logger.error(f"Failed to load audio devices: {e}", exc_info=True)
            self.device_combo["values"] = ["Error loading devices"]
            self.device_var.set("Error loading devices")
            self._set_status(f"Error loading devices: {e}")

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
            self.voice_help.config(
                text="(Optional) e.g., 'v2/en_speaker_6' - leave empty for default"
            )
            if not self.voice_var.get() or self.voice_var.get() in [
                "",
                "Alex",
                "Samantha",
            ]:
                self.voice_var.set("v2/en_speaker_6")
            # Show sample rate for Bark
            self.sample_rate_label.grid()
            self.sample_rate_combo.grid()
        else:
            # Update voice help for Say
            self.voice_help.config(
                text="(Optional) e.g., 'Alex', 'Samantha' - leave empty for default"
            )
            if self.voice_var.get().startswith("v2/"):
                self.voice_var.set("")
            # Hide sample rate for Say (not applicable)
            self.sample_rate_label.grid_remove()
            self.sample_rate_combo.grid_remove()

    def _update_engine(self) -> None:
        """Recreate the TTS engine with current settings."""
        engine_type: str = self.engine_var.get()
        device: str = self.device_var.get().strip()
        voice: str = self.voice_var.get().strip()
        sample_rate: int = int(self.sample_rate_var.get())

        if not device:
            device = "BlackHole 16ch"

        try:
            self._set_status("Initializing engine...")

            engine_class: type[TTSEngine] = self.engines[engine_type]["class"]

            if engine_type == "say":
                self.tts_engine = engine_class(
                    output_devices=[device],
                    voice=voice if voice else None,
                    timeout=30,
                )
            else:  # bark
                self.tts_engine = engine_class(
                    output_devices=[device],
                    voice_preset=voice if voice else "v2/en_speaker_6",
                    sample_rate=sample_rate,
                )

            self.current_engine_type = engine_type
            engine_name: str = self.engines[engine_type]["name"]
            self._set_status(f"Ready - Using {engine_name}")

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
        if self.is_processing:
            self._set_status("Already processing...")
            return

        text: str = self.text_input.get("1.0", tk.END).strip()
        if not text:
            self._set_status("Please enter some text")
            return

        # Update engine if settings changed
        device: str = self.device_var.get().strip()
        voice: str = self.voice_var.get().strip()

        # Check if we need to reinitialize
        if (
            not self.tts_engine
            or (
                isinstance(self.tts_engine, SayTTSEngine)
                and self.tts_engine.voice != (voice if voice else None)
            )
            or self.tts_engine.output_devices != [device]
        ):
            self._update_engine()

        # Speak in background thread
        threading.Thread(target=self._speak_threaded, args=(text,), daemon=True).start()

    def _speak_threaded(self, text: str) -> None:
        """Speak text in a background thread."""
        self.is_processing = True
        self.root.after(0, lambda: self.speak_button.config(state="disabled"))
        self.root.after(0, lambda: self._set_status("Generating speech..."))

        try:
            self.tts_engine.process_text(text)  # type: ignore[union-attr]
            self.root.after(0, lambda: self._set_status("Playback complete"))
        except Exception as e:
            error_msg: str = f"Error: {str(e)}"
            self.root.after(0, lambda: self._set_status(error_msg))
            logger.error(f"Error during TTS processing: {e}", exc_info=True)
        finally:
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
