from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+")


@dataclass(frozen=True)
class Document:
    name: str
    text: str


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def load_documents(path: Path) -> list[Document]:
    return [
        Document(name=file_path.name, text=file_path.read_text(encoding="utf-8"))
        for file_path in sorted(path.glob("*.md"))
    ]


def retrieve_relevant_docs(
    query: str,
    documents: list[Document],
    limit: int = 3,
) -> list[Document]:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return documents[:limit]

    scored: list[tuple[float, Document]] = []
    for document in documents:
        doc_tokens = _tokenize(document.text)
        if not doc_tokens:
            continue
        overlap = len(set(query_tokens) & set(doc_tokens))
        density = overlap / math.sqrt(len(set(doc_tokens)))
        scored.append((density, document))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [document for score, document in scored if score > 0][:limit] or documents[:limit]


def build_context_snippets(documents: list[Document]) -> str:
    snippets = []
    for document in documents:
        body = " ".join(document.text.strip().split())
        snippets.append(f"[{document.name}] {body}")
    return "\n".join(snippets)

