"""
Database tools for Cerebrum.

This module provides tools for interacting with databases using JDBC connection strings.
"""
from typing import Dict, List, Optional, Union, Any, Tuple
import os
import json
import logging
import time
import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine, text, MetaData, Table, inspect, select, Column
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine.url import make_url
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseTools:
    """Tools for interacting with databases."""
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize database tools with a connection string.
        
        Args:
            connection_string: JDBC connection string or connection ID from configuration
        """
        self.connection_string = connection_string
        self._engine = None
        self._metadata = None
        self._config_file = os.path.join(os.path.expanduser("~"), ".cerebrum", "database_config.json")
        
        # If no connection string is provided, we'll load later from config when needed
        if connection_string:
            self._setup_connection(connection_string)
    
    def _load_connection_from_config(self, connection_id: str) -> str:
        """
        Load a database connection string from configuration file.
        
        Args:
            connection_id: ID of the connection to load
            
        Returns:
            The connection string
            
        Raises:
            ValueError: If the connection ID is not found in configuration
        """
        if not os.path.exists(self._config_file):
            raise ValueError(f"Database configuration file not found: {self._config_file}")
        
        try:
            with open(self._config_file, 'r') as f:
                config = json.load(f)
            
            if connection_id not in config:
                raise ValueError(f"Connection ID '{connection_id}' not found in configuration")
            
            return config[connection_id]
        except Exception as e:
            logger.error(f"Failed to load connection from config: {str(e)}")
            raise
    
    def _setup_connection(self, connection_string_or_id: str):
        """
        Set up the database connection.
        
        Args:
            connection_string_or_id: JDBC connection string or connection ID from configuration
            
        Raises:
            ValueError: If the connection string is invalid
        """
        try:
            # Check if this is a connection ID first
            if not connection_string_or_id.startswith(('jdbc:', 'mysql:', 'postgresql:', 'oracle:', 'mssql:', 'sqlite:')):
                # This looks like a connection ID, load from config
                connection_string = self._load_connection_from_config(connection_string_or_id)
            else:
                connection_string = connection_string_or_id
            
            # Convert JDBC URL to SQLAlchemy format if needed
            if connection_string.startswith('jdbc:'):
                connection_string = self._convert_jdbc_to_sqlalchemy(connection_string)
            
            # Create the SQLAlchemy engine
            self._engine = create_engine(connection_string)
            self._metadata = MetaData()
            self._metadata.reflect(bind=self._engine)
            self.connection_string = connection_string
        except Exception as e:
            logger.error(f"Failed to set up database connection: {str(e)}")
            raise ValueError(f"Failed to set up database connection: {str(e)}")
    
    def _convert_jdbc_to_sqlalchemy(self, jdbc_url: str) -> str:
        """
        Convert a JDBC connection string to SQLAlchemy format.
        
        Args:
            jdbc_url: JDBC connection string
            
        Returns:
            SQLAlchemy connection string
            
        Raises:
            ValueError: If the JDBC URL is not supported
        """
        # Strip the 'jdbc:' prefix
        if jdbc_url.startswith('jdbc:'):
            jdbc_url = jdbc_url[5:]
        
        # Parse the database type
        if jdbc_url.startswith('mysql:'):
            # jdbc:mysql://hostname:port/database?user=username&password=password
            jdbc_url = jdbc_url.replace('mysql://', 'mysql+pymysql://')
        elif jdbc_url.startswith('postgresql:'):
            # jdbc:postgresql://hostname:port/database?user=username&password=password
            jdbc_url = jdbc_url.replace('postgresql://', 'postgresql+psycopg2://')
        elif jdbc_url.startswith('oracle:'):
            # jdbc:oracle:thin:username/password@hostname:port:SID
            jdbc_url = jdbc_url.replace('oracle:thin:', 'oracle+cx_oracle://')
        elif jdbc_url.startswith('sqlserver:'):
            # jdbc:sqlserver://hostname:port;databaseName=database;user=username;password=password
            jdbc_url = jdbc_url.replace('sqlserver://', 'mssql+pyodbc://')
        elif jdbc_url.startswith('sqlite:'):
            # jdbc:sqlite:database.db
            pass  # SQLite URLs are the same in JDBC and SQLAlchemy
        else:
            raise ValueError(f"Unsupported JDBC URL format: {jdbc_url}")
        
        return jdbc_url
    
    def _ensure_connection(self, connection_string_or_id: Optional[str] = None):
        """
        Ensure that a database connection is established.
        
        Args:
            connection_string_or_id: Optional JDBC connection string or connection ID
            
        Raises:
            ValueError: If no connection is available
        """
        if connection_string_or_id:
            # If a new connection string is provided, use it
            self._setup_connection(connection_string_or_id)
        elif not self._engine and self.connection_string:
            # If we have a connection string but no engine, try to connect
            self._setup_connection(self.connection_string)
        elif not self._engine:
            # No connection is available
            raise ValueError("No database connection available. Please provide a connection string or call set_connection first.")
    
    @contextmanager
    def _get_connection(self):
        """
        Context manager for database connections.
        
        Yields:
            Database connection
            
        Raises:
            ValueError: If no connection is available
        """
        self._ensure_connection()
        connection = self._engine.connect()
        try:
            yield connection
        finally:
            connection.close()
    
    def set_connection(self, connection_string_or_id: str) -> Dict[str, Any]:
        """
        Set the database connection string or ID.
        
        Args:
            connection_string_or_id: JDBC connection string or connection ID from configuration
            
        Returns:
            Dictionary containing connection information
        """
        try:
            self._setup_connection(connection_string_or_id)
            
            # Get database type and version info
            with self._get_connection() as conn:
                version_info = conn.execute(text("SELECT version();")).scalar()
            
            url = make_url(self.connection_string)
            return {
                "status": "success",
                "database_type": url.drivername,
                "database_name": url.database,
                "host": url.host,
                "port": url.port,
                "username": url.username,
                "version": version_info
            }
        except Exception as e:
            logger.error(f"Failed to set connection: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def save_connection(self, connection_id: str, connection_string: str) -> Dict[str, Any]:
        """
        Save a database connection to configuration.
        
        Args:
            connection_id: ID to use for this connection
            connection_string: JDBC connection string
            
        Returns:
            Dictionary containing operation status
        """
        try:
            # Ensure the config directory exists
            os.makedirs(os.path.dirname(self._config_file), exist_ok=True)
            
            # Load existing config if it exists
            config = {}
            if os.path.exists(self._config_file):
                with open(self._config_file, 'r') as f:
                    config = json.load(f)
            
            # Add or update the connection
            config[connection_id] = connection_string
            
            # Save the config
            with open(self._config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            return {
                "status": "success",
                "message": f"Connection '{connection_id}' saved successfully"
            }
        except Exception as e:
            logger.error(f"Failed to save connection: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def list_saved_connections(self) -> Dict[str, Any]:
        """
        List all saved database connections.
        
        Returns:
            Dictionary containing list of saved connections
        """
        try:
            if not os.path.exists(self._config_file):
                return {
                    "status": "success",
                    "connections": []
                }
            
            with open(self._config_file, 'r') as f:
                config = json.load(f)
            
            # Create a sanitized version of connections (without passwords)
            sanitized_connections = {}
            for conn_id, conn_string in config.items():
                if isinstance(conn_string, str):
                    # Mask password in connection string
                    if 'password=' in conn_string:
                        parts = conn_string.split('password=')
                        if len(parts) > 1:
                            password_end = parts[1].find('&')
                            if password_end == -1:
                                password_end = len(parts[1])
                            sanitized = parts[0] + 'password=*****' + parts[1][password_end:]
                            sanitized_connections[conn_id] = sanitized
                        else:
                            sanitized_connections[conn_id] = conn_string
                    else:
                        sanitized_connections[conn_id] = conn_string
            
            return {
                "status": "success",
                "connections": sanitized_connections
            }
        except Exception as e:
            logger.error(f"Failed to list connections: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def delete_saved_connection(self, connection_id: str) -> Dict[str, Any]:
        """
        Delete a saved database connection.
        
        Args:
            connection_id: ID of the connection to delete
            
        Returns:
            Dictionary containing operation status
        """
        try:
            if not os.path.exists(self._config_file):
                return {
                    "status": "error",
                    "error": f"Configuration file not found: {self._config_file}"
                }
            
            with open(self._config_file, 'r') as f:
                config = json.load(f)
            
            if connection_id not in config:
                return {
                    "status": "error",
                    "error": f"Connection ID '{connection_id}' not found"
                }
            
            # Remove the connection
            del config[connection_id]
            
            # Save the config
            with open(self._config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            return {
                "status": "success",
                "message": f"Connection '{connection_id}' deleted successfully"
            }
        except Exception as e:
            logger.error(f"Failed to delete connection: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def list_tables(self, schema: Optional[str] = None) -> Dict[str, Any]:
        """
        List all tables in the database.
        
        Args:
            schema: Optional schema name to filter tables
            
        Returns:
            Dictionary containing list of tables
        """
        try:
            self._ensure_connection()
            inspector = inspect(self._engine)
            
            if schema:
                tables = inspector.get_table_names(schema=schema)
                result = {
                    "status": "success",
                    "schema": schema,
                    "tables": tables
                }
            else:
                # Get all schemas and their tables
                schemas = inspector.get_schema_names()
                result = {
                    "status": "success",
                    "schemas": {}
                }
                
                for schema_name in schemas:
                    tables = inspector.get_table_names(schema=schema_name)
                    result["schemas"][schema_name] = tables
            
            return result
        except Exception as e:
            logger.error(f"Failed to list tables: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_table_schema(self, table_name: str, schema: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the schema of a table.
        
        Args:
            table_name: Name of the table
            schema: Optional schema name
            
        Returns:
            Dictionary containing table schema information
        """
        try:
            self._ensure_connection()
            inspector = inspect(self._engine)
            
            # Get column information
            columns = inspector.get_columns(table_name, schema=schema)
            
            # Get primary key information
            primary_keys = inspector.get_pk_constraint(table_name, schema=schema)
            
            # Get foreign key information
            foreign_keys = inspector.get_foreign_keys(table_name, schema=schema)
            
            # Get index information
            indices = inspector.get_indexes(table_name, schema=schema)
            
            return {
                "status": "success",
                "table_name": table_name,
                "schema": schema,
                "columns": columns,
                "primary_keys": primary_keys,
                "foreign_keys": foreign_keys,
                "indices": indices
            }
        except Exception as e:
            logger.error(f"Failed to get table schema: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a SQL query and return the results.
        
        Args:
            query: SQL query string
            params: Optional parameters for the query
            
        Returns:
            Dictionary containing query results
        """
        try:
            self._ensure_connection()
            start_time = time.time()
            
            # Execute the query
            with self._get_connection() as conn:
                if params:
                    result_proxy = conn.execute(text(query), params)
                else:
                    result_proxy = conn.execute(text(query))
                
                # Check if it's a SELECT query (returns rows)
                if result_proxy.returns_rows:
                    # Convert to pandas DataFrame
                    df = pd.DataFrame(result_proxy.fetchall())
                    if not df.empty:
                        df.columns = result_proxy.keys()
                    
                    end_time = time.time()
                    execution_time = end_time - start_time
                    
                    return {
                        "status": "success",
                        "execution_time": execution_time,
                        "row_count": len(df),
                        "column_names": list(df.columns) if not df.empty else [],
                        "results": df.to_dict(orient='records')
                    }
                else:
                    # For non-SELECT queries (INSERT, UPDATE, DELETE)
                    end_time = time.time()
                    execution_time = end_time - start_time
                    
                    return {
                        "status": "success",
                        "execution_time": execution_time,
                        "row_count": result_proxy.rowcount,
                        "message": f"Query executed successfully. Rows affected: {result_proxy.rowcount}"
                    }
        except Exception as e:
            logger.error(f"Failed to execute query: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def execute_transaction(self, queries: List[str], params_list: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Execute multiple SQL queries as a transaction.
        
        Args:
            queries: List of SQL query strings
            params_list: Optional list of parameter dictionaries for each query
            
        Returns:
            Dictionary containing transaction results
        """
        try:
            self._ensure_connection()
            start_time = time.time()
            
            # Create a transaction
            with self._engine.begin() as transaction:
                results = []
                
                for i, query in enumerate(queries):
                    params = params_list[i] if params_list and i < len(params_list) else None
                    
                    if params:
                        result_proxy = transaction.execute(text(query), params)
                    else:
                        result_proxy = transaction.execute(text(query))
                    
                    # Store result information
                    if result_proxy.returns_rows:
                        # Convert to pandas DataFrame
                        df = pd.DataFrame(result_proxy.fetchall())
                        if not df.empty:
                            df.columns = result_proxy.keys()
                        
                        results.append({
                            "query_index": i,
                            "row_count": len(df),
                            "column_names": list(df.columns) if not df.empty else [],
                            "results": df.to_dict(orient='records')
                        })
                    else:
                        results.append({
                            "query_index": i,
                            "row_count": result_proxy.rowcount,
                            "message": f"Query executed successfully. Rows affected: {result_proxy.rowcount}"
                        })
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            return {
                "status": "success",
                "execution_time": execution_time,
                "query_count": len(queries),
                "results": results
            }
        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_table_preview(self, table_name: str, schema: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """
        Get a preview of the data in a table.
        
        Args:
            table_name: Name of the table
            schema: Optional schema name
            limit: Maximum number of rows to return (default: 10)
            
        Returns:
            Dictionary containing table data preview
        """
        try:
            self._ensure_connection()
            
            # Construct the query
            if schema:
                query = f'SELECT * FROM "{schema}"."{table_name}" LIMIT {limit}'
            else:
                query = f'SELECT * FROM "{table_name}" LIMIT {limit}'
            
            # Execute the query
            return self.execute_query(query)
        except Exception as e:
            logger.error(f"Failed to get table preview: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_table_row_count(self, table_name: str, schema: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the number of rows in a table.
        
        Args:
            table_name: Name of the table
            schema: Optional schema name
            
        Returns:
            Dictionary containing row count information
        """
        try:
            self._ensure_connection()
            
            # Construct the query
            if schema:
                query = f'SELECT COUNT(*) as row_count FROM "{schema}"."{table_name}"'
            else:
                query = f'SELECT COUNT(*) as row_count FROM "{table_name}"'
            
            # Execute the query
            result = self.execute_query(query)
            
            if result["status"] == "success" and "results" in result and result["results"]:
                row_count = result["results"][0]["row_count"]
                return {
                    "status": "success",
                    "table_name": table_name,
                    "schema": schema,
                    "row_count": row_count
                }
            
            return result
        except Exception as e:
            logger.error(f"Failed to get table row count: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def export_query_results(self, query: str, params: Optional[Dict[str, Any]] = None, 
                             file_path: str = None, format: str = 'csv') -> Dict[str, Any]:
        """
        Execute a query and export the results to a file.
        
        Args:
            query: SQL query string
            params: Optional parameters for the query
            file_path: Path to save the exported file (or None to return data)
            format: Export format ('csv', 'json', 'excel', 'html', 'parquet')
            
        Returns:
            Dictionary containing export status
        """
        try:
            self._ensure_connection()
            
            # Execute the query
            result = self.execute_query(query, params)
            
            if result["status"] != "success":
                return result
            
            if not result.get("results"):
                return {
                    "status": "error",
                    "error": "Query returned no results to export"
                }
            
            # Convert to DataFrame
            df = pd.DataFrame(result["results"])
            
            # Export to file if path provided
            if file_path:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                
                # Export based on format
                if format.lower() == 'csv':
                    df.to_csv(file_path, index=False)
                elif format.lower() == 'json':
                    df.to_json(file_path, orient='records', indent=2)
                elif format.lower() == 'excel':
                    df.to_excel(file_path, index=False)
                elif format.lower() == 'html':
                    df.to_html(file_path, index=False)
                elif format.lower() == 'parquet':
                    df.to_parquet(file_path, index=False)
                else:
                    return {
                        "status": "error",
                        "error": f"Unsupported export format: {format}"
                    }
                
                return {
                    "status": "success",
                    "message": f"Data exported successfully to {file_path}",
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "file_format": format,
                    "file_path": file_path
                }
            else:
                # Return the data in the requested format
                if format.lower() == 'csv':
                    data = df.to_csv(index=False)
                elif format.lower() == 'json':
                    data = df.to_json(orient='records', indent=2)
                elif format.lower() == 'html':
                    data = df.to_html(index=False)
                else:
                    return {
                        "status": "error",
                        "error": f"Unsupported return format: {format}"
                    }
                
                return {
                    "status": "success",
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "format": format,
                    "data": data
                }
        except Exception as e:
            logger.error(f"Failed to export query results: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def test_connection(self, connection_string_or_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Test a database connection.
        
        Args:
            connection_string_or_id: Optional connection string or ID to test
            
        Returns:
            Dictionary containing connection test results
        """
        try:
            start_time = time.time()
            
            # Use provided connection or current one
            if connection_string_or_id:
                # Save the current connection if any
                current_engine = self._engine
                current_metadata = self._metadata
                current_connection_string = self.connection_string
                
                try:
                    # Test the new connection
                    self._setup_connection(connection_string_or_id)
                    
                    # Try to execute a simple query
                    with self._get_connection() as conn:
                        conn.execute(text("SELECT 1")).fetchall()
                    
                    end_time = time.time()
                    connection_time = end_time - start_time
                    
                    # Get database type and version info
                    url = make_url(self.connection_string)
                    
                    return {
                        "status": "success",
                        "message": "Connection successful",
                        "connection_time": connection_time,
                        "database_type": url.drivername,
                        "database_name": url.database,
                        "host": url.host,
                        "port": url.port,
                        "username": url.username
                    }
                finally:
                    # Restore the original connection
                    self._engine = current_engine
                    self._metadata = current_metadata
                    self.connection_string = current_connection_string
            else:
                # Test the current connection
                self._ensure_connection()
                
                with self._get_connection() as conn:
                    conn.execute(text("SELECT 1")).fetchall()
                
                end_time = time.time()
                connection_time = end_time - start_time
                
                # Get database type and version info
                url = make_url(self.connection_string)
                
                return {
                    "status": "success",
                    "message": "Connection successful",
                    "connection_time": connection_time,
                    "database_type": url.drivername,
                    "database_name": url.database,
                    "host": url.host,
                    "port": url.port,
                    "username": url.username
                }
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            } 