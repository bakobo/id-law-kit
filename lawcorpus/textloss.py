"""Did the words survive? The one oracle here that reads text rather than declared structure.

Every other check in this package is about **declared structure** — the sections a manifest says
are present, contiguous numbering, a non-empty extraction, a stated validity. All of them pass on
a document that quietly lost a line, because none of them ever compares what came out with what
went in. Four corpora found that hole in one round, each by diffing a word stream by hand:
`singapore-id` lost two amendment dates and two years of an amendment history, `japan-id` lost two
footnote markers and had a sentence welded out of the remains, `thailand-id` lost a standard's
number from both its cover pages, and `eu-data-law` lost 7,772 words of an instrument at the fetch
layer. See @sqxbhlk2.

Two asymmetric claims, because the evidence for them is asymmetric:

* **Removal is reported, never refused.** Cleaning a PDF removes thousands of words on purpose;
  measured over 38 documents from three corpora it removes 11,763, of which four were law. What
  made those four wrong is *why* they were dropped, and that belongs in the rules that drop them.
  `compare` hands the harvester the list, because the harvester is the one who knows what the
  document should say.
* **Fabrication is refused.** A cleaner deletes lines and joins them; it has no business minting a
  token that was in no source line. That is zero across the same 38 documents and zero by
  construction, so `refuse_fabrication` can stay switched on without ever crying wolf — the test
  @uf4epdvm set for a guard that is allowed to fire by default.

Nothing here re-renders or re-fetches anything. Both sides of the comparison are values the caller
already holds.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .errors import LawcorpusError
from .normalise import normalise_text

# Whitespace-delimited runs: the unit of meaning in a script that writes spaces between words.
WORDS = re.compile(r"\S+")
# Every non-space character, for a script that does not. Japanese rejoins wrapped lines with **no**
# separator, because it writes no inter-word space — so `WORDS` sees two tokens become one on every
# legitimate rejoin and would report a fabrication on the first line of every document.
CHARACTERS = re.compile(r"\S")


class TextLossError(LawcorpusError):
    """Text left this package carrying a word that was in none of its sources.

    `self.corrupt` rather than `input.format`: the obstacle is not the shape of what we were given
    but what we did to it, and the caller can do nothing about their end of it. Final, because the
    same input goes through the same code and comes out the same way.
    """

    code = "e.self.corrupt.text.f"


@dataclass(frozen=True)
class TextDelta:
    """What a transformation took out and what it put in, as multisets.

    Multisets rather than sets, because a running head removed from 40 pages and a year removed
    from one are the same word to a set and very different evidence.
    """

    removed: dict
    added: dict

    def any(self) -> bool:
        """Did anything change at all?"""
        return bool(self.removed or self.added)


def counts(text: str, tokens=WORDS) -> Counter:
    """The token multiset of `text`, read after normalisation.

    Normalising first is what keeps this from reporting its own vocabulary: a no-break space that
    becomes an ordinary one, or a ligature that becomes two letters, is not a word that vanished.
    Both sides of every comparison go through here, so no normalisation step can register as a
    change.
    """
    return Counter(tokens.findall(normalise_text(text)))


def compare(before: str, after: str, tokens=WORDS) -> TextDelta:
    """What `after` lost from `before`, and what it gained that `before` never had."""
    source, result = counts(before, tokens), counts(after, tokens)
    return TextDelta(removed=dict(source - result), added=dict(result - source))


def refuse_fabrication(before: str, after: str, tokens=WORDS, what: str = "this text") -> None:
    """Refuse text carrying a token that no source carried. Returns None, so it reads as an assert.

    Removals are deliberately not checked here; see the module docstring and @sqxbhlk2.
    """
    added = compare(before, after, tokens).added
    if not added:
        return None
    sample = sorted(added)[:12]
    raise TextLossError(
        f"Cleaning {what} produced {sum(added.values())} occurrences of "
        f"{len(added)} token(s) that appear nowhere in the source: "
        f"{', '.join(repr(token) for token in sample)}"
        f"{', …' if len(added) > len(sample) else ''}. A cleaner removes lines and joins them, so "
        f"it cannot invent a token — this means a step rewrote text rather than dropping it, and "
        f"the result would be stored as law that no source says. Compare the source rendering with "
        f"`lawcorpus.textloss.compare` to see the whole delta before changing anything."
    )
