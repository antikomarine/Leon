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


# ---------------------------------------------------------------------------
# Reading PNGs back in.
#
# The app ships artwork it draws itself, but a wordmark set in a real typeface
# has to come from outside.  These helpers let the asset build take a supplied
# PNG, lift it off its background, recolour it and scale it down cleanly --
# still without any third-party library.
# ---------------------------------------------------------------------------
def read_png(path: str) -> tuple[int, int, bytearray]:
    """Decode a PNG into (width, height, RGBA bytes).

    Supports 8- and 16-bit greyscale, RGB, palette and alpha images, which
    covers anything an image editor or a browser will hand you.  Interlaced
    files are refused with a clear message rather than decoded wrongly.
    """
    with open(path, "rb") as handle:
        data = handle.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG file")

    pos = 8
    header = None
    palette = b""
    transparency = b""
    idat = bytearray()
    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        tag = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if tag == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif tag == b"PLTE":
            palette = body
        elif tag == b"tRNS":
            transparency = body
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
    if header is None:
        raise ValueError(f"{path} has no header chunk")

    width, height, depth, color_type, _comp, _filt, interlace = header
    if interlace:
        raise ValueError(f"{path} is interlaced; save it without interlacing")
    if depth not in (8, 16):
        raise ValueError(f"{path} uses {depth}-bit samples; save it as 8-bit")

    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
    sample = depth // 8
    stride = width * channels * sample
    step = channels * sample
    raw = zlib.decompress(bytes(idat))

    # Undo the per-scanline filters.
    lines = bytearray(stride * height)
    previous = bytearray(stride)
    at = 0
    for y in range(height):
        filter_type = raw[at]
        at += 1
        line = bytearray(raw[at : at + stride])
        at += stride
        if filter_type == 1:
            for i in range(step, stride):
                line[i] = (line[i] + line[i - step]) & 0xFF
        elif filter_type == 2:
            for i in range(stride):
                line[i] = (line[i] + previous[i]) & 0xFF
        elif filter_type == 3:
            for i in range(stride):
                left = line[i - step] if i >= step else 0
                line[i] = (line[i] + ((left + previous[i]) >> 1)) & 0xFF
        elif filter_type == 4:
            for i in range(stride):
                left = line[i - step] if i >= step else 0
                up = previous[i]
                upper_left = previous[i - step] if i >= step else 0
                p = left + up - upper_left
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - upper_left)
                nearest = left if (pa <= pb and pa <= pc) else (up if pb <= pc else upper_left)
                line[i] = (line[i] + nearest) & 0xFF
        elif filter_type != 0:
            raise ValueError(f"{path} uses unknown filter {filter_type}")
        lines[y * stride : (y + 1) * stride] = line
        previous = line

    # Expand whatever colour model it used into straight RGBA.
    out = bytearray(width * height * 4)
    alpha_for_index = {}
    for index, value in enumerate(transparency):
        alpha_for_index[index] = value
    for y in range(height):
        row = y * stride
        for x in range(width):
            i = row + x * step
            o = (y * width + x) * 4
            if color_type == 0:
                grey = lines[i]
                out[o : o + 4] = bytes((grey, grey, grey, 255))
            elif color_type == 2:
                out[o : o + 3] = bytes((lines[i], lines[i + sample], lines[i + 2 * sample]))
                out[o + 3] = 255
            elif color_type == 3:
                index = lines[i]
                out[o : o + 3] = palette[index * 3 : index * 3 + 3]
                out[o + 3] = alpha_for_index.get(index, 255)
            elif color_type == 4:
                grey = lines[i]
                out[o : o + 4] = bytes((grey, grey, grey, lines[i + sample]))
            else:
                out[o] = lines[i]
                out[o + 1] = lines[i + sample]
                out[o + 2] = lines[i + 2 * sample]
                out[o + 3] = lines[i + 3 * sample]
    return width, height, out


def looks_like_flat_background(width: int, height: int, px: bytearray) -> bool:
    """True when the four corners are the same opaque light colour."""
    corners = []
    for x, y in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)):
        i = (y * width + x) * 4
        corners.append(tuple(px[i : i + 4]))
    first = corners[0]
    if first[3] < 250 or min(first[:3]) < 200:
        return False
    return all(max(abs(a - b) for a, b in zip(corner, first)) < 12 for corner in corners)


def background_to_alpha(width: int, height: int, px: bytearray, ink: Color) -> bytearray:
    """Lift artwork off a flat light background, keeping its soft edges.

    Every pixel is treated as a blend of the ink colour over the background, so
    the coverage can be recovered instead of guessed -- which is what keeps the
    edges smooth rather than jagged.
    """
    i = 0
    background = tuple(px[0:3])
    channel = max(range(3), key=lambda c: abs(background[c] - ink[c]))
    span = background[channel] - ink[channel]
    if span == 0:
        return px
    out = bytearray(len(px))
    for i in range(0, len(px), 4):
        coverage = (background[channel] - px[i + channel]) / span
        alpha = max(0.0, min(1.0, coverage)) * (px[i + 3] / 255)
        out[i : i + 3] = bytes(ink[:3])
        out[i + 3] = round(alpha * 255)
    return out


