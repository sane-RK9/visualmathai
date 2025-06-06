import json
import aiosqlite
from typing import Optional
from pathlib import Path
from datetime import datetime
from backend.app.models.context import LearningContext, create_session_id

# Define the database file path
# Use an environment variable or config for this in a real app
DATABASE_DIR = Path("runtime")
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = DATABASE_DIR / "context.db"

# SQL statement to create the context table
CREATE_CONTEXTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS contexts (
    session_id TEXT PRIMARY KEY,
    context_data TEXT NOT NULL, -- Store JSON representation of LearningContext
    created_at TEXT,
    updated_at TEXT
);
"""

class SQLiteContextStorage:
    """
    Handles persistence of LearningContext objects using SQLite.
    Uses aiosqlite for async database operations.
    """
    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self._connection = None # Use this to hold a single connection if needed, or open/close per operation

    async def _init_db(self):
        """Initializes the database connection and creates tables."""
        # Use a connection context manager for simple operations
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(CREATE_CONTEXTS_TABLE_SQL)
            await db.commit()
        print(f"SQLiteContextStorage initialized at {self.db_path}")

    async def save_context(self, context: LearningContext):
        """Saves or updates a context in the database."""
        context_json = context.model_dump_json() # Serialize Pydantic model to JSON string
        session_id = context.session_id
        now = datetime.now().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            # Use INSERT OR REPLACE for upsert functionality
            await db.execute(
                "INSERT OR REPLACE INTO contexts (session_id, context_data, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, context_json, context.created_at.isoformat() if hasattr(context, 'created_at') else now, now)
            )
            await db.commit()
        print(f"Context saved for session: {session_id}") 

    async def load_context(self, session_id: str) -> Optional[LearningContext]:
        """Loads a context from the database."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT context_data FROM contexts WHERE session_id = ?", (session_id,))
            row = await cursor.fetchone()
            await cursor.close()

        if row:
            context_json = row[0]
            try:
                # Deserialize JSON string back to Pydantic model
                context = LearningContext.model_validate_json(context_json)
                print(f"Context loaded for session: {session_id}") # verbose logging
                return context
            except Exception as e:
                print(f"Error loading or validating context for session {session_id}: {e}")
                # Handle corrupted data - maybe return None or a default context
                return None
        else:
            print(f"No context found for session: {session_id}") 
            return None

    async def delete_context(self, session_id: str):
        """Deletes a context from the database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM contexts WHERE session_id = ?", (session_id,))
            await db.commit()
        print(f"Context deleted for session: {session_id}")


    # Important: For a long-running application, managing the connection pool
    # for aiosqlite might be necessary instead of opening/closing per operation.
    # For simplicity here, we use the context manager which handles per-operation.

# This ensures the table exists before any operations.
async def initialize_context_storage():
     """Helper function to initialize the DB and table."""
     # Create a temporary instance just for init
     temp_storage = SQLiteContextStorage()
     await temp_storage._init_db()
