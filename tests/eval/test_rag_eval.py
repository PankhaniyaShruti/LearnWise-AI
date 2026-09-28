from tests.eval.rag_eval import evaluate_retrieval


def test_eval_retrieval_runs():
    metrics = evaluate_retrieval()
    assert metrics["n"] == 3
    assert metrics["hit_at_1"] >= 0.99
    assert metrics["mrr"] >= 0.99
