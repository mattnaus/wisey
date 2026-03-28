## Transaction log full — emergency recovery
Date: January 2026
Source: Real incident on ARCUS_TEST and production

### Problem
Database in FULL recovery model with no log backup jobs running. Log kept growing indefinitely until disk filled up (80GB+). Database became read-only. Users got "transaction log is full due to LOG_BACKUP" errors.

In production the trigger was a massive ERP→WMS data sync that generated far more transactions than normal, overwhelming the available log space faster than expected.

### Root cause
FULL recovery model tells SQL Server to preserve all transaction log records for point-in-time recovery. The only thing that marks log space as reusable is a log backup. Without regular log backups, the log grows forever.

### Fix (test environment — switch to SIMPLE)
```sql
ALTER DATABASE ARCUS_TEST SET RECOVERY SIMPLE;

-- Find log file name
SELECT name, type_desc, physical_name, size/128 AS size_mb
FROM sys.master_files
WHERE database_id = DB_ID('ARCUS_TEST');

-- Shrink (replace log file name as found above)
USE ARCUS_TEST;
DBCC SHRINKFILE (ARCUS_TEST_log, 1024); -- target 1GB
-- May need to run multiple times
```

### Fix (production — keep FULL recovery)
```sql
-- Step 1: take a log backup to mark inactive log as reusable
BACKUP LOG YourDatabase
TO DISK = 'D:\Backups\YourDatabase_log.trn'
WITH COMPRESSION;

-- Step 2: shrink the log file
USE YourDatabase;
DBCC SHRINKFILE (YourDatabase_log, 1024);
```

### Diagnostic: why won't it shrink?
```sql
SELECT log_reuse_wait_desc FROM sys.databases WHERE name = 'YourDatabase';
```
Common values:
- `LOG_BACKUP` — still waiting on a log backup
- `ACTIVE_TRANSACTION` — long-running transaction blocking truncation
- `REPLICATION` — replication configured but not running

### Prevention
- Schedule SQL Agent log backup jobs every 15–30 minutes in FULL recovery
- If point-in-time recovery isn't needed, use SIMPLE recovery (log auto-truncates)
- After large bulk operations (e.g. ERP→WMS sync), monitor log growth proactively

### Notes
- File extension (.trn vs .bak) doesn't matter to SQL Server — it's just convention
- DBCC SHRINKFILE may need multiple runs due to VLF layout at end of file
- Shrinking log files is normally bad practice (causes VLF fragmentation) but acceptable in emergency recovery
