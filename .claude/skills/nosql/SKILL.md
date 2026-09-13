---
name: nosql
description: Design, implement, optimize, and troubleshoot NoSQL and polyglot database architectures. Covers MongoDB document modeling, Redis caching and pub/sub, Cassandra/ScyllaDB wide-column design, DynamoDB single-table design, and Neo4j graph modeling. Use for database schema design, query optimization, data migration, polyglot selection, indexing strategy, replication/sharding, and Byblos CRM data architecture.
---

# NoSQL & Polyglot Engineering

Design the right data layer for the workload. NoSQL is not a synonym for "schemaless" — each engine has strong opinions on access patterns, consistency models, and operational complexity. Match the engine to the problem, not the other way around.

## Core Design Workflow

1. **Capture access patterns first.** List every query the application will run before touching schema. NoSQL schema design is query-driven, not entity-driven.
2. **Select the engine(s).** Choose based on: data shape, consistency requirements, read/write ratio, latency SLA, operational complexity budget.
3. **Design the schema.** Apply engine-specific patterns (embedding vs. referencing, partition key selection, column family layout, adjacency list, etc.).
4. **Define indexes.** Add only indexes that support known access patterns. Index sprawl degrades write throughput.
5. **Plan consistency and conflict resolution.** Specify consistency level per operation, not globally.
6. **Model for operations.** Include TTL strategy, compaction/cleanup, backup frequency, and monitoring targets.
7. **Prototype and benchmark.** Test with realistic data volumes before committing to schema.
8. **Document the schema contract.** Record access patterns, index rationale, and evolution rules.

## Engine Selection Guide

| Workload | Best Engine | Avoid |
|---|---|---|
| Flexible documents, rich queries | MongoDB | Redis (no rich query) |
| Sub-millisecond cache, sessions | Redis | MongoDB (persistence cost) |
| High-write time-series, IoT | Cassandra / ScyllaDB | MongoDB (write amplification) |
| Serverless key-value, pay-per-request | DynamoDB | Neo4j (wrong model) |
| Highly connected data, recommendations | Neo4j | Cassandra (no traversal) |
| OLTP + analytics hybrid | PostgreSQL + Redis | Pure NoSQL |

## MongoDB

**Schema design rules:**
- Embed when data is always retrieved together and the embedded array is bounded (< ~100 items)
- Reference when the sub-document is large, independently updated, or shared across documents
- Use `_id` as the natural lookup key; avoid separate UUID fields unless required by application
- Apply partial indexes for sparse data; use TTL indexes for expiring documents
- Prefer aggregation pipeline over client-side data transformation

**Byblos CRM patterns:**
- Customers: embed latest contact event, reference full history
- Service contracts: reference customer, embed contract lines
- Interventions: embed location snapshot, reference customer and team

## Redis

**Usage patterns:**
- Cache-aside: application checks Redis → miss → fetch DB → write Redis with TTL
- Write-through: write to Redis and DB simultaneously
- Pub/Sub: use Streams (not Pub/Sub) for reliable message delivery
- Sessions: use Redis with sliding TTL, serialize as JSON
- Rate limiting: INCR + EXPIRE with Lua script for atomicity

**Key naming convention:** `{service}:{entity}:{id}:{field}` — e.g. `crm:customer:42:session`

## Cassandra / ScyllaDB

**Partition key rules:**
- Partition key determines data distribution — choose for uniform spread, not semantic meaning
- Avoid "hot partitions" (high-cardinality keys with unbounded growth)
- Clustering columns define sort order within a partition — design for range queries
- Denormalize aggressively — Cassandra has no joins; one table per access pattern

**Consistency levels:**
- `QUORUM` for most reads/writes (balanced consistency + availability)
- `LOCAL_QUORUM` for multi-region with local-first semantics
- `ONE` only for metrics/logs where loss is acceptable

## DynamoDB

**Single-table design:**
- One table per application context; use `PK` + `SK` composite key
- Overload `PK`/`SK` with prefixes: `CUSTOMER#42`, `ORDER#2024-01-15`
- Use GSIs for alternate access patterns (max 20 per table)
- Use `begins_with`, `between` on SK for range queries within a partition

**Cost control:**
- Use `ProjectionExpression` to fetch only needed attributes
- Prefer `Query` over `Scan` always
- Enable TTL on ephemeral records

## Neo4j

**Graph modeling rules:**
- Nodes = entities (Customer, Service, Technician, Location)
- Relationships = verbs with direction (Customer)-[:SIGNED]->(Contract)
- Put properties on relationships when the property describes the relationship, not the nodes
- Avoid storing large arrays on nodes — model as connected nodes instead

**Cypher patterns:**
- Use parameters (`$param`) in all queries — never string interpolation
- Use `MERGE` for upsert, `MATCH` for read, `CREATE` for guaranteed-new writes
- Profile queries with `EXPLAIN`/`PROFILE` before deploying

## Polyglot Architecture

For Byblos CRM:
- **Primary store**: PostgreSQL (relational core: customers, contracts, invoices)
- **Cache layer**: Redis (sessions, rate limits, hot customer records)
- **Document store**: MongoDB (intervention reports, flexible metadata)
- **Graph (future)**: Neo4j (team assignments, customer relationship graph)

**Cross-engine consistency:**
- Never distribute a transaction across two engines
- Use the outbox pattern for eventual consistency between engines
- Cache invalidation: delete on write, never update-in-place in cache

## Reference Map (Lazy Load)

| Scope | Reference |
|---|---|
| Byblos CRM-specific blueprints and schemas | `references/byblos-blueprints.md` |
| MongoDB schema patterns and indexes | `references/mongodb.md` |
| Redis commands, patterns, and cluster setup | `references/redis.md` |
| Cassandra/ScyllaDB design and operations | `references/cassandra.md` |
| DynamoDB single-table design patterns | `references/dynamodb.md` |
| Neo4j graph modeling and Cypher | `references/neo4j.md` |
| Migration strategies and zero-downtime cutover | `references/migration.md` |
| Performance benchmarking and profiling | `references/performance.md` |
