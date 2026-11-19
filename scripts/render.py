"""Render a data-infographic brief as a standalone HTML file (standard library)."""
import argparse
import json
import math
from functools import partial
from html import escape
from pathlib import Path
from string import Template
from urllib.parse import urlsplit

from palette import mix, readable, resolve, text_on_fill


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


def heading_text(value, lang, citations=""):
    # Keep short Chinese clauses together when a headline wraps on a phone.
    value = str(value)
    if lang.lower().startswith("zh") and "，" in value:
        clauses = value.split("，")
        phrases = [e(clause) + "，" for clause in clauses[:-1]] + [e(clauses[-1]) + citations]
        return "<wbr>".join(f'<span class="phrase">{phrase}</span>' for phrase in phrases)
    return e(value) + citations


def domain(block, values):
    lo, hi = block["domain"]
    if len(numbers([lo, hi])) != 2 or hi <= lo:
        raise ValueError("A chart domain needs two increasing finite numbers")
    if any(v < lo or v > hi for v in values):
        raise ValueError("A plotted value falls outside the specified domain")
    return lo, hi


def scale_axis(lo, hi, suffix=""):
    ticks = [(0, lo), (100, hi)]
    if lo < 0 < hi:
        zero = -100 * lo / (hi - lo)
        # Leave room for the end labels when zero lies close to either edge.
        if 8 < zero < 92:
            ticks.insert(1, (zero, 0))
    labels = [f'<span style="left:{position:.4f}%">{fmt(value)}{e(suffix)}</span>' for position, value in ticks]
    return '<div class="scale-axis">' + "".join(labels) + '</div>'


def bars(block, refs):
    rows = checked_list(block["rows"], "bar rows")
    values = numbers([row["value"] for row in rows])
    lo, hi = min([0, *values]), max([0, *values])
    if "domain" in block:
        lo, hi = domain(block, [0, *values])
    suffix = block.get("suffix", "")
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
            f'<span class="value">{fmt(value)}{e(suffix) if value is not None else ""}</span></div>'
        )
    axis = '<div class="bar-axis">' + scale_axis(lo, hi, suffix) + '</div>' if "domain" in block else ""
    return '<div class="bar-chart">' + "".join(result) + axis + "</div>"


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


def column_chart(block, refs):
    rows = checked_list(block["rows"], "column rows")
    values = numbers([row["value"] for row in rows])
    if any(value < 0 for value in values):
        raise ValueError("Columns use a zero baseline and nonnegative counts. Use bars for signed values.")
    highest = max(values, default=0) or 1
    items = []
    for row in rows:
        value = row["value"]
        height = 0 if value is None else 100 * value / highest
        items.append(f'<div class="column"><div class="column-area"><i style="height:{height:.4f}%">'
                     f'<b>{fmt(value)}</b></i></div><span>{e(row["label"])}{refs(row)}</span></div>')
    return '<div class="columns-chart">' + "".join(items) + '</div>'


def matrix(block, refs, colors, cell_content=None):
    columns = checked_list(block["columns"], "matrix columns")
    rows = checked_list(block["rows"], "matrix rows")
    values = []
    for row in rows:
        if len(row["values"]) != len(columns):
            raise ValueError(f'Matrix row {row["label"]!r} must have {len(columns)} values')
        values.extend(numbers(row["values"]))
    scale = max([abs(v) for v in values], default=0) or 1
    def cell(value, row_index, col_index):
        if value is None:
            return '<td class="missing">—</td>'
        endpoint = colors["matrix-negative"] if value < 0 else colors["primary"]
        fill = mix(colors["matrix-base"], endpoint, abs(value) / scale)
        paper, body_ink = colors["paper"], colors["ink"]
        ink = text_on_fill(body_ink, fill, (body_ink, paper))
        fill = readable(fill, ink, endpoint=paper if ink == body_ink else body_ink)
        content = cell_content(row_index, col_index, value) if cell_content else fmt(value)
        return f'<td style="background:{fill};color:{ink}">{content}</td>'

    tables = []
    for start in range(0, len(columns), 8):
        stop = start + 8
        head = "".join(f'<th scope="col">{e(c)}</th>' for c in columns[start:stop])
        body = []
        for row_index, row in enumerate(rows):
            cells = "".join(cell(v, row_index, j) for j, v in enumerate(row["values"][start:stop], start))
            body.append(f'<tr><th scope="row">{e(row["label"])}{refs(row)}</th>{cells}</tr>')
        tables.append('<div class="matrix-wrap"><table><thead><tr><th></th>' + head
                      + '</tr></thead><tbody>' + "".join(body) + '</tbody></table></div>')
    return "".join(tables)


