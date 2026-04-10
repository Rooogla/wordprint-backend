import os

import spacy

SPACY_MODEL = os.getenv("SPACY_MODEL", "de_core_news_lg")

_nlp = None

STOP_WORDS_DE = {
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer", "eines",
    "einem", "einen", "und", "oder", "aber", "doch", "sondern", "nicht", "kein",
    "keine", "keiner", "keines", "keinem", "keinen", "ich", "du", "er", "sie",
    "es", "wir", "ihr", "mich", "mir", "dich", "dir", "ihn", "ihm", "uns",
    "euch", "ihnen", "sich", "mein", "dein", "sein", "unser", "euer",
    "dieser", "diese", "dieses", "jener", "jene", "jenes", "welcher", "welche",
    "welches", "ist", "sind", "war", "waren", "wird", "werden", "wurde", "wurden",
    "hat", "haben", "hatte", "hatten", "kann", "können", "konnte", "konnten",
    "muss", "müssen", "musste", "mussten", "soll", "sollen", "sollte", "sollten",
    "will", "wollen", "wollte", "wollten", "darf", "dürfen", "durfte", "durften",
    "mag", "mögen", "mochte", "mochten", "dass", "wenn", "weil", "obwohl",
    "als", "wie", "so", "auch", "noch", "schon", "nur", "dann", "da", "dort",
    "hier", "wo", "wann", "warum", "was", "wer", "wem", "wen", "mit", "von",
    "zu", "für", "auf", "in", "an", "aus", "bei", "nach", "vor", "über",
    "unter", "zwischen", "durch", "um", "gegen", "ohne", "bis", "seit",
    "während", "wegen", "trotz", "statt", "außer", "ab", "sein", "haben",
    "werden", "sehr", "mehr", "viel", "man", "ja", "nein", "denn", "zum",
    "zur", "im", "am", "vom", "beim", "ins", "ans", "aufs", "ums",
}


def get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load(SPACY_MODEL)
    return _nlp


def process_text(text: str) -> dict:
    """Process text through spaCy and return structured token data."""
    nlp = get_nlp()
    doc = nlp(text)

    tokens = []
    for token in doc:
        if token.is_punct or token.is_space or token.like_num:
            continue
        if not token.text.strip():
            continue

        lemma = token.lemma_.lower()
        is_foreign = not token.is_alpha or (hasattr(token, "lang_") and token.lang_ != "de" and token.lang_ != "")

        # Heuristic: if word contains only ASCII and isn't common German, might be foreign
        if token.is_alpha and all(ord(c) < 128 for c in token.text):
            # Simple heuristic: if spaCy doesn't recognize it well
            if token.pos_ == "X":
                is_foreign = True

        tokens.append({
            "surface": token.text,
            "lemma": lemma,
            "pos": token.pos_,
            "is_foreign": is_foreign,
        })

    sentences = list(doc.sents)

    return {
        "tokens": tokens,
        "num_sentences": len(sentences),
        "sentence_lengths": [
            len([t for t in sent if not t.is_punct and not t.is_space])
            for sent in sentences
        ],
    }


def compute_unique_lemmas(tokens: list[dict]) -> set[str]:
    """Compute unique lemmas excluding stop words."""
    unique = set()
    for t in tokens:
        lemma = t["lemma"]
        if lemma.lower() not in STOP_WORDS_DE and len(lemma) > 1:
            unique.add(lemma)
    return unique
