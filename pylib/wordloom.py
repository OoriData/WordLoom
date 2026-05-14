# SPDX-FileCopyrightText: 2023-present Oori Data <info@oori.dev>
# SPDX-License-Identifier: Apache-2.0
# wordloom

'''
Routines to help with processing text in the word loom convention:
https://github.com/OoriData/WordLoom

Word Loom is a TOML-based format for managing language text and templates
for AI/LLM applications, with support for multiple languages and metadata.
'''

import io
import tomli
import warnings
from pathlib import Path


class language_item(str):
    '''
    Text or template for use with LLM tools
    Largely keeps metadata around language, template markers, etc.

    >>> from wordloom import language_item as LI
    >>> t = LI('spam', deflang='en')
    >>> t
    'spam'
    >>> t.lang
    'en'
    >>> t = LI('spam', deflang='en', altlang={'fr': 'jambon'})
    >>> t.altlang['fr']
    'jambon'
    '''

    def __new__(cls, value, deflang, altlang=None, meta=None, markers=None, file_bindings=None):
        '''
        Construct a new text item

        value - text value in the default language
        deflang - default language - made mandatory to avoid sloppy language assumptions
        altlang - dictionary of text values in alternative languages
        meta - dictionary of metadata
        markers - used to specify values that can be set, with the text value is treated as a template
        file_bindings - resolved file/dir/glob inclusions (populated by the file-inclusion feature)
        '''
        assert isinstance(value, str)
        self = super(language_item, cls).__new__(cls, value)
        self.lang = deflang  # Default language
        self.meta = meta or {}
        self.markers = markers or {}
        self.altlang = altlang or {}
        self.file_bindings = file_bindings or {}
        return self

    def __repr__(self):
        return u'T(' + repr(str(self)) + ')'

    def in_lang(self, lang):
        return self.altlang.get(lang)

    def render(self, **kwargs):
        '''
        Format this template, merging file_bindings with any runtime kwargs.

        file_bindings values are the base; kwargs override them, so callers can
        supply or override individual slots at runtime.

        >>> from wordloom import language_item as LI
        >>> t = LI('Hello {name}', deflang='en')
        >>> t.render(name='World')
        'Hello World'
        '''
        return str(self).format(**{**self.file_bindings, **kwargs})

    def clone(self, value=None, deflang=None, altlang=None, meta=None, markers=None, file_bindings=None):
        '''
        Clone the text item, with optional overrides

        >>> from wordloom import language_item as LI
        >>> t = LI('spam', deflang='en', meta={'tag': 'food'})
        >>> t, t.meta
        'spam', {'tag': 'food'}
        >>> t_cloned = t.clone(meta={'tag': 'protein'})
        >>> t_cloned, t_cloned.meta
        'spam', {'tag': 'protein'}
        >>> t_cloned = t.clone('eggs')
        >>> t_cloned, t_cloned.meta
        'spam', {'tag': 'food'}
        '''
        value = str(self) if value is None else value
        deflang = self.lang if deflang is None else deflang
        altlang = self.altlang if altlang is None else altlang
        meta = self.meta if meta is None else meta
        markers = self.markers if markers is None else markers
        file_bindings = self.file_bindings if file_bindings is None else file_bindings
        return language_item(value, deflang, altlang=altlang, meta=meta, markers=markers, file_bindings=file_bindings)


# Following 2 lines are deprecated
T = language_item
text_item = language_item

LI = language_item  # Alias for language_item