def cases(block, refs):
    items = []
    for item in checked_list(block["items"], "case items"):
        items.append(f'<li><strong>{e(item["title"])}{refs(item)}</strong><p>{e(item["text"])}</p></li>')
    return '<ul class="cases">' + "".join(items) + "</ul>"


def flow(block, refs, colors=None):
    sides = [checked_list(block[key], key) for key in ("from", "to")]
    links = checked_list(block["links"], "flow links")
    weighted = any("value" in link for link in links)
    by_id, totals = [], []
    for nodes in sides:
        ids = {node["id"]: i for i, node in enumerate(nodes)}
        if len(ids) != len(nodes):
            raise ValueError("Flow node ids must be unique on each side")
        by_id.append(ids)
        totals.append([0] * len(nodes))
    edges, pair_weights = [], {}
    for link in links:
        a, b = by_id[0][link["from"]], by_id[1][link["to"]]
        value = link.get("value") if weighted else 1
        if value is None:
            raise ValueError("A weighted flow needs a value on every link")
        numbers([value])
        if value < 0:
            raise ValueError("Weighted flows require a nonnegative value on every link")
        totals[0][a] += value
        totals[1][b] += value
        pair_weights[a, b] = pair_weights.get((a, b), 0) + value
        if value:
            edges.append((a, b, value))

    # Both ends of a ribbon use the same pixels per unit, even with different row counts.
    height = max(len(nodes) for nodes in sides) * 64
    capacity = min((height / len(nodes) * .68 / max(amounts)
                    for nodes, amounts in zip(sides, totals) if max(amounts)), default=1)
    scale = capacity if weighted else min(4, capacity)
    centers = [[height * (i + .5) / len(nodes) for i in range(len(nodes))] for nodes in sides]
    offsets = [[y - total * scale / 2 for y, total in zip(positions, amounts)]
               for positions, amounts in zip(centers, totals)]
    paths, descriptions = [], []
    for a, b, value in sorted(edges):
        y, z, thick = offsets[0][a], offsets[1][b], value * scale
        band = (f"M3 {y:.3f} C145 {y:.3f} 175 {z:.3f} 317 {z:.3f} "
                f"v{thick:.3f} C175 {z+thick:.3f} 145 {y+thick:.3f} 3 {y+thick:.3f} Z")
        paint = a if len(sides[0]) > 1 else b
        description = f'{sides[0][a]["label"]} → {sides[1][b]["label"]}'
        descriptions.append(f"{description} ({fmt(value)})" if weighted else description)
        paths.append(f'<path d="{band}" fill="var(--ribbon-{paint % 4})"><title>{e(descriptions[-1])}</title></path>')
        offsets[0][a] += thick
        offsets[1][b] += thick
    for x, positions, amounts in zip((0, 317), centers, totals):
        for y, total in zip(positions, amounts):
            if total:
                h = max(6, total * scale)
                if not weighted and x == 317:
                    paths.append(f'<path d="M312 {y-5:.3f} L320 {y:.3f} L312 {y+5:.3f} Z" fill="currentColor"/>')
                else:
                    paths.append(f'<rect x="{x}" y="{y-h/2:.3f}" width="3" height="{h:.3f}" fill="currentColor"/>')

    labels = []
    for nodes, amounts in zip(sides, totals):
        rows = []
        for node, total in zip(nodes, amounts):
            figure = f'<strong class="flow-total">{fmt(total)}</strong>' if weighted and block.get("show_totals", True) else ""
            rows.append('<div class="flow-node"><div>' + figure + f'<b>{e(node["label"])}{refs(node)}</b>'
                        + optional("small", node.get("detail")) + "</div></div>")
        labels.append('<div class="flow-side">' + "".join(rows) + "</div>")
    headers = ('<div class="flow-head">' + optional("span", block.get("from_label") or " ", "flow-from")
               + optional("span", block.get("to_label") or " ", "flow-to") + "</div>") if (
                   block.get("from_label") or block.get("to_label")) else ""
    svg = (f'<svg class="ribbons" viewBox="0 0 320 {height}" preserveAspectRatio="none" '
           f'role="img" aria-label="{e(" · ".join(descriptions))}">{"".join(paths)}</svg>')
    diagram = headers + f'<div class="flow-plot" style="--flow-height:{height}px">{labels[0]}{svg}{labels[1]}</div>'
    if not block.get("matrix_label"):
        return diagram
    if not weighted:
        raise ValueError("A flow matrix needs measured link weights")
    cross = {"columns":[node["label"] for node in sides[1]],
             "rows":[{"label":node["label"], "values":[pair_weights.get((i,j)) for j in range(len(sides[1]))]}
                     for i,node in enumerate(sides[0])]}
    key = matrix(cross, refs, colors if colors is not None else resolve(None))
    return ('<div class="flow-and-table"><div>' + diagram + '</div><div class="flow-table">'
            + optional("p", block["matrix_label"], "unit") + key + '</div></div>')


