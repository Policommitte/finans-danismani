"""Iki asamali chunking: semantik once, recursive yalnizca tasan parcalarda.

Kural: bir chunk icin nihai metni hangi bolucu uretiyorsa yalnizca o
kaydedilir. Bir semantik parca boyut sinirini asarsa, o parca TAMAMEN
atilir ve yerine recursive_split'in urettigi 2+ alt-parca konur - ikisi
birden asla saklanmaz.

Semantik bolme bugun paragraf sinirlarini konu siniri sayan bir yer
tutucudur. Gercek embedding-benzerligi tabanli semantik bolme (LangChain'in
SemanticChunker'i gibi) da aslinda bir embedding modeli gerektirir -
Cohere embed-v4 secildigine gore bu ileride buraya baglanabilir, ama bugun
`semantic_split` hala paragraf sinirlarina dayanan basit bir yer tutucu;
gercek embedding-benzerligi ile konu-kaymasi tespiti ayri bir is. Model
tabanli versiyon yazildiginda yalnizca `semantic_split` govdesi degisir;
`chunk_document` ve cagiran taraf degismez.
"""

from __future__ import annotations

import re

DEFAULT_MAX_CHUNK_CHARS = 1000

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")


def semantic_split(text: str) -> list[str]:
    """Yer tutucu semantik bolme: paragraf sinirlarini konu siniri sayar."""
    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT_RE.split(text) if p.strip()]
    if paragraphs:
        return paragraphs
    stripped = text.strip()
    return [stripped] if stripped else []


def recursive_split(
    text: str,
    max_chars: int,
    separators: tuple[str, ...] = ("\n\n", "\n", ". ", " "),
) -> list[str]:
    """Metni, gittikce daha ince ayirici kullanarak `max_chars` alti parcalara boler."""
    if len(text) <= max_chars:
        return [text]

    if not separators:
        return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]

    sep, rest = separators[0], separators[1:]
    parts = text.split(sep)
    if len(parts) == 1:
        return recursive_split(text, max_chars, rest)

    chunks: list[str] = []
    current = ""
    for part in parts:
        candidate = f"{current}{sep}{part}" if current else part
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
        if len(part) > max_chars:
            chunks.extend(recursive_split(part, max_chars, rest))
            current = ""
        else:
            current = part

    if current:
        chunks.append(current)
    return chunks


def chunk_document(text: str, max_chars: int = DEFAULT_MAX_CHUNK_CHARS) -> list[str]:
    """Bir dokuman govdesini nihai chunk metinleri listesine cevirir.

    Once `semantic_split` calisir. Sinira uyan parcalar oldugu gibi gecer;
    tasanlar `recursive_split` ile degistirilir (oversized parca atilir).
    """
    final_chunks: list[str] = []
    for candidate in semantic_split(text):
        if len(candidate) <= max_chars:
            final_chunks.append(candidate)
        else:
            final_chunks.extend(recursive_split(candidate, max_chars))
    return final_chunks
