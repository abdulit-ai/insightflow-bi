# Project plan and architecture decisions

## Milestones
1. Data layer: normalized relational schema and sample CSV (complete)
2. API: validation, idempotent import, aggregated dashboard endpoint (complete)
3. Frontend: responsive charts, filters, upload, sample seed (complete)
4. Quality: automated API tests and documented local setup (complete)
5. Portfolio polish: deploy to hosting, add real screenshots, accessibility review, CI pipeline (next)

## Data model
- `customers`: ID, name, segment, region
- `products`: ID, name, category
- `sales`: unique external line ID, date, customer FK, product FK, quantity, unit price

## Test scenarios
- Import valid CSV and reconcile revenue/order-line count
- Reimport same CSV without duplicates
- Apply region and date filters
- Reject malformed CSV and confirm no partial writes

## Planned improvements
- Sales order header and line item separation
- Tax, discounts, returns, multi-currency support
- SQL-level aggregation for large datasets
- User accounts and row-level tenant isolation
- ETL jobs and data freshness indicators
- Exportable reports, accessibility testing, CI, production deployment
