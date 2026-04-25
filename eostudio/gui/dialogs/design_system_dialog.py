"""Design System dialog — export and manage design tokens, themes, and component variants."""

from __future__ import annotations

import json
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
from typing import Any, Dict, Optional

from eostudio.core.ui_flow.design_system import DesignSystem


class DesignSystemDialog(tk.Toplevel):
    """Dialog for managing and exporting the design system."""

    def __init__(self, master: tk.Widget, design_system: Optional[DesignSystem] = None,
                 bg: str = "#1e1e2e", fg: str = "#cdd6f4", **kw: Any):
        super().__init__(master, bg=bg, **kw)
        self.title("Design System Manager")
        self.geometry("800x600")
        self._bg = bg
        self._fg = fg
        self._ds = design_system or DesignSystem()

        self._build_ui()

    def _build_ui(self) -> None:
        # Header
        header = tk.Frame(self, bg="#181825")
        header.pack(fill=tk.X)
        tk.Label(header, text=f"Design System: {self._ds.name}", bg="#181825",
                 fg=self._fg, font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT, padx=12, pady=8)

        # Theme toggle
        self._theme_var = tk.StringVar(value=self._ds.active_theme)
        tk.Radiobutton(header, text="Light", variable=self._theme_var, value="light",
                       bg="#181825", fg=self._fg, selectcolor="#313244",
                       command=self._switch_theme).pack(side=tk.RIGHT, padx=4)
        tk.Radiobutton(header, text="Dark", variable=self._theme_var, value="dark",
                       bg="#181825", fg=self._fg, selectcolor="#313244",
                       command=self._switch_theme).pack(side=tk.RIGHT, padx=4)

        # Main content
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Colors tab
        colors_frame = tk.Frame(nb, bg=self._bg)
        nb.add(colors_frame, text="Colors")
        self._build_colors_tab(colors_frame)

        # Typography tab
        type_frame = tk.Frame(nb, bg=self._bg)
        nb.add(type_frame, text="Typography")
        self._build_typography_tab(type_frame)

        # Components tab
        comp_frame = tk.Frame(nb, bg=self._bg)
        nb.add(comp_frame, text="Component Variants")
        self._build_components_tab(comp_frame)

        # Export tab
        export_frame = tk.Frame(nb, bg=self._bg)
        nb.add(export_frame, text="Export")
        self._build_export_tab(export_frame)

        # Preview tab
        preview_frame = tk.Frame(nb, bg=self._bg)
        nb.add(preview_frame, text="CSS Preview")
        self._build_preview_tab(preview_frame)

    def _build_colors_tab(self, parent: tk.Frame) -> None:
        canvas = tk.Canvas(parent, bg=self._bg, highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        y = 10
        for token in self._ds.current_theme.by_category("color"):
            name = token.name.replace("color.", "")
            canvas.create_rectangle(10, y, 50, y + 30, fill=token.value, outline="#45475a")
            canvas.create_text(60, y + 15, text=f"{name}: {token.value}",
                              fill=self._fg, font=("Consolas", 10), anchor=tk.W)
            y += 36

    def _build_typography_tab(self, parent: tk.Frame) -> None:
        for token in self._ds.current_theme.by_category("typography"):
            name = token.name.replace("type.", "")
            frame = tk.Frame(parent, bg="#313244", padx=12, pady=8)
            frame.pack(fill=tk.X, padx=8, pady=4)
            tk.Label(frame, text=name.upper(), bg="#313244", fg="#89b4fa",
                     font=("Segoe UI", 8, "bold")).pack(anchor=tk.W)
            tk.Label(frame, text=f"{token.font_family} / {token.font_size}px / "
                     f"Weight {token.font_weight} / Line {token.line_height}",
                     bg="#313244", fg=self._fg,
                     font=("Segoe UI", int(min(token.font_size * 0.6, 18)))).pack(anchor=tk.W)

    def _build_components_tab(self, parent: tk.Frame) -> None:
        for comp_type, vs in self._ds.component_variants.items():
            comp_frame = tk.LabelFrame(parent, text=comp_type, bg=self._bg,
                                       fg="#cba6f7", font=("Segoe UI", 10, "bold"),
                                       bd=1, relief=tk.GROOVE)
            comp_frame.pack(fill=tk.X, padx=8, pady=4)
            for variant in vs.variants:
                row = tk.Frame(comp_frame, bg=self._bg)
                row.pack(fill=tk.X, padx=4, pady=2)
                bg_color = variant.properties.get("bg", "#313244")
                fg_color = variant.properties.get("color", self._fg)
                tk.Label(row, text=variant.name, bg=bg_color, fg=fg_color,
                         font=("Segoe UI", 9), padx=12, pady=4, relief=tk.RAISED).pack(
                    side=tk.LEFT, padx=4)
                states = ", ".join(s.state.value for s in variant.states)
                tk.Label(row, text=f"States: {states}", bg=self._bg, fg="#6c7086",
                         font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=4)

    def _build_export_tab(self, parent: tk.Frame) -> None:
        tk.Label(parent, text="Export Design System", bg=self._bg, fg=self._fg,
                 font=("Segoe UI", 12, "bold")).pack(padx=8, pady=(12, 8))

        exports = [
            ("Export CSS Variables", self._export_css),
            ("Export Tailwind Config", self._export_tailwind),
            ("Export Style Dictionary", self._export_style_dictionary),
            ("Export JSON", self._export_json),
        ]
        for label, cmd in exports:
            tk.Button(parent, text=label, bg="#89b4fa", fg="#1e1e2e",
                      font=("Segoe UI", 10), relief=tk.FLAT, padx=16, pady=6,
                      command=cmd).pack(fill=tk.X, padx=24, pady=4)

    def _build_preview_tab(self, parent: tk.Frame) -> None:
        text = tk.Text(parent, bg="#181825", fg=self._fg, font=("Consolas", 9),
                       wrap=tk.NONE, relief=tk.FLAT)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        text.insert("1.0", self._ds.export_css())
        text.config(state=tk.DISABLED)

    def _switch_theme(self) -> None:
        self._ds.active_theme = self._theme_var.get()

    def _export_css(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".css",
                                             filetypes=[("CSS", "*.css")])
        if path:
            with open(path, "w") as f:
                f.write(self._ds.export_css())
            messagebox.showinfo("Exported", f"CSS exported to {path}")

    def _export_tailwind(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                             filetypes=[("JSON", "*.json")])
        if path:
            with open(path, "w") as f:
                json.dump(self._ds.export_tailwind_config(), f, indent=2)
            messagebox.showinfo("Exported", f"Tailwind config exported to {path}")

    def _export_style_dictionary(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                             filetypes=[("JSON", "*.json")])
        if path:
            with open(path, "w") as f:
                json.dump(self._ds.export_style_dictionary(), f, indent=2)
            messagebox.showinfo("Exported", f"Style Dictionary exported to {path}")

    def _export_json(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                             filetypes=[("JSON", "*.json")])
        if path:
            self._ds.save_json(path)
            messagebox.showinfo("Exported", f"Design system JSON exported to {path}")
