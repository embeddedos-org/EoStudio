"""Promo Video Editor — create promotional content for App Store, social media, product launches."""

from __future__ import annotations

import json
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
from typing import Any, Dict, List, Optional

from eostudio.core.video.compositor import VideoCompositor, Layer, LayerType, LayerTransform
from eostudio.core.video.promo_templates import (
    PROMO_TEMPLATES, get_template, list_templates, template_categories, PromoTemplate,
)
from eostudio.core.video.export import VideoExporter, ExportConfig, ExportFormat, ExportPreset, PRESET_SIZES
from eostudio.core.video.recorder import ScreenRecorder, RecordingConfig
from eostudio.gui.widgets.timeline import TimelineWidget


class PromoEditor(tk.Frame):
    """Video and promotional content editor with templates, compositor, and export."""

    def __init__(self, master: tk.Widget, bg: str = "#1e1e2e", fg: str = "#cdd6f4", **kw: Any):
        super().__init__(master, bg=bg, **kw)
        self._bg = bg
        self._fg = fg
        self._compositor: Optional[VideoCompositor] = None
        self._current_template: Optional[PromoTemplate] = None
        self._current_time = 0.0
        self._playing = False

        self._build_ui()

    def _build_ui(self) -> None:
        # ---- Left: Templates ----
        left = tk.Frame(self, bg=self._bg, width=200)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        tk.Label(left, text="Promo Templates", bg=self._bg, fg=self._fg,
                 font=("Segoe UI", 11, "bold")).pack(fill=tk.X, padx=8, pady=(8, 4))

        for category in template_categories():
            cat_frame = tk.LabelFrame(left, text=category.title(), bg=self._bg,
                                      fg="#f9e2af", font=("Segoe UI", 8, "bold"),
                                      bd=1, relief=tk.GROOVE)
            cat_frame.pack(fill=tk.X, padx=4, pady=2)
            for tmpl in list_templates(category):
                btn = tk.Button(cat_frame, text=tmpl.name.replace("_", " ").title(),
                                bg="#313244", fg="#89b4fa", relief=tk.FLAT,
                                font=("Segoe UI", 8), anchor=tk.W, padx=6,
                                command=lambda t=tmpl: self._load_template(t))
                btn.pack(fill=tk.X, padx=2, pady=1)

        # Custom settings
        settings_frame = tk.LabelFrame(left, text="Settings", bg=self._bg,
                                       fg="#a6e3a1", font=("Segoe UI", 8, "bold"),
                                       bd=1, relief=tk.GROOVE)
        settings_frame.pack(fill=tk.X, padx=4, pady=4)

        for label, var_name, default in [
            ("Product Name", "_product_name_var", "My Product"),
            ("Tagline", "_tagline_var", "The next big thing"),
            ("CTA", "_cta_var", "Try it now"),
        ]:
            tk.Label(settings_frame, text=label, bg=self._bg, fg=self._fg,
                     font=("Segoe UI", 8)).pack(fill=tk.X, padx=4, pady=(2, 0))
            var = tk.StringVar(value=default)
            setattr(self, var_name, var)
            tk.Entry(settings_frame, textvariable=var, bg="#313244", fg=self._fg,
                     font=("Segoe UI", 8)).pack(fill=tk.X, padx=4, pady=1)

        tk.Button(settings_frame, text="Apply Settings", bg="#89b4fa", fg="#1e1e2e",
                  font=("Segoe UI", 9), relief=tk.FLAT,
                  command=self._apply_settings).pack(fill=tk.X, padx=4, pady=4)

        # ---- Right: Export ----
        right = tk.Frame(self, bg=self._bg, width=200)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)

        tk.Label(right, text="Export", bg=self._bg, fg=self._fg,
                 font=("Segoe UI", 11, "bold")).pack(fill=tk.X, padx=8, pady=(8, 4))

        # Format
        format_frame = tk.Frame(right, bg=self._bg)
        format_frame.pack(fill=tk.X, padx=4, pady=2)
        tk.Label(format_frame, text="Format:", bg=self._bg, fg=self._fg,
                 font=("Segoe UI", 8)).pack(anchor=tk.W, padx=4)
        self._format_var = tk.StringVar(value="mp4")
        ttk.Combobox(format_frame, textvariable=self._format_var,
                     values=["mp4", "gif", "webm", "png_sequence"],
                     width=14, state="readonly").pack(fill=tk.X, padx=4)

        # Preset size
        preset_frame = tk.Frame(right, bg=self._bg)
        preset_frame.pack(fill=tk.X, padx=4, pady=2)
        tk.Label(preset_frame, text="Size Preset:", bg=self._bg, fg=self._fg,
                 font=("Segoe UI", 8)).pack(anchor=tk.W, padx=4)
        self._preset_var = tk.StringVar(value="social_landscape")
        ttk.Combobox(preset_frame, textvariable=self._preset_var,
                     values=[p.value for p in ExportPreset],
                     width=18, state="readonly").pack(fill=tk.X, padx=4)

        tk.Button(right, text="Export Video", bg="#a6e3a1", fg="#1e1e2e",
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=12,
                  command=self._export_video).pack(fill=tk.X, padx=8, pady=8)

        tk.Button(right, text="Generate ffmpeg Command", bg="#313244", fg="#89b4fa",
                  font=("Segoe UI", 8), relief=tk.FLAT,
                  command=self._show_ffmpeg_command).pack(fill=tk.X, padx=8, pady=2)

        # Layer list
        layers_frame = tk.LabelFrame(right, text="Layers", bg=self._bg,
                                     fg="#cba6f7", font=("Segoe UI", 8, "bold"),
                                     bd=1, relief=tk.GROOVE)
        layers_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._layers_list = tk.Listbox(layers_frame, bg="#181825", fg=self._fg,
                                       font=("Consolas", 8), selectbackground="#313244",
                                       relief=tk.FLAT)
        self._layers_list.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        btn_row = tk.Frame(layers_frame, bg=self._bg)
        btn_row.pack(fill=tk.X)
        tk.Button(btn_row, text="+ Text", bg="#313244", fg="#89b4fa",
                  font=("Segoe UI", 7), relief=tk.FLAT,
                  command=self._add_text_layer).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_row, text="+ Device", bg="#313244", fg="#a6e3a1",
                  font=("Segoe UI", 7), relief=tk.FLAT,
                  command=self._add_device_layer).pack(side=tk.LEFT, padx=2)

        # ---- Center: Preview ----
        center = tk.Frame(self, bg=self._bg)
        center.pack(fill=tk.BOTH, expand=True)

        # Transport
        transport = tk.Frame(center, bg="#181825")
        transport.pack(fill=tk.X)

        tk.Button(transport, text="\u25B6 Play", bg="#a6e3a1", fg="#1e1e2e",
                  font=("Segoe UI", 9), relief=tk.FLAT, padx=8,
                  command=self._toggle_play).pack(side=tk.LEFT, padx=4, pady=4)

        self._time_slider = ttk.Scale(transport, from_=0, to=100,
                                       orient=tk.HORIZONTAL,
                                       command=self._on_scrub)
        self._time_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)

        self._time_label = tk.Label(transport, text="0.0s / 0.0s", bg="#181825",
                                    fg="#f9e2af", font=("Consolas", 9))
        self._time_label.pack(side=tk.RIGHT, padx=8)

        # Canvas preview
        self._preview = tk.Canvas(center, bg="#0f0f1a", highlightthickness=0)
        self._preview.pack(fill=tk.BOTH, expand=True)
        self._preview.bind("<Configure>", lambda e: self._render_preview())

        # Info
        self._info_label = tk.Label(center, text="Select a template to get started",
                                    bg=self._bg, fg="#6c7086", font=("Segoe UI", 10))
        self._info_label.pack(pady=4)

    def _load_template(self, template: PromoTemplate) -> None:
        self._current_template = template
        self._compositor = template.create_compositor(
            product_name=self._product_name_var.get(),
            tagline=self._tagline_var.get(),
            cta=self._cta_var.get(),
            app_name=self._product_name_var.get(),
            product=self._product_name_var.get(),
        )
        self._current_time = 0.0
        self._update_layers_list()
        self._render_preview()
        self._info_label.config(
            text=f"{template.name} | {template.width}x{template.height} | {template.duration}s")

    def _apply_settings(self) -> None:
        if self._current_template:
            self._load_template(self._current_template)

    def _update_layers_list(self) -> None:
        self._layers_list.delete(0, tk.END)
        if self._compositor:
            for layer in self._compositor.layers:
                visibility = "👁" if layer.visible else "  "
                self._layers_list.insert(tk.END,
                    f"{visibility} {layer.name} [{layer.layer_type.value}]")

    def _render_preview(self) -> None:
        self._preview.delete("all")
        if not self._compositor:
            self._preview.create_text(
                self._preview.winfo_width() / 2,
                self._preview.winfo_height() / 2,
                text="Select a template", fill="#585b70", font=("Segoe UI", 14))
            return

        frame = self._compositor.render_frame(self._current_time)
        pw = self._preview.winfo_width() or 800
        ph = self._preview.winfo_height() or 500
        scale = min(pw / frame["width"], ph / frame["height"]) * 0.85
        ox = (pw - frame["width"] * scale) / 2
        oy = (ph - frame["height"] * scale) / 2

        # Background
        self._preview.create_rectangle(ox, oy,
                                        ox + frame["width"] * scale,
                                        oy + frame["height"] * scale,
                                        fill="#1a1a2e", outline="#45475a")

        # Render layers
        for layer_data in frame["layers"]:
            t = layer_data["transform"]
            lx = ox + t["x"] * scale
            ly = oy + t["y"] * scale
            lw = t["width"] * scale
            lh = t["height"] * scale
            content = layer_data["content"]

            if layer_data["type"] == "text":
                font_size = max(8, int(content.get("font_size", 24) * scale * 0.4))
                color = content.get("color", "#ffffff")
                self._preview.create_text(lx, ly, text=content.get("text", ""),
                                           fill=color, font=("Segoe UI", font_size, "bold"),
                                           anchor=tk.CENTER)

            elif layer_data["type"] == "gradient":
                colors = content.get("colors", ["#000", "#333"])
                self._preview.create_rectangle(ox, oy,
                                                ox + frame["width"] * scale,
                                                oy + frame["height"] * scale,
                                                fill=colors[0] if colors else "#000",
                                                outline="")

            elif layer_data["type"] == "device_frame":
                # Draw simplified device frame
                dw, dh = 120 * scale, 250 * scale
                dx, dy = lx - dw / 2, ly - dh / 2
                self._preview.create_rectangle(dx, dy, dx + dw, dy + dh,
                                                fill="#181825", outline="#45475a",
                                                width=2)
                self._preview.create_oval(dx + dw / 2 - 5, dy + dh - 15,
                                           dx + dw / 2 + 5, dy + dh - 5,
                                           outline="#585b70")

        self._time_label.config(
            text=f"{self._current_time:.1f}s / {self._compositor.duration:.1f}s")

    def _toggle_play(self) -> None:
        self._playing = not self._playing
        if self._playing:
            self._animate()

    def _animate(self) -> None:
        if not self._playing or not self._compositor:
            return
        self._current_time += 1.0 / 30.0
        if self._current_time > self._compositor.duration:
            self._current_time = 0.0
        self._render_preview()
        self.after(33, self._animate)

    def _on_scrub(self, value: str) -> None:
        if self._compositor:
            pct = float(value) / 100
            self._current_time = pct * self._compositor.duration
            self._render_preview()

    def _add_text_layer(self) -> None:
        if self._compositor:
            self._compositor.add_text_layer("New Text", x=self._compositor.width / 2,
                                             y=self._compositor.height / 2)
            self._update_layers_list()
            self._render_preview()

    def _add_device_layer(self) -> None:
        if self._compositor:
            self._compositor.add_device_mockup("iphone_14",
                                                x=self._compositor.width / 2,
                                                y=self._compositor.height / 2)
            self._update_layers_list()
            self._render_preview()

    def _export_video(self) -> None:
        if not self._compositor:
            messagebox.showinfo("No Project", "Load a template first.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=f".{self._format_var.get()}",
            filetypes=[
                ("MP4", "*.mp4"), ("GIF", "*.gif"),
                ("WebM", "*.webm"), ("All", "*.*"),
            ],
        )
        if not path:
            return

        fmt_map = {"mp4": ExportFormat.MP4, "gif": ExportFormat.GIF,
                   "webm": ExportFormat.WEBM, "png_sequence": ExportFormat.PNG_SEQUENCE}
        config = ExportConfig(
            format=fmt_map.get(self._format_var.get(), ExportFormat.MP4),
            width=self._compositor.width,
            height=self._compositor.height,
            fps=self._compositor.fps,
        )
        try:
            preset = ExportPreset(self._preset_var.get())
            config.preset = preset
        except ValueError:
            pass

        cmd = self._compositor.generate_ffmpeg_command(path)
        messagebox.showinfo("Export Command",
            f"To render the video, run:\n\n{cmd}\n\n"
            f"Output: {path}\n"
            f"Resolution: {config.width}x{config.height}\n"
            f"Format: {self._format_var.get()}")

    def _show_ffmpeg_command(self) -> None:
        if self._compositor:
            cmd = self._compositor.generate_ffmpeg_command("output.mp4")
            win = tk.Toplevel(self, bg=self._bg)
            win.title("ffmpeg Command")
            win.geometry("600x200")
            text = tk.Text(win, bg="#181825", fg=self._fg, font=("Consolas", 10),
                          wrap=tk.WORD, relief=tk.FLAT)
            text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
            text.insert("1.0", cmd)
