import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.validator import validate_and_dry_run
from app.executor import execute
import os
import time

checks = [
    ('DELETE', 'DELETE FROM fact_sales'),
    ('UPDATE', 'UPDATE fact_sales SET amount=0'),
    ('multi_statement', 'SELECT 1; SELECT 2'),
    ('limit_injection', 'SELECT * FROM fact_sales'),
]
for label, sql in checks:
    print(label, validate_and_dry_run(sql))

os.environ['SQL_TIMEOUT_SECONDS'] = '0.01'
start = time.monotonic()
try:
    execute('SELECT COUNT(*) FROM fact_sales AS a CROSS JOIN fact_sales AS b CROSS JOIN fact_sales AS c')
    print('timeout', 'NOT_INTERRUPTED')
except Exception as exc:
    print('timeout', type(exc).__name__, str(exc), f'{time.monotonic()-start:.2f}s')
