"""
Integration test for database tools example workflow.

This test converts the example.py workflow into a proper unit test that validates
the entire flow of operations in sequence.
"""
import os
import tempfile
import pytest
import pandas as pd
from sqlalchemy import create_engine, text

from src.server.tools.database_tools.database_tools import DatabaseTools


class TestDatabaseToolsExample:
    """Integration tests for DatabaseTools example workflow."""
    
    @pytest.fixture
    def temp_db_file(self):
        """Create a temporary SQLite database file for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Create an SQLite database
        engine = create_engine(f"sqlite:///{path}")
        with engine.connect() as conn:
            # Create test tables
            conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)"))
            conn.execute(text("CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, content TEXT, FOREIGN KEY(user_id) REFERENCES users(id))"))
            
            # Insert test data
            conn.execute(text("INSERT INTO users (name, email) VALUES ('John Doe', 'john@example.com')"))
            conn.execute(text("INSERT INTO users (name, email) VALUES ('Jane Smith', 'jane@example.com')"))
            conn.execute(text("INSERT INTO posts (user_id, title, content) VALUES (1, 'First Post', 'Hello World')"))
            conn.execute(text("INSERT INTO posts (user_id, title, content) VALUES (2, 'Introduction', 'Nice to meet you')"))
            conn.commit()
        
        yield path
        
        # Cleanup
        if os.path.exists(path):
            os.unlink(path)
    
    @pytest.fixture
    def db_tools(self, temp_db_file):
        """Create a DatabaseTools instance for testing."""
        connection_string = f"sqlite:///{temp_db_file}"
        db_tools = DatabaseTools(connection_string)
        return db_tools
    
    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing."""
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "database_config.json")
        
        yield config_path
        
        # Cleanup
        if os.path.exists(config_path):
            os.unlink(config_path)
        os.rmdir(temp_dir)
    
    def test_database_example_workflow(self, db_tools, temp_db_file, temp_config_file, monkeypatch, tmpdir):
        """Test the complete database example workflow."""
        # Override the config file path
        monkeypatch.setattr(db_tools, "_config_file", temp_config_file)
        
        # Step 1: Test connection
        connection_result = db_tools.test_connection()
        assert connection_result["status"] == "success"
        assert connection_result["message"] == "Connection successful"
        assert connection_result["database_type"] == "sqlite"
        
        # Step 2: List tables
        tables_result = db_tools.list_tables()
        assert tables_result["status"] == "success"
        assert "schemas" in tables_result
        
        # For SQLite, the schema is usually called "main"
        main_schema = list(tables_result["schemas"].keys())[0]
        assert "users" in tables_result["schemas"][main_schema]
        assert "posts" in tables_result["schemas"][main_schema]
        
        # Step 3: Get table schema
        schema_result = db_tools.get_table_schema("users")
        assert schema_result["status"] == "success"
        assert schema_result["table_name"] == "users"
        assert len(schema_result["columns"]) == 3
        
        column_names = [col["name"] for col in schema_result["columns"]]
        assert "id" in column_names
        assert "name" in column_names
        assert "email" in column_names
        
        # Step 4: Get table preview
        preview_result = db_tools.get_table_preview("users")
        assert preview_result["status"] == "success"
        assert preview_result["row_count"] == 2
        assert len(preview_result["results"]) == 2
        
        # Step 5: Execute a simple query
        query = "SELECT * FROM users WHERE name LIKE :name_pattern"
        params = {"name_pattern": "J%"}
        query_result = db_tools.execute_query(query, params)
        
        assert query_result["status"] == "success"
        assert query_result["row_count"] == 2
        assert len(query_result["results"]) == 2
        
        # Verify both John and Jane are in the results
        user_names = [user["name"] for user in query_result["results"]]
        assert "John Doe" in user_names
        assert "Jane Smith" in user_names
        
        # Step 6: Execute a transaction
        queries = [
            "INSERT INTO users (name, email) VALUES (:name, :email)",
            "SELECT * FROM users WHERE name = :name"
        ]
        
        params_list = [
            {"name": "Bob Johnson", "email": "bob@example.com"},
            {"name": "Bob Johnson"}
        ]
        
        transaction_result = db_tools.execute_transaction(queries, params_list)
        
        assert transaction_result["status"] == "success"
        assert transaction_result["query_count"] == 2
        
        # First query (INSERT) should have affected 1 row
        assert transaction_result["results"][0]["row_count"] == 1
        
        # Second query (SELECT) should have returned 1 row
        assert transaction_result["results"][1]["row_count"] == 1
        assert transaction_result["results"][1]["results"][0]["name"] == "Bob Johnson"
        assert transaction_result["results"][1]["results"][0]["email"] == "bob@example.com"
        
        # Step 7: Get row count
        row_count_result = db_tools.get_table_row_count("users")
        
        assert row_count_result["status"] == "success"
        assert row_count_result["table_name"] == "users"
        assert row_count_result["row_count"] == 3  # Now 3 users after adding Bob
        
        # Step 8: Execute a join query
        join_query = """
        SELECT u.name, p.title, p.content
        FROM users u
        JOIN posts p ON u.id = p.user_id
        """
        join_result = db_tools.execute_query(join_query)
        
        assert join_result["status"] == "success"
        assert join_result["row_count"] == 2
        
        # Verify join results
        for result in join_result["results"]:
            if result["name"] == "John Doe":
                assert result["title"] == "First Post"
                assert result["content"] == "Hello World"
            elif result["name"] == "Jane Smith":
                assert result["title"] == "Introduction"
                assert result["content"] == "Nice to meet you"
        
        # Step 9: Export query results
        export_path = os.path.join(tmpdir, "users.csv")
        export_result = db_tools.export_query_results(
            "SELECT * FROM users", 
            file_path=export_path, 
            format="csv"
        )
        
        assert export_result["status"] == "success"
        assert export_result["row_count"] == 3
        assert os.path.exists(export_path)
        
        # Check the exported file
        df = pd.read_csv(export_path)
        assert len(df) == 3
        assert "Bob Johnson" in df["name"].values
        
        # Step 10: Export results in memory
        memory_export_result = db_tools.export_query_results(
            "SELECT * FROM users", 
            format="csv"
        )
        
        assert memory_export_result["status"] == "success"
        assert memory_export_result["row_count"] == 3
        assert "data" in memory_export_result
        assert "Bob Johnson" in memory_export_result["data"]
        
        # Step 11: Save connection to config
        save_result = db_tools.save_connection("example_sqlite", f"sqlite:///{temp_db_file}")
        
        assert save_result["status"] == "success"
        assert save_result["message"] == "Connection 'example_sqlite' saved successfully"
        
        # Step 12: List saved connections
        list_result = db_tools.list_saved_connections()
        
        assert list_result["status"] == "success"
        assert "example_sqlite" in list_result["connections"]
        
        # Step 13: Delete the connection
        delete_result = db_tools.delete_saved_connection("example_sqlite")
        
        assert delete_result["status"] == "success"
        assert delete_result["message"] == "Connection 'example_sqlite' deleted successfully"
        
        # Step 14: Verify connection was deleted
        final_list_result = db_tools.list_saved_connections()
        
        assert final_list_result["status"] == "success"
        assert "example_sqlite" not in final_list_result["connections"] 