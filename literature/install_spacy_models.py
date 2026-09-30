"""Install spaCy models via uv pip using direct release URLs."""
import subprocess

# spaCy 3.7 compatible model URLs
MODELS = [
    "https://github.com/explosion/spacy-models/releases/download/fr_core_news_sm-3.7.0/fr_core_news_sm-3.7.0-py3-none-any.whl",
    "https://github.com/explosion/spacy-models/releases/download/de_core_news_sm-3.7.0/de_core_news_sm-3.7.0-py3-none-any.whl",
    "https://github.com/explosion/spacy-models/releases/download/es_core_news_sm-3.7.0/es_core_news_sm-3.7.0-py3-none-any.whl",
    "https://github.com/explosion/spacy-models/releases/download/it_core_news_sm-3.7.0/it_core_news_sm-3.7.0-py3-none-any.whl",
    "https://github.com/explosion/spacy-models/releases/download/pt_core_news_sm-3.7.0/pt_core_news_sm-3.7.0-py3-none-any.whl",
    "https://github.com/explosion/spacy-models/releases/download/nl_core_news_sm-3.7.0/nl_core_news_sm-3.7.0-py3-none-any.whl",
    "https://github.com/explosion/spacy-models/releases/download/pl_core_news_sm-3.7.0/pl_core_news_sm-3.7.0-py3-none-any.whl",
    "https://github.com/explosion/spacy-models/releases/download/fi_core_news_sm-3.7.0/fi_core_news_sm-3.7.0-py3-none-any.whl",
    "https://github.com/explosion/spacy-models/releases/download/sv_core_news_sm-3.7.0/sv_core_news_sm-3.7.0-py3-none-any.whl",
    "https://github.com/explosion/spacy-models/releases/download/ru_core_news_sm-3.7.0/ru_core_news_sm-3.7.0-py3-none-any.whl",
]

for url in MODELS:
    name = url.split("/")[-1].replace("-py3-none-any.whl", "")
    print(f"\nInstalling {name}...")
    result = subprocess.run(["uv", "pip", "install", url], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  ✓ {name}")
    else:
        print(f"  ✗ {name}: {result.stderr.strip()[:200]}")
