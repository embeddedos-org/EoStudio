"""UI Designer — canvas with snap grid, component palette, flow view, animation timeline,
design system, responsive preview, prototyping, AI generation, and code export."""

from __future__ import annotations

import json
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
from typing import Any, Dict, List, Optional, Tuple

from eostudio.gui.widgets.canvas_2d import Canvas2D
from eostudio.gui.widgets.toolbar import ToolBar
from eostudio.gui.widgets.properties import PropertiesPanel
from eostudio.gui.widgets.timeline import TimelineWidget

from eostudio.core.animation.timeline import AnimationTimeline, AnimationClip
from eostudio.core.animation.presets import PRESETS, get_preset, list_presets, preset_categories
from eostudio.core.animation.keyframe import EasingFunction

from eostudio.core.ui_flow.design_tokens import DesignTokenSet
from eostudio.core.ui_flow.design_system import DesignSystem
from eostudio.core.ui_flow.auto_layout import AutoLayout, LayoutDirection, LayoutAlignment, LayoutDistribution
from eostudio.core.ui_flow.variants import VariantSet, ComponentState
from eostudio.core.ui_flow.responsive import BREAKPOINTS, ResponsiveConfig

from eostudio.core.prototyping.interactions import InteractionManager, InteractionTrigger, InteractionAction, Interaction
from eostudio.core.prototyping.transitions import ScreenTransition, TransitionType
from eostudio.core.prototyping.player import PrototypePlayer, PrototypeScreen


