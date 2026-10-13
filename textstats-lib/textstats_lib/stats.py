import re


def analyze_text(text: str):
    stripped_text = text.strip()

    if stripped_text:
        sentence_count = max(
            1,
            len(re.findall(r"[.!?]+", stripped_text)),
        )
    else:
        sentence_count = 0

    return {
        "word_count": len(text.split()),
        "character_count": len(text),
        "sentence_count": sentence_count,
    }