def units(block, refs):
    total = block["total"]
    if type(total) is not int or total <= 0:
        raise ValueError("Unit grids need a positive integer total")
    columns = block.get("columns", min(total, 10))
    if type(columns) is not int or not 1 <= columns <= total:
        raise ValueError("Unit grid columns must be a whole number from 1 to total")
    display = block.get("show_as", "fraction")
    if display not in ("fraction", "percent"):
        raise ValueError("Unit grid show_as must be fraction or percent")
    groups = []
    for row in checked_list(block["rows"], "unit grid rows"):
        value = row["value"]
        if type(value) is not int or not 0 <= value <= total:
            raise ValueError("Unit grid values must be whole marks between zero and total")
        reading = f'{fmt(round(100 * value / total, 1))}%' if display == "percent" else f"{value}/{total}"
        if row.get("approx"):
            reading = "≈" + reading
        # Runs of equally spaced dots keep the SVG compact even for large denominators.
        height = math.ceil(total / columns)
        fill_from = row.get("fill_from", "start")
        if fill_from not in ("start", "end"):
            raise ValueError("A unit grid fills from start or end")
        filled_start = total - value if fill_from == "end" else 0
        runs = []
        for j in range(height):
            count = min(columns, total - j * columns)
            first = max(0, min(count, filled_start - j * columns))
            last = max(0, min(count, filled_start + value - j * columns))
            for start, n, color in ((0, first, "var(--empty-mark)"), (first, last-first, "currentColor"),
                                    (last, count-last, "var(--empty-mark)")):
                if n:
                    runs.append(f'<path d="M{start*10+5} {j*10+5} h{(n-1)*10+.01}" stroke="{color}" '
                                'stroke-width="6.6" stroke-linecap="round" stroke-dasharray=".01 9.99"/>')
        marks = (f'<svg viewBox="0 0 {columns*10} {height*10}" style="max-width:{columns*15}px" '
                 f'aria-hidden="true">{"".join(runs)}</svg>')
        groups.append('<div class="unit-group">' + f'<strong class="big-value">{reading}</strong>'
                      + marks + f'<b>{e(row["label"])}{refs(row)}</b>' + optional("small", row.get("detail")) + "</div>")
    return '<div class="unit-groups">' + "".join(groups) + "</div>"


def figures(block, refs):
    cells = []
    for row in checked_list(block["rows"], "figure rows"):
        cells.append('<div class="figure-cell"><strong class="big-value">' + e(row["value"])
                     + optional("small", row.get("suffix")) + "</strong>"
                     + f'<b>{e(row["label"])}{refs(row)}</b>' + optional("small", row.get("detail")) + "</div>")
    return '<div class="figure-cells">' + "".join(cells) + "</div>"


