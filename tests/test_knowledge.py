from backend.knowledge.graph import ensure_seeded, prerequisites_for, recommended_next_concepts


def test_prerequisites_for_logistic_regression(store):
    ensure_seeded()
    prereqs = prerequisites_for("Logistic Regression")
    names = {p["name"] for p in prereqs}
    assert "Probability" in names or "Gradient Descent" in names or "Classification" in names


def test_weak_logistic_surfaces_foundations(store):
    ensure_seeded()
    recs = recommended_next_concepts(["Logistic Regression"])
    assert recs
    assert any("Probability" in r["name"] or "Gradient" in r["name"] or "Classification" in r["name"] for r in recs)
