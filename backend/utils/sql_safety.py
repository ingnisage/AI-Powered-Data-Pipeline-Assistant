# utils/sql_safety.py - SQL Injection Prevention and Query Safety
"""
Utilities for preventing SQL injection attacks and ensuring safe query execution.
Provides query validation, parameterization, and complexity analysis.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import text, create_engine
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class SQLSafetyError(Exception):
    """Custom exception for SQL safety violations."""
    pass


class SQLQueryValidator:
    """Validates and sanitizes SQL queries to prevent injection attacks."""
    
    # Dangerous SQL keywords that should not appear in user queries
    DANGEROUS_KEYWORDS = [
        'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE',
        'TRUNCATE', 'REPLACE', 'EXEC', 'EXECUTE', 'GRANT', 'REVOKE'
    ]
    
    # Dangerous SQL patterns
    DANGEROUS_PATTERNS = [
        r';\s*(DROP|DELETE|INSERT|UPDATE)',  # Multiple statements
        r'--',  # SQL comments
        r'/\*.*\*/',  # Block comments
        r'xp_',  # SQL Server extended procedures
        r'sp_',  # SQL Server stored procedures
        r'\bUNION\b.*\bSELECT\b',  # Union injection
        r'\bINTO\s+OUTFILE\b',  # File writes
        r'\bLOAD_FILE\b',  # File reads
    ]
    
    # Maximum allowed query complexity
    MAX_JOINS = 5
    MAX_SUBQUERIES = 3
    MAX_QUERY_LENGTH = 5000
    
    def __init__(self):
        """Initialize SQL query validator."""
        logger.info("SQLQueryValidator initialized")
    
    def is_select_query(self, query: str) -> bool:
        """Check if query is a SELECT statement.
        
        Args:
            query: SQL query to check
            
        Returns:
            True if query is a SELECT statement, False otherwise
        """
        normalized = query.strip().upper()
        return normalized.startswith('SELECT')
    
    def contains_dangerous_keywords(self, query: str) -> Tuple[bool, Optional[str]]:
        """Check for dangerous SQL keywords.
        
        Args:
            query: SQL query to check
            
        Returns:
            Tuple of (contains_danger, found_keyword)
        """
        normalized = query.upper()
        for keyword in self.DANGEROUS_KEYWORDS:
            if re.search(r'\b' + keyword + r'\b', normalized):
                return True, keyword
        return False, None
    
    def contains_dangerous_patterns(self, query: str) -> Tuple[bool, Optional[str]]:
        """Check for dangerous SQL patterns.
        
        Args:
            query: SQL query to check
            
        Returns:
            Tuple of (contains_danger, matched_pattern)
        """
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return True, pattern
        return False, None
    
    def check_query_complexity(self, query: str) -> Tuple[bool, Optional[str]]:
        """Analyze query complexity to prevent DoS attacks.
        
        Args:
            query: SQL query to analyze
            
        Returns:
            Tuple of (is_acceptable, error_message)
        """
        # Check length
        if len(query) > self.MAX_QUERY_LENGTH:
            return False, f"Query too long ({len(query)} chars, max {self.MAX_QUERY_LENGTH})"
        
        # Count joins
        join_count = len(re.findall(r'\bJOIN\b', query, re.IGNORECASE))
        if join_count > self.MAX_JOINS:
            return False, f"Too many JOINs ({join_count}, max {self.MAX_JOINS})"
        
        # Count subqueries
        subquery_count = query.count('(SELECT') + query.count('( SELECT')
        if subquery_count > self.MAX_SUBQUERIES:
            return False, f"Too many subqueries ({subquery_count}, max {self.MAX_SUBQUERIES})"
        
        return True, None
    
    def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """Comprehensive query validation.
        
        Args:
            query: SQL query to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if it's a SELECT query
        if not self.is_select_query(query):
            return False, "Only SELECT queries are allowed"
        
        # Check for dangerous keywords
        has_danger, keyword = self.contains_dangerous_keywords(query)
        if has_danger:
            logger.warning(f"Dangerous keyword detected in query: {keyword}")
            return False, f"Dangerous keyword detected: {keyword}"
        
        # Check for dangerous patterns
        has_pattern, pattern = self.contains_dangerous_patterns(query)
        if has_pattern:
            logger.warning(f"Dangerous pattern detected in query: {pattern}")
            return False, "Dangerous SQL pattern detected"
        
        # Check complexity
        is_acceptable, complexity_error = self.check_query_complexity(query)
        if not is_acceptable:
            logger.warning(f"Query complexity exceeded: {complexity_error}")
            return False, complexity_error
        
        logger.info("Query validation passed")
        return True, None
    
    def sanitize_identifier(self, identifier: str) -> str:
        """Sanitize a SQL identifier (table/column name).
        
        Args:
            identifier: Identifier to sanitize
            
        Returns:
            Sanitized identifier
            
        Raises:
            SQLSafetyError: If identifier contains invalid characters
        """
        # Only allow alphanumeric and underscore
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
            raise SQLSafetyError(f"Invalid identifier: {identifier}")
        
        # Escape with double quotes for PostgreSQL/SQLAlchemy
        return f'"{identifier}"'


class SafeQueryExecutor:
    """Executes SQL queries safely with parameterization and validation."""
    
    def __init__(self, database_url: str):
        """Initialize safe query executor.
        
        Args:
            database_url: SQLAlchemy database connection URL
        """
        self.engine = create_engine(database_url, echo=False)
        self.validator = SQLQueryValidator()
        logger.info(f"SafeQueryExecutor initialized for: {database_url.split('@')[0]}@...")
    
    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        max_rows: int = 1000
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
        """Execute a query safely with validation and parameterization.
        
        Args:
            query: SQL query with placeholders (e.g., :param_name)
            params: Dictionary of parameters to bind
            max_rows: Maximum number of rows to return
            
        Returns:
            Tuple of (success, results, error_message)
        """
        params = params or {}
        
        # Validate the query structure
        is_valid, error = self.validator.validate_query(query)
        if not is_valid:
            logger.error(f"Query validation failed: {error}")
            return False, None, error
        
        try:
            # Use parameterized execution with SQLAlchemy
            with self.engine.connect() as conn:
                # Execute with bound parameters (prevents injection)
                result = conn.execute(text(query), params)
                
                # Fetch limited results
                rows = result.fetchmany(max_rows)
                
                # Convert to list of dicts
                results = [dict(row._mapping) for row in rows]
                
                logger.info(f"Query executed successfully, returned {len(results)} rows")
                return True, results, None
                
        except SQLAlchemyError as e:
            error_msg = f"Database error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, None, error_msg
    
    def close(self) -> None:
        """Close the database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")


# Convenience functions
def validate_sql_query(query: str) -> Tuple[bool, Optional[str]]:
    """Validate a SQL query for safety.
    
    Args:
        query: SQL query to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = SQLQueryValidator()
    return validator.validate_query(query)


def safe_execute_query(
    database_url: str,
    query: str,
    params: Optional[Dict[str, Any]] = None,
    max_rows: int = 1000
) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
    """Execute a SQL query safely.
    
    Args:
        database_url: Database connection URL
        query: SQL query with parameter placeholders
        params: Query parameters
        max_rows: Maximum rows to return
        
    Returns:
        Tuple of (success, results, error_message)
    """
    executor = SafeQueryExecutor(database_url)
    try:
        return executor.execute_query(query, params, max_rows)
    finally:
        executor.close()
