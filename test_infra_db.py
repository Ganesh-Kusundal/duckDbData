import sys
sys.path.insert(0, '.')

from src.infrastructure.adapters.duckdb_adapter import DuckDBAdapter

try:
    adapter = DuckDBAdapter()
    with adapter.get_connection() as conn:
        print('Infrastructure DuckDB adapter connected successfully')
        result = conn.execute('SELECT 1 as test').fetchall()
        print(f'Query executed: {result}')
        print('Connection successful')
except Exception as e:
    print(f'Connection failed: {e}')
    import traceback
    traceback.print_exc()
