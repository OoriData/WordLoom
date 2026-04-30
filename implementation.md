# WordLoom — Python Implementation

This document covers the internals of the Python library, including the core
data model, the `load()` API, and available opt-in extensions.

---

## Core data model: `language_item`

`language_item` is a `str` subclass.  Every item parsed from a loom file is
one of these.  Converting to `str` gives the default-language text, which
means items drop into any `str.format()` call naturally.

Key attributes:

| Attribute | Type | Description |
|---|---|---|
| `lang` | `str` | Default language code (BCP 47) |
| `altlang` | `dict[str, str]` | Alternate-language texts keyed by language code |
| `meta` | `dict` | Raw metadata from the TOML table (non-reserved keys) |
| `markers` | `list \| None` | Template variable names declared with `_m` |
| `file_bindings` | `dict[str, str]` | Resolved file/dir/glob inclusions (empty when the feature is not active) |

### `in_lang(lang)`

Returns the alternate-language text for `lang`, or `None` if not present.

### `render(**kwargs)`

Formats the template text by merging `file_bindings` with any runtime
`kwargs` (runtime values win on collision), then calling `str.format`.

```python
prompt.render(extra='value')
# equivalent to: str(prompt).format(**{**prompt.file_bindings, **kwargs})
```

When `file_bindings` is empty (feature disabled), this is a transparent
wrapper around `str.format`.

### `clone(**overrides)`

Returns a new `language_item` with selective attribute overrides.
`file_bindings` is preserved unless explicitly replaced.

---

## `load()` — reading a loom file

```python
wordloom.load(fp_or_str, lang='en', preserve_key=False, features=None, base_dir=None)
```

Returns a `dict` mapping each TOML key (and its default-language text) to a
`language_item`.  Only items whose `lang` (or the file-level default `lang`)
matches the requested `lang` are included.

### Input forms

| Type passed | Behaviour |
|---|---|
| `pathlib.Path` | Opened as a file; parent directory used as loom base |
| `str` that resolves to an existing file | Opened as a file; parent directory used as loom base |
| `str` with no matching file | Treated as raw TOML content |
| `bytes` | Treated as raw TOML content |
| File-like object from `open()` | Read directly; `.name` used to detect loom base |

### Parameters

`lang` — language to select (default: `'en'`).

`preserve_key` — if `True`, the TOML key name is stored in `meta['_key']`.

`features` — a `set` or `dict` enabling optional extensions.  A set entry or
a truthy dict value activates that feature.  Example:

```python
loom = wordloom.load(Path('prompts.toml'), features={'file-inclusion'})
# or equivalently:
loom = wordloom.load(Path('prompts.toml'), features={'file-inclusion': True})
```

`base_dir` — override the auto-detected loom base directory.  Useful when
loading from a `bytes` or in-memory string with extensions that need path
resolution.

---

## Extension: `file-inclusion`

**Module**: `wordloom.ext.file_includes`  
**Feature key**: `'file-inclusion'`

This extension interprets metadata values that carry a scheme prefix as
references to external content, and resolves them at load time.

**Warning:** The security model prevents path traversal, but it cannot protect against malicious *content* inside included files. If file contents are user-influenced or come from untrusted sources, they could inject instructions into your prompts. Only include files you trust, or inspect/strip their content before loading.


### TOML syntax

```toml
[my_prompt]
_ = """
Analyse the following documents:

{corpus}
"""
_m = ["corpus"]
corpus = "dir:documents"
```

Any metadata key (non-`_`, non-`lang`) whose string value begins with one of
the three schemes below is treated as a file reference.  All other metadata
values pass through unmodified.

| Scheme | Example value | Resolves to |
|---|---|---|
| `file:<rel-path>` | `file:context/background.txt` | UTF-8 content of that file |
| `dir:<rel-path>` | `dir:analysis` | All UTF-8 files under that directory, concatenated with `=== relative/path ===` headers |
| `glob:<pattern>` | `glob:notes/**/*.md` | All UTF-8 files matching the glob, same concatenation format |

Paths are always **relative to the directory containing the loom TOML file**.

### Accessing resolved content

```python
from pathlib import Path
import wordloom

loom = wordloom.load(Path('prompts.toml'), features={'file-inclusion'})

prompt = loom['my_prompt']

# Inspect what was resolved
print(prompt.file_bindings)  # {'corpus': '=== doc1.txt ===\n...'}

# Format the template — file_bindings are applied automatically
result = prompt.render()

# Supply additional runtime values; they override file_bindings on collision
result = prompt.render(extra_context='additional info')
```

The raw metadata values (`"dir:documents"` etc.) remain in `prompt.meta`
unchanged — `file_bindings` holds only the resolved content.

### Security model

The extension enforces that all resolved paths stay within the loom base
directory:

- Absolute paths (`file:/etc/passwd`) → `ValueError`
- Traversal escapes (`file:../../secret`) → `ValueError`
- `glob:` patterns with `..` segments → `ValueError`
- Missing `file:` target → `FileNotFoundError`
- Missing `dir:` target → `NotADirectoryError`

For `dir:` and `glob:` scans:
- Files larger than 2 MB are silently skipped
- Non-UTF-8 files are silently skipped
- Hidden paths (any component starting with `.`) are silently skipped

### Requiring a base directory

The extension needs to know where the loom file lives.  It is auto-detected
when you pass a `Path`, a path string, or an `open()` handle.  When loading
from raw bytes or an in-memory string, set `base_dir` explicitly:

```python
loom = wordloom.load(toml_bytes, features={'file-inclusion'}, base_dir='/path/to/loom-dir')
```

Without a base directory, the feature raises `ValueError` at load time.

---

## Development workflow

```bash
# Install (required after any pylib/ change)
uv pip install -U .

# Run tests
pytest test/ -v

# Run only the file-inclusion tests
pytest test/test_file_inclusion.py -v

# Lint
ruff check .
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for release and packaging details.
