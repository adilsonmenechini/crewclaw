import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from crewclaw.agent.tools.directory_list import DirectoryListTool
from crewclaw.agent.memory.conversation import ConversationMemory
from crewclaw.agent.loop import ReActRuntime

@pytest.mark.asyncio
async def test_directory_list_truncation():
    tool = DirectoryListTool(restrict_to_workspace=False)
    
    # Mocking iterdir to return many files
    # We need to mock entry.is_dir() to return False for files
    def mock_is_dir(entry):
        return False

    mock_files = []
    for i in range(20):
        f = MagicMock()
        f.is_dir.return_value = False
        f.name = f"file_{i}.txt"
        f.relative_to.return_value = Path(f.name)
        mock_files.append(f)
        
    with patch("pathlib.Path.iterdir", return_value=mock_files):
        with patch("pathlib.Path.is_dir", return_value=True):
            # We also need to patch Path constructor or the validation
            with patch.object(DirectoryListTool, "_validate_path", return_value=(True, "")):
                result_json = await tool.execute(path=".", max_items=10)
                result = json.loads(result_json)
                
                assert result["total_items"] == 20
                assert len(result["files"]) <= 10
                assert "truncated" in result["note"]

def test_react_runtime_new_completion_patterns():
    agent = MagicMock()
    runtime = ReActRuntime(agent)
    
    assert runtime._is_complete("FINAL ANSWER: The task is done.") is True
    assert runtime._is_complete("TERMINATE") is True
    # This should now be False because it's long and doesn't start/end with indicator
    assert runtime._is_complete("This is a long text that mentions done in the middle but is not a finish indicator.") is False
    assert runtime._is_complete("done") is True

@pytest.mark.asyncio
async def test_conversation_memory_compaction():
    # Mock database and LLM
    with patch("crewclaw.agent.memory.conversation.sqlite3"):
        with patch("crewclaw.agent.memory.conversation.create_embedder"):
            memory = ConversationMemory(db_path=":memory:")
            memory._conn = MagicMock()
            
            # Mock get_all_messages to return enough messages to trigger compaction
            long_messages = [{"id": i, "role": "user", "content": "long text " * 100} for i in range(10)]
            memory.get_all_messages = MagicMock(return_value=long_messages)
            
            # Mock get_config to have a low threshold
            with patch("crewclaw.agent.memory.conversation.get_config") as mock_config:
                mock_config.return_value.get.side_effect = lambda k, d=None: 100 if k == "memory.compaction_threshold_tokens" else d
                
                with patch("crewclaw.providers.crewai.create_crewai_llm") as mock_llm_factory:
                    mock_llm = MagicMock()
                    mock_llm.call.return_value = "Summary of conversation"
                    mock_llm_factory.return_value = mock_llm
                    
                    # Mock connection execute for deletion and insertion
                    # We need to mock the SELECT that finds IDs to delete
                    memory._conn.execute.return_value.fetchone.return_value = {"id": 1} # for deduplication check if any
                    memory._conn.execute.return_value.fetchall.return_value = [{"id": i} for i in range(1, 7)]
                    
                    memory._compact_if_needed("test_session")
                    
                    # Verify that IDs were selected for deletion
                    # Looking for DELETE FROM conversations
                    calls = memory._conn.execute.call_args_list
                    delete_called = any("DELETE FROM conversations" in str(call) for call in calls)
                    assert delete_called
