#!/usr/bin/env python3
"""
数据库迁移脚本 - 将保留策略从天数改为份数
"""

import os
import sys
import sqlite3
import shutil
from datetime import datetime

def backup_database():
    """备份数据库"""
    try:
        db_path = 'database.db'
        if os.path.exists(db_path):
            backup_path = f'database_backup_retention_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
            shutil.copy2(db_path, backup_path)
            print(f"✓ 数据库已备份到: {backup_path}")
            return backup_path
        else:
            print("✓ 数据库文件不存在，跳过备份")
            return None
    except Exception as e:
        print(f"✗ 数据库备份失败: {e}")
        return None

def migrate_retention_policy():
    """迁移保留策略"""
    try:
        db_path = 'database.db'
        if not os.path.exists(db_path):
            print("✓ 数据库文件不存在，无需迁移")
            return True
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查是否已经有retention_count字段
        cursor.execute("PRAGMA table_info(backup_tasks)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'retention_count' in columns:
            print("✓ retention_count字段已存在，无需迁移")
            conn.close()
            return True
        
        if 'retention_days' not in columns:
            print("✓ retention_days字段不存在，无需迁移")
            conn.close()
            return True
        
        print("开始迁移保留策略...")
        
        # 添加新字段
        cursor.execute("ALTER TABLE backup_tasks ADD COLUMN retention_count INTEGER DEFAULT 10")
        
        # 将retention_days转换为retention_count
        # 简单的转换规则：天数/3 = 份数（假设每3天备份一次）
        cursor.execute("""
            UPDATE backup_tasks 
            SET retention_count = CASE 
                WHEN retention_days <= 7 THEN 3
                WHEN retention_days <= 30 THEN 10
                WHEN retention_days <= 90 THEN 30
                ELSE 50
            END
        """)
        
        # 删除旧字段（SQLite不支持直接删除列，需要重建表）
        print("重建表结构...")
        
        # 创建新表
        cursor.execute("""
            CREATE TABLE backup_tasks_new (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                source_path VARCHAR(500) NOT NULL,
                storage_config_id INTEGER NOT NULL,
                remote_path VARCHAR(500) NOT NULL,
                cron_expression VARCHAR(100),
                compression_enabled BOOLEAN DEFAULT 1,
                compression_type VARCHAR(20) DEFAULT 'tar.gz',
                encryption_enabled BOOLEAN DEFAULT 0,
                encryption_password VARCHAR(255),
                retention_count INTEGER DEFAULT 10,
                is_active BOOLEAN DEFAULT 1,
                last_run_at DATETIME,
                next_run_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (storage_config_id) REFERENCES storage_configs (id)
            )
        """)
        
        # 复制数据
        cursor.execute("""
            INSERT INTO backup_tasks_new 
            (id, name, description, source_path, storage_config_id, remote_path, 
             cron_expression, compression_enabled, compression_type, encryption_enabled, 
             encryption_password, retention_count, is_active, last_run_at, next_run_at, 
             created_at, updated_at)
            SELECT 
                id, name, description, source_path, storage_config_id, remote_path,
                cron_expression, compression_enabled, compression_type, encryption_enabled,
                encryption_password, retention_count, is_active, last_run_at, next_run_at,
                created_at, updated_at
            FROM backup_tasks
        """)
        
        # 删除旧表
        cursor.execute("DROP TABLE backup_tasks")
        
        # 重命名新表
        cursor.execute("ALTER TABLE backup_tasks_new RENAME TO backup_tasks")
        
        # 提交更改
        conn.commit()
        conn.close()
        
        print("✓ 保留策略迁移完成")
        return True
        
    except Exception as e:
        print(f"✗ 迁移失败: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def verify_migration():
    """验证迁移结果"""
    try:
        db_path = 'database.db'
        if not os.path.exists(db_path):
            return True
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表结构
        cursor.execute("PRAGMA table_info(backup_tasks)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'retention_count' not in columns:
            print("✗ 验证失败: retention_count字段不存在")
            return False
        
        if 'retention_days' in columns:
            print("✗ 验证失败: retention_days字段仍然存在")
            return False
        
        # 检查数据
        cursor.execute("SELECT COUNT(*) FROM backup_tasks WHERE retention_count IS NULL")
        null_count = cursor.fetchone()[0]
        
        if null_count > 0:
            print(f"✗ 验证失败: 有 {null_count} 条记录的retention_count为空")
            return False
        
        cursor.execute("SELECT COUNT(*) FROM backup_tasks")
        total_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"✓ 验证成功: {total_count} 条备份任务记录已更新")
        return True
        
    except Exception as e:
        print(f"✗ 验证失败: {e}")
        return False

def main():
    print("RClone备份系统 - 保留策略迁移")
    print("=" * 50)
    print("将保留策略从'保留天数'改为'保留份数'")
    print()
    
    # 备份数据库
    backup_path = backup_database()
    
    # 执行迁移
    if migrate_retention_policy():
        # 验证迁移
        if verify_migration():
            print()
            print("=" * 50)
            print("✓ 迁移完成！")
            print()
            print("变更说明:")
            print("- retention_days 字段已删除")
            print("- 新增 retention_count 字段（默认值：10）")
            print("- 保留策略现在基于备份文件数量而非天数")
            print()
            if backup_path:
                print(f"如需回滚，请恢复备份文件: {backup_path}")
        else:
            print()
            print("=" * 50)
            print("✗ 迁移验证失败！")
            if backup_path:
                print(f"请检查问题或恢复备份文件: {backup_path}")
    else:
        print()
        print("=" * 50)
        print("✗ 迁移失败！")
        if backup_path:
            print(f"请恢复备份文件: {backup_path}")

if __name__ == '__main__':
    main()
