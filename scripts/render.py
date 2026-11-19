"""Render a data-infographic brief as a standalone HTML file (standard library)."""
import argparse
import json
import math
from html import escape
from pathlib import Path
from string import Template
from urllib.parse import urlsplit


def checked_list(items, name):
    if not isinstance(items, list) or not items:
        raise ValueError(f"{name} must be a non-empty list")
    return items


def numbers(values):
    for value in values:
        if value is None:
            continue
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f"Expected a finite number or null, got {value!r}")
    return [value for value in values if value is not None]


def fmt(value):
    if value is None:
        return "—"
    if isinstance(value, int):
        return format(value, ",")
    if value.is_integer():
        return format(int(value), ",")
    return str(value)


def e(value):
    return escape(str(value), quote=True)


def optional(tag, content, css=""):
    if content is None or content == "":
        return ""
    attr = f' class="{css}"' if css else ""
    return f"<{tag}{attr}>{e(content)}</{tag}>"


def bars(block, refs):
    rows = checked_list(block["rows"], "bar rows")
    values = numbers([row["value"] for row in rows])
    lo, hi = min([0, *values]), max([0, *values])
    span = hi - lo or 1
    zero = 100 * -lo / span
    result = []
    for row in rows:
        value = row["value"]
        fill = ""
        if value is not None:
            start = zero + 100 * min(value, 0) / span
            width = 100 * abs(value) / span
            css = "fill negative" if value < 0 else "fill"
            fill = f'<i class="{css}" style="left:{start:.4f}%;width:{width:.4f}%"></i>'
        result.append(
            f'<div class="bar-row"><span class="row-label">{e(row["label"])}{refs(row)}</span>'
            f'<span class="track" style="--zero:{zero:.4f}%" aria-hidden="true">{fill}</span>'
            f'<span class="value">{fmt(value)}</span></div>'
        )
    return "".join(result)


def trend(block, refs):
    rows = checked_list(block["rows"], "trend rows")
    values = numbers([row["value"] for row in rows])
    lo, hi = min([0, *values]), max([0, *values])
    if hi == lo:
        hi = lo + 1
    left, right, top, bottom = 66, 592, 13, 142

    def ordinate(value):
        return bottom - (value - lo) * (bottom - top) / (hi - lo)

    grid = []
    for bound in (lo, hi):
        y = ordinate(bound)
        grid.append(
            f'<line x1="{left}" y1="{y}" x2="{right}" y2="{y}" stroke="#acbaaa"/>'
            f'<text x="{left - 7}" y="{y + 4}" text-anchor="end" font-size="13" '
            f'fill="#4d625a">{fmt(bound)}</text>'
        )
    if lo < 0 < hi:
        y = ordinate(0)
        grid.append(f'<line x1="{left}" y1="{y}" x2="{right}" y2="{y}" stroke="#748b7e"/>')
    path, dots, key = [], [], []
    connected = False
    aligned = len(rows) <= 6 and all(len(str(row["label"])) <= 12 for row in rows)
    for index, row in enumerate(rows):
        value = row["value"]
        key.append(f'<div class="point">{e(row["label"])}{refs(row)}<b>{fmt(value)}</b></div>')
        if value is None:
            connected = False
            continue
        if aligned or len(rows) == 1:
            x = left + (right - left) * (index + .5) / len(rows)
        else:
            x = left + (right - left) * index / max(1, len(rows) - 1)
        y = ordinate(value)
        command = "L" if connected else "M"
        path.append(f"{command}{x:.2f} {y:.2f}")
        dots.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.5" fill="#236554"/>')
        connected = True
    key_class = "points axis" if aligned else "points"
    return (
        '<svg class="trend" viewBox="0 0 602 153" aria-hidden="true">'
        + "".join(grid) + f'<path d="{" ".join(path)}" stroke="#236554" stroke-width="3" fill="none"/>'
        + "".join(dots) + f'</svg><div class="{key_class}" style="--count:{len(rows)}">'
        + "".join(key) + "</div>"
    )


def matrix(block, refs):
    columns = checked_list(block["columns"], "matrix columns")
    rows = checked_list(block["rows"], "matrix rows")
    values = []
    for row in rows:
        if len(row["values"]) != len(columns):
            raise ValueError(f'Matrix row {row["label"]!r} must have {len(columns)} values')
        values.extend(numbers(row["values"]))
    scale = max([abs(v) for v in values], default=0) or 1
    head = "".join(f'<th scope="col">{e(column)}</th>' for column in columns)
    body = []
    for row in rows:
        cells = []
        for value in row["values"]:
            if value is None:
                cells.append('<td class="missing">—</td>')
                continue
            intensity = abs(value) / scale
            light = (237, 241, 225)
            dark = (150, 58, 39) if value < 0 else (35, 101, 84)
            rgb = [round(a + (b - a) * intensity) for a, b in zip(light, dark)]
            channels = [((c / 255 + .055) / 1.055) ** 2.4 for c in rgb]
            luminance = sum(c * w for c, w in zip(channels, (.2126, .7152, .0722)))
            ink = "#061713" if luminance > .20 else "#fff"
            bg = ",".join(map(str, rgb))
            cells.append(f'<td style="background:rgb({bg});color:{ink}">{fmt(value)}</td>')
        body.append(f'<tr><th scope="row">{e(row["label"])}{refs(row)}</th>{"".join(cells)}</tr>')
    return (
        '<div class="matrix-wrap"><table><thead><tr><th></th>' + head
        + "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div>"
    )


