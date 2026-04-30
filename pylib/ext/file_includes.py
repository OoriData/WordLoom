# SPDX-FileCopyrightText: 2023-present Oori Data <info@oori.dev>
# SPDX-License-Identifier: Apache-2.0
# wordloom.ext.file_includes

'''
Word Loom extension: file-inclusion via metadata conventions.

Metadata values in a Word Loom item (i.e. non-underscore, non-lang keys) that
carry a ``file:``, ``dir:``, or ``glob:`` prefix are resolved to their text
content at load time when this extension is active.

  file:<rel-path>: UTF-8 content of that single file
  dir:<rel-path> : all UTF-8 files under the directory, concatenated and
                   headed with ``=== relative/path ===`` separators
  glob:<pattern> : same concatenation for files matching the glob pattern
                   relative to the loom directory

All paths are relative to the directory containing the loom TOML file and must
stay within that directory (directory-traversal attempts raise ValueError).
Files larger than 2 MB are silently skipped when scanning directories/globs;
an explicit ``file:`` reference to an oversized or binary file raises an error.

This extension is opt-in:

    from wordloom import load
    loom = load(Path('prompts.toml'), features={'file-inclusion'})

Resolved values are exposed as ``language_item.file_bindings`` (a plain dict),
and the ``language_item.render(**kwargs)`` helper merges them with any runtime
kwargs before calling ``str.format``.

**Warning:** The security model prevents path traversal, but it cannot protect against malicious *content* inside included files. If file contents are user-influenced or come from untrusted sources, they could inject instructions into your prompts. Only include files you trust, or inspect/strip their content before loading.
'''

from __future__ import annotations

from pathlib import Path
from typing import Iterable

_MAX_BYTES = 2 * 1024 * 1024  # 2 MB — skip silently for dir/glob scans


def _under_base(target: Path, base: Path) -> bool:
    target = target.resolve()
    base = base.resolve()
    return target == base or target.is_relative_to(base)


def _concat_utf8_files(paths: Iterable[Path], *, loom_base: Path, rel_root: Path) -> str:
    '''Concatenate UTF-8 files into a single string with path-headed blocks.'''
    loom_base = loom_base.resolve()
    rel_root = rel_root.resolve()
    unique = sorted({p.resolve() for p in paths}, key=lambda p: p.as_posix().lower())
    chunks: list[str] = []
    for path in unique:
        if not path.is_file() or not _under_base(path, loom_base):
            continue
        try:
            rel = path.relative_to(rel_root)
        except ValueError:
            continue
        if any(part.startswith('.') for part in rel.parts):
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if len(data) > _MAX_BYTES:
            continue
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            continue
        chunks.append(f'=== {rel.as_posix()} ===\n{text}')
    return '\n\n'.join(chunks)


def _read_dir(dir_path: Path, loom_base: Path) -> str:
    if not dir_path.is_dir():
        raise NotADirectoryError(f'Not a directory: {dir_path}')
    paths = [p for p in dir_path.rglob('*') if p.is_file()]
    return _concat_utf8_files(paths, loom_base=loom_base, rel_root=dir_path)


def _read_glob(pattern: str, loom_base: Path) -> str:
    if '..' in Path(pattern).parts:
        raise ValueError(f'glob: pattern must not contain ".." segments: {pattern!r}')
    paths = list(loom_base.glob(pattern))
    return _concat_utf8_files(paths, loom_base=loom_base, rel_root=loom_base)


def resolve_file_bindings(table: dict, loom_base: Path) -> dict[str, str]:
    '''
    Scan one TOML item table and resolve file:/dir:/glob: metadata values.

    Returns a dict mapping each resolved key to its text content.
    Reserved keys (those starting with ``_`` and ``lang``) are skipped, as are
    non-string values.

    Raises:
        ValueError: absolute path, path escaping loom dir, or bad glob pattern.
        FileNotFoundError: explicit ``file:`` target does not exist.
        NotADirectoryError: explicit ``dir:`` target is not a directory.
    '''
    loom_base = loom_base.resolve()
    out: dict[str, str] = {}
    for key, raw in table.items():
        if not isinstance(key, str) or key.startswith('_') or key == 'lang':
            continue
        if not isinstance(raw, str):
            continue

        if raw.startswith('file:'):
            rel = raw[len('file:'):].strip()
            if not rel or rel.startswith('/'):
                raise ValueError(f'{key!r}: file: path must be relative to the loom directory: {raw!r}')
            target = (loom_base / rel).resolve()
            if not _under_base(target, loom_base):
                raise ValueError(f'{key!r}: path escapes the loom directory: {raw!r}')
            if not target.is_file():
                raise FileNotFoundError(f'{key!r}: not a file: {target}')
            out[key] = target.read_text(encoding='utf-8')

        elif raw.startswith('dir:'):
            rel = raw[len('dir:'):].strip()
            if not rel or rel.startswith('/'):
                raise ValueError(f'{key!r}: dir: path must be relative to the loom directory: {raw!r}')
            target = (loom_base / rel).resolve()
            if not _under_base(target, loom_base):
                raise ValueError(f'{key!r}: path escapes the loom directory: {raw!r}')
            out[key] = _read_dir(target, loom_base=loom_base)

        elif raw.startswith('glob:'):
            pattern = raw[len('glob:'):].strip()
            if not pattern or pattern.startswith('/'):
                raise ValueError(f'{key!r}: glob: pattern must be non-empty and relative: {raw!r}')
            out[key] = _read_glob(pattern, loom_base=loom_base)

    return out
