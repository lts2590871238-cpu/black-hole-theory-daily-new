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


def test_metric_affine_paper_is_included(paper_factory, topics, settings) -> None:
    paper = paper_factory(
        title_en="Gravitational waves in metric-affine gravity",
        abstract_en=(
            "We study a metric-affine theory with nonmetricity, torsion and hypermomentum. "
            "The independent connection enters the field equations, and we derive the "
            "propagating gravitational degrees of freedom and test their limits. " * 4
        ),
    )
    result = filter_paper(paper, topics, settings)
    assert result.passed
    assert "metric_affine_gravity" in result.candidate_topics


def test_palatini_paper_is_included(paper_factory, topics, settings) -> None:
    paper = paper_factory(
        title_en="Cosmological perturbations in Palatini f(R) gravity",
        abstract_en=(
            "We use the Palatini formalism to vary the metric and connection independently. "
            "The study derives the cosmological field equations and tests the perturbative "
            "solutions against the Einstein limit with controlled assumptions. " * 4
        ),
    )
    result = filter_paper(paper, topics, settings)
    assert result.passed
    assert "palatini_gravity" in result.candidate_topics


def test_modified_gravity_families_are_included(paper_factory, topics, settings) -> None:
    for family in ("Horndeski", "f(Q) gravity", "Einstein-aether"):
        paper = paper_factory(
            title_en=f"Perturbations in {family}",
            abstract_en=(
                f"We derive linearized field equations in {family} and explore "
                "their physical modes in a controlled relativistic approximation. " * 6
            ),
        )
        result = filter_paper(paper, topics, settings)
        assert result.passed
        assert "modified_gravity" in result.candidate_topics


def test_bare_mag_abbreviation_is_not_enough(paper_factory, topics, settings) -> None:
    paper = paper_factory(
        title_en="MAG observations of a magnetic plasma",
        abstract_en=(
            "The MAG instrument measures magnetic fluctuations in the plasma. "
            "We report the instrument settings and calibrate the observed signal. " * 8
        ),
    )
    result = filter_paper(paper, topics, settings)
    assert "metric_affine_gravity" not in result.candidate_topics


def test_recall_settings_are_broader(settings) -> None:
    assert settings.pipeline.since_days == 7
    assert settings.pipeline.selection_threshold == 50
    assert settings.pipeline.review_min_score == 45
    assert settings.pipeline.arxiv_page_size == 100
    assert settings.pipeline.arxiv_max_pages == 10
