# SPDX-FileCopyrightText: 2023-present Oori Data <info@oori.dev>
# SPDX-License-Identifier: Apache-2.0
# test/test_openai_integration.py
'''
Test WordLoom integration with OpenAI API using mocks

pytest test/test_openai_integration.py
'''

import pytest

import wordloom


# Sample TOML content for OpenAI-style prompts
OPENAI_PROMPTS_TOML = b"""
# OpenAI-style prompts
lang = 'en'

[system_instruction]
_ = 'You are a helpful assistant that provides concise and accurate answers.'

[code_review_prompt]
_ = '''
Review the following code and provide feedback on:
1. Code quality and readability
2. Potential bugs or issues
3. Suggestions for improvement

Code:
{code_snippet}
'''
_m = ['code_snippet']

[translation_prompt]
_ = 'Translate the following text to {target_lang}: {text}'
_m = ['target_lang', 'text']

[summarize_prompt]
_ = 'Summarize the following text in {num_sentences} sentences:\\n\\n{text}'
_m = ['num_sentences', 'text']
"""


@pytest.fixture
def openai_loom():
    '''Load the OpenAI prompts loom'''
    return wordloom.load(OPENAI_PROMPTS_TOML)


def test_load_openai_prompts(openai_loom):
    '''Test that OpenAI-style prompts load correctly'''
    assert 'system_instruction' in openai_loom
    assert 'code_review_prompt' in openai_loom
    assert 'translation_prompt' in openai_loom

    # Check markers are preserved
    assert openai_loom['code_review_prompt'].markers == ['code_snippet']
    assert openai_loom['translation_prompt'].markers == ['target_lang', 'text']


def test_basic_template_expansion(openai_loom):
    '''Test basic template marker expansion'''
    prompt = openai_loom['translation_prompt']

    # Manual template expansion (simple example)
    expanded = str(prompt).format(target_lang='French', text='Hello, world!')
    assert 'French' in expanded
    assert 'Hello, world!' in expanded


def test_openai_chat_completion_format(openai_loom):
    '''Test formatting prompts for OpenAI chat completion API'''
    system_prompt = openai_loom['system_instruction']
    user_prompt = openai_loom['summarize_prompt']

    # Format for OpenAI API
    messages = [
        {'role': 'system', 'content': str(system_prompt)},
        {'role': 'user', 'content': str(user_prompt).format(
            num_sentences='3',
            text='This is a long article about AI. It discusses many topics...'
        )}
    ]

    assert messages[0]['role'] == 'system'
    assert 'helpful assistant' in messages[0]['content']
    assert messages[1]['role'] == 'user'
    assert '3 sentences' in messages[1]['content']


@pytest.mark.parametrize('target_lang,text,expected_in_output', [
    ('Spanish', 'Good morning', 'Spanish'),
    ('German', 'Thank you', 'German'),
    ('Japanese', 'Welcome', 'Japanese'),
])
def test_translation_prompt_variations(openai_loom, target_lang, text, expected_in_output):
    '''Test translation prompt with different languages'''
    prompt = openai_loom['translation_prompt']
    expanded = str(prompt).format(target_lang=target_lang, text=text)

    assert expected_in_output in expanded
    assert text in expanded


def test_mock_openai_completion(openai_loom, mocker):
    '''Test with a mocked OpenAI API call'''
    # Mock the OpenAI client
    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_response.choices = [mocker.MagicMock()]
    mock_response.choices[0].message.content = 'This is a test response from the AI.'

    mock_client.chat.completions.create.return_value = mock_response

    # Use WordLoom prompt
    system_prompt = openai_loom['system_instruction']
    user_prompt = openai_loom['summarize_prompt']

    # Simulate API call
    response = mock_client.chat.completions.create(
        model='gpt-4',
        messages=[
            {'role': 'system', 'content': str(system_prompt)},
            {'role': 'user', 'content': str(user_prompt).format(
                num_sentences='2',
                text='Sample text to summarize.'
            )}
        ]
    )

    # Verify the mock was called correctly
    assert mock_client.chat.completions.create.called
    assert response.choices[0].message.content == 'This is a test response from the AI.'

    # Verify the prompt was formatted correctly
    call_args = mock_client.chat.completions.create.call_args
    messages_sent = call_args[1]['messages']
    assert len(messages_sent) == 2
    assert messages_sent[0]['role'] == 'system'
    assert messages_sent[1]['role'] == 'user'
    assert '2 sentences' in messages_sent[1]['content']


def test_code_review_prompt_expansion(openai_loom):
    '''Test code review prompt with actual code snippet'''
    prompt = openai_loom['code_review_prompt']

    code_snippet = '''
def add_numbers(a, b):
    return a + b
'''

    expanded = str(prompt).format(code_snippet=code_snippet)

    assert 'Code quality' in expanded
    assert 'def add_numbers' in expanded
    assert 'return a + b' in expanded


def test_metadata_preservation(openai_loom):
    '''Test that metadata is preserved from TOML'''
    # All prompts should have the default language
    assert openai_loom['system_instruction'].lang == 'en'
    assert openai_loom['code_review_prompt'].lang == 'en'


if __name__ == '__main__':
    raise SystemExit('Attention! Run with pytest')
