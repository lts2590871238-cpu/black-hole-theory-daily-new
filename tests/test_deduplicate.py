from theory_daily.deduplicate import deduplicate


def test_two_sources_same_paper_merge(paper_factory) -> None:
    arxiv = paper_factory()
    inspire = paper_factory(
        canonical_key="doi:10.1000/example.1",
        arxiv_id="2607.00001",
        arxiv_version=None,
        inspire_id="123",
        doi="10.1000/example.1",
        abs_url=None,
        pdf_url=None,
        inspire_url="https://inspirehep.net/literature/123",
        citation_count=7,
        source_provenance=[
            {
                "source": "inspire",
                "record_id": "123",
                "fetched_at": arxiv.updated_at,
                "url": "https://inspirehep.net/literature/123",
            }
        ],
    )
    merged = deduplicate([arxiv, inspire])
    assert len(merged) == 1
    assert merged[0].inspire_id == "123"
    assert merged[0].citation_count == 7
    assert merged[0].abstract_en == arxiv.abstract_en


def test_similar_but_different_titles_do_not_merge(paper_factory) -> None:
    first = paper_factory(
        arxiv_id=None,
        canonical_key="title:a",
        abs_url=None,
        inspire_url="https://example.invalid/1",
    )
    second = paper_factory(
        arxiv_id=None,
        canonical_key="title:b",
        title_en="Black hole thermodynamics beyond generalized entropy",
        abs_url=None,
        inspire_url="https://example.invalid/2",
    )
    assert len(deduplicate([first, second])) == 2


def test_update_version_is_marked(paper_factory) -> None:
    paper = paper_factory(arxiv_version=2, is_update=True)
    assert paper.is_update
    assert paper.arxiv_version == 2
