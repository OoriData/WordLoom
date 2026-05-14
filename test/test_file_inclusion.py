# SPDX-FileCopyrightText: 2023-present Oori Data <info@oori.dev>
# SPDX-License-Identifier: Apache-2.0
# test/test_file_inclusion.py
'''
Tests for the file-inclusion extension (features={'file-inclusion'}).

pytest test/test_file_inclusion.py
'''

import textwrap
from pathlib import Path

import pytest

import wordloom


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_loom(tmp_path: Path, toml: str) -> Path:
    p = tmp_path / 'prompts.toml'
    p.write_text(textwrap.dedent(toml), encoding='utf-8')
    return p


# ---------------------------------------------------------------------------
# basic file: inclusion
# ---------------------------------------------------------------------------

def test_file_inclusion_single_file(tmp_path):
    (tmp_path / 'context.txt').write_text('Some context text.', encoding='utf-8')
    loom_path = _write_loom(tmp_path, '''
        lang = "en"
        [my_prompt]
        _ = "Answer using: {context}"
        _m = ["context"]
        context = "file:context.txt"
    ''')

    loom = wordloom.load(loom_path, features={'file-inclusion'})
    prompt = loom['my_prompt']
    assert prompt.file_bindings == {'context': 'Some context text.'}
    assert prompt.render() == 'Answer using: Some context text.'


def test_file_inclusion_via_path_object(tmp_path):
    (tmp_path / 'note.txt').write_text('Hello from file.', encoding='utf-8')
    loom_path = _write_loom(tmp_path, '''
        lang = "en"
        [item]
        _ = "{note}"
        note = "file:note.txt"
    ''')

    loom = wordloom.load(Path(loom_path), features={'file-inclusion'})
    assert loom['item'].file_bindings['note'] == 'Hello from file.'


def test_file_inclusion_via_open_handle(tmp_path):
    (tmp_path / 'data.txt').write_text('data', encoding='utf-8')
    loom_path = _write_loom(tmp_path, '''
        lang = "en"
        [item]
        _ = "{data}"
        data = "file:data.txt"
    ''')

    with open(loom_path, 'rb') as fp:
        loom = wordloom.load(fp, features={'file-inclusion'})
    assert loom['item'].file_bindings['data'] == 'data'


def test_no_file_inclusion_without_feature(tmp_path):
    (tmp_path / 'context.txt').write_text('Some context.', encoding='utf-8')
    loom_path = _write_loom(tmp_path, '''
        lang = "en"
        [my_prompt]
        _ = "Answer using: {context}"
        context = "file:context.txt"
    ''')

    loom = wordloom.load(loom_path)
    assert loom['my_prompt'].file_bindings == {}
    # raw metadata value is still accessible
    assert loom['my_prompt'].meta['context'] == 'file:context.txt'


# ---------------------------------------------------------------------------
# dir: and glob: inclusion
# ---------------------------------------------------------------------------

def test_dir_inclusion(tmp_path):
    docs = tmp_path / 'docs'
    docs.mkdir()
    (docs / 'a.txt').write_text('file A', encoding='utf-8')
    (docs / 'b.txt').write_text('file B', encoding='utf-8')
    loom_path = _write_loom(tmp_path, '''
        lang = "en"
        [item]
        _ = "{docs}"
        docs = "dir:docs"
    ''')

    loom = wordloom.load(loom_path, features={'file-inclusion'})
    result = loom['item'].file_bindings['docs']
    assert 'file A' in result
    assert 'file B' in result
    assert '=== a.txt ===' in result


def test_glob_inclusion(tmp_path):
    (tmp_path / 'one.md').write_text('# One', encoding='utf-8')
    (tmp_path / 'two.md').write_text('# Two', encoding='utf-8')
    (tmp_path / 'skip.txt').write_text('skip me', encoding='utf-8')
    loom_path = _write_loom(tmp_path, '''
        lang = "en"
        [item]
        _ = "{notes}"
        notes = "glob:*.md"
    ''')

    loom = wordloom.load(loom_path, features={'file-inclusion'})
    result = loom['item'].file_bindings['notes']
    assert '# One' in result
    assert '# Two' in result
    assert 'skip me' not in result


# ---------------------------------------------------------------------------
# render() method
# ---------------------------------------------------------------------------