class UIDesigner(tk.Frame):
    """Full-featured UI design editor with animation, design system, prototyping, and AI."""

    COMPONENTS = [
        ("button", "Button", "#89b4fa"),
        ("text", "Text", "#cdd6f4"),
        ("input", "Input", "#a6e3a1"),
        ("image", "Image", "#f9e2af"),
        ("container", "Container", "#585b70"),
        ("card", "Card", "#cba6f7"),
        ("appbar", "AppBar", "#f38ba8"),
        ("bottomnav", "BottomNav", "#fab387"),
        ("toggle", "Toggle", "#94e2d5"),
        ("slider", "Slider", "#74c7ec"),
        ("avatar", "Avatar", "#b4befe"),
        ("badge", "Badge", "#eba0ac"),
    ]

    FRAMEWORKS = ["HTML/CSS", "Flutter", "Compose", "React", "React + Framer Motion", "React + GSAP"]

    def __init__(self, master: tk.Widget, bg: str = "#1e1e2e", fg: str = "#cdd6f4", **kw: Any):
        super().__init__(master, bg=bg, **kw)
        self._bg = bg
        self._fg = fg
        self._placed: List[Dict[str, Any]] = []
        self._drag_comp: Optional[str] = None
        self._selected_idx: Optional[int] = None
        self._screens: List[Dict[str, Any]] = [
            {"name": "Home", "x": 100, "y": 100},
            {"name": "Detail", "x": 350, "y": 100},
            {"name": "Settings", "x": 250, "y": 300},
        ]
        self._flows: List[Tuple[int, int]] = [(0, 1), (0, 2)]

        # New subsystems
        self._animation_timeline = AnimationTimeline(name="UI Animations")
        self._design_system = DesignSystem()
        self._auto_layout = AutoLayout(direction=LayoutDirection.COLUMN, gap=12, padding_top=16,
                                        padding_right=16, padding_bottom=16, padding_left=16)
        self._responsive_config = ResponsiveConfig()
        self._active_breakpoint = "mobile"
        self._prototype_player = PrototypePlayer()
        self._interaction_manager = InteractionManager()
        self._active_variant = "default"
        self._active_state = ComponentState.DEFAULT

        self._build_ui()

    def _build_ui(self) -> None:
        # ---- Left: Component Palette + Design Tokens ----
        left_panel = tk.Frame(self, bg=self._bg, width=180)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        left_panel.pack_propagate(False)

        left_nb = ttk.Notebook(left_panel)
        left_nb.pack(fill=tk.BOTH, expand=True)

        # Components tab
        comp_frame = tk.Frame(left_nb, bg=self._bg)
        left_nb.add(comp_frame, text="Components")

        tk.Label(comp_frame, text="Drag to Canvas", bg=self._bg, fg="#6c7086",
                 font=("Segoe UI", 8)).pack(fill=tk.X, padx=8, pady=(4, 2))

        for comp_id, comp_name, color in self.COMPONENTS:
            btn = tk.Button(comp_frame, text=f"  {comp_name}", bg="#313244", fg=self._fg,
                            relief=tk.FLAT, font=("Segoe UI", 9), anchor=tk.W, padx=8, pady=3)
            btn.pack(fill=tk.X, padx=4, pady=1)
            btn.bind("<ButtonPress-1>", lambda e, cid=comp_id: self._start_drag(cid))

        # Design Tokens tab
        tokens_frame = tk.Frame(left_nb, bg=self._bg)
        left_nb.add(tokens_frame, text="Tokens")
        self._build_tokens_panel(tokens_frame)

        # Animations tab
        anim_frame = tk.Frame(left_nb, bg=self._bg)
        left_nb.add(anim_frame, text="Animate")
        self._build_presets_panel(anim_frame)

        # ---- Right: Properties + Export + Preview ----
        right_panel = tk.Frame(self, bg=self._bg, width=240)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        right_panel.pack_propagate(False)

        right_nb = ttk.Notebook(right_panel)
        right_nb.pack(fill=tk.BOTH, expand=True)

        # Properties tab
        props_tab = tk.Frame(right_nb, bg=self._bg)
        right_nb.add(props_tab, text="Properties")

        self._properties = PropertiesPanel(props_tab, bg=self._bg, fg=self._fg,
                                           on_change=self._on_prop_change)
        self._properties.pack(fill=tk.BOTH, expand=True)

        # Variant state selector
        state_frame = tk.LabelFrame(props_tab, text="Component State", bg=self._bg,
                                    fg="#cba6f7", font=("Segoe UI", 8, "bold"),
                                    bd=1, relief=tk.GROOVE)
        state_frame.pack(fill=tk.X, padx=4, pady=2)
        self._state_var = tk.StringVar(value="default")
        for state in ["default", "hover", "active", "focus", "disabled"]:
            tk.Radiobutton(state_frame, text=state.title(), variable=self._state_var,
                          value=state, bg=self._bg, fg=self._fg, selectcolor="#313244",
                          font=("Segoe UI", 8), command=self._on_state_change).pack(
                side=tk.LEFT, padx=2)

        # Export tab
        export_tab = tk.Frame(right_nb, bg=self._bg)
        right_nb.add(export_tab, text="Export")
        self._build_export_panel(export_tab)

        # Responsive tab
        responsive_tab = tk.Frame(right_nb, bg=self._bg)
        right_nb.add(responsive_tab, text="Responsive")
        self._build_responsive_panel(responsive_tab)

        # ---- Center: Main workspace ----
        center = tk.Frame(self, bg=self._bg)
        center.pack(fill=tk.BOTH, expand=True)

        # Top tabs
        self._tab_nb = ttk.Notebook(center)
        self._tab_nb.pack(fill=tk.BOTH, expand=True)

        # Design tab
        design_frame = tk.Frame(self._tab_nb, bg=self._bg)
        self._tab_nb.add(design_frame, text="Design")
        self._canvas = Canvas2D(design_frame, bg="#11111b", grid_size=10, snap=True)
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._canvas.bind("<ButtonPress-1>", self._on_canvas_click)
        self._canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self._draw_phone_frame()

        # Flow View tab
        flow_frame = tk.Frame(self._tab_nb, bg=self._bg)
        self._tab_nb.add(flow_frame, text="Flow View")
        self._flow_canvas = tk.Canvas(flow_frame, bg="#11111b", highlightthickness=0)
        self._flow_canvas.pack(fill=tk.BOTH, expand=True)
        self._flow_canvas.bind("<Configure>", lambda e: self._draw_flow())

        # Prototype tab
        proto_frame = tk.Frame(self._tab_nb, bg=self._bg)
        self._tab_nb.add(proto_frame, text="Prototype")
        self._build_prototype_tab(proto_frame)

        # AI Generate tab
        ai_frame = tk.Frame(self._tab_nb, bg=self._bg)
        self._tab_nb.add(ai_frame, text="AI Generate")
        self._build_ai_tab(ai_frame)

        # ---- Bottom: Animation Timeline ----
        timeline_container = tk.Frame(center, bg=self._bg, height=180)
        timeline_container.pack(fill=tk.X, side=tk.BOTTOM)
        timeline_container.pack_propagate(False)

        self._timeline_widget = TimelineWidget(
            timeline_container, bg=self._bg, fg=self._fg,
            on_time_change=self._on_timeline_time_change,
            on_keyframe_change=self._on_keyframe_changed,
        )
        self._timeline_widget.pack(fill=tk.BOTH, expand=True)
        self._timeline_widget.set_timeline(self._animation_timeline)

    # ------------------------------------------------------------------
    # Design Tokens Panel
    # ------------------------------------------------------------------

    def _build_tokens_panel(self, parent: tk.Frame) -> None:
        tk.Label(parent, text="Design System", bg=self._bg, fg=self._fg,
                 font=("Segoe UI", 10, "bold")).pack(fill=tk.X, padx=8, pady=(8, 4))

        # Theme toggle
        theme_frame = tk.Frame(parent, bg=self._bg)
        theme_frame.pack(fill=tk.X, padx=4, pady=2)
        self._theme_var = tk.StringVar(value="light")
        tk.Radiobutton(theme_frame, text="Light", variable=self._theme_var, value="light",
                       bg=self._bg, fg=self._fg, selectcolor="#313244", font=("Segoe UI", 8),
                       command=self._toggle_theme).pack(side=tk.LEFT)
        tk.Radiobutton(theme_frame, text="Dark", variable=self._theme_var, value="dark",
                       bg=self._bg, fg=self._fg, selectcolor="#313244", font=("Segoe UI", 8),
                       command=self._toggle_theme).pack(side=tk.LEFT)

        # Color tokens
        colors_frame = tk.LabelFrame(parent, text="Colors", bg=self._bg, fg="#89b4fa",
                                     font=("Segoe UI", 8, "bold"), bd=1, relief=tk.GROOVE)
        colors_frame.pack(fill=tk.X, padx=4, pady=2)

        self._color_labels: Dict[str, tk.Label] = {}
        for token in self._design_system.current_theme.by_category("color")[:8]:
            row = tk.Frame(colors_frame, bg=self._bg)
            row.pack(fill=tk.X, padx=4, pady=1)
            swatch = tk.Label(row, bg=token.value, width=3, height=1, relief=tk.SUNKEN)
            swatch.pack(side=tk.LEFT, padx=(0, 4))
            name = token.name.replace("color.", "")
            tk.Label(row, text=name, bg=self._bg, fg="#6c7086",
                     font=("Segoe UI", 7), anchor=tk.W).pack(side=tk.LEFT)
            self._color_labels[token.name] = swatch

        # Typography
        type_frame = tk.LabelFrame(parent, text="Typography", bg=self._bg, fg="#a6e3a1",
                                   font=("Segoe UI", 8, "bold"), bd=1, relief=tk.GROOVE)
        type_frame.pack(fill=tk.X, padx=4, pady=2)
        for token in self._design_system.current_theme.by_category("typography")[:4]:
            name = token.name.replace("type.", "")
            tk.Label(type_frame, text=f"{name}: {token.font_size}px / {token.font_weight}",
                     bg=self._bg, fg="#6c7086", font=("Segoe UI", 7), anchor=tk.W).pack(
                fill=tk.X, padx=4, pady=1)

        # Export buttons
        tk.Button(parent, text="Export CSS", bg="#89b4fa", fg="#1e1e2e",
                  font=("Segoe UI", 8), relief=tk.FLAT, padx=6,
                  command=self._export_design_system_css).pack(fill=tk.X, padx=8, pady=2)
        tk.Button(parent, text="Export Tailwind", bg="#a6e3a1", fg="#1e1e2e",
                  font=("Segoe UI", 8), relief=tk.FLAT, padx=6,
                  command=self._export_tailwind).pack(fill=tk.X, padx=8, pady=2)

    # ------------------------------------------------------------------
    # Animation Presets Panel
    # ------------------------------------------------------------------

    def _build_presets_panel(self, parent: tk.Frame) -> None:
        tk.Label(parent, text="Animation Presets", bg=self._bg, fg=self._fg,
                 font=("Segoe UI", 10, "bold")).pack(fill=tk.X, padx=8, pady=(8, 4))

        for category in preset_categories():
            cat_frame = tk.LabelFrame(parent, text=category.title(), bg=self._bg,
                                      fg="#f9e2af", font=("Segoe UI", 8, "bold"),
                                      bd=1, relief=tk.GROOVE)
            cat_frame.pack(fill=tk.X, padx=4, pady=2)
            for preset in list_presets(category)[:4]:
                btn = tk.Button(cat_frame, text=preset.name, bg="#313244", fg="#89b4fa",
                                relief=tk.FLAT, font=("Segoe UI", 8), anchor=tk.W, padx=6,
                                command=lambda p=preset: self._apply_preset(p))
                btn.pack(fill=tk.X, padx=2, pady=1)

    # ------------------------------------------------------------------
    # Export Panel
    # ------------------------------------------------------------------

    def _build_export_panel(self, parent: tk.Frame) -> None:
        tk.Label(parent, text="Code Generation", bg=self._bg, fg=self._fg,
                 font=("Segoe UI", 10, "bold")).pack(fill=tk.X, padx=8, pady=(8, 4))

        self._framework_var = tk.StringVar(value=self.FRAMEWORKS[0])
        ttk.Combobox(parent, textvariable=self._framework_var,
                     values=self.FRAMEWORKS, width=22, state="readonly").pack(padx=8, pady=4)

        tk.Button(parent, text="Generate Code", bg="#89b4fa", fg="#1e1e2e",
                  relief=tk.FLAT, font=("Segoe UI", 10, "bold"), padx=12, pady=4,
                  command=self._generate_code).pack(padx=8, pady=4)

        # Preview
        preview_frame = tk.LabelFrame(parent, text="Live Preview", bg=self._bg,
                                      fg="#a6e3a1", font=("Segoe UI", 9, "bold"),
                                      bd=1, relief=tk.GROOVE)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._preview_canvas = tk.Canvas(preview_frame, bg="#181825", highlightthickness=0)
        self._preview_canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Prototype export
        tk.Button(parent, text="Export Prototype (HTML)", bg="#cba6f7", fg="#1e1e2e",
                  relief=tk.FLAT, font=("Segoe UI", 9), padx=8,
                  command=self._export_prototype_html).pack(padx=8, pady=2)

    # ------------------------------------------------------------------
    # Responsive Panel
    # ------------------------------------------------------------------

    def _build_responsive_panel(self, parent: tk.Frame) -> None:
        tk.Label(parent, text="Responsive Preview", bg=self._bg, fg=self._fg,
                 font=("Segoe UI", 10, "bold")).pack(fill=tk.X, padx=8, pady=(8, 4))

        bp_frame = tk.Frame(parent, bg=self._bg)
        bp_frame.pack(fill=tk.X, padx=4, pady=4)

        self._bp_var = tk.StringVar(value="mobile")
        for bp_name, bp in BREAKPOINTS.items():
            tk.Radiobutton(bp_frame, text=f"{bp.label}\n{bp.min_width}px",
                          variable=self._bp_var, value=bp_name,
                          bg=self._bg, fg=self._fg, selectcolor="#313244",
                          font=("Segoe UI", 7), indicatoron=False, padx=4, pady=2,
                          command=self._on_breakpoint_change).pack(
                fill=tk.X, padx=2, pady=1)

        # Auto-layout controls
        layout_frame = tk.LabelFrame(parent, text="Auto Layout", bg=self._bg,
                                     fg="#fab387", font=("Segoe UI", 8, "bold"),
                                     bd=1, relief=tk.GROOVE)
        layout_frame.pack(fill=tk.X, padx=4, pady=4)

        dir_frame = tk.Frame(layout_frame, bg=self._bg)
        dir_frame.pack(fill=tk.X, padx=4, pady=2)
        self._layout_dir_var = tk.StringVar(value="column")
        for d in ["row", "column"]:
            tk.Radiobutton(dir_frame, text=d.title(), variable=self._layout_dir_var,
                          value=d, bg=self._bg, fg=self._fg, selectcolor="#313244",
                          font=("Segoe UI", 8), command=self._on_layout_change).pack(
                side=tk.LEFT, padx=4)

        gap_frame = tk.Frame(layout_frame, bg=self._bg)
        gap_frame.pack(fill=tk.X, padx=4, pady=2)
        tk.Label(gap_frame, text="Gap:", bg=self._bg, fg=self._fg,
                 font=("Segoe UI", 8)).pack(side=tk.LEFT)
        self._gap_var = tk.StringVar(value="12")
        tk.Entry(gap_frame, textvariable=self._gap_var, width=5, bg="#313244",
                 fg=self._fg, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=4)

        pad_frame = tk.Frame(layout_frame, bg=self._bg)
        pad_frame.pack(fill=tk.X, padx=4, pady=2)
        tk.Label(pad_frame, text="Padding:", bg=self._bg, fg=self._fg,
                 font=("Segoe UI", 8)).pack(side=tk.LEFT)
        self._pad_var = tk.StringVar(value="16")
        tk.Entry(pad_frame, textvariable=self._pad_var, width=5, bg="#313244",
                 fg=self._fg, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=4)

    # ------------------------------------------------------------------
    # Prototype Tab
    # ------------------------------------------------------------------

    def _build_prototype_tab(self, parent: tk.Frame) -> None:
        toolbar = tk.Frame(parent, bg="#181825")
        toolbar.pack(fill=tk.X)

        tk.Button(toolbar, text="Play", bg="#a6e3a1", fg="#1e1e2e",
                  font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10,
                  command=self._play_prototype).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(toolbar, text="Add Screen", bg="#89b4fa", fg="#1e1e2e",
                  font=("Segoe UI", 9), relief=tk.FLAT, padx=8,
                  command=self._add_prototype_screen).pack(side=tk.LEFT, padx=2, pady=4)
        tk.Button(toolbar, text="Add Transition", bg="#cba6f7", fg="#1e1e2e",
                  font=("Segoe UI", 9), relief=tk.FLAT, padx=8,
                  command=self._add_prototype_transition).pack(side=tk.LEFT, padx=2, pady=4)

        # Device selector
        self._device_var = tk.StringVar(value="iphone_14")
        ttk.Combobox(toolbar, textvariable=self._device_var,
                     values=list(PrototypePlayer.DEVICE_FRAMES.keys()),
                     width=14, state="readonly").pack(side=tk.RIGHT, padx=4, pady=4)
        tk.Label(toolbar, text="Device:", bg="#181825", fg=self._fg,
                 font=("Segoe UI", 9)).pack(side=tk.RIGHT)

        # Transition type
        self._transition_var = tk.StringVar(value="push")
        ttk.Combobox(toolbar, textvariable=self._transition_var,
                     values=[t.value for t in TransitionType],
                     width=12, state="readonly").pack(side=tk.RIGHT, padx=4, pady=4)

        # Prototype canvas
        self._proto_canvas = tk.Canvas(parent, bg="#0f0f1a", highlightthickness=0)
        self._proto_canvas.pack(fill=tk.BOTH, expand=True)
        self._proto_canvas.bind("<Configure>", lambda e: self._draw_prototype())

        # Interaction list
        interact_frame = tk.LabelFrame(parent, text="Interactions", bg=self._bg,
                                       fg="#f9e2af", font=("Segoe UI", 9, "bold"),
                                       bd=1, relief=tk.GROOVE, height=100)
        interact_frame.pack(fill=tk.X, padx=4, pady=4)
        interact_frame.pack_propagate(False)

        self._interaction_list = tk.Listbox(interact_frame, bg="#181825", fg=self._fg,
                                            font=("Consolas", 8), selectbackground="#313244",
                                            relief=tk.FLAT)
        self._interaction_list.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        btn_row = tk.Frame(interact_frame, bg=self._bg)
        btn_row.pack(fill=tk.X)
        tk.Button(btn_row, text="+ Click→Navigate", bg="#313244", fg="#89b4fa",
                  font=("Segoe UI", 7), relief=tk.FLAT,
                  command=self._add_click_navigate).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_row, text="+ Hover→Animate", bg="#313244", fg="#a6e3a1",
                  font=("Segoe UI", 7), relief=tk.FLAT,
                  command=self._add_hover_animate).pack(side=tk.LEFT, padx=2)

    # ------------------------------------------------------------------
    # AI Generate Tab
    # ------------------------------------------------------------------

    def _build_ai_tab(self, parent: tk.Frame) -> None:
        tk.Label(parent, text="AI UI Generation", bg=self._bg, fg=self._fg,
                 font=("Segoe UI", 12, "bold")).pack(padx=8, pady=(12, 4))

        prompt_frame = tk.Frame(parent, bg=self._bg)
        prompt_frame.pack(fill=tk.X, padx=8, pady=4)

        self._ai_prompt = tk.Text(prompt_frame, bg="#313244", fg=self._fg,
                                  insertbackground=self._fg, font=("Segoe UI", 10),
                                  wrap=tk.WORD, height=4, relief=tk.FLAT)
        self._ai_prompt.pack(fill=tk.X, pady=4)
        self._ai_prompt.insert("1.0", "Design a responsive dashboard with charts and sidebar navigation")

        btn_row = tk.Frame(parent, bg=self._bg)
        btn_row.pack(fill=tk.X, padx=8, pady=4)

        tk.Button(btn_row, text="Generate UI", bg="#89b4fa", fg="#1e1e2e",
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=16, pady=4,
                  command=self._ai_generate_ui).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_row, text="Generate Animated UI", bg="#cba6f7", fg="#1e1e2e",
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=16, pady=4,
                  command=self._ai_generate_animated_ui).pack(side=tk.LEFT, padx=2)

        tk.Button(btn_row, text="Design System", bg="#a6e3a1", fg="#1e1e2e",
                  font=("Segoe UI", 9), relief=tk.FLAT, padx=8,
                  command=self._ai_generate_design_system).pack(side=tk.LEFT, padx=2)

        tk.Button(btn_row, text="Screenshot → UI", bg="#f9e2af", fg="#1e1e2e",
                  font=("Segoe UI", 9), relief=tk.FLAT, padx=8,
                  command=self._ai_screenshot_to_ui).pack(side=tk.LEFT, padx=2)

        tk.Button(btn_row, text="A11y Audit", bg="#f38ba8", fg="#1e1e2e",
                  font=("Segoe UI", 9), relief=tk.FLAT, padx=8,
                  command=self._ai_accessibility_audit).pack(side=tk.LEFT, padx=2)

        # Result area
        self._ai_result = tk.Text(parent, bg="#181825", fg=self._fg,
                                  insertbackground=self._fg, font=("Consolas", 9),
                                  wrap=tk.WORD, relief=tk.FLAT)
        self._ai_result.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

    # ------------------------------------------------------------------
    # Phone frame on design canvas
    # ------------------------------------------------------------------

    def _draw_phone_frame(self) -> None:
        bp = BREAKPOINTS.get(self._active_breakpoint)
        if bp and bp.device_frame:
            w, h = bp.device_frame
            scale = min(600 / w, 700 / h) * 0.8
            pw, ph = int(w * scale), int(h * scale)
        else:
            pw, ph = 300, 660

        ox, oy = 150, 20
        self._canvas.draw_rect(ox, oy, ox + pw, oy + ph, color="#45475a", fill="#181825", tag="user")
        self._canvas.draw_rect(ox, oy, ox + pw, oy + 40, color="#45475a", fill="#313244", tag="user")
        self._canvas.draw_text(ox + pw // 2, oy + 20, "Status Bar", color="#6c7086", tag="user")
        self._canvas.draw_rect(ox, oy + ph - 40, ox + pw, oy + ph, color="#45475a", fill="#313244", tag="user")
        self._canvas.draw_text(ox + pw // 2, oy + ph - 20, "Navigation", color="#6c7086", tag="user")

    # ------------------------------------------------------------------
    # Drag and drop
    # ------------------------------------------------------------------

    def _start_drag(self, comp_id: str) -> None:
        self._drag_comp = comp_id

    def _on_canvas_click(self, event: tk.Event) -> None:
        if self._drag_comp:
            wx, wy = self._canvas.screen_to_world(event.x, event.y)
            wx, wy = self._canvas.snap_point(wx, wy)
            self._place_component(self._drag_comp, wx, wy)
            self._drag_comp = None
            return

        wx, wy = self._canvas.screen_to_world(event.x, event.y)
        self._selected_idx = None
        for i, comp in enumerate(self._placed):
            cx, cy, cw, ch = comp["x"], comp["y"], comp["width"], comp["height"]
            if cx <= wx <= cx + cw and cy <= wy <= cy + ch:
                self._selected_idx = i
                self._show_comp_properties(comp)
                break

        if self._selected_idx is None:
            self._properties.clear_properties()
        self._redraw_components()

    def _on_canvas_drag(self, event: tk.Event) -> None:
        if self._selected_idx is not None:
            wx, wy = self._canvas.screen_to_world(event.x, event.y)
            wx, wy = self._canvas.snap_point(wx, wy)
            comp = self._placed[self._selected_idx]
            comp["x"] = wx - comp["width"] / 2
            comp["y"] = wy - comp["height"] / 2
            self._redraw_components()

    def _on_canvas_release(self, event: tk.Event) -> None:
        self._update_preview()

    def _place_component(self, comp_id: str, x: float, y: float) -> None:
        sizes = {
            "button": (120, 40), "text": (100, 24), "input": (200, 36),
            "image": (100, 100), "container": (250, 200), "card": (200, 150),
            "appbar": (300, 50), "bottomnav": (300, 50),
            "toggle": (50, 28), "slider": (200, 24), "avatar": (48, 48), "badge": (60, 24),
        }
        w, h = sizes.get(comp_id, (100, 40))
        color = "#89b4fa"
        for cid, cname, cc in self.COMPONENTS:
            if cid == comp_id:
                color = cc
                break

        comp_data = {
            "type": comp_id, "id": f"comp_{len(self._placed)}",
            "x": x, "y": y, "width": w, "height": h,
            "color": color, "text": comp_id.title(),
            "font_size": 12, "padding": 8,
            "variant": "default", "state": "default",
            "animation": None,
        }
        self._placed.append(comp_data)
        self._redraw_components()
        self._update_preview()

    def _redraw_components(self) -> None:
        self._canvas.delete("comp")
        for i, comp in enumerate(self._placed):
            outline = "#f9e2af" if i == self._selected_idx else comp["color"]
            width = 2 if i == self._selected_idx else 1
            self._canvas.draw_rect(comp["x"], comp["y"],
                                   comp["x"] + comp["width"],
                                   comp["y"] + comp["height"],
                                   color=outline, fill="#313244", width=width, tag="comp")
            label = comp["text"]
            if comp.get("animation"):
                label += f" [{comp['animation']}]"
            self._canvas.draw_text(comp["x"] + comp["width"] / 2,
                                   comp["y"] + comp["height"] / 2,
                                   label, color=comp["color"], tag="comp")

    def _show_comp_properties(self, comp: Dict[str, Any]) -> None:
        self._properties.show_properties(comp["type"].title(), {
            "position": (comp["x"], comp["y"], 0),
            "width": comp["width"],
            "height": comp["height"],
            "text": comp["text"],
            "color": comp["color"],
            "font_size": comp["font_size"],
            "padding": comp["padding"],
        })

    def _on_prop_change(self, section: str, key: str, value: Any) -> None:
        if self._selected_idx is not None and self._selected_idx < len(self._placed):
            comp = self._placed[self._selected_idx]
            if key in comp:
                comp[key] = value
                self._redraw_components()

    # ------------------------------------------------------------------
    # State handling
    # ------------------------------------------------------------------

    def _on_state_change(self) -> None:
        self._active_state = ComponentState(self._state_var.get())

    # ------------------------------------------------------------------
    # Animation integration
    # ------------------------------------------------------------------

    def _apply_preset(self, preset: Any) -> None:
        if self._selected_idx is None:
            messagebox.showinfo("Select Component", "Select a component first to apply animation.")
            return
        comp = self._placed[self._selected_idx]
        comp["animation"] = preset.name
        clip = preset.apply(comp["id"], delay=self._selected_idx * 0.1)
        self._animation_timeline.add_clip(clip)
        self._timeline_widget.set_timeline(self._animation_timeline)
        self._redraw_components()

    def _on_timeline_time_change(self, time: float) -> None:
        values = self._animation_timeline.evaluate(time)
        # Could animate canvas positions in real-time here

    def _on_keyframe_changed(self, target_id: str, kf_idx: int, time: float) -> None:
        pass  # Timeline widget handles internal updates

    # ------------------------------------------------------------------
    # Responsive
    # ------------------------------------------------------------------

    def _on_breakpoint_change(self) -> None:
        self._active_breakpoint = self._bp_var.get()
        self._canvas.delete("user")
        self._draw_phone_frame()
        self._redraw_components()

    def _on_layout_change(self) -> None:
        self._auto_layout.direction = LayoutDirection(self._layout_dir_var.get())
        try:
            self._auto_layout.gap = float(self._gap_var.get())
        except ValueError:
            pass

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _toggle_theme(self) -> None:
        self._design_system.active_theme = self._theme_var.get()
        # Refresh token swatches
        for token in self._design_system.current_theme.by_category("color")[:8]:
            label = self._color_labels.get(token.name)
            if label:
                label.config(bg=token.value)

    # ------------------------------------------------------------------
    # Design System Export
    # ------------------------------------------------------------------

    def _export_design_system_css(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".css",
                                             filetypes=[("CSS", "*.css")])
        if path:
            css = self._design_system.export_css()
            with open(path, "w") as f:
                f.write(css)
            messagebox.showinfo("Exported", f"Design system CSS exported to {path}")

    def _export_tailwind(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                             filetypes=[("JSON", "*.json")])
        if path:
            config = self._design_system.export_tailwind_config()
            with open(path, "w") as f:
                json.dump(config, f, indent=2)
            messagebox.showinfo("Exported", f"Tailwind config exported to {path}")

    # ------------------------------------------------------------------
    # Prototype
    # ------------------------------------------------------------------

    def _play_prototype(self) -> None:
        if not self._prototype_player.screens:
            # Auto-populate from screens
            for screen in self._screens:
                self._prototype_player.add_screen(PrototypeScreen(
                    id=screen["name"].lower(), name=screen["name"],
                    components=[c for c in self._placed],
                    device_frame=self._device_var.get(),
                ))
        self._prototype_player.start()
        self._draw_prototype()

    def _add_prototype_screen(self) -> None:
        name = f"Screen {len(self._screens) + 1}"
        self._screens.append({"name": name, "x": 100 + len(self._screens) * 150, "y": 100})
        self._draw_flow()

    def _add_prototype_transition(self) -> None:
        if len(self._screens) >= 2:
            si = len(self._flows)
            self._flows.append((si % len(self._screens), (si + 1) % len(self._screens)))
            self._draw_flow()

    def _add_click_navigate(self) -> None:
        if self._selected_idx is not None and len(self._screens) > 1:
            comp = self._placed[self._selected_idx]
            interaction = Interaction(
                id=f"int_{len(self._interaction_manager._interactions)}",
                source_id=comp["id"],
                trigger=InteractionTrigger.CLICK,
                action=InteractionAction.NAVIGATE,
                target_id=self._screens[1]["name"].lower(),
                parameters={"transition": self._transition_var.get()},
            )
            self._interaction_manager.add_interaction(interaction)
            self._interaction_list.insert(tk.END,
                f"{comp['text']} → Click → Navigate to {self._screens[1]['name']}")

    def _add_hover_animate(self) -> None:
        if self._selected_idx is not None:
            comp = self._placed[self._selected_idx]
            interaction = Interaction(
                id=f"int_{len(self._interaction_manager._interactions)}",
                source_id=comp["id"],
                trigger=InteractionTrigger.HOVER_IN,
                action=InteractionAction.PLAY_ANIMATION,
                parameters={"preset": "pulse"},
            )
            self._interaction_manager.add_interaction(interaction)
            self._interaction_list.insert(tk.END,
                f"{comp['text']} → Hover → Pulse animation")

    def _draw_prototype(self) -> None:
        self._proto_canvas.delete("all")
        w = self._proto_canvas.winfo_width() or 600
        h = self._proto_canvas.winfo_height() or 400

        device = self._device_var.get()
        device_info = PrototypePlayer.DEVICE_FRAMES.get(device, {"width": 390, "height": 844, "label": device})
        dw, dh = device_info["width"], device_info["height"]
        scale = min((w - 40) / dw, (h - 60) / dh) * 0.8
        ox = (w - dw * scale) / 2
        oy = (h - dh * scale) / 2

        # Device frame
        self._proto_canvas.create_rectangle(ox - 10, oy - 10,
                                             ox + dw * scale + 10, oy + dh * scale + 10,
                                             fill="#1e1e2e", outline="#45475a", width=2)
        self._proto_canvas.create_rectangle(ox, oy, ox + dw * scale, oy + dh * scale,
                                             fill="#181825", outline="#585b70")
        self._proto_canvas.create_text(w / 2, oy - 20, text=device_info["label"],
                                        fill=self._fg, font=("Segoe UI", 10, "bold"))

        # Render components
        for comp in self._placed:
            cx = ox + (comp["x"] - 150) * scale
            cy = oy + (comp["y"] - 20) * scale
            cw = comp["width"] * scale
            ch = comp["height"] * scale
            self._proto_canvas.create_rectangle(cx, cy, cx + cw, cy + ch,
                                                 fill="#313244", outline=comp["color"])
            if cw > 20 and ch > 10:
                self._proto_canvas.create_text(cx + cw / 2, cy + ch / 2,
                                                text=comp["text"][:10],
                                                fill=comp["color"],
                                                font=("Segoe UI", max(7, int(9 * scale))))

    def _export_prototype_html(self) -> None:
        # Ensure player has screens
        if not self._prototype_player.screens:
            self._play_prototype()

        path = filedialog.asksaveasfilename(defaultextension=".html",
                                             filetypes=[("HTML", "*.html")])
        if path:
            html = self._prototype_player.export_html()
            with open(path, "w") as f:
                f.write(html)
            messagebox.showinfo("Exported", f"Interactive prototype exported to {path}")

    # ------------------------------------------------------------------
    # AI Generation
    # ------------------------------------------------------------------

    def _ai_generate_ui(self) -> None:
        prompt = self._ai_prompt.get("1.0", tk.END).strip()
        if not prompt:
            return
        try:
            from eostudio.core.ai.generator import AIDesignGenerator
            gen = AIDesignGenerator()
            result = gen.text_to_ui(prompt)
            self._ai_result.delete("1.0", tk.END)
            self._ai_result.insert("1.0", json.dumps(result, indent=2))
            self._load_ai_components(result)
        except Exception as e:
            self._ai_result.delete("1.0", tk.END)
            self._ai_result.insert("1.0", f"Error: {e}\n\nUsing fallback generation...")

    def _ai_generate_animated_ui(self) -> None:
        prompt = self._ai_prompt.get("1.0", tk.END).strip()
        if not prompt:
            return
        try:
            from eostudio.core.ai.generator_pro import AIDesignGeneratorPro
            gen = AIDesignGeneratorPro()
            result = gen.text_to_animated_ui(prompt)
            self._ai_result.delete("1.0", tk.END)
            self._ai_result.insert("1.0", json.dumps(result, indent=2))
            self._load_ai_components(result)
            # Also load animations
            for anim in result.get("animations", []):
                preset = get_preset(anim.get("preset", "fadeIn"))
                if preset:
                    clip = preset.apply(anim["target_id"], delay=anim.get("delay", 0))
                    self._animation_timeline.add_clip(clip)
            self._timeline_widget.set_timeline(self._animation_timeline)
        except Exception as e:
            self._ai_result.delete("1.0", tk.END)
            self._ai_result.insert("1.0", f"Error: {e}")

    def _ai_generate_design_system(self) -> None:
        prompt = self._ai_prompt.get("1.0", tk.END).strip()
        try:
            from eostudio.core.ai.generator_pro import AIDesignGeneratorPro
            gen = AIDesignGeneratorPro()
            result = gen.text_to_design_system(prompt or "Modern SaaS product")
            self._ai_result.delete("1.0", tk.END)
            self._ai_result.insert("1.0", json.dumps(result, indent=2))
        except Exception as e:
            self._ai_result.delete("1.0", tk.END)
            self._ai_result.insert("1.0", f"Error: {e}")

    def _ai_screenshot_to_ui(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if not path:
            return
        try:
            from eostudio.core.ai.generator_pro import AIDesignGeneratorPro
            gen = AIDesignGeneratorPro()
            result = gen.screenshot_to_ui(path)
            self._ai_result.delete("1.0", tk.END)
            self._ai_result.insert("1.0", json.dumps(result, indent=2))
            self._load_ai_components(result)
        except Exception as e:
            self._ai_result.delete("1.0", tk.END)
            self._ai_result.insert("1.0", f"Error: {e}")

    def _ai_accessibility_audit(self) -> None:
        components = [{"id": c.get("id", f"comp_{i}"), "type": c["type"].title(),
                       "label": c["text"], "size": {"width": c["width"], "height": c["height"]}}
                      for i, c in enumerate(self._placed)]
        try:
            from eostudio.core.ai.generator_pro import AIDesignGeneratorPro
            gen = AIDesignGeneratorPro()
            result = gen.accessibility_audit(components)
            self._ai_result.delete("1.0", tk.END)
            self._ai_result.insert("1.0", json.dumps(result, indent=2))
        except Exception as e:
            self._ai_result.delete("1.0", tk.END)
            self._ai_result.insert("1.0", f"Error: {e}")

    def _load_ai_components(self, result: Dict[str, Any]) -> None:
        """Load AI-generated components onto the canvas."""
        for comp in result.get("components", []):
            pos = comp.get("position", {"x": 200, "y": 100 + len(self._placed) * 50})
            size = comp.get("size", {"width": 120, "height": 40})
            comp_type = comp.get("type", "Container").lower()
            if comp_type not in [c[0] for c in self.COMPONENTS]:
                comp_type = "container"
            self._place_component(comp_type,
                                  pos.get("x", 200) + 150,
                                  pos.get("y", 100) + 20)
            # Update text
            if self._placed:
                self._placed[-1]["text"] = comp.get("label", comp.get("type", ""))

    # ------------------------------------------------------------------
    # Flow view
    # ------------------------------------------------------------------

    def _draw_flow(self) -> None:
        self._flow_canvas.delete("all")
        for si, di in self._flows:
            if si < len(self._screens) and di < len(self._screens):
                s, d = self._screens[si], self._screens[di]
                self._flow_canvas.create_line(
                    s["x"] + 60, s["y"] + 40, d["x"] + 60, d["y"] + 40,
                    fill="#585b70", width=2, arrow=tk.LAST, arrowshape=(10, 12, 5))

        for i, screen in enumerate(self._screens):
            x, y = screen["x"], screen["y"]
            self._flow_canvas.create_rectangle(x, y, x + 120, y + 80,
                                               fill="#313244", outline="#89b4fa", width=2)
            self._flow_canvas.create_text(x + 60, y + 40, text=screen["name"],
                                          fill=self._fg, font=("Segoe UI", 10, "bold"))

    # ------------------------------------------------------------------
    # Preview and code export
    # ------------------------------------------------------------------

    def _update_preview(self) -> None:
        self._preview_canvas.delete("all")
        pw = self._preview_canvas.winfo_width() or 200
        ph = self._preview_canvas.winfo_height() or 300
        scale = min(pw / 300, ph / 660) * 0.9

        self._preview_canvas.create_rectangle(
            10, 10, 10 + 300 * scale, 10 + 660 * scale,
            fill="#181825", outline="#45475a")

        for comp in self._placed:
            x = 10 + (comp["x"] - 150) * scale
            y = 10 + (comp["y"] - 20) * scale
            w = comp["width"] * scale
            h = comp["height"] * scale
            self._preview_canvas.create_rectangle(x, y, x + w, y + h,
                                                  fill="#313244", outline=comp["color"])
            if w > 20 and h > 10:
                self._preview_canvas.create_text(x + w / 2, y + h / 2,
                                                 text=comp["text"][:8],
                                                 fill=comp["color"],
                                                 font=("Segoe UI", max(6, int(8 * scale))))

    def _generate_code(self) -> None:
        framework = self._framework_var.get()
        win = tk.Toplevel(self, bg=self._bg)
        win.title(f"Generated Code — {framework}")
        win.geometry("800x600")
        win.transient(self)

        # Tab for each file
        nb = ttk.Notebook(win)
        nb.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        files = self._build_code_files(framework)
        for filename, code in files.items():
            frame = tk.Frame(nb, bg="#181825")
            nb.add(frame, text=filename.split("/")[-1])
            text = tk.Text(frame, bg="#181825", fg=self._fg, insertbackground=self._fg,
                           font=("Consolas", 10), wrap=tk.NONE, relief=tk.FLAT)
            scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
            text.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
            text.insert("1.0", code)
            text.config(state=tk.DISABLED)

        # Save all button
        tk.Button(win, text="Save All Files", bg="#a6e3a1", fg="#1e1e2e",
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=16,
                  command=lambda: self._save_generated_files(files)).pack(pady=4)

    def _build_code_files(self, framework: str) -> Dict[str, str]:
        components = [{"type": c["type"].title(), "label": c["text"],
                       "id": c.get("id", f"comp_{i}"),
                       "position": {"x": c["x"], "y": c["y"]},
                       "size": {"width": c["width"], "height": c["height"]}}
                      for i, c in enumerate(self._placed)]
        screens = [{"name": s["name"], "components": components} for s in self._screens]

        if framework == "React + Framer Motion":
            from eostudio.codegen.react_motion import ReactMotionGenerator
            gen = ReactMotionGenerator(library="framer-motion")
            return gen.generate(self._animation_timeline, components, screens)
        elif framework == "React + GSAP":
            from eostudio.codegen.react_motion import ReactMotionGenerator
            gen = ReactMotionGenerator(library="gsap")
            return gen.generate(self._animation_timeline, components, screens)
        elif framework == "React":
            from eostudio.codegen.react import ReactGenerator
            return ReactGenerator().generate(components, screens)
        elif framework == "Flutter":
            from eostudio.codegen.flutter import FlutterGenerator
            return FlutterGenerator().generate(components, screens)
        elif framework == "Compose":
            from eostudio.codegen.compose import ComposeGenerator
            return ComposeGenerator().generate(components, screens)
        else:
            # HTML/CSS fallback
            return {"index.html": self._build_html(components)}

    def _build_html(self, components: List[Dict[str, Any]]) -> str:
        lines = ["<!DOCTYPE html>", '<html lang="en"><head><meta charset="UTF-8">',
                 '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
                 "<style>"]
        lines.append(self._design_system.export_css())
        lines.append("  .container { position: relative; width: 300px; margin: auto; }")
        lines.append("</style></head><body>")
        lines.append('<div class="container">')
        for comp in self._placed:
            tag = {"button": "button", "text": "p", "input": "input",
                   "image": "img", "container": "div", "card": "div",
                   "appbar": "header", "bottomnav": "nav"}.get(comp["type"], "div")
            style = (f"position:absolute;left:{comp['x'] - 150}px;"
                     f"top:{comp['y'] - 20}px;"
                     f"width:{comp['width']}px;height:{comp['height']}px;")
            if tag == "input":
                lines.append(f'  <input style="{style}" placeholder="{comp["text"]}"/>')
            elif tag == "img":
                lines.append(f'  <img style="{style}" alt="{comp["text"]}"/>')
            else:
                lines.append(f'  <{tag} style="{style}">{comp["text"]}</{tag}>')
        lines.append("</div></body></html>")
        return "\n".join(lines)

    def _save_generated_files(self, files: Dict[str, str]) -> None:
        import os
        directory = filedialog.askdirectory(title="Select output directory")
        if not directory:
            return
        for fname, content in files.items():
            path = os.path.join(directory, fname)
            os.makedirs(os.path.dirname(path) or directory, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        messagebox.showinfo("Saved", f"Generated {len(files)} files to {directory}")
