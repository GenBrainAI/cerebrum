"""
Database Tools Example

This script demonstrates how to use the DatabaseTools class to interact with a SQLite database.
"""
import os
import tempfile
import pprint
from sqlalchemy import create_engine, text
from src.server.tools.database_tools.database_tools import DatabaseTools

def setup_test_database():
    """Create a temporary SQLite database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    print(f"Creating temporary database at: {path}")
    
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
    
    return path

def print_result(result, title=None):
    """Pretty print the result of a database operation."""
    if title:
        print(f"\n--- {title} ---")
    
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(result)
    print()

def main():
    """Main function to demonstrate the DatabaseTools class."""
    # Setup a test database
    db_path = setup_test_database()
    
    try:
        # Create a DatabaseTools instance
        db_tools = DatabaseTools(f"sqlite:///{db_path}")
        
        # Test connection
        print_result(db_tools.test_connection(), "Testing Connection")
        
        # List tables
        print_result(db_tools.list_tables(), "Listing Tables")
        
        # Get table schema
        print_result(db_tools.get_table_schema("users"), "User Table Schema")
        
        # Get table preview
        print_result(db_tools.get_table_preview("users"), "User Table Preview")
        
        # Execute a simple query
        query = "SELECT * FROM users WHERE name LIKE :name_pattern"
        params = {"name_pattern": "J%"}
        print_result(db_tools.execute_query(query, params), "Query Users with Names Starting with J")
        
        # Execute a transaction
        queries = [
            "INSERT INTO users (name, email) VALUES (:name, :email)",
            "SELECT * FROM users WHERE name = :name"
        ]
        params_list = [
            {"name": "Bob Johnson", "email": "bob@example.com"},
            {"name": "Bob Johnson"}
        ]
        print_result(db_tools.execute_transaction(queries, params_list), "Transaction Example")
        
        # Get row count
        print_result(db_tools.get_table_row_count("users"), "User Table Row Count")
        
        # Execute a join query
        join_query = """
        SELECT u.name, p.title, p.content
        FROM users u
        JOIN posts p ON u.id = p.user_id
        """
        print_result(db_tools.execute_query(join_query), "Join Query Example")
        
        # Export to CSV in memory
        export_result = db_tools.export_query_results("SELECT * FROM users", format="csv")
        print_result(export_result, "Export Query Results (CSV)")
        
        # Save a connection to config
        config_result = db_tools.save_connection("example_sqlite", f"sqlite:///{db_path}")
        print_result(config_result, "Save Connection to Config")
        
        # List saved connections
        print_result(db_tools.list_saved_connections(), "List Saved Connections")
        
        # Delete the connection
        print_result(db_tools.delete_saved_connection("example_sqlite"), "Delete Saved Connection")
        
    finally:
        # Clean up the temporary database
        if os.path.exists(db_path):
            os.unlink(db_path)
            print(f"Temporary database removed: {db_path}")

if __name__ == "__main__":
    main() 