def intervals(block, refs):
    lo, hi = domain(block, [])
    suffix = block.get("suffix", "")
    out = []
    for row in checked_list(block["rows"], "interval rows"):
        a, b = row["low"], row["high"]
        if len(numbers([a, b])) != 2 or not lo <= a <= b <= hi:
            raise ValueError("Interval endpoints must be ordered and inside the shared domain")
        start, end = ((v-lo)*100/(hi-lo) for v in (a, b))
        point = row.get("estimate")
        reading = f'{fmt(a)}{e(suffix)}–{fmt(b)}{e(suffix)}'
        marker = ""
        if point is not None:
            if not numbers([point]) or not lo <= point <= hi:
                raise ValueError("The point estimate must be inside the plotted domain")
            reading = f'{fmt(point)}{e(suffix)} <small>[{fmt(a)}, {fmt(b)}]</small>'
            marker = f'<b class="estimate-dot" style="left:{100*(point-lo)/(hi-lo):.4f}%"></b>'
        zero = f'<span class="scale-zero" style="left:{-100*lo/(hi-lo):.4f}%"></span>' if lo < 0 < hi else ""
        css = "interval-row estimated" if marker else "interval-row"
        out.append(f'<div class="{css}"><b>{e(row["label"])}{refs(row)}</b>'
                   f'<strong>{reading}</strong><div class="interval-track" aria-hidden="true">{zero}'
                   f'<i style="left:{start:.4f}%;width:{end-start:.4f}%"></i>{marker}</div></div>')
    return '<div class="intervals">' + "".join(out) + scale_axis(lo, hi, suffix) + '</div>'


def paired(block, refs):
    groups = checked_list(block["groups"], "paired groups")
    if len(groups) != 2:
        raise ValueError("A paired chart needs two group labels")
    rows = checked_list(block["rows"], "paired rows")
    lo, hi = domain(block, numbers([r[k] for r in rows for k in ("a", "b")]))
    suffix = e(block.get("suffix", ""))
    legend = "".join(f'<span><i class="pair-dot {key}"></i>{e(label)}</span>' for key, label in zip(("a","b"),groups))
    out = []
    for row in rows:
        a, b = row["a"], row["b"]
        marks = []
        if a is not None and b is not None:
            left = 100 * (min(a,b) - lo) / (hi-lo)
            width = 100 * abs(b-a) / (hi-lo)
            marks.append(f'<i class="pair-line" style="left:{left:.4f}%;width:{width:.4f}%"></i>')
        readings = []
        for key, group, value in zip(("a","b"), groups, (a,b)):
            reading = fmt(value) + (suffix if value is not None else "")
            readings.append(f'<span aria-label="{e(group)} · {reading}"><i class="pair-dot {key}"></i>{reading}</span>')
            if value is not None:
                pos = 100 * (value-lo) / (hi-lo)
                marks.append(f'<i class="pair-dot {key}" style="left:{pos:.4f}%"></i>')
        out.append(f'<div class="pair-row"><div class="pair-name">{e(row["label"])}{refs(row)}</div>'
                   + '<div class="pair-values">' + ''.join(readings) + '</div>'
                   + '<div class="pair-track" aria-hidden="true">' + ''.join(marks) + '</div></div>')
    return '<div class="pair-legend">' + legend + '</div><div class="paired">' + ''.join(out) + scale_axis(lo, hi, block.get("suffix","")) + '</div>'


def web_link(label, url):
    parsed = urlsplit(url)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ValueError(f"Expected an HTTP(S) URL for {label!r}")
    return f'<a href="{e(url)}">{e(label)}</a>'


