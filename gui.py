#!/usr/bin/env python3
"""
macOS TTS to Device - GUI Application

A minimalistic Tkinter-based GUI for routing text-to-speech audio to specific devices.
"""

import logging
import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
from typing import Optional, Any

from src import TTSEngine, TTSManager
from src.utils import setup_logging
import settings

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# Constants
DEFAULT_VOICE_OPTION = "Default"
ENGINE_SAY = "say"
ENGINE_BARK = "bark"


class TTSApp:
    """Minimalistic TTS GUI Application."""

    def __init__(self, root: tk.Tk) -> None:
        self.root: tk.Tk = root
        self.root.title(settings.WINDOW_TITLE)
        self.root.geometry(f"{settings.WINDOW_WIDTH}x{settings.WINDOW_HEIGHT}")
        self.root.resizable(True, True)

        # Manager for orchestration
        self.manager = TTSManager()
        self.manager.on_status_change = self._set_status
        self.manager.on_processing_start = self._on_processing_start
        self.manager.on_processing_end = self._on_processing_end
        self.manager.on_history_update = self._refresh_history_list

        # State for UI
        self.current_engine_type: str = settings.DEFAULT_ENGINE

        # Available engines (for UI selection)
        self.engines: dict[str, dict[str, Any]] = {}
        for engine_id, engine_class in TTSEngine.get_registered_engines().items():
            self.engines[engine_id] = {
                "class": engine_class,
                "name": engine_class.display_name,
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
        self.volume_var: tk.DoubleVar
        self.volume_scale: ttk.Scale
        self.volume_label: ttk.Label
        self.volume_value_label: ttk.Label
        self.voice_var: tk.StringVar
        self.voice_help: ttk.Label
        self.voice_combo: ttk.Combobox
        self.preview_button: ttk.Button
        self.voice_name_to_id: dict[str, str] = {}
        self.available_voices: list[str] = []
        self.text_input: scrolledtext.ScrolledText
        self.speak_button: ttk.Button
        self.stop_button: ttk.Button
        self.status_var: tk.StringVar
        self.progress_bar: ttk.Progressbar

        self.profile_var: tk.StringVar
        self.history_listbox: Optional[tk.Listbox] = None

        # Create UI
        self._create_widgets()
        self._load_audio_devices()
        self._load_voices_for_engine()  # Load voices for initial engine
        self._update_ui_for_engine()  # Hide/show elements based on initial engine
        self._initialize_default_engine()

    def _on_processing_start(self) -> None:
        """Handle processing start (UI updates)."""
        engine_id = self.engine_var.get()
        if engine_id == ENGINE_BARK:
            self.root.after(0, self._show_progress)

        self.root.after(0, lambda: self.speak_button.config(state="disabled"))
        self.root.after(0, lambda: self.preview_button.config(state="disabled"))
        self.root.after(0, lambda: self.stop_button.config(state="normal"))

    def _on_processing_end(self) -> None:
        """Handle processing end (UI updates)."""
        self.root.after(0, self._hide_progress)
        self.root.after(0, lambda: self.speak_button.config(state="normal"))
        self.root.after(0, lambda: self.preview_button.config(state="normal"))
        self.root.after(0, lambda: self.stop_button.config(state="disabled"))

    def _create_widgets(self) -> None:
        """Create all UI widgets."""

        # Use Notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab 1: TTS Interface
        main_tab = ttk.Frame(self.notebook)
        self.notebook.add(main_tab, text="TTS")

        # Main container with padding (now inside main_tab)
        main_frame: ttk.Frame = ttk.Frame(main_tab, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Tab 2: History
        history_tab = ttk.Frame(self.notebook)
        self.notebook.add(history_tab, text="History")
        self._create_history_widgets(history_tab)

        # Configure grid weights for responsiveness
        main_tab.columnconfigure(0, weight=1)
        main_tab.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(
            7, weight=1
        )  # Updated from 6 to 7 for playback speed row

        # ===== Top Section: Profile & Engine =====
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        top_frame.columnconfigure(1, weight=1)

        # Profile Group
        profile_group = ttk.LabelFrame(top_frame, text="Profile", padding=10)
        profile_group.grid(
            row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5)
        )
        profile_group.columnconfigure(0, weight=1)

        profile_inner = ttk.Frame(profile_group)
        profile_inner.pack(fill=tk.X)

        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(
            profile_inner,
            textvariable=self.profile_var,
            state="readonly",
        )
        self.profile_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_select)
        self._refresh_profile_list()

        ttk.Button(
            profile_inner, text="Save", command=self._on_profile_save, width=8
        ).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Button(
            profile_inner, text="Delete", command=self._on_profile_delete, width=8
        ).pack(side=tk.LEFT, padx=(5, 0))

        # Engine Group
        engine_group = ttk.LabelFrame(top_frame, text="Engine Settings", padding=10)
        engine_group.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.engine_var = tk.StringVar(value=settings.DEFAULT_ENGINE)
        engine_row_frame = ttk.Frame(engine_group)
        engine_row_frame.pack(fill=tk.X)

        # Engine selection
        engine_selection_frame = ttk.Frame(engine_row_frame)
        engine_selection_frame.pack(side=tk.LEFT)

        for engine_id, engine_info in self.engines.items():
            ttk.Radiobutton(
                engine_selection_frame,
                text=engine_info["name"],
                variable=self.engine_var,
                value=engine_id,
                command=self._on_engine_change,
            ).pack(side=tk.LEFT, padx=5)

        # Sample Rate (Bark only)
        self.sample_rate_frame = ttk.Frame(engine_row_frame)
        self.sample_rate_frame.pack(side=tk.RIGHT)

        self.sample_rate_label = ttk.Label(self.sample_rate_frame, text="Rate:")
        self.sample_rate_label.pack(side=tk.LEFT, padx=(5, 2))

        self.sample_rate_var = tk.StringVar(value=settings.DEFAULT_SAMPLE_RATE)
        self.sample_rate_combo = ttk.Combobox(
            self.sample_rate_frame,
            textvariable=self.sample_rate_var,
            values=settings.AVAILABLE_SAMPLE_RATES,
            width=8,
            state="readonly",
        )
        self.sample_rate_combo.pack(side=tk.LEFT)

        # ===== Middle Section: Devices and Voice =====
        middle_frame = ttk.Frame(main_frame)
        middle_frame.grid(
            row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S)
        )
        middle_frame.columnconfigure(0, weight=1)
        middle_frame.columnconfigure(1, weight=1)

        # Output Devices Group
        device_group = ttk.LabelFrame(middle_frame, text="Audio Output", padding=10)
        device_group.grid(
            row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5), pady=5
        )

        device_header = ttk.Frame(device_group)
        device_header.pack(fill=tk.X)

        ttk.Button(
            device_header,
            text="↻ Refresh Devices",
            command=self._on_refresh_devices,
        ).pack(fill=tk.X, pady=(0, 5))

        self.device_frame = ttk.Frame(device_group)
        self.device_frame.pack(fill=tk.BOTH, expand=True)

        # Voice Settings Group
        voice_group = ttk.LabelFrame(middle_frame, text="Voice & Playback", padding=10)
        voice_group.grid(
            row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0), pady=5
        )

        # Playback Speed
        ttk.Label(voice_group, text="Speed:").pack(anchor=tk.W)
        speed_inner = ttk.Frame(voice_group)
        speed_inner.pack(fill=tk.X, pady=(0, 5))

        self.playback_speed_var = tk.DoubleVar(value=settings.DEFAULT_PLAYBACK_SPEED)
        self.playback_speed_scale = ttk.Scale(
            speed_inner,
            from_=settings.MIN_PLAYBACK_SPEED,
            to=settings.MAX_PLAYBACK_SPEED,
            variable=self.playback_speed_var,
            orient=tk.HORIZONTAL,
            command=self._on_playback_speed_change,
        )
        self.playback_speed_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.playback_speed_value_label = ttk.Label(speed_inner, text="1.0x", width=6)
        self.playback_speed_value_label.pack(side=tk.LEFT, padx=(5, 0))

        # Volume
        ttk.Label(voice_group, text="Volume:").pack(anchor=tk.W)
        volume_inner = ttk.Frame(voice_group)
        volume_inner.pack(fill=tk.X, pady=(0, 5))

        self.volume_var = tk.DoubleVar(value=settings.DEFAULT_VOLUME)
        self.volume_scale = ttk.Scale(
            volume_inner,
            from_=0.0,
            to=1.0,
            variable=self.volume_var,
            orient=tk.HORIZONTAL,
            command=self._on_volume_change,
        )
        self.volume_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.volume_value_label = ttk.Label(volume_inner, text="100%", width=6)
        self.volume_value_label.pack(side=tk.LEFT, padx=(5, 0))

        # Voice selection
        ttk.Label(voice_group, text="Voice/Speaker:").pack(anchor=tk.W)
        voice_inner_frame = ttk.Frame(voice_group)
        voice_inner_frame.pack(fill=tk.X, pady=(0, 2))

        self.voice_var = tk.StringVar(value=settings.DEFAULT_SAY_VOICE)
        self.voice_combo = ttk.Combobox(
            voice_inner_frame,
            textvariable=self.voice_var,
            state="readonly",
        )
        self.voice_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.preview_button = ttk.Button(
            voice_group, text="▶ Preview Voice", command=self._on_preview
        )
        self.preview_button.pack(fill=tk.X, pady=(2, 0))

        self.voice_help = ttk.Label(
            voice_group,
            text=settings.VOICE_HELP_SAY,
            font=("", settings.HELP_TEXT_FONT_SIZE),
            foreground="gray",
            wraplength=200,
        )
        self.voice_help.pack(anchor=tk.W, pady=(5, 0))

        # ===== Bottom Section: Text Input =====
        text_group = ttk.LabelFrame(main_frame, text="Text to Speak", padding=10)
        text_group.grid(
            row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0)
        )
        text_group.columnconfigure(0, weight=1)
        text_group.rowconfigure(0, weight=1)

        self.text_input = scrolledtext.ScrolledText(
            text_group,
            height=6,
            width=settings.TEXT_INPUT_WIDTH,
            wrap=tk.WORD,
            font=("", settings.TEXT_INPUT_FONT_SIZE),
        )
        self.text_input.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.text_input.focus()

        # Bindings
        self.text_input.bind("<Command-Return>", lambda e: self._on_speak())
        self.text_input.bind("<Control-Return>", lambda e: self._on_speak())
        self.root.bind("<Escape>", lambda e: self._on_stop())

        # ===== Control Buttons =====
        control_frame = ttk.Frame(main_frame, padding=(0, 10, 0, 0))
        control_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E))

        self.speak_button = ttk.Button(
            control_frame,
            text="Speak (⌘+Enter)",
            command=self._on_speak,
        )
        self.speak_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        ttk.Button(
            control_frame,
            text="Export to File",
            command=self._on_export,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.stop_button = ttk.Button(
            control_frame,
            text="⏹ Stop",
            command=self._on_stop,
            state="disabled",
        )
        self.stop_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Button(control_frame, text="Clear", command=self._on_clear).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0)
        )

        # ===== Progress & Status =====
        self.progress_bar = ttk.Progressbar(
            main_frame,
            mode="indeterminate",
        )
        self.progress_bar.grid(
            row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0)
        )
        self.progress_bar.grid_remove()

        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2),
        )
        status_bar.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))

    def _refresh_profile_list(self) -> None:
        """Update the profile combobox with current profile names."""
        profiles = self.manager.profile_manager.list_profiles()
        self.profile_combo["values"] = profiles
        if not self.profile_var.get() and profiles:
            self.profile_combo.set("")

    def _on_profile_select(self, event: Optional[tk.Event] = None) -> None:
        """Load settings from the selected profile."""
        profile_name = self.profile_var.get()
        profile = self.manager.profile_manager.get_profile(profile_name)
        if not profile:
            return

        try:
            # Set engine
            engine_id = profile.get("engine")
            if engine_id in self.engines:
                self.engine_var.set(engine_id)
                self._on_engine_change()

            # Set voice
            voice_id = profile.get("voice")
            if voice_id:
                # Find the display name for this ID
                display_name = voice_id
                for v_name, vid in self.voice_name_to_id.items():
                    if vid == voice_id:
                        display_name = v_name
                        break
                self.voice_var.set(display_name)

            # Set speed
            speed = profile.get("speed", settings.DEFAULT_PLAYBACK_SPEED)
            self.playback_speed_var.set(speed)
            self._on_playback_speed_change(str(speed))

            # Set volume
            volume = profile.get("volume", 1.0)
            self.volume_var.set(volume)
            self._on_volume_change(str(volume))

            # Set sample rate if applicable (only if valid)
            sample_rate = profile.get("sample_rate")
            if sample_rate:
                sample_rate_str = str(sample_rate)
                if sample_rate_str in settings.AVAILABLE_SAMPLE_RATES:
                    self.sample_rate_var.set(sample_rate_str)

            # Set devices
            devices = profile.get("devices", [])
            for device_name, var in self.device_vars.items():
                var.set(device_name in devices)

            self._set_status(f"Loaded profile: {profile_name}")
        except Exception as e:
            logger.error(f"Failed to load profile '{profile_name}': {e}")
            self._set_status(f"Error loading profile: {e}")

    def _on_profile_save(self) -> None:
        """Save current settings to a profile."""
        from tkinter import simpledialog, messagebox

        name = simpledialog.askstring(
            "Save Profile",
            "Enter profile name:",
            initialvalue=self.profile_var.get(),
            parent=self.root,
        )
        if not name:
            return

        voice_name = self.voice_var.get()
        voice_id = self.voice_name_to_id.get(voice_name, voice_name)

        settings_dict = {
            "engine": self.engine_var.get(),
            "voice": voice_id,
            "speed": self.playback_speed_var.get(),
            "volume": self.volume_var.get(),
            "sample_rate": self.sample_rate_var.get(),
            "devices": self._get_selected_devices(),
        }

        if self.manager.profile_manager.save_profile(name, settings_dict):
            self._refresh_profile_list()
            self.profile_var.set(name)
            self._set_status(f"Saved profile: {name}")
        else:
            messagebox.showerror("Error", f"Failed to save profile '{name}'")

    def _on_profile_delete(self) -> None:
        """Delete the currently selected profile."""
        from tkinter import messagebox

        name = self.profile_var.get()
        if not name:
            messagebox.showinfo("Delete Profile", "Please select a profile to delete.")
            return

        if messagebox.askyesno(
            "Delete Profile", f"Are you sure you want to delete profile '{name}'?"
        ):
            if self.manager.profile_manager.delete_profile(name):
                self._refresh_profile_list()
                self.profile_var.set("")
                self._set_status(f"Deleted profile: {name}")
            else:
                messagebox.showerror("Error", f"Failed to delete profile '{name}'")

    def _create_history_widgets(self, parent: ttk.Frame) -> None:
        """Create widgets for the history tab with more controls."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        # Listbox for history entries
        history_frame = ttk.Frame(parent, padding="10")
        history_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)

        self.history_listbox = tk.Listbox(
            history_frame,
            font=("", settings.TEXT_INPUT_FONT_SIZE),
            selectmode=tk.SINGLE,
        )
        self.history_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Scrollbar for listbox
        scrollbar = ttk.Scrollbar(
            history_frame, orient=tk.VERTICAL, command=self.history_listbox.yview
        )
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.history_listbox.config(yscrollcommand=scrollbar.set)

        # Bind double-click or enter to load from history
        self.history_listbox.bind(
            "<Double-Button-1>", lambda e: self._on_history_load()
        )
        self.history_listbox.bind("<Return>", lambda e: self._on_history_load())
        self.history_listbox.bind("<Delete>", lambda e: self._on_history_delete())

        # Buttons frame
        btn_frame = ttk.Frame(history_frame, padding=(0, 10, 0, 0))
        btn_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))

        ttk.Button(
            btn_frame, text="Replay", command=self._on_history_replay, width=12
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            btn_frame, text="Load Settings", command=self._on_history_load, width=15
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            btn_frame, text="Delete Item", command=self._on_history_delete, width=12
        ).pack(side=tk.LEFT, padx=2)

        ttk.Frame(btn_frame).pack(side=tk.LEFT, expand=True)  # Spacer

        ttk.Button(
            btn_frame, text="Clear All", command=self._on_history_clear, width=12
        ).pack(side=tk.RIGHT, padx=2)

        self._refresh_history_list()

    def _refresh_history_list(self) -> None:
        """Update the history listbox with current entries."""
        if not self.history_listbox:
            return

        self.history_listbox.delete(0, tk.END)
        for entry in self.manager.history_manager.get_history():
            # Format: [Timestamp] Engine: Text...
            ts = datetime.fromisoformat(entry["timestamp"]).strftime("%H:%M:%S")
            text_preview = entry["text"].replace("\n", " ")[:40]
            if len(entry["text"]) > 40:
                text_preview += "..."
            label = f"[{ts}] {entry['engine']}: {text_preview}"
            self.history_listbox.insert(tk.END, label)

    def _on_history_load(self) -> None:
        """Load settings and text from the selected history item."""
        selection = self.history_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        entry = self.manager.history_manager.get_history()[index]

        try:
            # Set text
            self.text_input.delete("1.0", tk.END)
            self.text_input.insert("1.0", entry["text"])

            # Set engine
            engine_id = entry.get("engine")
            if engine_id in self.engines:
                self.engine_var.set(engine_id)
                self._on_engine_change()

            # Set voice
            voice_id = entry.get("voice")
            if voice_id:
                # Find the display name for this ID
                display_name = voice_id
                for name, vid in self.voice_name_to_id.items():
                    if vid == voice_id:
                        display_name = name
                        break
                self.voice_var.set(display_name)

            # Set speed
            speed = entry.get("speed", settings.DEFAULT_PLAYBACK_SPEED)
            self.playback_speed_var.set(speed)
            self._on_playback_speed_change(str(speed))

            # Set volume
            volume = entry.get("volume", 1.0)
            self.volume_var.set(volume)
            self._on_volume_change(str(volume))

            # Set sample rate (only if valid for current engine)
            sample_rate = entry.get("sample_rate")
            if sample_rate:
                sample_rate_str = str(sample_rate)
                if sample_rate_str in settings.AVAILABLE_SAMPLE_RATES:
                    self.sample_rate_var.set(sample_rate_str)

            # Set devices
            devices = entry.get("devices", [])
            for device_name, var in self.device_vars.items():
                var.set(device_name in devices)

            # Switch back to main tab
            self.notebook.select(0)
            self._set_status("Loaded settings from history")

        except Exception as e:
            logger.error(f"Failed to load history item: {e}")
            self._set_status(f"Error loading from history: {e}")

    def _on_history_replay(self) -> None:
        """Instantly replay the selected history item."""
        selection = self.history_listbox.curselection()
        if not selection:
            return

        # First load the settings
        self._on_history_load()
        # Then speak
        self._on_speak()

    def _on_history_delete(self) -> None:
        """Delete the selected history item."""
        if not self.history_listbox:
            return

        selection = self.history_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        if self.manager.history_manager.delete_entry(index):
            self._refresh_history_list()
            self._set_status("Deleted history item")

    def _on_history_clear(self) -> None:
        """Clear all history entries."""
        from tkinter import messagebox

        if messagebox.askyesno(
            "Clear History", "Are you sure you want to clear all history?"
        ):
            self.manager.history_manager.clear_history()
            self._refresh_history_list()
            self._set_status("History cleared")

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
                else:
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
        plural = "" if device_count == 1 else "s"
        self._set_status(f"Refreshed - Found {device_count} device{plural}")

        # If engine is already initialized and selected devices changed, update it
        selected_devices = self._get_selected_devices()
        if (
            self.manager.tts_engine
            and selected_devices
            and set(self.manager.tts_engine.output_devices) != set(selected_devices)
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
        engine_class = self.engines[engine_type]["class"]

        try:
            voice_list = engine_class.list_available_voices()

            # Reset mapping
            self.voice_name_to_id = {DEFAULT_VOICE_OPTION: DEFAULT_VOICE_OPTION}
            self.available_voices = [DEFAULT_VOICE_OPTION]

            # Populate mapping and names
            for v in voice_list:
                if isinstance(v, dict):
                    v_id = v["id"]
                    v_name = v["name"]
                else:
                    # Fallback for any engine not returning dicts yet
                    v_id = v
                    v_name = v

                self.voice_name_to_id[v_name] = v_id
                self.available_voices.append(v_name)

            # Update combobox values
            self.voice_combo["values"] = self.available_voices

            # Try to restore current voice if it exists in the new list, or set default
            current_voice_name = self.voice_var.get()
            if current_voice_name not in self.available_voices:
                if engine_type == ENGINE_BARK:
                    # Look for the default speaker by ID
                    default_id = settings.DEFAULT_BARK_SPEAKER
                    default_name = DEFAULT_VOICE_OPTION
                    for name, vid in self.voice_name_to_id.items():
                        if vid == default_id:
                            default_name = name
                            break
                    self.voice_var.set(default_name)
                else:
                    self.voice_var.set(DEFAULT_VOICE_OPTION)

        except Exception as e:
            logger.error(
                f"Failed to load voices for engine '{engine_type}': {e}", exc_info=True
            )
            self.available_voices = [DEFAULT_VOICE_OPTION]
            self.voice_name_to_id = {DEFAULT_VOICE_OPTION: DEFAULT_VOICE_OPTION}
            self.voice_combo["values"] = self.available_voices
            self.voice_var.set(DEFAULT_VOICE_OPTION)

    def _update_ui_for_engine(self) -> None:
        """Update UI elements based on selected engine."""
        engine_type: str = self.engine_var.get()
        engine_class = self.engines[engine_type]["class"]

        # Update voice help
        if engine_type == ENGINE_BARK:
            self.voice_help.config(text=settings.VOICE_HELP_BARK)
        elif engine_type == ENGINE_SAY:
            self.voice_help.config(text=settings.VOICE_HELP_SAY)
        elif engine_type == "piper":
            self.voice_help.config(text=settings.VOICE_HELP_PIPER)
        else:
            self.voice_help.config(text=f"Select a voice for {engine_type}")

        # Show/hide sample rate based on engine support
        if engine_class.supports_sample_rate:
            self.sample_rate_frame.pack(side=tk.RIGHT, padx=5)
        else:
            self.sample_rate_frame.pack_forget()

    def _get_selected_devices(self) -> list[str]:
        """Get list of currently selected devices."""
        return [
            device_name for device_name, var in self.device_vars.items() if var.get()
        ]

    def _on_playback_speed_change(self, value: str) -> None:
        """Handle playback speed slider change."""
        speed = float(value)
        self.playback_speed_value_label.config(text=f"{speed:.1f}x")

    def _on_volume_change(self, value: str) -> None:
        """Handle volume slider change."""
        volume = float(value)
        self.volume_value_label.config(text=f"{int(volume * 100)}%")

    def _update_engine(self) -> None:
        """Update the TTS engine in the manager."""
        voice_name: str = self.voice_var.get().strip()
        voice_id: str = self.voice_name_to_id.get(voice_name, voice_name)

        success = self.manager.update_engine(
            engine_id=self.engine_var.get(),
            selected_devices=self._get_selected_devices(),
            voice_id=voice_id,
            sample_rate=int(self.sample_rate_var.get()),
            playback_speed=self.playback_speed_var.get(),
            volume=self.volume_var.get(),
        )
        if success:
            self.current_engine_type = self.engine_var.get()

    def _on_speak(self, override_text: Optional[str] = None) -> None:
        """Handle speak button click."""
        text = (
            override_text
            if override_text is not None
            else self.text_input.get("1.0", tk.END).strip()
        )
        voice_name = self.voice_var.get().strip()
        voice_id = self.voice_name_to_id.get(voice_name, voice_name)

        config = {
            "engine_id": self.engine_var.get(),
            "selected_devices": self._get_selected_devices(),
            "voice_id": voice_id,
            "sample_rate": int(self.sample_rate_var.get()),
            "playback_speed": self.playback_speed_var.get(),
            "volume": self.volume_var.get(),
        }
        self.manager.speak(text, config)

    def _on_export(self) -> None:
        """Handle export button click."""
        text = self.text_input.get("1.0", tk.END).strip()
        if not text:
            self._set_status("Please enter some text")
            return

        engine_type = self.engine_var.get()
        ext = "aiff" if engine_type == ENGINE_SAY else "wav"

        file_path = filedialog.asksaveasfilename(
            defaultextension=f".{ext}",
            filetypes=[(f"{ext.upper()} files", f"*.{ext}"), ("All files", "*.*")],
            title="Export Audio",
            initialfile=f"speech_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}",
        )

        if not file_path:
            return

        voice_name = self.voice_var.get().strip()
        voice_id = self.voice_name_to_id.get(voice_name, voice_name)

        config = {
            "engine_id": engine_type,
            "selected_devices": self._get_selected_devices(),
            "voice_id": voice_id,
            "sample_rate": int(self.sample_rate_var.get()),
            "playback_speed": self.playback_speed_var.get(),
            "volume": self.volume_var.get(),
        }
        self.manager.export(text, config, file_path)

    def _on_preview(self) -> None:
        """Handle preview button click."""
        self._on_speak(override_text=settings.VOICE_PREVIEW_TEXT)

    def _on_stop(self) -> None:
        """Handle stop button click."""
        self.manager.stop()

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

    def on_closing() -> None:
        app.manager.shutdown()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
