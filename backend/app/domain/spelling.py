import re

_BRITISH_ONLY = [
    "colour", "favour", "honour", "behaviour", "labour", "neighbour", "flavour", "harbour",
    "centre", "metre", "theatre", "litre", "fibre", "calibre",
    "organise", "organised", "organising", "recognise", "recognised", "realise", "realised",
    "analyse", "analysed", "apologise", "criticise", "emphasise", "minimise", "maximise",
    "defence", "offence", "licence", "pretence",
    "travelled", "travelling", "cancelled", "cancelling", "modelling", "labelled",
    "catalogue", "dialogue",
    "fertiliser", "fertilisers", "grey", "tyre", "aluminium", "mould",
]
_AMERICAN_ONLY = [
    "color", "favor", "honor", "behavior", "labor", "neighbor", "flavor", "harbor",
    "center", "meter", "theater", "liter", "fiber", "caliber",
    "organize", "organized", "organizing", "recognize", "recognized", "realize", "realized",
    "analyze", "analyzed", "apologize", "criticize", "emphasize", "minimize", "maximize",
    "defense", "offense", "license", "pretense",
    "traveled", "traveling", "canceled", "canceling", "modeling", "labeled",
    "catalog", "dialog",
    "fertilizer", "fertilizers", "gray", "tire", "aluminum", "mold",
]

_BRITISH_RE = re.compile(r"\b(" + "|".join(_BRITISH_ONLY) + r")\b", re.IGNORECASE)
_AMERICAN_RE = re.compile(r"\b(" + "|".join(_AMERICAN_ONLY) + r")\b", re.IGNORECASE)


# ponytail: word-list heuristic over a curated ~40-word lexicon of unambiguous British/American
# spelling pairs, not a full locale classifier. Good enough to bias the rewrite prompt toward
# whichever convention already dominates the document; upgrade to a proper dictionary-backed
# detector (e.g. pyenchant with both dictionaries) if precision on short/mixed documents matters.
def detect_spelling_variant(text: str) -> str | None:
    """Returns "British English", "American English", or None if the signal is absent or tied."""
    british = len(_BRITISH_RE.findall(text))
    american = len(_AMERICAN_RE.findall(text))
    if british == american:
        return None
    return "British English" if british > american else "American English"
