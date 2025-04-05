"""
Tests for database tools for Cerebrum.
"""
import os
import json
import pytest
import tempfile
import pandas as pd
from sqlalchemy import create_engine, text
from src.server.tools.database_tools.database_tools import DatabaseTools

class TestDatabaseTools:
    """Tests for the DatabaseTools class."""
    
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
        os.unlink(path)
    
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
    
    @pytest.fixture
    def db_tools(self, temp_db_file):
        """Create a DatabaseTools instance for testing."""
        connection_string = f"sqlite:///{temp_db_file}"
        db_tools = DatabaseTools(connection_string)
        return db_tools
    
    def test_init(self, temp_db_file):
        """Test the initialization of the DatabaseTools class."""
        connection_string = f"sqlite:///{temp_db_file}"
        db_tools = DatabaseTools(connection_string)
        
        assert db_tools.connection_string == connection_string
        assert db_tools._engine is not None
        assert db_tools._metadata is not None
    
    def test_list_tables(self, db_tools):
        """Test listing tables in the database."""
        result = db_tools.list_tables()
        
        assert result["status"] == "success"
        assert "schemas" in result
        
        # For SQLite, the schema is usually called "main"
        main_schema = list(result["schemas"].keys())[0]
        assert len(result["schemas"][main_schema]) >= 2
        assert "users" in result["schemas"][main_schema]
        assert "posts" in result["schemas"][main_schema]
    
    def test_get_table_schema(self, db_tools):
        """Test getting the schema of a table."""
        result = db_tools.get_table_schema("users")
        
        assert result["status"] == "success"
        assert result["table_name"] == "users"
        
        # Check column information
        assert len(result["columns"]) == 3
        column_names = [col["name"] for col in result["columns"]]
        assert "id" in column_names
        assert "name" in column_names
        assert "email" in column_names
        
        # Check primary key information
        assert len(result["primary_keys"]["constrained_columns"]) == 1
        assert "id" in result["primary_keys"]["constrained_columns"]
    
    def test_execute_query(self, db_tools):
        """Test executing a query."""
        query = "SELECT * FROM users WHERE name = :name"
        params = {"name": "John Doe"}
        
        result = db_tools.execute_query(query, params)
        
        assert result["status"] == "success"
        assert result["row_count"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["name"] == "John Doe"
        assert result["results"][0]["email"] == "john@example.com"
    
    def test_execute_transaction(self, db_tools):
        """Test executing a transaction with multiple queries."""
        queries = [
            "INSERT INTO users (name, email) VALUES (:name, :email)",
            "SELECT * FROM users WHERE name = :name"
        ]
        
        params_list = [
            {"name": "Test User", "email": "test@example.com"},
            {"name": "Test User"}
        ]
        
        result = db_tools.execute_transaction(queries, params_list)
        
        assert result["status"] == "success"
        assert result["query_count"] == 2
        
        # First query (INSERT) should have affected 1 row
        assert result["results"][0]["row_count"] == 1
        
        # Second query (SELECT) should have returned 1 row
        assert result["results"][1]["row_count"] == 1
        assert result["results"][1]["results"][0]["name"] == "Test User"
        assert result["results"][1]["results"][0]["email"] == "test@example.com"
    
    def test_get_table_preview(self, db_tools):
        """Test getting a preview of table data."""
        result = db_tools.get_table_preview("users", limit=5)
        
        assert result["status"] == "success"
        assert result["row_count"] >= 2  # We inserted 2 users in the fixture
        assert len(result["results"]) >= 2
        
        # Check that expected columns are present
        assert "id" in result["results"][0]
        assert "name" in result["results"][0]
        assert "email" in result["results"][0]
    
    def test_get_table_row_count(self, db_tools):
        """Test getting the row count of a table."""
        result = db_tools.get_table_row_count("users")
        
        assert result["status"] == "success"
        assert result["table_name"] == "users"
        assert result["row_count"] >= 2  # We inserted 2 users in the fixture
    
    def test_export_query_results(self, db_tools, tmpdir):
        """Test exporting query results to a file."""
        query = "SELECT * FROM users"
        export_path = os.path.join(tmpdir, "users.csv")
        
        result = db_tools.export_query_results(query, file_path=export_path, format="csv")
        
        assert result["status"] == "success"
        assert result["row_count"] >= 2
        assert os.path.exists(export_path)
        
        # Check the exported file
        df = pd.read_csv(export_path)
        assert len(df) >= 2
        assert "name" in df.columns
        assert "email" in df.columns
    
    def test_convert_jdbc_to_sqlalchemy(self, db_tools):
        """Test converting JDBC connection strings to SQLAlchemy format."""
        # Test MySQL
        jdbc_url = "jdbc:mysql://localhost:3306/mydb?user=root&password=secret"
        sa_url = db_tools._convert_jdbc_to_sqlalchemy(jdbc_url)
        assert sa_url.startswith("mysql+pymysql://")
        
        # Test PostgreSQL
        jdbc_url = "jdbc:postgresql://localhost:5432/mydb?user=postgres&password=secret"
        sa_url = db_tools._convert_jdbc_to_sqlalchemy(jdbc_url)
        assert sa_url.startswith("postgresql+psycopg2://")
        
        # Test SQLite
        jdbc_url = "jdbc:sqlite:mydb.db"
        sa_url = db_tools._convert_jdbc_to_sqlalchemy(jdbc_url)
        assert sa_url == "sqlite:mydb.db"
    
    def test_save_and_load_connection(self, db_tools, temp_config_file, monkeypatch):
        """Test saving and loading connection strings."""
        # Override the config file path
        monkeypatch.setattr(db_tools, "_config_file", temp_config_file)
        
        # Save a connection
        db_tools.save_connection("test_conn", "jdbc:sqlite:test.db")
        
        # Check that the file was created
        assert os.path.exists(temp_config_file)
        
        # Load the config and check the connection was saved
        with open(temp_config_file, 'r') as f:
            config = json.load(f)
        
        assert "test_conn" in config
        assert config["test_conn"] == "jdbc:sqlite:test.db"
        
        # List saved connections
        result = db_tools.list_saved_connections()
        assert result["status"] == "success"
        assert "test_conn" in result["connections"]
        
        # Delete the connection
        result = db_tools.delete_saved_connection("test_conn")
        assert result["status"] == "success"
        
        # Check it was deleted
        with open(temp_config_file, 'r') as f:
            config = json.load(f)
        
        assert "test_conn" not in config
    
    def test_test_connection(self, db_tools, temp_db_file):
        """Test the connection testing functionality."""
        connection_string = f"sqlite:///{temp_db_file}"
        
        # Test the current connection
        result = db_tools.test_connection()
        assert result["status"] == "success"
        assert result["message"] == "Connection successful"
        assert result["database_type"] == "sqlite"
        
        # Test a new connection
        result = db_tools.test_connection(connection_string)
        assert result["status"] == "success"
        assert result["message"] == "Connection successful"
        assert result["database_type"] == "sqlite"
        
        # Test an invalid connection - Use an invalid protocol to guarantee failure
        result = db_tools.test_connection("invalid://localhost/nonexistent")
        assert result["status"] == "error"
        assert "error" in result 