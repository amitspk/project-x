# Database Health Monitoring - Current State

## ✅ What We Have

### 1. Database Exporters (Configured)

#### MongoDB Exporter
- **Container**: `fyi-widget-mongodb-exporter`
- **Image**: `percona/mongodb_exporter:0.39`
- **Port**: `9216`
- **Status**: ✅ Configured and running
- **Metrics Exposed**: Connection stats, operations, replication, storage, etc.

#### PostgreSQL Exporter
- **Container**: `fyi-widget-postgres-exporter`
- **Image**: `prometheuscommunity/postgres-exporter:v0.15.0`
- **Port**: `9187`
- **Status**: ✅ Configured and running
- **Metrics Exposed**: Connection stats, query performance, table sizes, etc.

---

### 2. Prometheus Scraping

**Configuration**: `prometheus.yml`

```yaml
# MongoDB Exporter
- job_name: 'mongodb'
  static_configs:
    - targets: ['mongodb-exporter:9216']

# PostgreSQL Exporter
- job_name: 'postgresql'
  static_configs:
    - targets: ['postgres-exporter:9187']
```

**Status**: ✅ Prometheus is scraping both exporters every 15 seconds

---

### 3. Database Health Alerts

**Configuration**: `prometheus/alerts.yml`

#### MongoDB Alerts
- **MongoDBDown**: Alert when MongoDB exporter is down (`up{job="mongodb"} == 0`)
  - Severity: **Critical**
  - For: 1 minute

- **MongoDBHighConnections**: Alert when connection usage > 80%
  - Severity: **Warning**
  - For: 5 minutes
  - Formula: `mongodb_connections{state="current"} / mongodb_connections{state="available"} * 100 > 80`

#### PostgreSQL Alerts
- **PostgreSQLDown**: Alert when PostgreSQL exporter is down (`up{job="postgresql"} == 0`)
  - Severity: **Critical**
  - For: 1 minute

- **PostgreSQLHighConnections**: Alert when connection usage > 80%
  - Severity: **Warning**
  - For: 5 minutes
  - Formula: `pg_stat_database_numbackends / pg_settings_max_connections * 100 > 80`

**Status**: ✅ All alerts configured

---

### 4. Grafana Dashboard

**File**: `grafana/dashboards/system-overview.json`

**Database Status Panel**:
- Shows: `sum(up{job=~"mongodb|postgresql"})`
- Displays: Combined status of both database exporters
- Location: System Overview Dashboard

**Status**: ✅ Basic database status visualization exists

---

### 5. Application Health Endpoints

#### API Service Health Check
**Endpoint**: `GET /health`

**What it checks**:
```python
# Checks MongoDB connection
db_healthy = await db_manager.health_check()

# Returns:
{
    "status": "healthy" | "degraded" | "unhealthy",
    "service": "api-service",
    "database": "connected" | "disconnected",
    "job_queue": {...}
}
```

**Status**: ✅ Endpoint exists but **NOT exposed as Prometheus metric**

#### DatabaseManager Health Check
**Method**: `async def health_check() -> bool`

**What it does**:
- Pings MongoDB: `await self.client.admin.command('ping')`
- Lists collections: `await self._database.list_collection_names()`

**Status**: ✅ Basic health check implemented

#### PostgreSQL Health Check
**Method**: `async def health_check() -> dict`

**What it does**:
- Counts publishers: `SELECT COUNT(*) FROM publishers`
- Returns: `{"status": "healthy", "total_publishers": count}`

**Status**: ✅ Basic health check implemented

---

## ⚠️ What's Missing / Could Be Improved

### 1. Dedicated Database Dashboard

**Current State**: Only basic status in system overview

**Missing**:
- Database connection pool metrics
- Query performance metrics (slow queries)
- Database size / growth metrics
- Replication lag (if applicable)
- Lock contention
- Index usage
- Cache hit rates

**Recommendation**: Create a dedicated "Database Health" Grafana dashboard

---

### 2. Application-Level Database Metrics

**Current State**: 
- `health_check_status` metric is **defined but never updated**
- `/health` endpoint exists but doesn't expose metrics

**Missing**:
- Database connection health as Prometheus metric
- Database operation duration metrics
- Database error rate metrics

**Recommendation**: 
- Update `/health` endpoint to set `health_check_status` gauge
- Add periodic health check that updates metrics

---

### 3. More Comprehensive Alerts

**Current State**: Only basic "down" and "high connections" alerts

**Missing Alerts**:
- Slow query alerts (queries taking > X seconds)
- Database size alerts (approaching disk limits)
- Replication lag alerts (if using replica sets)
- High error rate alerts
- Connection pool exhaustion alerts
- Database lock contention alerts

**Recommendation**: Add more granular alerts based on business needs

---

### 4. Database Operation Metrics

**Current State**: We have `mongodb_operations_total` and `mongodb_operation_duration_seconds` metrics defined, but need to verify they're being instrumented

**What to check**:
- Are database operations in `storage_service.py` instrumented?
- Are PostgreSQL operations instrumented?
- Are slow queries being tracked?

---

## 📊 Available MongoDB Metrics (from Exporter)

The MongoDB exporter exposes many metrics. Key ones include:

