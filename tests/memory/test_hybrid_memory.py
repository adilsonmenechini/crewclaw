import pytest
from crewclaw.agent.memory.conversation import ConversationMemory


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_conversations.db"
    return str(db_path)


@pytest.fixture
def memory(temp_db):
    mem = ConversationMemory(db_path=temp_db)
    yield mem
    mem.close()


def test_add_and_retrieve_messages(memory):
    session_id = "test_session_1"
    memory.add_message(session_id, "user", "Hello agent")
    memory.add_message(session_id, "assistant", "Hello user, how can I help?")

    messages = memory.get_all_messages(session_id)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_deduplication(memory):
    session_id = "test_session_2"
    content = "This is a unique message"

    added1 = memory.add_message(session_id, "user", content)
    added2 = memory.add_message(session_id, "user", content)

    assert added1 is True
    assert added2 is False

    messages = memory.get_all_messages(session_id)
    assert len(messages) == 1


def test_summary_and_vector_persistence(memory):
    session_id = "test_session_3"
    summary = "The user asked for help with testing."

    memory.save_summary(session_id, summary)

    saved_summary = memory.get_summary(session_id)
    assert saved_summary == summary

    # Check if vector was actually inserted (indirectly via count if we don't want to mock too much)
    assert memory.vector_store.count() > 0


def test_context_retrieval_between_sessions(memory):
    # Session 1
    session_1 = "session_1"
    memory.save_summary(session_1, "User likes Python.")

    # Session 2
    session_2 = "session_2"
    context = memory.get_context_for_new_session(session_2)

    assert len(context) > 0
    assert "User likes Python" in context[0]["content"]


def test_hybrid_search_functionality(memory):
    # This test assumes sqlite-vec is available or falls back to brute force
    # We add a summary and search for it correctly
    session_id = "search_session"
    memory.save_summary(session_id, "The secret recipe for cake is chocolate.")

    # Search for something related
    context = memory.get_context_for_new_session("new_session", query="cake recipe")

    assert len(context) > 0
    assert "secret recipe" in context[0]["content"].lower()
