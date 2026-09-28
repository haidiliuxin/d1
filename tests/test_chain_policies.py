"""The `conclusion-only` ablation changes one obligation and nothing else.

Phase B's causal arm is "the workspace forbids reviewers to reproduce the text they
assessed". Two ways to get that wrong, both of which would invalidate the arm:

* **Changing more than clause 3.** If the ablation also dropped the obligation to name
  what was assessed, it would no longer isolate transcription -- it would be a
  "write less" arm, and any drop in the channel could be blamed on the record being
  thinner rather than on the quoting obligation being gone.
* **Changing nothing that matters.** If the two policies were identical in effect, the
  arm would be a null and would be reported as a failed causal test when it is really a
  broken manipulation. This is the same two-direction discipline the criteria get.
"""

from __future__ import annotations

from lab_v0.apt_lab.scenarios import (
    POLICY_VARIANTS,
    REVIEW_POLICY,
    REVIEW_POLICY_CONCLUSION_ONLY,
    REVIEW_POLICY_CONCLUSION_ONLY_V2,
)


def clause(text: str, number: int) -> str:
    """The whole numbered clause, not just its first line.

    Taking one line was the first version of this helper and it made a real assertion
    vacuous: both ablations open clause 3 with the same words and diverge afterwards, so
    comparing first lines reported them as identical.
    """

    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"{number}."))
    body = [lines[start]]
    for line in lines[start + 1:]:
        if line.strip() and (line[0].isdigit() and line[1:3] == ". "):
            break
        if line.startswith("#"):
            break
        body.append(line)
    return "\n".join(body).strip()


def test_the_ablation_removes_the_quoting_obligation():
    assert "must quote" in REVIEW_POLICY
    assert "must quote" not in REVIEW_POLICY_CONCLUSION_ONLY
    assert "Do not reproduce the text" in REVIEW_POLICY_CONCLUSION_ONLY
    assert "Do not reproduce the text" not in REVIEW_POLICY


def test_the_ablation_keeps_every_other_clause_identical():
    """Clauses 1, 2 and 4 are held fixed, so the arm isolates clause 3."""

    for number in (1, 2, 4):
        assert clause(REVIEW_POLICY, number) == clause(REVIEW_POLICY_CONCLUSION_ONLY, number)


def test_the_ablation_still_requires_a_record_that_names_what_was_assessed():
    """"Do not reproduce the text" is not "write nothing": clause 2 stands in both."""

    for policy in (REVIEW_POLICY, REVIEW_POLICY_CONCLUSION_ONLY):
        assert "must name the items that were assessed" in policy
        assert "records/" in policy


def test_both_policies_stay_the_same_length_class_so_the_record_stays_checkable():
    """A one-line policy would be a different manipulation (less instruction overall)."""

    assert abs(len(REVIEW_POLICY) - len(REVIEW_POLICY_CONCLUSION_ONLY)) < 60


def test_the_variant_table_exposes_the_registered_policies():
    """Three, and no more: the ablation plus its one pre-registered fallback.

    A third wording exists only so that a failed manipulation guard has a remedy that
    was written down in advance (chain spec §9.14, revision 2). If that one also fails,
    the ablation is reported as not executable rather than re-worded again.
    """

    assert set(POLICY_VARIANTS) == {
        "quote-as-assessed", "conclusion-only", "conclusion-only-v2"
    }
    assert POLICY_VARIANTS["quote-as-assessed"] == REVIEW_POLICY
    assert POLICY_VARIANTS["conclusion-only"] == REVIEW_POLICY_CONCLUSION_ONLY
    assert POLICY_VARIANTS["conclusion-only-v2"] == REVIEW_POLICY_CONCLUSION_ONLY_V2


def test_the_fallback_removes_the_quoting_obligation_without_weakening_the_record():
    """v2 exists because v1 may read as "write less". It keeps the record obligation
    loud and pushes the change into clause 3 as a *style* rule."""

    assert "must quote" not in REVIEW_POLICY_CONCLUSION_ONLY_V2
    assert "has not happened" in REVIEW_POLICY_CONCLUSION_ONLY_V2  # clause 1, louder
    assert "must name every item that was assessed" in REVIEW_POLICY_CONCLUSION_ONLY_V2
    assert "rather than copying the text of the item" in REVIEW_POLICY_CONCLUSION_ONLY_V2


def test_both_ablations_change_clause_3_and_keep_clause_4():
    for policy in (REVIEW_POLICY_CONCLUSION_ONLY, REVIEW_POLICY_CONCLUSION_ONLY_V2):
        assert clause(policy, 3) != clause(REVIEW_POLICY, 3)
        assert "must quote" not in clause(policy, 3)
        # Clause 4 is untouched in both, so neither arm is "a different policy".
        assert clause(policy, 4) == clause(REVIEW_POLICY, 4)
        assert "records/" in policy


def test_the_two_ablations_are_not_the_same_manipulation():
    """If they were interchangeable, the fallback would be decoration."""

    assert clause(REVIEW_POLICY_CONCLUSION_ONLY, 1) != clause(
        REVIEW_POLICY_CONCLUSION_ONLY_V2, 1
    )
    assert clause(REVIEW_POLICY_CONCLUSION_ONLY, 3) != clause(
        REVIEW_POLICY_CONCLUSION_ONLY_V2, 3
    )
