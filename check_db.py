import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# 获取所有表
cursor.execute('SELECT name FROM sqlite_master WHERE type=\'table\'')
tables = cursor.fetchall()
print('数据库中的表:', [t[0] for t in tables])

# 检查每个表的结构
for table in tables:
    table_name = table[0]
    cursor.execute(f'PRAGMA table_info({table_name})')
    columns = cursor.fetchall()
    print(f'\n{table_name}表字段:')
    for col in columns:
        print(f'  {col[1]} ({col[2]})')

conn.close()
