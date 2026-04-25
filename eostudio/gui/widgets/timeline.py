"""Timeline widget — visual keyframe editor with draggable handles and easing preview."""

from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk
from typing import Any, Callable, Dict, List, Optional, Tuple

from eostudio.core.animation.keyframe import EasingFunction, EASING_FUNCTIONS, KeyframeTrack
from eostudio.core.animation.timeline import AnimationClip, AnimationTimeline, PlayState


class TimelineWidget(tk.Frame):
    """Multi-track keyframe timeline editor for animations."""

    TRACK_HEIGHT = 28
    HEADER_WIDTH = 140
    KEYFRAME_RADIUS = 5
    RULER_HEIGHT = 24
    MIN_PIXELS_PER_SECOND = 60
    MAX_PIXELS_PER_SECOND = 600

    def __init__(self, master: tk.Widget, bg: str = "#1e1e2e", fg: str = "#cdd6f4",
                 on_time_change: Optional[Callable[[float], None]] = None,
                 on_keyframe_change: Optional[Callable[[str, int, float], None]] = None,
                 **kw: Any) -> None:
        super().__init__(master, bg=bg, **kw)
        self._bg = bg
        self._fg = fg
        self._on_time_change = on_time_change
        self._on_keyframe_change = on_keyframe_change

        self._timeline: Optional[AnimationTimeline] = None
        self._pixels_per_second = 120.0
        self._scroll_x = 0.0
        self._current_time = 0.0
        self._playing = False
        self._selected_kf: Optional[Tuple[int, int, int]] = None  # clip_idx, track_idx, kf_idx
        self._drag_start_x: Optional[int] = None
        self._drag_kf_original_time: float = 0.0

        self._build_ui()

    def _build_ui(self) -> None:
        # Transport controls
        transport = tk.Frame(self, bg=self._bg)
        transport.pack(fill=tk.X, padx=4, pady=2)

        self._play_btn = tk.Button(transport, text="\u25B6", bg="#313244", fg="#a6e3a1",
                                   font=("Segoe UI", 10), relief=tk.FLAT, width=3,
                                   command=self._toggle_play)
        self._play_btn.pack(side=tk.LEFT, padx=2)

        tk.Button(transport, text="\u23F9", bg="#313244", fg="#f38ba8",
                  font=("Segoe UI", 10), relief=tk.FLAT, width=3,
                  command=self._stop).pack(side=tk.LEFT, padx=2)

        tk.Button(transport, text="\u23EE", bg="#313244", fg=self._fg,
                  font=("Segoe UI", 10), relief=tk.FLAT, width=3,
                  command=self._go_to_start).pack(side=tk.LEFT, padx=2)

        tk.Button(transport, text="\u23ED", bg="#313244", fg=self._fg,
                  font=("Segoe UI", 10), relief=tk.FLAT, width=3,
                  command=self._go_to_end).pack(side=tk.LEFT, padx=2)

        self._time_label = tk.Label(transport, text="0.000s", bg=self._bg, fg="#f9e2af",
                                    font=("Consolas", 10))
        self._time_label.pack(side=tk.LEFT, padx=8)

        tk.Button(transport, text="+KF", bg="#89b4fa", fg="#1e1e2e",
                  font=("Segoe UI", 9), relief=tk.FLAT, padx=6,
                  command=self._add_keyframe_at_cursor).pack(side=tk.RIGHT, padx=2)

        # Zoom controls
        tk.Button(transport, text="\u2796", bg="#313244", fg=self._fg,
                  font=("Segoe UI", 9), relief=tk.FLAT, width=2,
                  command=self._zoom_out).pack(side=tk.RIGHT, padx=1)
        tk.Button(transport, text="\u2795", bg="#313244", fg=self._fg,
                  font=("Segoe UI", 9), relief=tk.FLAT, width=2,
                  command=self._zoom_in).pack(side=tk.RIGHT, padx=1)

        # Easing selector
        self._easing_var = tk.StringVar(value="ease_in_out")
        easing_combo = ttk.Combobox(transport, textvariable=self._easing_var,
                                    values=[e.value for e in EasingFunction if e != EasingFunction.CUBIC_BEZIER],
                                    width=16, state="readonly")
        easing_combo.pack(side=tk.RIGHT, padx=4)
        tk.Label(transport, text="Easing:", bg=self._bg, fg=self._fg,
                 font=("Segoe UI", 9)).pack(side=tk.RIGHT)

        # Main timeline area
        main = tk.Frame(self, bg=self._bg)
        main.pack(fill=tk.BOTH, expand=True)

        # Track headers
        self._header_canvas = tk.Canvas(main, bg="#181825", width=self.HEADER_WIDTH,
                                        highlightthickness=0)
        self._header_canvas.pack(side=tk.LEFT, fill=tk.Y)

        # Timeline canvas
        self._canvas = tk.Canvas(main, bg="#11111b", highlightthickness=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self._canvas.bind("<ButtonPress-1>", self._on_click)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        self._canvas.bind("<Configure>", lambda e: self._redraw())
        self._canvas.bind("<MouseWheel>", self._on_scroll)

    def set_timeline(self, timeline: AnimationTimeline) -> None:
        self._timeline = timeline
        self._current_time = 0.0
        self._selected_kf = None
        self._redraw()

    def get_timeline(self) -> Optional[AnimationTimeline]:
        return self._timeline

    def set_time(self, time: float) -> None:
        self._current_time = max(0.0, time)
        self._time_label.config(text=f"{self._current_time:.3f}s")
        self._redraw()

    # --- Transport ---

    def _toggle_play(self) -> None:
        self._playing = not self._playing
        self._play_btn.config(text="\u23F8" if self._playing else "\u25B6")
        if self._playing:
            self._animate_step()

    def _stop(self) -> None:
        self._playing = False
        self._play_btn.config(text="\u25B6")
        self._current_time = 0.0
        self._time_label.config(text="0.000s")
        self._redraw()

    def _go_to_start(self) -> None:
        self.set_time(0.0)
        if self._on_time_change:
            self._on_time_change(0.0)

    def _go_to_end(self) -> None:
        if self._timeline:
            self.set_time(self._timeline.duration)
            if self._on_time_change:
                self._on_time_change(self._timeline.duration)

    def _animate_step(self) -> None:
        if not self._playing or not self._timeline:
            return
        dt = 1.0 / 30.0
        self._current_time += dt
        if self._current_time > self._timeline.duration:
            self._current_time = 0.0
        self._time_label.config(text=f"{self._current_time:.3f}s")
        self._redraw()
        if self._on_time_change:
            self._on_time_change(self._current_time)
        self.after(33, self._animate_step)

    # --- Zoom ---

    def _zoom_in(self) -> None:
        self._pixels_per_second = min(self.MAX_PIXELS_PER_SECOND, self._pixels_per_second * 1.3)
        self._redraw()

    def _zoom_out(self) -> None:
        self._pixels_per_second = max(self.MIN_PIXELS_PER_SECOND, self._pixels_per_second / 1.3)
        self._redraw()

    def _on_scroll(self, event: tk.Event) -> None:
        if event.delta > 0:
            self._zoom_in()
        else:
            self._zoom_out()

    # --- Drawing ---

    def _time_to_x(self, t: float) -> float:
        return (t - self._scroll_x) * self._pixels_per_second

    def _x_to_time(self, x: float) -> float:
        return x / self._pixels_per_second + self._scroll_x

    def _redraw(self) -> None:
        self._canvas.delete("all")
        self._header_canvas.delete("all")

        if not self._timeline:
            self._canvas.create_text(200, 40, text="No timeline loaded",
                                     fill="#585b70", font=("Segoe UI", 11))
            return

        canvas_w = self._canvas.winfo_width() or 600
        canvas_h = self._canvas.winfo_height() or 200

        # Draw ruler
        self._draw_ruler(canvas_w)

        # Draw tracks
        y_offset = self.RULER_HEIGHT
        for ci, clip in enumerate(self._timeline.clips):
            for ti, track in enumerate(clip.tracks):
                track_y = y_offset + (ci * len(clip.tracks) + ti) * self.TRACK_HEIGHT
                self._draw_track(clip, ci, track, ti, track_y, canvas_w)

        # Draw playhead
        playhead_x = self._time_to_x(self._current_time)
        if 0 <= playhead_x <= canvas_w:
            self._canvas.create_line(playhead_x, 0, playhead_x, canvas_h,
                                     fill="#f38ba8", width=2, tags="playhead")
            self._canvas.create_polygon(
                playhead_x - 5, 0, playhead_x + 5, 0, playhead_x, 8,
                fill="#f38ba8", tags="playhead")

    def _draw_ruler(self, width: float) -> None:
        step = max(0.1, 1.0 / (self._pixels_per_second / 60))
        t = 0.0
        max_time = self._x_to_time(width)
        while t <= max_time + step:
            x = self._time_to_x(t)
            if 0 <= x <= width:
                is_major = abs(t - round(t)) < 0.01
                h = self.RULER_HEIGHT if is_major else self.RULER_HEIGHT * 0.5
                color = "#585b70" if is_major else "#45475a"
                self._canvas.create_line(x, self.RULER_HEIGHT - h, x, self.RULER_HEIGHT,
                                         fill=color, width=1)
                if is_major:
                    self._canvas.create_text(x, 4, text=f"{t:.1f}s", anchor=tk.N,
                                             fill="#6c7086", font=("Consolas", 8))
            t += step

        self._canvas.create_line(0, self.RULER_HEIGHT, width, self.RULER_HEIGHT,
                                 fill="#45475a", width=1)

    def _draw_track(self, clip: AnimationClip, ci: int, track: KeyframeTrack,
                    ti: int, y: float, width: float) -> None:
        # Track background
        bg_color = "#1e1e2e" if (ci + ti) % 2 == 0 else "#181825"
        self._canvas.create_rectangle(0, y, width, y + self.TRACK_HEIGHT,
                                      fill=bg_color, outline="#313244", width=1)

        # Header
        self._header_canvas.create_rectangle(0, y, self.HEADER_WIDTH, y + self.TRACK_HEIGHT,
                                             fill=bg_color, outline="#313244", width=1)
        label = f"{clip.target_id[:10]}.{track.property_name}"
        self._header_canvas.create_text(8, y + self.TRACK_HEIGHT / 2, text=label,
                                        anchor=tk.W, fill=self._fg, font=("Segoe UI", 8))

        # Clip duration bar
        start_x = self._time_to_x(clip.delay)
        end_x = self._time_to_x(clip.delay + clip.duration)
        bar_y = y + 8
        bar_h = self.TRACK_HEIGHT - 16
        self._canvas.create_rectangle(start_x, bar_y, end_x, bar_y + bar_h,
                                      fill="#313244", outline="#45475a", width=1)

        # Keyframes
        colors = {"entrance": "#a6e3a1", "exit": "#f38ba8", "attention": "#f9e2af",
                  "scroll": "#89b4fa", "transition": "#cba6f7", "layout": "#fab387"}
        kf_color = colors.get(clip.label, "#89b4fa")

        for ki, kf in enumerate(track.keyframes):
            kx = self._time_to_x(clip.delay + kf.time)
            ky = y + self.TRACK_HEIGHT / 2
            is_selected = self._selected_kf == (ci, ti, ki)
            r = self.KEYFRAME_RADIUS + 1 if is_selected else self.KEYFRAME_RADIUS
            outline = "#f9e2af" if is_selected else kf_color
            self._canvas.create_oval(kx - r, ky - r, kx + r, ky + r,
                                     fill=kf_color, outline=outline,
                                     width=2 if is_selected else 1,
                                     tags=f"kf_{ci}_{ti}_{ki}")

    # --- Interaction ---

    def _on_click(self, event: tk.Event) -> None:
        x, y = event.x, event.y
        if y < self.RULER_HEIGHT:
            self._current_time = max(0.0, self._x_to_time(x))
            self._time_label.config(text=f"{self._current_time:.3f}s")
            self._redraw()
            if self._on_time_change:
                self._on_time_change(self._current_time)
            return

        self._selected_kf = self._hit_test_keyframe(x, y)
        if self._selected_kf:
            ci, ti, ki = self._selected_kf
            clip = self._timeline.clips[ci]
            kf = clip.tracks[ti].keyframes[ki]
            self._drag_start_x = x
            self._drag_kf_original_time = kf.time
            self._easing_var.set(kf.easing.value)
        self._redraw()

    def _on_drag(self, event: tk.Event) -> None:
        if not self._selected_kf or self._drag_start_x is None or not self._timeline:
            return
        ci, ti, ki = self._selected_kf
        dx = event.x - self._drag_start_x
        dt = dx / self._pixels_per_second
        new_time = max(0.0, self._drag_kf_original_time + dt)
        clip = self._timeline.clips[ci]
        clip.tracks[ti].keyframes[ki].time = new_time
        clip.tracks[ti].keyframes.sort(key=lambda k: k.time)
        # Re-find index after sort
        for new_ki, kf in enumerate(clip.tracks[ti].keyframes):
            if abs(kf.time - new_time) < 1e-6:
                self._selected_kf = (ci, ti, new_ki)
                break
        self._redraw()

    def _on_release(self, event: tk.Event) -> None:
        if self._selected_kf and self._on_keyframe_change and self._timeline:
            ci, ti, ki = self._selected_kf
            clip = self._timeline.clips[ci]
            kf = clip.tracks[ti].keyframes[ki]
            self._on_keyframe_change(clip.target_id, ki, kf.time)
        self._drag_start_x = None

    def _hit_test_keyframe(self, x: float, y: float) -> Optional[Tuple[int, int, int]]:
        if not self._timeline:
            return None
        y_offset = self.RULER_HEIGHT
        for ci, clip in enumerate(self._timeline.clips):
            for ti, track in enumerate(clip.tracks):
                track_y = y_offset + (ci * len(clip.tracks) + ti) * self.TRACK_HEIGHT
                ky = track_y + self.TRACK_HEIGHT / 2
                if abs(y - ky) > self.TRACK_HEIGHT / 2:
                    continue
                for ki, kf in enumerate(track.keyframes):
                    kx = self._time_to_x(clip.delay + kf.time)
                    if abs(x - kx) <= self.KEYFRAME_RADIUS + 3 and abs(y - ky) <= self.KEYFRAME_RADIUS + 3:
                        return (ci, ti, ki)
        return None

    def _add_keyframe_at_cursor(self) -> None:
        if not self._timeline or not self._timeline.clips:
            return
        clip = self._timeline.clips[0]
        if clip.tracks:
            track = clip.tracks[0]
            easing = EasingFunction(self._easing_var.get())
            current_value = track.evaluate(self._current_time)
            track.add_keyframe(self._current_time, current_value, easing)
            self._redraw()
