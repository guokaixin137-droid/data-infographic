"""Render a data-infographic brief as a standalone HTML file (standard library)."""
import argparse
import json
import math
from functools import partial
from html import escape
from pathlib import Path
from string import Template
from urllib.parse import urlsplit

from palette import mix, resolve, text_on_fill


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
    return '<div class="bar-chart">' + "".join(result) + "</div>"


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
            f'<line x1="{left}" y1="{y}" x2="{right}" y2="{y}" stroke="var(--grid)"/>'
            f'<text x="{left - 7}" y="{y + 4}" text-anchor="end" font-size="13" '
            f'fill="var(--muted)">{fmt(bound)}</text>'
        )
    if lo < 0 < hi:
        y = ordinate(0)
        grid.append(f'<line x1="{left}" y1="{y}" x2="{right}" y2="{y}" stroke="var(--grid-zero)"/>')
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
        dots.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.5" fill="var(--primary)"/>')
        connected = True
    key_class = "points axis" if aligned else "points"
    return (
        '<svg class="trend" viewBox="0 0 602 153" aria-hidden="true">'
        + "".join(grid) + f'<path d="{" ".join(path)}" stroke="var(--primary)" stroke-width="3" fill="none"/>'
        + "".join(dots) + f'</svg><div class="{key_class}" style="--count:{len(rows)}">'
        + "".join(key) + "</div>"
    )


def matrix(block, refs, colors):
    columns = checked_list(block["columns"], "matrix columns")
    rows = checked_list(block["rows"], "matrix rows")
    values = []
    for row in rows:
        if len(row["values"]) != len(columns):
            raise ValueError(f'Matrix row {row["label"]!r} must have {len(columns)} values')
        values.extend(numbers(row["values"]))
    scale = max([abs(v) for v in values], default=0) or 1
    def cell(value):
        if value is None:
            return '<td class="missing">—</td>'
        endpoint = colors["matrix-negative"] if value < 0 else colors["primary"]
        fill = mix(colors["matrix-base"], endpoint, abs(value) / scale)
        ink = text_on_fill(colors["ink"], fill)
        return f'<td style="background:{fill};color:{ink}">{fmt(value)}</td>'

    tables = []
    for start in range(0, len(columns), 8):
        stop = start + 8
        head = "".join(f'<th scope="col">{e(c)}</th>' for c in columns[start:stop])
        body = []
        for row in rows:
            cells = "".join(cell(v) for v in row["values"][start:stop])
            body.append(f'<tr><th scope="row">{e(row["label"])}{refs(row)}</th>{cells}</tr>')
        tables.append('<div class="matrix-wrap"><table><thead><tr><th></th>' + head
                      + '</tr></thead><tbody>' + "".join(body) + '</tbody></table></div>')
    return "".join(tables)


def cases(block, refs):
    items = []
    for item in checked_list(block["items"], "case items"):
        items.append(f'<li><strong>{e(item["title"])}{refs(item)}</strong><p>{e(item["text"])}</p></li>')
    return '<ul class="cases">' + "".join(items) + "</ul>"


def web_link(label, url):
    parsed = urlsplit(url)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ValueError(f"Expected an HTTP(S) URL for {label!r}")
    return f'<a href="{e(url)}">{e(label)}</a>'


def palette_references(settings, lang):
    references = settings.get("references", [])
    if not isinstance(references, list):
        raise ValueError("palette.references must be a list")
    if not references:
        return ""
    title = settings.get("heading", "配色参考" if lang.lower().startswith("zh") else "Palette references")
    items = []
    for ref in references:
        link = web_link(ref["label"], ref["url"])
        note = optional("span", ref.get("note"), "source-detail")
        items.append(f"<li>{link}{note}</li>")
    return f'<section class="palette-refs"><h2>{e(title)}</h2><ul>{"".join(items)}</ul></section>'


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
    settings = data.get("palette", {})
    if not isinstance(settings, dict):
        raise ValueError("palette must be an object")
    colors = resolve(settings.get("colors"))
    palette_note = palette_references(settings, lang)
    charts = {"bars": bars, "trend": trend, "matrix": partial(matrix, colors=colors), "cases": cases}
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
            if kind not in charts:
                raise ValueError(f"Unknown chart type {kind!r}")
            wide = block.get("wide") or (kind == "matrix" and len(block["columns"]) > 6)
            css = "block wide" if wide else "block"
            body.extend([
                f'<figure class="{css}"><figcaption><h3>{e(block["title"])}{refs(block)}</h3>',
                optional("p", block.get("unit"), "unit"), '</figcaption><div class="chart">',
                charts[kind](block, refs), "</div>", optional("p", block.get("note"), "chart-note"),
                "</figure>",
            ])
        body.append("</div></section>")

    if data.get("method") or sources or palette_note:
        body.append("<footer>")
        if data.get("method") or sources:
            footer_title = data.get("footer_title", "口径与出处" if lang.lower().startswith("zh") else "Methods and sources")
            body.extend([f"<h2>{e(footer_title)}</h2>", optional("p", data.get("method"))])
        if sources:
            body.append('<ol class="sources">')
            for index, source in enumerate(sources, 1):
                url = source.get("url")
                label = web_link(source["label"], url) if url else e(source["label"])
                body.extend([
                    f'<li id="source-{index}"><span class="source-id">[{index}]</span><div><b>{label}</b>',
                    optional("span", source.get("locator"), "source-detail"),
                    optional("span", source.get("excerpt"), "source-detail"), "</div></li>",
                ])
            body.append("</ol>")
        body.extend([palette_note, "</footer>"])
    template_path = Path(__file__).resolve().parent.parent / "assets" / "poster.html"
    template = Template(template_path.read_text(encoding="utf-8"))
    variables = " ".join(f"--{name}:{value};" for name, value in colors.items())
    return template.substitute(lang=e(lang), title=e(title), body="\n".join(body), palette_vars=variables)


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
