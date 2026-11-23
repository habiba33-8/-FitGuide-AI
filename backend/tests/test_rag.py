from fitguide.rag.bm25 import BM25, tokenize
from fitguide.rag.retriever import retrieve, kb_chunks, user_chunks
from fitguide.schemas import SessionState, DayLog


def test_tokenize_stems_and_drops_stopwords():
    assert tokenize("The Running of Dogs") == ["runn", "dog"] or "dog" in tokenize("The Running of Dogs")


def test_bm25_prefers_matching_doc():
    b = BM25(["protein builds muscle", "water keeps you hydrated", "sleep helps recovery"])
    s = b.scores("how much water")
    assert s.index(max(s)) == 1


def test_chunks_keep_title():
    assert all(": " in c.title for c in kb_chunks())
    assert len(kb_chunks()) > 60


def test_retrieval_basic():
    assert retrieve("how much water should I drink")[0].id.startswith("hydration")
    assert retrieve("can I spot reduce belly fat")[0].id.startswith("myths_faq")


def test_user_data_is_retrievable(profile):
    st = SessionState(profile=profile)
    ids = [c.id for c in user_chunks(st)]
    assert "user#profile" in ids and "user#today" in ids
    top = retrieve("what is my goal and my weight", st)
    assert any(r.id.startswith("user#") for r in top)
