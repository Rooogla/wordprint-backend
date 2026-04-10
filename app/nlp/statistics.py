from collections import Counter

from .pipeline import STOP_WORDS_DE, compute_unique_lemmas, process_text

POS_LABELS_DE = {
    "NOUN": "Substantive",
    "VERB": "Verben",
    "ADJ": "Adjektive",
    "ADV": "Adverbien",
}

CONTENT_POS = {"NOUN", "VERB", "ADJ", "ADV", "PROPN"}
TECHNICAL_THRESHOLD = 5  # per 100k tokens


def compute_statistics(text: str) -> tuple[dict, list[dict], int]:
    """
    Compute full statistics for a text.
    Returns (statistics_dict, word_records, wordprint_score).
    """
    result = process_text(text)
    tokens = result["tokens"]
    num_sentences = result["num_sentences"]
    sentence_lengths = result["sentence_lengths"]

    if not tokens:
        empty_stats = {
            "wordprint_score": 0,
            "total_tokens": 0,
            "total_sentences": 0,
            "avg_sentence_length": 0,
            "avg_word_length": 0,
            "lexical_density": 0,
            "unique_lemmas": 0,
            "hapax_legomena": 0,
            "by_pos": {"detailed": {}, "simplified": {}},
            "foreign_words": {"count": 0, "words": []},
            "technical_words": {"count": 0, "words": []},
            "top_words": [],
            "top_lemmas": [],
            "pos_ratio": {"content_words": 0, "function_words": 0},
        }
        return empty_stats, [], 0

    total_tokens = len(tokens)

    # Unique lemmas (excluding stop words)
    unique_lemmas = compute_unique_lemmas(tokens)
    wordprint_score = len(unique_lemmas)

    # POS distribution
    pos_counter = Counter(t["pos"] for t in tokens)
    detailed_pos = {}
    for pos in ["NOUN", "VERB", "ADJ", "ADV", "PROPN"]:
        if pos in pos_counter:
            detailed_pos[pos] = pos_counter[pos]
    other_count = sum(c for p, c in pos_counter.items() if p not in detailed_pos)
    if other_count:
        detailed_pos["OTHER"] = other_count

    simplified_pos = {}
    for pos, count in pos_counter.items():
        label = POS_LABELS_DE.get(pos, "Sonstiges")
        simplified_pos[label] = simplified_pos.get(label, 0) + count

    # Lemma frequency
    lemma_counter = Counter(t["lemma"] for t in tokens)

    # Hapax legomena (lemmas appearing exactly once)
    hapax = sum(1 for lemma, count in lemma_counter.items()
                if count == 1 and lemma not in STOP_WORDS_DE)

    # Surface form frequency
    surface_counter = Counter((t["surface"], t["lemma"], t["pos"]) for t in tokens)

    # Top words by surface form
    top_words = []
    for (surface, lemma, pos), count in surface_counter.most_common(20):
        top_words.append({
            "surface": surface,
            "lemma": lemma,
            "pos": pos,
            "count": count,
        })

    # Top lemmas
    lemma_pos = {}
    for t in tokens:
        if t["lemma"] not in lemma_pos:
            lemma_pos[t["lemma"]] = t["pos"]
    top_lemmas = []
    for lemma, count in lemma_counter.most_common(20):
        top_lemmas.append({
            "lemma": lemma,
            "pos": lemma_pos.get(lemma, ""),
            "total_count": count,
        })

    # Foreign words
    foreign_words = list({t["surface"] for t in tokens if t["is_foreign"]})

    # Technical words heuristic: low frequency NOUN with capitalization
    technical_words = []
    for t in tokens:
        if (t["pos"] == "NOUN"
                and t["surface"][0].isupper()
                and lemma_counter[t["lemma"]] <= TECHNICAL_THRESHOLD
                and t["lemma"] not in STOP_WORDS_DE
                and not t["is_foreign"]):
            technical_words.append(t["surface"])
    technical_words = list(set(technical_words))

    # Lexical density
    content_count = sum(1 for t in tokens if t["pos"] in CONTENT_POS)
    lexical_density = round(content_count / total_tokens, 2) if total_tokens else 0

    # Average values
    avg_sentence_length = round(sum(sentence_lengths) / len(sentence_lengths), 1) if sentence_lengths else 0
    avg_word_length = round(sum(len(t["surface"]) for t in tokens) / total_tokens, 1) if total_tokens else 0

    # POS ratio
    function_count = total_tokens - content_count
    pos_ratio = {
        "content_words": round(content_count / total_tokens, 2) if total_tokens else 0,
        "function_words": round(function_count / total_tokens, 2) if total_tokens else 0,
    }

    statistics = {
        "wordprint_score": wordprint_score,
        "total_tokens": total_tokens,
        "total_sentences": num_sentences,
        "avg_sentence_length": avg_sentence_length,
        "avg_word_length": avg_word_length,
        "lexical_density": lexical_density,
        "unique_lemmas": wordprint_score,
        "hapax_legomena": hapax,
        "by_pos": {
            "detailed": detailed_pos,
            "simplified": simplified_pos,
        },
        "foreign_words": {
            "count": len(foreign_words),
            "words": sorted(foreign_words),
        },
        "technical_words": {
            "count": len(technical_words),
            "words": sorted(technical_words),
        },
        "top_words": top_words,
        "top_lemmas": top_lemmas,
        "pos_ratio": pos_ratio,
    }

    # Build word records for DB
    word_records = []
    lemma_surface_seen = {}
    for t in tokens:
        key = (t["lemma"], t["pos"])
        if key not in lemma_surface_seen:
            lemma_surface_seen[key] = {
                "surface_form": t["surface"],
                "lemma": t["lemma"],
                "pos_tag": t["pos"],
                "frequency": 0,
                "is_foreign": t["is_foreign"],
                "is_technical": t["surface"] in technical_words,
            }
        lemma_surface_seen[key]["frequency"] += 1

    word_records = list(lemma_surface_seen.values())

    return statistics, word_records, wordprint_score