# XXX Defaulting to en leaves a bit too imperialist a flavor, really
def load(fp_or_str, lang='en', preserve_key=False, features=None, base_dir=None):
    '''
    Read a word loom and return the tables as top-level result mapping.

    fp_or_str  - Path object or path string → opened as a file (base dir auto-detected);
                 file-like object → read directly (.name used for base dir if present);
                 bytes or a TOML content string → parsed in-memory (no base dir)
    lang       - select only items whose language matches (default: 'en')
    preserve_key - if True, store the TOML key in each item's metadata as '_key'
    features   - set or dict of optional features to enable, e.g. ``{'file-inclusion'}``
                 or ``{'file-inclusion': True}``
    base_dir   - explicit base directory for resolving relative paths used by extensions;
                 overrides the auto-detected value from the file path

    Supported features
    ------------------
    ``'file-inclusion'``
        Metadata values with a ``file:``, ``dir:``, or ``glob:`` prefix are resolved
        to their text contents and exposed as ``language_item.file_bindings``.
        Requires a resolvable base directory (pass a Path/path-string, an open() handle,
        or set ``base_dir`` explicitly).

    Example:
    >>> import wordloom
    >>> from pathlib import Path
    >>> loom = wordloom.load(Path('prompts.toml'), features={'file-inclusion'})
    >>> prompt = loom['my_prompt']
    >>> formatted = prompt.render(extra_var='value')
    '''
    # --- resolve base directory and normalise fp_or_str to a readable object ---
    _detected_base: Path | None = None

    if isinstance(fp_or_str, Path):
        _detected_base = fp_or_str.parent.resolve()
        fp_or_str = fp_or_str.open('rb')
    elif isinstance(fp_or_str, str):
        candidate = Path(fp_or_str)
        if candidate.is_file():
            # string looks like a file path and the file exists — open it
            _detected_base = candidate.parent.resolve()
            fp_or_str = candidate.open('rb')
        else:
            fp_or_str = io.BytesIO(fp_or_str.encode('utf-8'))
    elif isinstance(fp_or_str, bytes):
        fp_or_str = io.BytesIO(fp_or_str)
    elif hasattr(fp_or_str, 'name'):
        try:
            _detected_base = Path(fp_or_str.name).parent.resolve()
        except Exception:
            pass

    loom_base: Path | None = Path(base_dir).resolve() if base_dir is not None else _detected_base

    # --- feature flags ---
    file_inclusion = False
    if features is not None:
        if isinstance(features, set):
            file_inclusion = 'file-inclusion' in features
        else:
            file_inclusion = bool(features.get('file-inclusion', False))

    if file_inclusion and loom_base is None:
        raise ValueError(
            "The 'file-inclusion' feature requires a resolvable loom base directory. "
            'Pass a Path object, a path string pointing to an existing file, '
            'an open() file handle, or set base_dir= explicitly.'
        )

    if file_inclusion:
        from wordloom.ext.file_includes import resolve_file_bindings  # noqa: PLC0415

    # Load TOML
    loom_raw = tomli.load(fp_or_str)
    # Select text by language
    # FIXME: Only top level, for now. Presumably we'll want to support scoping
    texts = {}
    default_lang = loom_raw.get('lang', None)
    for k, v in loom_raw.items():
        if not isinstance(v, dict):
            # Skip top-level items
            continue
        if 'text' in v:
            warnings.warn('Deprecated attribute "text". Use "_" instead')
            text = v['text']
        else:
            text = v.get('_')
        if text is None: # Skip items without text
            continue
        markers = v.get('_m')
        if 'markers' in v:
            warnings.warn('Deprecated attribute "marker". Use "_m" instead')
            markers = v['markers']
        else:
            markers = v.get('_m')
        if v.get('lang') == lang or ('lang' not in v and lang == default_lang):
            altlang = {kk.lstrip('_'): vv for kk, vv in v.items() if (kk.startswith('_') and kk not in ('_', '_m'))}
            meta = {kk: vv for kk, vv in v.items() if (not kk.startswith('_') and kk not in ('text', 'markers'))}
            if preserve_key:
                meta['_key'] = k
            fb = resolve_file_bindings(v, loom_base) if file_inclusion else {}
            if k in texts:
                warnings.warn(f'Key {k} duplicates an existing item, which will be overwritten')
            texts[k] = T(text, lang, altlang=altlang, meta=meta, markers=markers, file_bindings=fb)
            # Also index by literal text
            if text in texts:
                warnings.warn(
                    f'Item default language text {text[:20]} duplicates an existing item, which will be overwritten')
            texts[text] = T(text, lang, altlang=altlang, meta=meta, markers=markers, file_bindings=fb)
    return texts
