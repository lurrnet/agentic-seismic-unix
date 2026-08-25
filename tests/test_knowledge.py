from knowledge.su_docs import SUDocKnowledgeBase


def test_supef_retrieval():
    kb = SUDocKnowledgeBase()
    docs = kb.retrieve('Explain predictive deconvolution minlag and maxlag')
    assert docs
    assert docs[0]['command'] == 'supef'


def test_irrelevant_query_returns_no_docs():
    kb = SUDocKnowledgeBase()
    assert kb.retrieve('hello there') == []
