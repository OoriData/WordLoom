# SPDX-FileCopyrightText: 2023-present Oori Data <info@oori.dev>
# SPDX-License-Identifier: Apache-2.0
# test/test_basics.py
'''
pytest test

or

pytest test/test_basics.py
'''
# ruff: noqa: E501

import os
import sys

import pytest

import wordloom


@pytest.fixture
def SAMPLE_TOML_STR():
    # Load language material (word loom) format
    fpath = os.path.dirname(sys.modules['wordloom'].__file__)

    with open(os.path.join(fpath, 'resources/wordloom/sample.toml'), 'rb') as fp:
        toml_content = fp.read()
    return toml_content


@pytest.fixture
def SAMPLE_TOML_FP():
    # Load language material (word loom) format
    fpath = os.path.dirname(sys.modules['wordloom'].__file__)

    return open(os.path.join(fpath, 'resources/wordloom/sample.toml'), 'rb')

def test_load_fp_vs_str(SAMPLE_TOML_STR, SAMPLE_TOML_FP):
    loom1 = wordloom.load(SAMPLE_TOML_STR)
    loom2 = wordloom.load(SAMPLE_TOML_FP)
    SAMPLE_TOML_FP.close()
    assert loom1 == loom2


def test_sample_texts_check(SAMPLE_TOML_STR):
    # print(SAMPLE_TOML)
    loom = wordloom.load(SAMPLE_TOML_STR)
    # default language text is also a key
    # We now have more items: i18n examples + general-purpose examples
    # Each item appears twice: once by key, once by text value
    assert len(loom.keys()) >= 10  # At least the core items

    # Check for i18n examples
    for k in ['davinci3_instruct_system', 'hello_translated', 'i18n_context', 'write_i18n_advocacy']:
        assert k in loom.keys()

    # Check for general-purpose examples
    for k in ['system_instruction', 'code_review_prompt', 'greeting_multilang']:
        assert k in loom.keys()

    assert 'Hello' in loom.keys()

    # Check markers for specific items
    assert loom['write_i18n_advocacy'].markers == ['davinci3_instruct_system', 'i18n_context']
    assert loom['code_review_prompt'].markers == ['code_snippet']
    assert loom['davinci3_instruct_system'].lang == 'en'
    assert loom['system_instruction'].lang == 'en'

    # Check multilang item has translations
    greeting = loom['greeting_multilang']
    assert greeting.in_lang('fr') is not None
    assert greeting.in_lang('ja') is not None
    assert 'Bonjour' in greeting.in_lang('fr')

    # Default language is English
    loom1 = wordloom.load(SAMPLE_TOML_STR, lang='en')
    assert loom1 == loom

    # Test French language selection
    loom_fr = wordloom.load(SAMPLE_TOML_STR, lang='fr')
    assert 'goodbye_translated' in loom_fr.keys()
    assert 'translate_request' in loom_fr.keys()
    assert 'hardcoded_food' in loom_fr.keys()
    assert loom_fr['hardcoded_food'].lang == 'fr'
    assert loom_fr['translate_request'].markers == ['hardcoded_food']


if __name__ == '__main__':
    raise SystemExit("Attention! Run with pytest")
