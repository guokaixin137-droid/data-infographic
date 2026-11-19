"""Index UTF-8 text files as bounded, source-located JSONL records."""
import argparse
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


TEXT_SUFFIXES = {".txt", ".md", ".markdown"}


def inputs(root):
    if root.is_file():
        if root.suffix.lower() not in TEXT_SUFFIXES:
            raise ValueError(f"Unsupported text file: {root}")
        yield root.name, root
        return
    if not root.is_dir():
        raise ValueError(f"Input does not exist: {root}")

    def report_error(error):
        raise error

    for folder, dirs, names in os.walk(root, onerror=report_error):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not (Path(folder) / d).is_symlink())
        for name in sorted(names):
            path = Path(folder) / name
            if (not name.startswith(".") and path.suffix.lower() in TEXT_SUFFIXES
                    and not path.is_symlink() and path.is_file()):
                yield path.relative_to(root).as_posix(), path


def segments(stream, limit):
    part = 0
    start = 0
    line = first_line = last_line = 1
    parts = []
    length = 0
    while True:
        fragment = stream.readline(limit)
        if parts and (not fragment or length + len(fragment) > limit):
            part += 1
            yield {"part": part, "first_line": first_line, "last_line": last_line,
                   "start": start, "end": start + length, "text": "".join(parts)}
            start += length
            parts, length, first_line = [], 0, line
        if not fragment:
            break
        parts.append(fragment)
        length += len(fragment)
        last_line = line
        if fragment.endswith("\n"):
            line += 1
    if not part:
        yield {"part": 0, "first_line": None, "last_line": None, "start": 0, "end": 0, "text": ""}


def index(root, output, limit):
    if limit < 1:
        raise ValueError("--max-chars must be positive")
    if output.suffix.lower() != ".jsonl":
        raise ValueError("Output must end in .jsonl")
    sources = chunks = empty = 0
    temp = None
    try:
        with NamedTemporaryFile("w", encoding="utf-8", dir=output.parent, delete=False) as out:
            temp = Path(out.name)
            for source, path in inputs(root):
                sources += 1
                try:
                    with path.open(encoding="utf-8-sig") as stream:
                        for record in segments(stream, limit):
                            if record["part"]:
                                chunks += 1
                            else:
                                empty += 1
                            out.write(json.dumps({"source": source, **record}, ensure_ascii=False) + "\n")
                except UnicodeError as error:
                    raise ValueError(f"{source}: expected UTF-8 text") from error
            if not sources:
                raise ValueError("No .txt, .md or .markdown files found")
        temp.replace(output)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()
    return sources, chunks, empty


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-chars", type=int, default=12000)
    args = parser.parse_args()
    try:
        total, chunks, empty = index(args.input, args.output, args.max_chars)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Could not index texts: {error}\n")
    print(f"{total} source files, {chunks} text chunks, {empty} empty files")


if __name__ == "__main__":
    main()
