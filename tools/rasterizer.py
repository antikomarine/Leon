"""A tiny dependency-free raster drawing library.

Everything the app displays is a real PNG file, and those PNGs are drawn by
this module instead of being shipped as binary blobs from somewhere else.
That keeps the project installable with nothing but the standard library.

Shapes are rasterised on a supersampled grid (``ss`` samples per axis) and
box-filtered down on save, which is what gives the artwork smooth edges.
All coordinates passed in by callers are in *output* pixels and may be floats.
"""

from __future__ import annotations

import math
import struct
import zlib

Color = tuple[int, int, int, int]


def rgba(hex_color: str, alpha: int = 255) -> Color:
    """``"#4caf50"`` -> ``(76, 175, 80, 255)``."""
    value = hex_color.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha)


def mix(a: str, b: str, t: float) -> str:
    """Blend two hex colors, ``t=0`` -> ``a``, ``t=1`` -> ``b``."""
    ar, ag, ab, _ = rgba(a)
    br, bg, bb, _ = rgba(b)
    return "#%02x%02x%02x" % (
        round(ar + (br - ar) * t),
        round(ag + (bg - ag) * t),
        round(ab + (bb - ab) * t),
    )


class Raster:
    """A supersampled RGBA canvas."""

    def __init__(self, width: int, height: int, ss: int = 4) -> None:
        self.width = width
        self.height = height
        self.ss = ss
        self.w = width * ss
        self.h = height * ss
        self.px = bytearray(self.w * self.h * 4)

    # -- low level ---------------------------------------------------------
    def _blend_span(self, y: int, x0: int, x1: int, color: Color) -> None:
        """Source-over blend of a horizontal run of samples."""
        if y < 0 or y >= self.h:
            return
        x0 = max(0, x0)
        x1 = min(self.w, x1)
        if x1 <= x0:
            return
        r, g, b, a = color
        row = y * self.w * 4
        if a >= 255:
            chunk = bytes((r, g, b, 255)) * (x1 - x0)
            self.px[row + x0 * 4 : row + x1 * 4] = chunk
            return
        sa = a / 255.0
        px = self.px
        for x in range(x0, x1):
            i = row + x * 4
            da = px[i + 3] / 255.0
            out_a = sa + da * (1 - sa)
            if out_a <= 0:
                continue
            px[i] = round((r * sa + px[i] * da * (1 - sa)) / out_a)
            px[i + 1] = round((g * sa + px[i + 1] * da * (1 - sa)) / out_a)
            px[i + 2] = round((b * sa + px[i + 2] * da * (1 - sa)) / out_a)
            px[i + 3] = round(out_a * 255)

    # -- shapes ------------------------------------------------------------
    def fill_all(self, color: Color) -> None:
        for y in range(self.h):
            self._blend_span(y, 0, self.w, color)

    def fill_rect(self, x0: float, y0: float, x1: float, y1: float, color: Color) -> None:
        s = self.ss
        for y in range(max(0, round(y0 * s)), min(self.h, round(y1 * s))):
            self._blend_span(y, round(x0 * s), round(x1 * s), color)

    def fill_ellipse(self, cx: float, cy: float, rx: float, ry: float, color: Color) -> None:
        s = self.ss
        cx, cy, rx, ry = cx * s, cy * s, rx * s, ry * s
        if rx <= 0 or ry <= 0:
            return
        for y in range(max(0, math.floor(cy - ry)), min(self.h, math.ceil(cy + ry) + 1)):
            dy = (y + 0.5 - cy) / ry
            if abs(dy) > 1:
                continue
            dx = math.sqrt(max(0.0, 1 - dy * dy)) * rx
            self._blend_span(y, round(cx - dx), round(cx + dx), color)

    def fill_circle(self, cx: float, cy: float, r: float, color: Color) -> None:
        self.fill_ellipse(cx, cy, r, r, color)

    def fill_poly(self, points: list[tuple[float, float]], color: Color) -> None:
        """Even-odd scanline fill."""
        if len(points) < 3:
            return
        s = self.ss
        pts = [(x * s, y * s) for x, y in points]
        top = max(0, math.floor(min(p[1] for p in pts)))
        bottom = min(self.h, math.ceil(max(p[1] for p in pts)) + 1)
        for y in range(top, bottom):
            yc = y + 0.5
            crossings = []
            for i in range(len(pts)):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % len(pts)]
                if (y0 <= yc < y1) or (y1 <= yc < y0):
                    crossings.append(x0 + (yc - y0) * (x1 - x0) / (y1 - y0))
            crossings.sort()
            for i in range(0, len(crossings) - 1, 2):
                self._blend_span(y, round(crossings[i]), round(crossings[i + 1]), color)

    def fill_round_rect(
        self, x0: float, y0: float, x1: float, y1: float, radius: float, color: Color
    ) -> None:
        radius = min(radius, (x1 - x0) / 2, (y1 - y0) / 2)
        self.fill_rect(x0 + radius, y0, x1 - radius, y1, color)
        self.fill_rect(x0, y0 + radius, x1, y1 - radius, color)
        for cx, cy in (
            (x0 + radius, y0 + radius),
            (x1 - radius, y0 + radius),
            (x0 + radius, y1 - radius),
            (x1 - radius, y1 - radius),
        ):
            self.fill_circle(cx, cy, radius, color)

    def stroke_line(
        self, x0: float, y0: float, x1: float, y1: float, width: float, color: Color,
        caps: bool = True,
    ) -> None:
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        if length == 0:
            if caps:
                self.fill_circle(x0, y0, width / 2, color)
            return
        nx, ny = -dy / length * width / 2, dx / length * width / 2
        self.fill_poly(
            [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)],
            color,
        )
        if caps:
            self.fill_circle(x0, y0, width / 2, color)
            self.fill_circle(x1, y1, width / 2, color)

    def stroke_path(self, points: list[tuple[float, float]], width: float, color: Color) -> None:
        for i in range(len(points) - 1):
            self.stroke_line(*points[i], *points[i + 1], width, color)

    def stroke_poly(self, points: list[tuple[float, float]], width: float, color: Color) -> None:
        self.stroke_path(list(points) + [points[0]], width, color)

    def arc(
        self, cx: float, cy: float, r: float, start_deg: float, end_deg: float,
        width: float, color: Color,
    ) -> None:
        """Stroked arc; angles in degrees, 0 = east, growing clockwise."""
        steps = max(6, int(abs(end_deg - start_deg) / 6))
        pts = []
        for i in range(steps + 1):
            angle = math.radians(start_deg + (end_deg - start_deg) * i / steps)
            pts.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
        self.stroke_path(pts, width, color)

    def ring(self, cx: float, cy: float, r: float, width: float, color: Color) -> None:
        self.arc(cx, cy, r, 0, 360, width, color)

    def star(self, cx: float, cy: float, r: float, points: int,
             inner: float, color: Color) -> None:
        pts = []
        for i in range(points * 2):
            radius = r if i % 2 == 0 else r * inner
            angle = math.radians(-90 + i * 180 / points)
            pts.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
        self.fill_poly(pts, color)

    # -- erasing (punching holes so icons read as outlines) ----------------
    def _clear_span(self, y: int, x0: int, x1: int) -> None:
        if y < 0 or y >= self.h:
            return
        for x in range(max(0, x0), min(self.w, x1)):
            self.px[(y * self.w + x) * 4 + 3] = 0

    def erase_rect(self, x0: float, y0: float, x1: float, y1: float) -> None:
        s = self.ss
        for y in range(max(0, round(y0 * s)), min(self.h, round(y1 * s))):
            self._clear_span(y, round(x0 * s), round(x1 * s))

    def erase_circle(self, cx: float, cy: float, r: float) -> None:
        s = self.ss
        cx, cy, r = cx * s, cy * s, r * s
        for y in range(max(0, math.floor(cy - r)), min(self.h, math.ceil(cy + r) + 1)):
            dy = y + 0.5 - cy
            if abs(dy) > r:
                continue
            dx = math.sqrt(max(0.0, r * r - dy * dy))
            self._clear_span(y, round(cx - dx), round(cx + dx))

    # -- output ------------------------------------------------------------
    def downsample(self) -> bytes:
        """Box-filter the supersampled buffer down to the final size."""
        s = self.ss
        out = bytearray(self.width * self.height * 4)
        samples = s * s
        px = self.px
        for y in range(self.height):
            for x in range(self.width):
                acc_a = acc_r = acc_g = acc_b = 0
                for sy in range(s):
                    row = ((y * s + sy) * self.w + x * s) * 4
                    for sx in range(s):
                        i = row + sx * 4
                        a = px[i + 3]
                        if a:
                            acc_a += a
                            acc_r += px[i] * a
                            acc_g += px[i + 1] * a
                            acc_b += px[i + 2] * a
                o = (y * self.width + x) * 4
                if acc_a:
                    out[o] = round(acc_r / acc_a)
                    out[o + 1] = round(acc_g / acc_a)
                    out[o + 2] = round(acc_b / acc_a)
                    out[o + 3] = round(acc_a / samples)
        return bytes(out)

    def save(self, path: str) -> None:
        write_png(path, self.width, self.height, self.downsample())


def write_png(path: str, width: int, height: int, rgba_bytes: bytes) -> None:
    """Write 8-bit RGBA pixel data as a PNG file."""
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)  # filter type: none
        raw += rgba_bytes[y * stride : (y + 1) * stride]

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as handle:
        handle.write(png)


def _clip_circle(raster: Raster, cx: float, cy: float, r: float) -> None:
    """Erase everything outside a circle (used to cut avatars to a disc)."""
    s = raster.ss
    cx, cy, r = cx * s, cy * s, r * s
    for y in range(raster.h):
        dy = y + 0.5 - cy
        for x in range(raster.w):
            dx = x + 0.5 - cx
            if dx * dx + dy * dy > r * r:
                raster.px[(y * raster.w + x) * 4 + 3] = 0


Raster.clip_circle = _clip_circle