def themes(block, refs, colors, sources, lang):
    source = sources[block["source"]]
    records = checked_list(source["records"], "reviewed records")
    topics = checked_list(block["themes"], "themes")
    labels = block["labels"]
    positions = {topic["id"]: i for i, topic in enumerate(topics)}
    if len(positions) != len(topics):
        raise ValueError("Each theme needs a unique id")
    members = [set() for topic in topics]
    seen, entries = set(), []
    for record in records:
        key = record["id"]
        if key in seen:
            raise ValueError(f"Repeated reviewed record id {key!r}")
        seen.add(key)
        tagged, notes = set(), []
        passages = record["passages"]
        if not isinstance(passages, list):
            raise ValueError("A reviewed record needs a passages list, possibly empty")
        for passage in passages:
            tags = set(checked_list(passage["themes"], "passage themes"))
            if tags - positions.keys():
                raise ValueError(f"Unknown theme in record {key!r}")
            indices = sorted(positions[tag] for tag in tags)
            tagged.update(indices)
            loc = passage["locator"]
            if not isinstance(loc, str) or not loc.strip():
                raise ValueError(f"A passage in {key!r} needs a locator")
            url = passage.get("url") or record.get("url")
            pointer = web_link(loc, url) if url else e(loc)
            tag_names = " · ".join(e(topics[i]["label"]) for i in indices)
            notes.append(f'<li><b>{tag_names}</b> {pointer}' + optional("p", passage.get("text")) + '</li>')
        for i in tagged:
            members[i].add(key)
        if notes:
            indices_text = " ".join(str(i) for i in sorted(tagged))
            entries.append(f'<article data-topics="{indices_text}"><h5>{e(record["label"])}</h5><ul>{"".join(notes)}</ul></article>')

    total = len(records)
    ranking = []
    for i in sorted(range(len(topics)), key=lambda i: -len(members[i])):
        count = len(members[i])
        strip = " segmented" if total <= 60 else ""
        ranking.append(f'<div class="theme-rank"><span>{e(topics[i]["label"])}</span><b>{count} / {total}</b>'
                       f'<div class="theme-meter{strip}" style="--step:{100/total:.6f}%" aria-hidden="true">'
                       f'<i style="width:{100*count/total:.5f}%"></i></div></div>')

    short = [t.get("short", t["label"]) for t in topics]
    cross = {"columns":short, "rows":[{"label":short[i], "values":[len(group & other) for other in members]}
                                     for i, group in enumerate(members)]}

    def button(i, j, value):
        name = topics[i]["label"] if i == j else f'{topics[i]["label"]} × {topics[j]["label"]}'
        return (f'<button type="button" class="theme-cell" data-pair="{i} {j}" data-label="{e(name)}" '
                f'aria-label="{e(labels["evidence"])} · {e(name)} · {value}">{value}</button>')

    evidence = (f'<details class="theme-evidence"><summary>{e(labels["evidence"])}</summary>'
                f'<div class="theme-actions"><output aria-live="polite">{len(entries)} / {total}</output>'
                f'<button type="button" data-all>{e(labels["all"])}</button></div>'
                f'<div class="theme-entries">{"".join(entries)}</div></details>')
    summary = (f'<p class="theme-coverage"><strong>{len(entries)} / {total}</strong> {e(labels["coverage"])}</p>'
               if labels.get("coverage") else "")
    hints = {"en":"Select a cell to see its records and source passages.",
             "zh":"点击矩阵数字可查看对应的记录和原文位置。"}
    language = lang.lower()
    default_hint = hints["en"] if language.split("-")[0] == "en" else hints.get(language, "")
    if language in ("zh-cn", "zh-hans", "zh-sg"):
        default_hint = hints["zh"]
    hint = optional("p", labels.get("hint", default_hint), "theme-hint")
    return (f'<div class="theme-chart" data-total="{total}">' + summary + '<div class="theme-pair"><div>'
            + optional("h4", labels["frequency"]) + "".join(ranking) + '</div><div>'
            + optional("h4", labels["overlap"]) + matrix(cross,refs,colors,button) + hint + '</div></div>'
            + evidence + '</div>')


