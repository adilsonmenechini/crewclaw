"""Health check utility for CrewClaw."""

import os
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Any

from crewclaw.config import get_config
from crewclaw.providers.llm import create_llm

def check_llm_provider(model: str | Dict[str, Any] = None) -> Dict[str, Any]:
    """Check LLM provider health by sending a minimal request.
    
    Args:
        model: Model name or config dict to check. If None, uses default from config.
        
    Returns:
        Dict with status and error message if any.
    """
    import logging
    logger = logging.getLogger("crewclaw.providers.llm")
    old_level = logger.level
    logger.setLevel(logging.CRITICAL)
    
    try:
        llm_kwargs = {}
        model_name = "default"
        
        if isinstance(model, dict):
            model_name = model.get("model", "unknown")
            if "api_key" in model:
                llm_kwargs["api_key"] = model["api_key"]
            if "api_key_env" in model:
                llm_kwargs["api_key_env"] = model["api_key_env"]
            if "base_url" in model:
                llm_kwargs["base_url"] = model["base_url"]
            model = model_name
        elif model:
            model_name = model

        llm = create_llm(model=model, **llm_kwargs)
        # We use a very simple probe message
        messages = [{"role": "user", "content": "Hello"}]
        
        start_time = time.time()
        # Using a low-token probe logic if possible, or just a simple completion
        # We don't want to waste tokens, so we use max_tokens=20 if supported
        try:
            # LiteLLM supports passing kwargs to completion
            response = llm.complete(messages, max_tokens=20)
            duration = time.time() - start_time
            return {
                "status": "ok",
                "model": llm.model,
                "latency": f"{duration:.2f}s",
                "message": "Provider responded successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "model": model_name,
                "error": str(e)
            }
    except Exception as e:
        return {
            "status": "critical",
            "model": str(model) if model else "default",
            "error": f"Failed to initialize LLM: {str(e)}"
        }
    finally:
        logger.setLevel(old_level)

def check_database() -> Dict[str, Any]:
    """Check database health and integrity."""
    config = get_config()
    db_path = config.get("project.database_path", "./workspace/memory/crewclaw.db")
    
    if not Path(db_path).exists():
        return {
            "status": "error",
            "path": db_path,
            "error": "Database file not found"
        }
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Check tables
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [t["name"] for t in tables]
        
        # Check for vector extension
        vec_loaded = False
        try:
            import sqlite_vec

            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            vec_loaded = hasattr(sqlite_vec, "load") # Minimal check if it worked
        except ImportError:
            try:
                conn.enable_load_extension(True)
                conn.execute("SELECT load_extension('vec0')")
                vec_loaded = True
            except:
                try:
                    conn.execute("SELECT load_extension('vec')")
                    vec_loaded = True
                except:
                    pass
        
        # Check vector count
        vector_count = 0
        if "vectors" in table_names:
            vector_count = conn.execute("SELECT COUNT(*) FROM vectors").fetchone()[0]
            
        conn.close()
        
        status = "ok"
        if not vec_loaded:
            status = "warning"
            
        return {
            "status": status,
            "path": db_path,
            "tables": len(table_names),
            "vectors": vector_count,
            "vector_extension": "loaded" if vec_loaded else "missing (using brute force fallback)",
            "message": "Database connected successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "path": db_path,
            "error": str(e)
        }

def check_system() -> Dict[str, Any]:
    """Check system-wide health."""
    config = get_config()
    memory_dir = config.get("project.memory_dir", "./workspace/memory")
    
    results = {
        "llm": [],
        "database": check_database(),
        "environment": {
            "memory_dir": memory_dir,
            "writable": os.access(memory_dir, os.W_OK) if os.path.exists(memory_dir) else False,
            "disk_free": "unknown" # Could add shutil.disk_usage if needed
        }
    }
    
    # Check primary LLM
    results["llm"].append(check_llm_provider())
    
    # Check fallbacks
    fallbacks = config.get("llm.fallbacks", [])
    for fb in fallbacks:
        results["llm"].append(check_llm_provider(model=fb))
        
    return results
