from database.adapters.duckdb_adapter import DuckDBAdapter

try:
    adapter = DuckDBAdapter()
    with adapter.get_connection() as conn:
        print('Database adapter connected successfully')
        result = conn.execute('SELECT 1 as test').fetchall()
        print(f'Query executed: {result}')
        print('Connection successful')
except Exception as e:
    print(f'Connection failed: {e}')
