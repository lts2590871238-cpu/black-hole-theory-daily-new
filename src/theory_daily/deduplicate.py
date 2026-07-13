"""Conservative cross-source deduplication."""

from __future__ import annotations

from collections import defaultdict

from theory_daily.models import NormalizedPaper
from theory_daily.normalize import normalize_doi, normalized_title


class _DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, index: int) -> int:
        while self.parent[index] != index:
            self.parent[index] = self.parent[self.parent[index]]
            index = self.parent[index]
        return index

    def union(self, left: int, right: int) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def _merge(group: list[NormalizedPaper]) -> NormalizedPaper:
    arxiv = next((paper for paper in group if paper.abs_url is not None), None)
    inspire = next((paper for paper in group if paper.inspire_id is not None), None)
    base = (arxiv or group[0]).model_copy(deep=True)
    base.source_provenance = [item for paper in group for item in paper.source_provenance]
    if arxiv:
        base.abstract_en = arxiv.abstract_en
        base.title_en = arxiv.title_en
        base.categories = arxiv.categories
        base.arxiv_id = arxiv.arxiv_id
        base.arxiv_version = arxiv.arxiv_version
        base.abs_url = arxiv.abs_url
        base.pdf_url = arxiv.pdf_url
        base.is_update = arxiv.is_update
        base.journal_ref = arxiv.journal_ref
    if inspire:
        base.inspire_id = inspire.inspire_id
        base.inspire_url = inspire.inspire_url
        base.citation_count = inspire.citation_count
        base.citation_count_without_self_citations = inspire.citation_count_without_self_citations
        base.publication_info = inspire.publication_info
        base.document_types = inspire.document_types
    base.doi = next((paper.doi for paper in group if paper.doi), None)
    base.authors = max((paper.authors for paper in group), key=len)
    base.submitted_at = min(paper.submitted_at for paper in group)
    base.updated_at = max(paper.updated_at for paper in group)
    return base


def deduplicate(papers: list[NormalizedPaper]) -> list[NormalizedPaper]:
    """Merge exact identifiers/titles, never fuzzy-match merely similar titles."""

    sets = _DisjointSet(len(papers))
    indexes: dict[tuple[str, str], int] = {}
    for index, paper in enumerate(papers):
        keys: list[tuple[str, str]] = []
        if paper.arxiv_id:
            keys.append(("arxiv", paper.arxiv_id.lower()))
        doi = normalize_doi(paper.doi)
        if doi:
            keys.append(("doi", doi))
        keys.append(("title", normalized_title(paper.title_en)))
        for key in keys:
            previous = indexes.get(key)
            if previous is not None:
                sets.union(previous, index)
            else:
                indexes[key] = index
    groups: dict[int, list[NormalizedPaper]] = defaultdict(list)
    for index, paper in enumerate(papers):
        groups[sets.find(index)].append(paper)
    return [_merge(group) for group in groups.values()]