### Connection Metrics
- `mongodb_connections{state="current"}` - Current connections
- `mongodb_connections{state="available"}` - Available connections
- `mongodb_connections{state="active"}` - Active connections

### Operation Metrics
- `mongodb_opcounters{op="insert"}` - Insert operations
- `mongodb_opcounters{op="query"}` - Query operations
- `mongodb_opcounters{op="update"}` - Update operations
- `mongodb_opcounters{op="delete"}` - Delete operations

### Replication Metrics
- `mongodb_replset_member_health` - Replica set member health
- `mongodb_replset_lag` - Replication lag

### Storage Metrics
- `mongodb_storage_size_bytes` - Storage size
- `mongodb_index_size_bytes` - Index size

---

## 📊 Available PostgreSQL Metrics (from Exporter)

The PostgreSQL exporter exposes many metrics. Key ones include:

### Connection Metrics
- `pg_stat_database_numbackends` - Number of backends
- `pg_settings_max_connections` - Max connections setting

### Performance Metrics
- `pg_stat_database_tup_fetched` - Tuples fetched
- `pg_stat_database_tup_returned` - Tuples returned
- `pg_stat_database_tup_inserted` - Tuples inserted
- `pg_stat_database_tup_updated` - Tuples updated
- `pg_stat_database_tup_deleted` - Tuples deleted

### Query Performance
- `pg_stat_statements_*` - Query statistics (if extension enabled)
- Slow query identification

### Table/Index Metrics
- `pg_stat_user_tables_*` - Table statistics
- `pg_stat_user_indexes_*` - Index statistics

---

## 🎯 Recommended Improvements

### Priority 1: Create Database Health Dashboard

**Create**: `grafana/dashboards/database-health.json`

**Should Include**:
1. **Connection Pool Status**
   - Current vs Max connections
   - Connection usage percentage
   - Connection pool exhaustion warning

2. **Database Size & Growth**
   - Total database size
   - Growth rate over time
   - Index size
   - Available space

3. **Query Performance**
   - Average query duration
   - Slow queries (> 1s)
   - Query rate (queries/sec)
   - Cache hit rate

4. **Operation Metrics**
   - Insert/Update/Delete rates
   - Read/Write operations per second
   - Error rate

5. **Health Status**
   - Database up/down status
   - Replication status (if applicable)
   - Last health check time

---

### Priority 2: Instrument Application Health Checks

**Update**: `fyi_widget_api/api/main.py` `/health` endpoint

**Add**:
```python
from fyi_widget_api.api.metrics import health_check_status

@app.get("/health")
async def health_check():
    # Check MongoDB
    db_healthy = await db_manager.health_check()
    health_check_status.labels(component="mongodb").set(1 if db_healthy else 0)
    
    # Check PostgreSQL (if needed)
    # postgres_healthy = await postgres_repo.health_check()
    # health_check_status.labels(component="postgresql").set(1 if postgres_healthy else 0)
    
    # Overall health
    overall_healthy = db_healthy  # and postgres_healthy
    health_check_status.labels(component="overall").set(1 if overall_healthy else 0)
    
    return {...}
```

---

### Priority 3: Add Database Operation Instrumentation

**Already Defined**: Metrics in `fyi_widget_api/api/metrics.py`
- `mongodb_operations_total`
- `mongodb_operation_duration_seconds`
- `postgresql_operations_total`
- `postgresql_operation_duration_seconds`

**Need to**: Verify these are being used in `storage_service.py` and PostgreSQL operations

---

### Priority 4: Enhanced Alerts

**Add**:
- Database query timeout alerts
- Database disk space alerts
- High error rate alerts
- Slow query alerts (queries > 5 seconds)

---

## 🔍 How to View Current Database Metrics

### 1. In Grafana

**System Overview Dashboard**:
- Navigate to: http://localhost:3000
- Open "System Overview" dashboard
- View "Database Status" panel

### 2. In Prometheus

**Query MongoDB connection usage**:
```
mongodb_connections{state="current"} / mongodb_connections{state="available"} * 100
```

**Query PostgreSQL connection usage**:
```
pg_stat_database_numbackends / pg_settings_max_connections * 100
```

**Check if databases are up**:
```
up{job=~"mongodb|postgresql"}
```

### 3. Direct Exporter Endpoints

**MongoDB Exporter**: http://localhost:9216/metrics
**PostgreSQL Exporter**: http://localhost:9187/metrics

---

## 📝 Summary

| Component | Status | Notes |
|-----------|--------|-------|
| MongoDB Exporter | ✅ Running | Scraping every 15s |
| PostgreSQL Exporter | ✅ Running | Scraping every 15s |
| Prometheus Scraping | ✅ Configured | Both exporters scraped |
| Basic Alerts | ✅ Configured | Down + High connections |
| Application Health Check | ✅ Exists | Not exposed as metric |
| Grafana Dashboard | ⚠️ Basic | Only in system overview |
| Detailed Metrics | ⚠️ Partial | Exporters work, app metrics incomplete |
| Database Dashboard | ❌ Missing | Should create dedicated dashboard |

**Overall**: Basic database health monitoring is in place, but could be enhanced with dedicated dashboards and more comprehensive metrics/alerts.