def evidence_list(source):
    records = source.get("records")
    if not records:
        return ""
    rows = []
    for record in checked_list(records, "source records"):
        link = web_link(record["label"], record["url"]) if record.get("url") else e(record["label"])
        rows.append(f'<li>{link}' + optional("span", record.get("locator"), "source-detail") + "</li>")
    return ('<details class="evidence"><summary>' + e(source["records_label"]) + '</summary>'
            + optional("p", source.get("key")) + '<ul>' + "".join(rows) + '</ul></details>')


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
    by_id = {source["id"]: source for source in sources}
    charts = {"bars": bars, "columns": column_chart, "trend": trend, "matrix": partial(matrix, colors=colors), "cases": cases,
              "flow": partial(flow, colors=colors), "units": units, "figures": figures, "intervals": intervals,
              "paired": paired, "themes": partial(themes, colors=colors, sources=by_id, lang=lang)}

    def draw(block, lead=False):
        kind = block["type"]
        if kind not in charts:
            raise ValueError(f"Unknown chart type {kind!r}")
        wide = block.get("wide") or kind == "themes" or (kind == "matrix" and len(block["columns"]) > 6)
        classes = "block wide" if wide else "block"
        heading = "h2" if lead else "h3"
        keys = list(block.get("refs", []))
        if kind == "themes" and block["source"] not in keys:
            keys.append(block["source"])
        label = heading_text(block["title"], lang, refs({"refs":keys}))
        pointers = []
        for key in keys:
            source = by_id[key]
            name = source.get("short_label", source["label"])
            if source.get("locator"):
                name += " · " + source["locator"]
            pointers.append(web_link(name, source["url"]) if source.get("url") else
                            f'<a href="#source-{source_index[key]}">{e(name)}</a>')
        source_line = '<div class="chart-sources">' + " · ".join(pointers) + '</div>' if pointers else ""
        return (f'<figure class="{classes}"><figcaption><{heading}>{label}</{heading}>'
                + optional("p", block.get("caption"), "chart-caption") + optional("p", block.get("unit"), "unit")
                + '</figcaption><div class="chart">'
                + charts[kind](block, refs) + '</div>' + optional("p", block.get("note"), "chart-note")
                + source_line + '</figure>')

    title = data["title"]
    metrics = []
    for m in data.get("metrics", []):
        metrics.append(f'<div class="metric"><dt>{e(m["label"])}{refs(m)}</dt><dd>{e(m["value"])}</dd></div>')
    lead = data.get("lead")
    beside = lead and lead.get("placement") == "beside"
    header = '<header class="hero compact-hero"><div class="hero-main">' if beside else '<header class="hero">'
    body = [
        header, '<div class="headline">', optional("p", data.get("kicker"), "eyebrow"),
        f'<h1>{heading_text(title, lang)}</h1>', optional("p", data.get("intro"), "intro"),
        optional("p", data.get("data_note"), "note"), "</div>",
        '<div class="lead hero-chart">' + draw(lead, lead=True) + '</div></div>' if beside else "",
        '<dl class="metrics">' + "".join(metrics) + "</dl>" if metrics else "", "</header>",
    ]
    if lead and not beside:
        body.append('<section class="lead">' + draw(lead, lead=True) + '</section>')
    for section in checked_list(data["sections"], "sections"):
        columns = section.get("columns", 2)
        if type(columns) is not int or columns not in (1, 2, 3):
            raise ValueError("Chapter columns must be 1, 2 or 3")
        body.append('<section class="chapter">')
        if section.get("title") or section.get("summary"):
            chapter_title = f'<h2>{heading_text(section["title"], lang)}</h2>' if section.get("title") else ""
            body.append('<div class="chapter-head">' + chapter_title
                        + optional("p", section.get("summary"), "summary") + '</div>')
        body.append(f'<div class="blocks cols-{columns}">')
        body.extend(draw(block) for block in checked_list(section["blocks"], "section blocks"))
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
                    optional("span", source.get("excerpt"), "source-detail"), evidence_list(source), "</div></li>",
                ])
            body.append("</ol>")
        body.extend([palette_note, "</footer>"])
    template_path = Path(__file__).resolve().parent.parent / "assets" / "poster.html"
    template = Template(template_path.read_text(encoding="utf-8"))
    variables = " ".join(f"--{name}:{value};" for name, value in colors.items())
    layout = " with-lead" if data.get("lead") else ""
    return template.substitute(lang=e(lang), title=e(title), body="\n".join(body), palette_vars=variables, layout=layout)


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
