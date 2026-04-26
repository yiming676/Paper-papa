import json
import re
from functools import lru_cache
from pathlib import Path


ABBREVIATION_PATH = Path(__file__).with_name("abbreviations.json")


def _normalize_base(value: str) -> str:
    text = value.strip().lower()
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\b([a-z]+)-([a-z]+)\b", r"\1 \2", text)
    parts = [singularize(part) for part in text.split()]
    return " ".join(parts)


@lru_cache
def load_abbreviation_maps() -> tuple[dict[str, str], dict[str, str]]:
    raw = json.loads(ABBREVIATION_PATH.read_text(encoding="utf-8"))
    full_to_short: dict[str, str] = {}
    alias_to_full: dict[str, str] = {}
    for full_name, aliases in raw.items():
        normalized_full = _normalize_base(full_name)
        full_to_short[normalized_full] = normalized_full
        alias_to_full[normalized_full] = normalized_full
        for alias in aliases:
            normalized_alias = _normalize_base(alias)
            alias_to_full[normalized_alias] = normalized_full
    return full_to_short, alias_to_full


def singularize(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("s") and not token.endswith("ss") and len(token) > 3:
        return token[:-1]
    return token


def normalize_text(value: str) -> str:
    text = _normalize_base(value)
    _, alias_to_full = load_abbreviation_maps()
    return alias_to_full.get(text, text)


def collect_aliases(value: str) -> set[str]:
    normalized = normalize_text(value)
    full_to_short, alias_to_full = load_abbreviation_maps()
    aliases = {normalized}
    for alias, full_name in alias_to_full.items():
        if full_name == normalized:
            aliases.add(alias)
    if normalized in full_to_short:
        aliases.add(normalized)
    return aliases
