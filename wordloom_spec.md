# Word Loom Specification

**License**: [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)

Word Loom is a convention for expressing language text and templates for AI language model-related uses, for example prompt templates. The format is based on [TOML](https://toml.io/), and word looms are meant to be kept in resource directories for use with code invoking LLMs.

## Basic Principles

1. Separation of code from natural language
    * Must be a straightforward process to translate any natural language elements
2. Composability of natural language elements
3. Friendliness to mechanical comparisons (i.e. via `diff`)
4. Friendliness to traditional globalization (G11N) techniques

Principle \#3 motivates the choice of TOML format. Principle \#1 makes templating languages such as Jinja2 unsuitable.

An example word loom with general-purpose prompts:

```toml
# Warning: there is a difference between single & double quotes in TOML. Former is not escaped.
# Since in the root table, all prompts in this file will default to English
# Can use more precise values, such as 'en_UK'.
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
_ = 'Summarize the following text in {num_sentences} sentences:\n\n{text}'
_m = ['num_sentences', 'text']

[hello_translated]
_ = 'Hello'
_fr = 'Salut'
_es = 'Hola'

[goodbye_translated]
_ = 'Goodbye'
_fr = 'Au revoir'
_es = 'Adiós'
```

An example emphasizing internationalization (i18n) for prompts:

```toml
# i18n-focused example - prompts that need to work across languages
# Note: Use double quotes when you need to include apostrophes in text
lang = 'en'

[davinci3_instruct_system]
_ = '''
Obey the instruction below, based on the provided context. If you cannot obey the instruction
based on the provided context, respond: "I don't have enough information to comply".
'''

[i18n_context]
_ = '''
Internationalization is a corporate strategy that involves making products and services as adaptable as possible, so they can easily enter different national markets. This often requires the assistance of subject matter experts. Internationalization is sometimes shortened to "i18n", where 18 represents the number of characters in the word.
'''
source = 'https://www.lionbridge.com/blog/translation-localization/localization-globalization-internationalization-whats-the-difference/'

[write_i18n_advocacy]
_ = '''
{davinci3_instruct_system}

CONTEXT: {i18n_context}

INSTRUCTION: Write a corporate memo encouraging our company to take i18n seriously
'''
_m = ['davinci3_instruct_system', 'i18n_context']

[translate_request]
_ = 'Comment dit-on en anglais: {hardcoded_food}?'
lang = 'fr'  # Override default language code for this item
_m = ['hardcoded_food']

[hardcoded_food]
_ = 'pomme de terre'
lang = 'fr'

[greeting_multilang]
_ = 'Hello, how can I help you today?'
_fr = "Bonjour, comment puis-je vous aider aujourd'hui?"  # Double quotes for apostrophe
_es = '¡Hola! ¿Cómo puedo ayudarte hoy?'
_de = 'Hallo, wie kann ich Ihnen heute helfen?'
_ja = 'こんにちは、今日はどのようにお手伝いできますか？'
```

## Using with OpenAI API

Here's how to use Word Loom with the popular OpenAI Python API:

```python
from openai import OpenAI
import wordloom

# Load your prompts
with open('prompts.toml', 'rb') as fp:
    loom = wordloom.load(fp)

# Initialize OpenAI client
client = OpenAI()

# Use a system prompt and user prompt
response = client.chat.completions.create(
    model='gpt-4',
    messages=[
        {'role': 'system', 'content': str(loom['system_instruction'])},
        {'role': 'user', 'content': str(loom['translation_prompt']).format(
            target_lang='Spanish',
            text='Hello, how are you?'
        )}
    ]
)

print(response.choices[0].message.content)
```

For more complex templates with nested references:

```python
# Using template composition
code_snippet = '''
def calculate_total(items):
    return sum(item.price for item in items)
'''

# Expand the template with your data
prompt = str(loom['code_review_prompt']).format(code_snippet=code_snippet)

response = client.chat.completions.create(
    model='gpt-4',
    messages=[
        {'role': 'system', 'content': str(loom['system_instruction'])},
        {'role': 'user', 'content': prompt}
    ]
)
```

### Internationalized prompts with OpenAI

One powerful use case is selecting prompts in different languages for multilingual applications:

```python
import wordloom

# Load i18n prompts
with open('i18n_prompts.toml', 'rb') as fp:
    loom = wordloom.load(fp, lang='en')

# Get greeting in user's language
user_lang = 'fr'  # Detect from user preferences
greeting = loom['greeting_multilang']

if user_lang != 'en':
    greeting_text = greeting.in_lang(user_lang) or str(greeting)
else:
    greeting_text = str(greeting)

# Use with OpenAI in the appropriate language
response = client.chat.completions.create(
    model='gpt-4',
    messages=[
        {'role': 'system', 'content': greeting_text},
        {'role': 'user', 'content': 'I need help with my account'}
    ]
)
```

This approach is crucial because **prompt engineering is not just translation**. A prompt that works well in English may need significant adjustments to achieve similar performance in other languages. WordLoom allows you to:

1. Keep all language variants together in one file for easy comparison
2. Test and tune prompts for each language independently
3. Maintain metadata about prompt performance across languages
4. Use traditional i18n workflows while respecting the unique needs of LLM prompting

# Language items

A language item (or just item) is an entity that encapsulates a text, which can be represented in multiple languages. An item comprises one text value in a default language, zero or more text values in alternate languages, and a hash table of metadata (key/value pairs). A word loom, or just loom, is a term for a file expressing one or more language items in Word Loom format.

The examples above define language items including:

General-purpose prompts:
* `system_instruction` - System prompt for OpenAI-style APIs
* `code_review_prompt` - Template for code review tasks
* `translation_prompt` - Template for translation requests
* `summarize_prompt` - Template for summarization tasks
* `hello_translated` / `goodbye_translated` - Simple multilingual greetings

Internationalization-focused items:
* `davinci3_instruct_system` - Instruction-following system prompt
* `i18n_context` - Context about internationalization (with metadata)
* `write_i18n_advocacy` - Composite template using multiple items
* `translate_request` - French-language prompt template
* `hardcoded_food` - French text constant
* `greeting_multilang` - Greeting in 5 languages (en, fr, es, de, ja)

They are defined by top-level TOML hash tables. Language item keys starting with `_` as well as the special key `lang` are reserved by the Word Loom specification. The key `_` sets the text value in the default language. A key in the form `_` followed by a language code sets the corresponding text value in an alternate language.

Any keys which are not reserved by Word Loom become part of the language item's metadata, and are made available to the processing layer for the loom.

You can add custom metadata to any language item. For example:

```toml
[research_prompt]
_ = 'Research the following topic and provide key findings: {topic}'
_m = ['topic']
source = 'internal'
category = 'research'
version = '2.0'
```

The `source`, `category`, and `version` keys become metadata accessible via `loom['research_prompt'].meta`.

# Languages and translations

A default language code fo rthe entire loom can be set with a top-level `loom` key, of which there must only be one. A language item's default language can be overridden within its TOML hash table using the `lang` key. Alternate language correspondences for the default text can be expressed using `_` prefixed language codes. All language codes in Word Loom follow the [IETF BCP 47](https://en.wikipedia.org/wiki/IETF_language_tag) specification.

Note: This example has multiple languages in one, but traditional i18n generally has a separate file per language. Word loom implementations should support selecting the correct file from a directory full of different language files.

LLM localization can't necessarily be treated as a simple extension of code l10n, though. If you just naively give LLM prompts to translators in, say gettext file format, their translations might result in dramatically different performance from the LLMs used. Prompt management (sometimes called prompt engineering) is not a simple matter of speaking the relevant language, and in fact it opens up a situation where natural language becomes code, with technical implications. It is still best treated separately from traditional coding languages, and yet it's not just simple text to be localized.

One approach would be to generate translation files from word loom files, for an initial, naive translation, reconstruct word looms from those translations, and then work on the localized word looms to meet LLM performance and alignment needs.

# Templating

The curly braces in text values provide templating ability, and are to be replaced with different text. The string between the curly braces is the marker, and can either be an identifier string or a full URL. Identifiers can refer to named items elsewhere in the same file, in an included file, or provided at runtime by the host system. A URL marker represents a service which can dynamically create the replacement text. This service gets the full word loom (with inclusions) as additional context. This can be used to implement e.g. the ReAct LLM pattern.

## Template markers

The `_m` key declares template markers (variables) that should be replaced at runtime. This serves as documentation and allows for validation:

```python
import wordloom

loom = wordloom.load(open('prompts.toml', 'rb'))

# Check what variables a prompt expects
prompt = loom['translation_prompt']
print(prompt.markers)  # ['target_lang', 'text']

# Expand the template
expanded = str(prompt).format(target_lang='French', text='Hello')
```

**TODO**: Add examples of more complex prompts with e.g. nested loops, and "agentic" blah blah blah.

Tips:

* For VS Code users, the [Even Better TOML](https://marketplace.visualstudio.com/items?itemName=tamasfe.even-better-toml) extension is better
* Python users: 3.11 or later builds in `tomllib`; for prior versions you can install [tomli](https://pypi.org/project/tomli/), which is API compatible

---

# Parallel work

* IBM's [Prompt Declaration Language](https://github.com/IBM/prompt-declaration-language) [mid 2024]

# Prompting, in general

Some useful resources for prompts in general

* [The Art of Prompt Design: Use Clear Syntax](https://towardsdatascience.com/the-art-of-prompt-design-use-clear-syntax-4fc846c1ebd5) | [The Art of Prompt Design: Prompt Boundaries and Token Healing](https://towardsdatascience.com/the-art-of-prompt-design-prompt-boundaries-and-token-healing-3b2448b0be38)

Sources of sample prompts

* [awesome-chatgpt-prompts](https://github.com/f/awesome-chatgpt-prompts/blob/main/prompts.csv)

Other names considered: Prompt Mark (prefer to generalize from "prompt"), Word Flux

Some useful resources for g10n in general (bias to Python):

* [Standard Python i18n tools](https://docs.python.org/3/library/i18n.html)
* [Python gettext](https://docs.python.org/3/library/gettext.html) - std lib facilities based on GNU gettext
* [Python Babel](https://babel.pocoo.org/en/latest/), "utilities that assist in internationalizing and localizing Python applications, with an emphasis on web-based applications."
* [Article on Python localization (touches on Babel, gettext, etc.)](https://phrase.com/blog/posts/python-localization/)
