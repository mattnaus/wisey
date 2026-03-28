## Thinkwise cubes — configuration patterns and prefilters
Date: February 2026
Source: Capacity planning screen build (WMS project)

### Core concepts

A **cube** defines what data is available — dimensions and values:

| Term | What it is | Example |
|---|---|---|
| Dimension | Field to group or filter by | planning_date, line_status, unit_id |
| Value | Field to measure/aggregate | expected_picks, wms_picks |

A **cube view** defines how to display that data — where dimensions and values are placed:

| Term | In a chart | In a pivot table |
|---|---|---|
| Categories / Rows | X-axis | Row headers |
| Series / Columns | Color groupings | Column headers |
| Values | Y-axis (bar height) | Cell values |
| Filters | Filter dropdown | Filter dropdown |

### Multiple cube views on one subject
You can have multiple cube views on the same underlying subject/view. They all share the same prefilters. This is the correct pattern for a dashboard with multiple charts — the user sets the filter once, then switches between views.

Example setup from the capacity screen:
```
Subject: capacity_orderlines (one view with all data)
├── Cube view 1: Picks per day (bar chart)
│     Categories: planning_date
│     Values: expected_picks
│
├── Cube view 2: Picks by status (stacked bar chart)
│     Categories: planning_date
│     Series: line_status
│     Values: expected_picks
│
└── Cube view 3: Orders (pivot table)
      Rows: sales_order_id
      Values: SUM(expected_picks)
```

### Configuring a date range prefilter
*Menu: User interface > Subjects > [your subject] > tab Prefilters*

Add two prefilters:

| Prefilter | Column | Condition | Default |
|---|---|---|---|
| Date from | planning_date | >= | today or empty |
| Date to | planning_date | <= | today +30 or empty |

Both cube views use the same prefilter automatically.

### Filtering options (from docs)
Two ways to limit what a cube runs against:
1. **Detail reference** — filters on the selected row in a parent subject (good for drilling into one record)
2. **Prefilter** — filters on a range or value the user sets (good for dashboards)

For capacity planning / date range screens, prefilters are the right choice.

### X-axis label crowding
If the full date string is too wide on the x-axis:
- Add a formatted display column to the view: `FORMAT(planning_date, 'dd-MM') AS planning_date_short`
- Use that as the dimension instead of the raw date column
- Or set a Group interval on the dimension (day of month, week of year, month)

### Tip
Don't try to combine two fundamentally different datasets (e.g. order lines aggregated by date AND order headers) into a single subject just to share filters. Use a pivot table cube view instead — it can show order-level data grouped from the same line-level source.
