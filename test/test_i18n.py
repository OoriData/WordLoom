# SPDX-FileCopyrightText: 2023-present Oori Data <info@oori.dev>
# SPDX-License-Identifier: Apache-2.0
# test/test_i18n_integration.py
'''
Test WordLoom i18n features with OpenAI API integration

pytest test/test_i18n_integration.py
'''

import os
import sys

import pytest

import wordloom


@pytest.fixture
def i18n_loom():
    '''Load the sample loom which includes i18n examples'''
    fpath = os.path.dirname(sys.modules['wordloom'].__file__)
    with open(os.path.join(fpath, 'resources/wordloom/sample.toml'), 'rb') as fp:
        return wordloom.load(fp)


def test_multilingual_greeting(i18n_loom):
    '''Test accessing greetings in multiple languages'''
    greeting = i18n_loom['greeting_multilang']

    # Check all languages are present
    assert str(greeting) == 'Hello, how can I help you today?'
    assert 'Bonjour' in greeting.in_lang('fr')
    assert 'Hola' in greeting.in_lang('es')
    assert 'Hallo' in greeting.in_lang('de')
    assert 'こんにちは' in greeting.in_lang('ja')


def test_language_override():
    '''Test that language overrides work correctly'''
    # goodbye_translated has lang='fr' set, so we need to load with lang='fr'
    fpath = os.path.dirname(sys.modules['wordloom'].__file__)
    with open(os.path.join(fpath, 'resources/wordloom/sample.toml'), 'rb') as fp:
        loom_fr = wordloom.load(fp, lang='fr')

    goodbye = loom_fr['goodbye_translated']
    assert goodbye.lang == 'fr'
    assert str(goodbye) == 'Adieu'
    assert goodbye.in_lang('en') == 'Goodbye'


def test_template_composition_i18n(i18n_loom):
    '''Test that template composition works with i18n content'''
    template = i18n_loom['write_i18n_advocacy']

    # Check markers are preserved
    assert 'davinci3_instruct_system' in template.markers
    assert 'i18n_context' in template.markers

    # Check the template references other items
    assert '{davinci3_instruct_system}' in str(template)
    assert '{i18n_context}' in str(template)


def test_metadata_with_i18n(i18n_loom):
    '''Test that metadata is preserved on i18n items'''
    context = i18n_loom['i18n_context']

    # Check metadata
    assert 'source' in context.meta
    assert 'lionbridge.com' in context.meta['source']


def test_french_language_selection():
    '''Test loading only French language items'''
    fpath = os.path.dirname(sys.modules['wordloom'].__file__)
    with open(os.path.join(fpath, 'resources/wordloom/sample.toml'), 'rb') as fp:
        loom_fr = wordloom.load(fp, lang='fr')

    # French items should be present
    assert 'hardcoded_food' in loom_fr
    assert 'translate_request' in loom_fr
    assert 'goodbye_translated' in loom_fr

    # Check the text is in French
    assert str(loom_fr['hardcoded_food']) == 'pomme de terre'
    assert 'Comment dit-on' in str(loom_fr['translate_request'])


def test_openai_multilingual_workflow(i18n_loom, mocker):
    '''
    Test a realistic multilingual workflow with OpenAI API mock
    Simulates serving users in different languages
    '''
    # Mock the OpenAI client
    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_response.choices = [mocker.MagicMock()]
    mock_response.choices[0].message.content = 'Voici votre réponse'

    mock_client.chat.completions.create.return_value = mock_response

    # Simulate user preference for French
    user_lang = 'fr'
    greeting = i18n_loom['greeting_multilang']

    # Select appropriate language
    if user_lang != 'en':
        greeting_text = greeting.in_lang(user_lang) or str(greeting)
    else:
        greeting_text = str(greeting)

    # Verify French greeting was selected
    assert 'Bonjour' in greeting_text

    # Use with mock OpenAI
    response = mock_client.chat.completions.create(  # noqa: F841
        model='gpt-4',
        messages=[
            {'role': 'system', 'content': greeting_text},
            {'role': 'user', 'content': 'J\'ai besoin d\'aide'}
        ]
    )

    # Verify the call was made with French greeting
    assert mock_client.chat.completions.create.called
    call_args = mock_client.chat.completions.create.call_args
    messages_sent = call_args[1]['messages']
    assert 'Bonjour' in messages_sent[0]['content']


@pytest.mark.parametrize('user_lang,expected_greeting_part', [
    ('fr', 'Bonjour'),
    ('es', 'Hola'),
    ('de', 'Hallo'),
    ('ja', 'こんにちは'),
    ('en', 'Hello'),
])
def test_language_selection_parametrized(i18n_loom, user_lang, expected_greeting_part):
    '''Test language selection for multiple languages'''
    greeting = i18n_loom['greeting_multilang']

    if user_lang != 'en':
        greeting_text = greeting.in_lang(user_lang) or str(greeting)
    else:
        greeting_text = str(greeting)

    assert expected_greeting_part in greeting_text


def test_i18n_context_usage(i18n_loom):
    '''Test using the i18n context in a prompt template'''
    context = i18n_loom['i18n_context']
    system_prompt = i18n_loom['davinci3_instruct_system']

    # These would be used together in a real scenario
    assert 'Internationalization' in str(context)
    assert 'i18n' in str(context)
    assert 'Obey the instruction' in str(system_prompt)


if __name__ == '__main__':
    raise SystemExit('Attention! Run with pytest')