def trim_rgba(width: int, height: int, px: bytearray, margin: int = 0):
    """Crop away fully transparent edges."""
    left, right, top, bottom = width, -1, height, -1
    for y in range(height):
        row = y * width * 4
        for x in range(width):
            if px[row + x * 4 + 3] > 4:
                left, right = min(left, x), max(right, x)
                top, bottom = min(top, y), max(bottom, y)
    if right < 0:
        return width, height, px
    left = max(0, left - margin)
    top = max(0, top - margin)
    right = min(width - 1, right + margin)
    bottom = min(height - 1, bottom + margin)
    new_w, new_h = right - left + 1, bottom - top + 1
    out = bytearray(new_w * new_h * 4)
    for y in range(new_h):
        source = ((y + top) * width + left) * 4
        out[y * new_w * 4 : (y + 1) * new_w * 4] = px[source : source + new_w * 4]
    return new_w, new_h, out


def scale_rgba(
    width: int, height: int, px: bytearray, new_w: int, new_h: int, sharpen: float = 2.2
) -> bytearray:
    """Resample to a new size, choosing the right method for the direction.

    Shrinking uses a box filter.  Growing uses bilinear interpolation followed
    by a contrast curve on the alpha channel: interpolation alone turns a small
    logo into a blur, and nearest-neighbour turns it into a staircase, but
    pulling the interpolated coverage back towards 0 and 1 reconstructs a clean
    edge.  Artwork in a single flat colour -- which a wordmark is -- takes to
    this well.
    """
    if new_w > width or new_h > height:
        return _grow_rgba(width, height, px, new_w, new_h, sharpen)
    return _shrink_rgba(width, height, px, new_w, new_h)


def _grow_rgba(
    width: int, height: int, px: bytearray, new_w: int, new_h: int, sharpen: float
) -> bytearray:
    out = bytearray(new_w * new_h * 4)
    x_ratio = width / new_w
    y_ratio = height / new_h
    for y in range(new_h):
        source_y = min(height - 1.0, max(0.0, (y + 0.5) * y_ratio - 0.5))
        y0 = int(source_y)
        y1 = min(height - 1, y0 + 1)
        wy = source_y - y0
        for x in range(new_w):
            source_x = min(width - 1.0, max(0.0, (x + 0.5) * x_ratio - 0.5))
            x0 = int(source_x)
            x1 = min(width - 1, x0 + 1)
            wx = source_x - x0
            acc = [0.0, 0.0, 0.0, 0.0]
            for (sx, sy, weight) in (
                (x0, y0, (1 - wx) * (1 - wy)), (x1, y0, wx * (1 - wy)),
                (x0, y1, (1 - wx) * wy), (x1, y1, wx * wy),
            ):
                if weight <= 0:
                    continue
                i = (sy * width + sx) * 4
                alpha = px[i + 3] / 255
                acc[0] += px[i] * alpha * weight
                acc[1] += px[i + 1] * alpha * weight
                acc[2] += px[i + 2] * alpha * weight
                acc[3] += alpha * weight
            o = (y * new_w + x) * 4
            coverage = acc[3]
            if coverage > 0:
                out[o] = min(255, round(acc[0] / coverage))
                out[o + 1] = min(255, round(acc[1] / coverage))
                out[o + 2] = min(255, round(acc[2] / coverage))
            # Push part-covered pixels towards fully on or fully off.
            edged = (coverage - 0.5) * sharpen + 0.5
            out[o + 3] = round(max(0.0, min(1.0, edged)) * 255)
    return out


def _shrink_rgba(width: int, height: int, px: bytearray, new_w: int, new_h: int) -> bytearray:
    """Box-filter resample, working on premultiplied alpha so edges stay clean."""
    out = bytearray(new_w * new_h * 4)
    for y in range(new_h):
        y0, y1 = y * height // new_h, max(y * height // new_h + 1, (y + 1) * height // new_h)
        for x in range(new_w):
            x0, x1 = x * width // new_w, max(x * width // new_w + 1, (x + 1) * width // new_w)
            acc_a = acc_r = acc_g = acc_b = 0
            count = 0
            for sy in range(y0, y1):
                row = (sy * width) * 4
                for sx in range(x0, x1):
                    i = row + sx * 4
                    a = px[i + 3]
                    acc_a += a
                    acc_r += px[i] * a
                    acc_g += px[i + 1] * a
                    acc_b += px[i + 2] * a
                    count += 1
            o = (y * new_w + x) * 4
            if acc_a:
                out[o] = round(acc_r / acc_a)
                out[o + 1] = round(acc_g / acc_a)
                out[o + 2] = round(acc_b / acc_a)
                out[o + 3] = round(acc_a / max(1, count))
    return out
