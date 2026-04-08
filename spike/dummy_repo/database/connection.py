"""Database connection management."""
from utils.helpers import generate_id


class DatabasePool:
    """Connection pool for database access."""

    def __init__(self, host: str, port: int = 5432):
        self.host = host
        self.port = port
        self.pool_id = generate_id("pool")
        self._connections: list = []

    def get_connection(self):
        """Get a connection from the pool."""
        conn_id = generate_id("conn")
        self._connections.append(conn_id)
        return conn_id

    def release(self, conn_id: str):
        """Release a connection back to the pool."""
        if conn_id in self._connections:
            self._connections.remove(conn_id)
