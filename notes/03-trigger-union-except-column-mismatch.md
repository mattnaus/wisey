## Trigger with UNION + EXCEPT — column count mismatch
Date: February 2026
Source: order_management_refresh_queue trigger

### Problem
Tried to include `queued_at` (with `getdate()`) in a trigger INSERT that used UNION + EXCEPT. Got error:

> All queries combined using a UNION, INTERSECT or EXCEPT operator must have an equal number of expressions in their target lists.

The `order_management_refresh_queue` table has a `queued_at datetime2 DEFAULT getdate()` column.

### Root cause
EXCEPT requires identical column lists across all combined queries. Adding `getdate()` to the UNION broke parity with the EXCEPT subquery (which only referenced the natural key columns).

### Wrong approach
```sql
insert into order_management_refresh_queue (administration_id, sales_order_id, queued_at)
select administration_id, sales_order_id, getdate() from inserted
union
select administration_id, sales_order_id, getdate() from deleted
except
select administration_id, sales_order_id              -- different column count!
  from order_management_refresh_queue
```

### Clean fix — rely on DEFAULT
Since `queued_at` has a DEFAULT, just omit it from the INSERT entirely:

```sql
insert into order_management_refresh_queue (administration_id, sales_order_id)
select administration_id, sales_order_id from inserted
union
select administration_id, sales_order_id from deleted
except
select administration_id, sales_order_id from order_management_refresh_queue
```

Timestamp is set automatically. Fewer columns, no mismatch.

### If you must pass the timestamp explicitly
Wrap the UNION first in a subquery, then apply EXCEPT outside:

```sql
insert into order_management_refresh_queue (administration_id, sales_order_id, queued_at)
select administration_id, sales_order_id, getdate()
from (
    select administration_id, sales_order_id from inserted
    union
    select administration_id, sales_order_id from deleted
    except
    select administration_id, sales_order_id from order_management_refresh_queue
) x
```

### Related gotcha
When a Thinkwise platform update touches a table covered by this trigger, every row in that table gets queued — even if nothing business-relevant changed. Fix: add a trace column check to only queue rows where meaningful columns actually changed.
