from theory_daily.deterministic_filter import filter_paper


def test_withdrawn_notice_is_filtered(paper_factory, topics, settings) -> None:
    paper = paper_factory(title_en="Withdrawn by the authors: Black hole thermodynamics")
    result = filter_paper(paper, topics, settings)
    assert not result.passed
    assert any("排除项" in reason for reason in result.reasons)


def test_holographic_display_is_low_relevance(paper_factory, topics, settings) -> None:
    paper = paper_factory(
        title_en="A holographic display for engineering",
        abstract_en=(
            "We present a holographic display and holographic imaging device for optical storage. "
            * 8
        ),
        categories=["cond-mat.str-el"],
    )
    result = filter_paper(paper, topics, settings)
    assert not result.passed
    assert "holographic display" in result.negative_hits


def test_holographic_superconductor_is_kept(paper_factory, topics, settings) -> None:
    paper = paper_factory(
        title_en="Holographic superconductor transport at a quantum critical point",
        abstract_en=(
            "We calculate holographic superconductor transport near a quantum critical transition. "
            * 8
        ),
        categories=["hep-th"],
    )
    result = filter_paper(paper, topics, settings)
    assert result.passed
    assert "holography_condensed_matter" in result.candidate_topics


def test_bare_pta_abbreviation_is_ambiguous(paper_factory, topics, settings) -> None:
    paper = paper_factory(
        title_en="A PTA method for polymer transfer analysis",
        abstract_en=(
            "This PTA protocol characterizes polymer transfer analysis in a laboratory. " * 10
        ),
        categories=["cond-mat.str-el"],
    )
    result = filter_paper(paper, topics, settings)
    assert not result.passed
    assert any("缩写" in reason for reason in result.reasons)


def test_pta_is_found_from_abstract_context_without_title_acronym(
    paper_factory, topics, settings
) -> None:
    paper = paper_factory(
        title_en="Correlated red processes in millisecond-pulsar observations",
        abstract_en=(
            "We compare common red noise and quadrupolar spatial correlations across "
            "millisecond pulsars. The timing analysis tests a nanohertz gravitational-wave "
            "background while marginalizing over clock error and Solar System ephemeris "
            "uncertainty. The method derives an angular correlation estimator and validates "
            "it on simulated timing residuals. " * 3
        ),
        categories=["astro-ph.HE"],
    )
    result = filter_paper(paper, topics, settings)
    assert result.passed
    assert "pta" in result.candidate_topics
    assert "millisecond pulsar" in result.medium_weight_hits
    assert "quadrupolar spatial correlation" in result.high_weight_hits


def test_recall_settings_are_broader(settings) -> None:
    assert settings.pipeline.since_days == 7
    assert settings.pipeline.selection_threshold == 65
    assert settings.pipeline.review_min_score == 60
    assert settings.pipeline.arxiv_page_size == 200
    assert settings.pipeline.arxiv_max_pages == 5
