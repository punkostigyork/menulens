"""Small deterministic vocabulary; no model calls or dietary inference here."""
import re
import unicodedata
from app.models import MenuItem
from app.schemas.search import SearchIntent


def normalize(value: str) -> str:
    text = "".join(char for char in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(char))
    return " ".join(re.findall(r"[^\W_]+", text, re.UNICODE))


# Exact words/phrases only: 'ham' must not match 'champignon'. This is not a translator or stemmer.
INGREDIENT_GROUPS = [
    ("chicken", "csirke", "csirkehus", "csirkemell"), ("beef", "marha", "marhahus"),
    ("pork", "sertes", "serteshus"), ("fish", "hal"), ("potato", "potatoes", "burgonya", "krumpli"),
    ("carrot", "carrots", "sargarepa"), ("mushroom", "mushrooms", "gomba"),
    ("cheese", "sajt"), ("sour cream", "tejfol"), ("chocolate", "csokolade"),
    ("rice", "rizs"), ("tomato", "tomatoes", "paradicsom"), ("egg", "eggs", "tojas"),
]
ALIASES = {term: group for group in INGREDIENT_GROUPS for term in group}



def contains(text: str, phrase: str) -> bool:
    return f" {phrase} " in f" {text} "


def match_item(item: MenuItem, intent: SearchIntent) -> tuple[bool, list[str]]:
    # Ingredient matching deliberately uses listed ingredients only, not inferred explanations.
    ingredients = [normalize(value) for value in item.ingredients]
    for term in intent.ingredients:
        normalized = normalize(term)
        if not any(contains(value, alias) for alias in ALIASES.get(normalized, (normalized,)) for value in ingredients):
            return False, []
    if intent.name and normalize(intent.name) not in normalize(item.name): return False, []
    # Source tags are stored explicitly; optional ready explanation tags remain labeled as inferred.
    source_tags = {normalize(tag) for tag in item.tags}
    inferred = {normalize(tag) for row in item.explanations if row.status == "ready" for tag in row.tags}
    matched_inferred = []
    for tag in intent.tags:
        if normalize(tag) in source_tags: continue
        if normalize(tag) in inferred:
            matched_inferred.append(tag)
            continue
        return False, []
    return True, matched_inferred
