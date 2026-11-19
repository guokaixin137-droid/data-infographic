"""Map a brief's five color roles to the surfaces, labels and data marks."""
import re


BASE = {"paper": "#f6f3e7", "ink": "#122c28", "primary": "#236554",
        "accent": "#e6f56e", "negative": "#a44735"}

# The original template palette is retained for briefs without custom colors.
DEFAULT = {
    **BASE, "muted": "#4d625a", "rule": "#a1b0a2", "outside": "#ced3c7",
    "on-hero": BASE["paper"], "hero-accent": BASE["accent"], "on-accent": BASE["ink"],
    "hero-rule": "#81958a", "track": "#e1e6d7", "baseline": "#667e70",
    "primary-text": BASE["primary"], "grid": "#acbaaa", "grid-zero": "#748b7e",
    "missing": "#e5e5d9", "footer": "#e1e8d9", "target": "#f2f7c5",
    "matrix-base": "#edf1e1", "matrix-negative": "#963a27",
}


def rgb(color):
    return tuple(int(color[n:n + 2], 16) for n in (1, 3, 5))


def mix(first, second, amount):
    channels = [round(a + (b - a) * amount) for a, b in zip(rgb(first), rgb(second))]
    return "#" + "".join(f"{channel:02x}" for channel in channels)


def luminance(color):
    channels = [v / 255 for v in rgb(color)]
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
    return sum(v * weight for v, weight in zip(linear, (.2126, .7152, .0722)))


def contrast(a, b):
    low, high = sorted((luminance(a), luminance(b)))
    return (high + .05) / (low + .05)


def readable(color, surface, minimum=4.5):
    if contrast(color, surface) >= minimum:
        return color
    endpoint = max(("#000000", "#ffffff"), key=lambda c: contrast(c, surface))
    lower, upper = 0.0, 1.0
    for _ in range(10):
        middle = (lower + upper) / 2
        if contrast(mix(color, endpoint, middle), surface) >= minimum:
            upper = middle
        else:
            lower = middle
    return mix(color, endpoint, upper)


def text_on_fill(ink, fill):
    if contrast(ink, fill) >= 4.5:
        return ink
    return max(("#ffffff", "#000000"), key=lambda c: contrast(c, fill))


def resolve(colors):
    if colors is None:
        return {**DEFAULT, "accent-mark": readable(BASE["accent"], BASE["paper"], 3),
                "accent-text": readable(BASE["accent"], BASE["paper"])}
    if not isinstance(colors, dict) or set(colors) != set(BASE):
        raise ValueError("palette.colors requires paper, ink, primary, accent and negative")
    for role, value in colors.items():
        if not isinstance(value, str) or not re.fullmatch("#[0-9A-Fa-f]{6}", value):
            raise ValueError(f"palette.colors.{role} must be a six-digit #RRGGBB color")
    paper = colors["paper"]
    ink = readable(colors["ink"], paper)
    accent = colors["accent"]
    track = mix(paper, ink, .09)
    primary = readable(readable(colors["primary"], paper, 3), track, 3)
    negative = readable(readable(colors["negative"], paper, 3), track, 3)
    footer = mix(paper, primary, .07)
    muted = readable(readable(mix(ink, paper, .23), paper), footer)
    primary_text = readable(readable(primary, paper), footer)
    return {
        **colors, "ink": ink, "primary": primary, "negative": negative, "muted": muted,
        "accent-mark": readable(accent, paper, 3), "accent-text": readable(accent, paper),
        "rule": mix(paper, ink, .36), "outside": mix(paper, ink, .18), "on-hero": paper,
        "hero-accent": readable(accent, ink), "on-accent": readable(ink, accent),
        "hero-rule": mix(ink, paper, .5), "track": track, "baseline": mix(paper, ink, .6),
        "primary-text": primary_text, "grid": mix(paper, ink, .32),
        "grid-zero": mix(paper, ink, .55), "missing": track, "footer": footer,
        "target": mix(paper, accent, .22), "matrix-base": mix(paper, primary, .06),
        "matrix-negative": negative,
    }
