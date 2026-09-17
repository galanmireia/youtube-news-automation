"""The one rule about written Spanish that this project keeps having to apply.

Both voices used here - the synthesiser and the cloned one - pronounce from
the SPELLING. They do not know Spanish; they read what is written. So an
unaccented word does not come out as a slightly sloppy version of itself, it
comes out as a different word: "anos" is not "años", and "tenia" puts the
stress on the wrong syllable of "tenía".

That makes the accents a functional requirement rather than a matter of
correctness, and it applies in two places that would otherwise drift apart -
the narration a model writes for us, and any text handed straight to the
speech API, including a test phrase written by hand. It was a hand-written
test phrase that proved the point: it scored zero and said "anos" out loud.
"""
import re
import unicodedata

# Written Spanish carries an accent or an ene on roughly one word in twenty.
# Well under that means the text is effectively unaccented, whatever it looks
# like at a glance.
MIN_TASA_ACENTOS = 0.02


def tasa_de_acentos(texto: str) -> tuple[int, int, float]:
    """How much of this text carries an accent or an ene.

    Returns (accented words, words counted, the rate). Words of one or two
    letters are not counted: they are articles and prepositions, they never
    carry an accent, and including them would drag the rate down for reasons
    that have nothing to do with the spelling being right."""
    palabras = re.findall(r"[^\W\d_]{3,}", texto, re.UNICODE)
    if not palabras:
        return 0, 0, 0.0
    acentuadas = sum(
        1
        for palabra in palabras
        if any(unicodedata.combining(c) for c in unicodedata.normalize("NFD", palabra))
        or "ñ" in palabra.lower()
    )
    return acentuadas, len(palabras), acentuadas / len(palabras)
