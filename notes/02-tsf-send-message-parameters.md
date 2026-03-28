## tsf_send_message — passing parameters correctly
Date: February 2026
Source: Real bug in loading list status procedure

### Problem
Calling `tsf_send_message` with a plain string variable produced no substitution in the message translation. The `{0}` placeholder in the message stayed empty or the call silently failed.

### Root cause
`tsf_send_message` expects parameters wrapped in `<text>` XML tags, not a plain string. Passing a raw value like `'LL-001234'` doesn't work — it must be `<text>LL-001234</text>`.

### Syntax
```sql
exec dbo.tsf_send_message 'message_id', '<text>value1</text><text>value2</text>', 0
```

Message translation uses `{0}`, `{1}`, etc. as positional placeholders matching the order of `<text>` tags.

### Correct pattern — wrapping a variable
Use `FOR XML PATH('text')` to wrap and auto-escape special characters (`&`, `<`, `>`):

```sql
declare @xml nvarchar(500) = concat(
    (select @var1 for xml path('text')),
    (select @var2 for xml path('text'))
)

exec dbo.tsf_send_message 'my_message_id', @xml, 0
```

### Real example (loading list status check)
Function `generate_subject_code()` returns a plain string — needs wrapping:

```sql
-- WRONG: passes plain string
select @xml = dbo.generate_subject_code('loading_list', ll.loading_list_id)
  from loading_list ll
 where ll.administration_id = @administration_id
   and ll.loading_list_id   = @loading_list_id

exec dbo.tsf_send_message 'source_loading_list_status_loaded_or_departed', @xml, 1;

-- CORRECT: wraps with FOR XML PATH
select @xml = (select dbo.generate_subject_code('loading_list', ll.loading_list_id)
               for xml path('text'))
  from loading_list ll
 where ll.administration_id = @administration_id
   and ll.loading_list_id   = @loading_list_id

exec dbo.tsf_send_message 'source_loading_list_status_loaded_or_departed', @xml, 1;
rollback;
return;
```

### Abort parameter
- `0` — continues flow (severity 9, non-fatal)
- `1` or `NULL` — aborts and reverses the action (treated as error)

### Tip
For simple cases where the value comes from the current row, you can reference column or parameter names directly in the message translation (e.g. `{column_name}`) and the GUI substitutes the value automatically — no XML needed.
