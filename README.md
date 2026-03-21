**Word Loom**

A convention for expressing language text and templates for AI language model-related uses, especially prompt templates. The format is based on [TOML](https://toml.io/), and word looms are meant to be kept in resource directories for use with code invoking LLMs.

# Why Word Loom?

When working with LLMs, we've found ourselves needing better ways to manage prompts. Traditional code doesn't quite fit—prompts are natural language, not code. But they're also not just static text—they need templating, versioning, metadata and, crucially, internationalization.

Word Loom addresses some gaps that become clear once you start building real LLM applications:

1. **Separation of concerns**: Keep your prompts out of your code, making them easier to iterate, version, and review
2. **Multilingual by design**: LLM prompt engineering isn't just translation—a prompt that works well in English may need significant changes to achieve similar results in Japanese or Spanish. Word Loom lets you keep all language variants together, test them independently, and maintain metadata about their performance
3. **Template composition**: Build complex prompts from reusable pieces, with clear markers for runtime values
4. **Diff-friendly**: TOML's structure makes it easy to track changes in version control
5. **Compatible with traditional i18n**: Works alongside gettext, Babel, and other localization tools, while respecting the unique needs of LLM prompting

# Quick Example

```toml
# prompts.toml
lang = 'en'

[system_instruction]
_ = 'You are a helpful assistant that provides concise and accurate answers.'

[greeting_multilang]
_ = 'Hello, how can I help you today?'
_fr = "Bonjour, comment puis-je vous aider aujourd'hui?"
_es = '¡Hola! ¿Cómo puedo ayudarte hoy?'
_de = 'Hallo, wie kann ich Ihnen heute helfen?'
_ja = 'こんにちは、今日はどのようにお手伝いできますか？'

[code_review_prompt]
_ = '''
Review the following code and provide feedback on:
1. Code quality and readability
2. Potential bugs or issues
3. Suggestions for improvement

Code:
{code_snippet}
'''
_m = ['code_snippet']  # Declare template variables
```

# Python implementation

[![PyPI - Version](https://img.shields.io/pypi/v/wordloom.svg)](https://pypi.org/project/WordLoom)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/wordloom.svg)](https://pypi.org/project/WordLoom)

An example using Word Loom with an LLM API. OpenAI in this case, but Word Loom can work with any integration.

```python
from openai import OpenAI
import wordloom

# Load your prompts
with open('prompts.toml', 'rb') as fp:
    loom = wordloom.load(fp)

client = OpenAI()

# Select language based on user preference
user_lang = 'fr'
greeting = loom['greeting_multilang']
greeting_text = greeting.in_lang(user_lang) or str(greeting)

# Use with OpenAI
response = client.chat.completions.create(
    model='gpt-4',
    messages=[
        {'role': 'system', 'content': greeting_text},
        {'role': 'user', 'content': 'How does an LLM work?'}
    ]
)
```

# Installation

```bash
uv pip install wordloom
```

Or without uv:

```bash
pip install wordloom
```

# Documentation

See [wordloom_spec.md](wordloom_spec.md) for the complete specification, including:
- Detailed format description
- Template marker syntax
- Internationalization features
- More usage examples
- Integration patterns

# LLM Prompting and internationalization

This is an under-considered area in AI prompting. When dealing with multiple languages, prompt engineering requires more than just translation. A prompt carefully tuned for English may perform very differently when naively translated to other languages. Word Loom helps by:

- Keeping all language variants in one place for easy comparison
- Allowing independent tuning of each language version
- Supporting metadata to track prompt performance across languages
- Enabling traditional i18n workflows while respecting LLM-specific needs

# Contributing

Contributions welcome! We're interested in feedback from the community about what works and what doesn't in real-world usage. To get help with the code implementation, read [CONTRIBUTING.md](CONTRIBUTING.md).

# License

- **Code** (Python library): Apache 2.0 - See [LICENSE](LICENSE)
- **Specification** (wordloom_spec.md): [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) - See [LICENSE-spec](LICENSE-spec)

The specification is under CC BY 4.0 to encourage broad adoption and derivative work while ensuring attribution. We want the format itself to be as open and reusable as possible, allowing anyone to create implementations in any language or adapt the format for their specific needs.

# Acknowledgments

<table><tr>
  <td><a href="https://oori.dev/"><img src="https://www.oori.dev/assets/branding/oori_Logo_FullColor.png" width="64" /></a></td>
  <td>Word Loom is primarily developed by the crew at <a href="https://oori.dev/">Oori Data</a>. We offer LLMOps, data pipelines and software engineering services around AI/LLM applications. Word Loom emerged from our work building LLM applications with sophisticated prompt management needs and multilingual imperatives.</td>
</tr></table>

# Related Work

Since we started work on Word Loom there have bene some other projects emerging with some degree of intersection.

- [IBM's Prompt Declaration Language](https://github.com/IBM/prompt-declaration-language) - A more comprehensive language for prompt engineering
- [PromptL](https://promptl.ai/)
- [Promptfoo](https://github.com/promptfoo/promptfoo) - Primarily for testing/evals; uses YAML-based configurations to manage and version prompts. Philosophy is: prompts as configuration
- [Lilypad](https://www.google.com/search?q=https://github.com/mirascope/lilypad) - newer project; emphasizes versioning and managing prompts as code artifacts rather than just strings
- [Dotprompt](https://www.google.com/search?q=https://github.com/firebase/genkit/tree/main/js/dotprompt) (by Firebase Genkit) - format specifically for defining prompts in .prompt files (using a subset of Handlebars)
- [Instructor](https://github.com/jxnl/instructor) - Uses Pydantic to swap raw LLM responses for structured Python objects
- [Magentic](https://github.com/jackmpcollins/magentic) - Uses Python decorators to turn functions into LLM calls
- [Pydantic AI](https://github.com/pydantic/pydantic-ai) - Newer framework from the Pydantic team that treats agents and prompts as strictly typed entities
- [BAML](https://github.com/boundaryml/baml) - AI framework for prompts within code