def cases(block, refs):
    items = []
    for item in checked_list(block["items"], "case items"):
        items.append(f'<li><strong>{e(item["title"])}{refs(item)}</strong><p>{e(item["text"])}</p></li>')
    return '<ul class="cases">' + "".join(items) + "</ul>"


CHARTS = {"bars": bars, "trend": trend, "matrix": matrix, "cases": cases}


def render(data):
    sources = data.get("sources", [])
    source_index = {src["id"]: i for i, src in enumerate(sources, 1)}
    if len(source_index) != len(sources):
        raise ValueError("Each source needs a unique id")

    def refs(item):
        links = []
        for key in item.get("refs", []):
            if key not in source_index:
                raise ValueError(f"Unknown source id {key!r}")
            index = source_index[key]
            label = e(sources[index - 1]["label"])
            links.append(f'<a class="ref" href="#source-{index}" aria-label="{label}">[{index}]</a>')
        return "".join(links)

    lang = data.get("lang", "zh-CN")
    title = data["title"]
    metrics = []
    for m in data.get("metrics", []):
        metrics.append(f'<div class="metric"><dt>{e(m["label"])}{refs(m)}</dt><dd>{e(m["value"])}</dd></div>')
    body = [
        '<header class="hero">', optional("p", data.get("kicker"), "eyebrow"),
        f'<h1>{e(title)}</h1>', optional("p", data.get("intro"), "intro"),
        optional("p", data.get("data_note"), "note"),
        '<dl class="metrics">' + "".join(metrics) + "</dl>" if metrics else "", "</header>",
    ]
    for index, section in enumerate(checked_list(data["sections"], "sections"), 1):
        body.extend([
            '<section class="chapter"><div class="chapter-head">',
            f'<span class="section-index">{index:02d}</span><div><h2>{e(section["title"])}</h2>',
            optional("p", section.get("summary"), "summary"), '</div></div><div class="blocks">',
        ])
        for block in checked_list(section["blocks"], "section blocks"):
            kind = block["type"]
            if kind not in CHARTS:
                raise ValueError(f"Unknown chart type {kind!r}")
            css = "block wide" if block.get("wide") else "block"
            body.extend([
                f'<figure class="{css}"><figcaption><h3>{e(block["title"])}{refs(block)}</h3>',
                optional("p", block.get("unit"), "unit"), '</figcaption><div class="chart">',
                CHARTS[kind](block, refs), "</div>", optional("p", block.get("note"), "chart-note"),
                "</figure>",
            ])
        body.append("</div></section>")

    if data.get("method") or sources:
        footer_title = data.get("footer_title", "口径与出处" if lang.lower().startswith("zh") else "Methods and sources")
        body.extend(["<footer>", f"<h2>{e(footer_title)}</h2>", optional("p", data.get("method"))])
        if sources:
            body.append('<ol class="sources">')
            for index, source in enumerate(sources, 1):
                label = e(source["label"])
                url = source.get("url")
                if url:
                    parsed = urlsplit(url)
                    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
                        raise ValueError(f'Expected an HTTP(S) source URL for {source["id"]!r}')
                    label = f'<a href="{e(url)}">{label}</a>'
                body.extend([
                    f'<li id="source-{index}"><span class="source-id">[{index}]</span><div><b>{label}</b>',
                    optional("span", source.get("locator"), "source-detail"),
                    optional("span", source.get("excerpt"), "source-detail"), "</div></li>",
                ])
            body.append("</ol>")
        body.append("</footer>")
    template_path = Path(__file__).resolve().parent.parent / "assets" / "poster.html"
    template = Template(template_path.read_text(encoding="utf-8"))
    return template.substitute(lang=e(lang), title=e(title), body="\n".join(body))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brief", type=Path, help="Input JSON brief")
    parser.add_argument("output", type=Path, help="Output HTML file")
    args = parser.parse_args()
    if args.output.suffix.lower() != ".html":
        parser.error("Output must end in .html")
    try:
        data = json.loads(args.brief.read_text(encoding="utf-8"))
        poster = render(data)
        args.output.write_text(poster, encoding="utf-8")
    except (KeyError, ValueError, TypeError, OSError) as exc:
        parser.exit(1, f"Could not render the infographic: {exc}\n")


if __name__ == "__main__":
    main()