def test_render_merges_file_bindings_with_runtime(tmp_path):
    (tmp_path / 'base.txt').write_text('base content', encoding='utf-8')
    loom_path = _write_loom(tmp_path, '''
        lang = "en"
        [tmpl]
        _ = "{base} and {extra}"
        base = "file:base.txt"
    ''')

    loom = wordloom.load(loom_path, features={'file-inclusion'})
    result = loom['tmpl'].render(extra='runtime value')
    assert result == 'base content and runtime value'


def test_render_runtime_overrides_file_binding(tmp_path):
    (tmp_path / 'base.txt').write_text('file value', encoding='utf-8')
    loom_path = _write_loom(tmp_path, '''
        lang = "en"
        [tmpl]
        _ = "{base}"
        base = "file:base.txt"
    ''')

    loom = wordloom.load(loom_path, features={'file-inclusion'})
    result = loom['tmpl'].render(base='override')
    assert result == 'override'


def test_render_works_without_file_inclusion():
    loom = wordloom.load(b"lang = 'en'\n[item]\n_ = 'Hello {name}'")
    assert loom['item'].render(name='World') == 'Hello World'


# ---------------------------------------------------------------------------
# security / error cases
# ---------------------------------------------------------------------------

def test_file_inclusion_path_traversal_raises(tmp_path):
    (tmp_path.parent / 'secret.txt').write_text('secret', encoding='utf-8')
    loom_path = _write_loom(tmp_path, '''
        lang = "en"
        [item]
        _ = "{leak}"
        leak = "file:../secret.txt"
    ''')

    with pytest.raises(ValueError, match='escapes the loom directory'):
        wordloom.load(loom_path, features={'file-inclusion'})


def test_file_inclusion_absolute_path_raises(tmp_path):
    loom_path = _write_loom(tmp_path, '''
        lang = "en"
        [item]
        _ = "{leak}"
        leak = "file:/etc/passwd"
    ''')

    with pytest.raises(ValueError, match='must be relative'):
        wordloom.load(loom_path, features={'file-inclusion'})


def test_file_inclusion_missing_file_raises(tmp_path):
    loom_path = _write_loom(tmp_path, '''
        lang = "en"
        [item]
        _ = "{missing}"
        missing = "file:does_not_exist.txt"
    ''')

    with pytest.raises(FileNotFoundError):
        wordloom.load(loom_path, features={'file-inclusion'})


def test_file_inclusion_glob_dotdot_raises(tmp_path):
    loom_path = _write_loom(tmp_path, '''
        lang = "en"
        [item]
        _ = "{leak}"
        leak = "glob:../*.txt"
    ''')

    with pytest.raises(ValueError, match='"\\.\\."'):
        wordloom.load(loom_path, features={'file-inclusion'})


def test_file_inclusion_requires_base_dir_for_bytes_input():
    toml_bytes = b"lang = 'en'\n[item]\n_ = '{x}'\nx = 'file:x.txt'"
    with pytest.raises(ValueError, match='file-inclusion'):
        wordloom.load(toml_bytes, features={'file-inclusion'})


def test_file_inclusion_explicit_base_dir(tmp_path):
    (tmp_path / 'data.txt').write_text('explicit base', encoding='utf-8')
    # Load from bytes but supply an explicit base_dir
    toml_bytes = b"lang = 'en'\n[item]\n_ = '{data}'\ndata = 'file:data.txt'"
    loom = wordloom.load(toml_bytes, features={'file-inclusion'}, base_dir=tmp_path)
    assert loom['item'].file_bindings['data'] == 'explicit base'


# ---------------------------------------------------------------------------
# clone() preserves file_bindings
# ---------------------------------------------------------------------------

def test_clone_preserves_file_bindings(tmp_path):
    (tmp_path / 'f.txt').write_text('content', encoding='utf-8')
    loom_path = _write_loom(tmp_path, '''
        lang = "en"
        [item]
        _ = "{f}"
        f = "file:f.txt"
    ''')

    loom = wordloom.load(loom_path, features={'file-inclusion'})
    original = loom['item']
    cloned = original.clone(value='new text {f}')
    assert cloned.file_bindings == original.file_bindings
    assert cloned.render() == 'new text content'


if __name__ == '__main__':
    raise SystemExit('Attention! Run with pytest')
