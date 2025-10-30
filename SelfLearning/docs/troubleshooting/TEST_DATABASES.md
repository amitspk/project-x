# Testing Databases on VPS

## ✅ Quick Health Checks

### Check Container Status

```bash
# Check if containers are running
docker ps | grep -E "mongodb|postgres"

# Should show:
# fyi-widget-mongodb    Up X minutes
# fyi-widget-postgres   Up X minutes
```

### Check Logs

```bash
# MongoDB logs
docker logs fyi-widget-mongodb --tail 20

# PostgreSQL logs
docker logs fyi-widget-postgres --tail 20

# Follow logs in real-time
docker logs -f fyi-widget-mongodb
```

---

## 🧪 Testing MongoDB

### Test 1: Basic Connection

```bash
# Test MongoDB is responding
docker exec fyi-widget-mongodb mongosh --eval "db.runCommand('ping')" --quiet

# Expected output:
# { ok: 1 }
```

### Test 2: Connect Interactively

```bash
# Connect to MongoDB shell
docker exec -it fyi-widget-mongodb mongosh -u admin -p

# When prompted, enter your MongoDB password
# Then try:
> db.runCommand({connectionStatus: 1})
> show dbs
> use blog_qa_db
> show collections
```

### Test 3: Create Test Data

```bash
# One-liner to create and read test data
docker exec fyi-widget-mongodb mongosh -u admin -p --quiet --eval "
  use blog_qa_db;
  db.test.insertOne({message: 'Hello from VPS', timestamp: new Date()});
  db.test.find().pretty();
"

# Or interactively:
docker exec -it fyi-widget-mongodb mongosh -u admin -p
> use blog_qa_db
> db.test.insertOne({message: "Hello", timestamp: new Date()})
> db.test.find()
```

### Test 4: Check Database Info

```bash
# List databases
docker exec fyi-widget-mongodb mongosh -u admin -p --quiet --eval "db.adminCommand('listDatabases')"

# Check current database stats
docker exec fyi-widget-mongodb mongosh -u admin -p --quiet --eval "
  use blog_qa_db;
  db.stats();
"
```

---

## 🧪 Testing PostgreSQL

### Test 1: Basic Connection

```bash
# Test PostgreSQL is ready
docker exec fyi-widget-postgres pg_isready -U postgres

# Expected output:
# fyi-widget-postgres:5432 - accepting connections
```

### Test 2: Connect Interactively

```bash
# Connect to PostgreSQL
docker exec -it fyi-widget-postgres psql -U postgres -d blog_qa_publishers

# Inside psql, try:
# \l              # List databases
# \dt             # List tables
# \du             # List users
# SELECT version(); # PostgreSQL version
```

### Test 3: Create Test Data

```bash
# One-liner to create and read test data
docker exec fyi-widget-postgres psql -U postgres -d blog_qa_publishers -c "
  CREATE TABLE IF NOT EXISTS test_table (
    id SERIAL PRIMARY KEY,
    message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
  );
  INSERT INTO test_table (message) VALUES ('Hello from VPS');
  SELECT * FROM test_table;
"
```

### Test 4: Check Database Info

```bash
# List all databases
docker exec fyi-widget-postgres psql -U postgres -c "\l"

# List tables in blog_qa_publishers
docker exec fyi-widget-postgres psql -U postgres -d blog_qa_publishers -c "\dt"

# Check database size
docker exec fyi-widget-postgres psql -U postgres -d blog_qa_publishers -c "
  SELECT pg_size_pretty(pg_database_size('blog_qa_publishers'));
"
```

---

## 🌐 Test Network Connectivity

### Test Containers Can See Each Other

```bash
# From MongoDB container, ping PostgreSQL
docker exec fyi-widget-mongodb ping -c 2 postgres

# From PostgreSQL container, ping MongoDB
docker exec fyi-widget-postgres ping -c 2 mongodb

# Check network
docker network inspect fyi-widget-network | grep -A 10 "Containers"
```

### Test Connection Strings

```bash
# Test MongoDB connection string (from within network)
docker run --rm --network fyi-widget-network \
  mongo:7.0 mongosh \
  "mongodb://admin:YOUR_PASSWORD@mongodb:27017/blog_qa_db?authSource=admin" \
  --eval "db.runCommand('ping')"

# Test PostgreSQL connection string
docker run --rm --network fyi-widget-network \
  postgres:16-alpine \
  psql "postgresql://postgres:YOUR_PASSWORD@postgres:5432/blog_qa_publishers" \
  -c "SELECT version();"
```

---

## 📊 Comprehensive Test Script

Create this script to test everything:

```bash
cat > test-databases.sh << 'EOF'
#!/bin/bash

echo "🧪 Testing Databases..."
echo ""

echo "1️⃣  Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "NAME|mongodb|postgres"
echo ""

echo "2️⃣  MongoDB Connection:"
docker exec fyi-widget-mongodb mongosh --eval "db.runCommand('ping')" --quiet && echo "✅ MongoDB: OK" || echo "❌ MongoDB: FAILED"
echo ""

echo "3️⃣  PostgreSQL Connection:"
docker exec fyi-widget-postgres pg_isready -U postgres > /dev/null && echo "✅ PostgreSQL: OK" || echo "❌ PostgreSQL: FAILED"
echo ""

echo "4️⃣  Network Connectivity:"
docker exec fyi-widget-mongodb ping -c 1 postgres > /dev/null 2>&1 && echo "✅ MongoDB → PostgreSQL: OK" || echo "❌ MongoDB → PostgreSQL: FAILED"
docker exec fyi-widget-postgres ping -c 1 mongodb > /dev/null 2>&1 && echo "✅ PostgreSQL → MongoDB: OK" || echo "❌ PostgreSQL → MongoDB: FAILED"
echo ""

echo "5️⃣  Database List:"
echo "MongoDB databases:"
docker exec fyi-widget-mongodb mongosh --eval "db.adminCommand('listDatabases').databases.map(d => d.name)" --quiet 2>/dev/null || echo "Could not list databases"
echo "PostgreSQL databases:"
docker exec fyi-widget-postgres psql -U postgres -t -c "SELECT datname FROM pg_database WHERE datistemplate = false;" 2>/dev/null || echo "Could not list databases"
echo ""

echo "✅ All tests completed!"
EOF

chmod +x test-databases.sh
./test-databases.sh
```

---

## 🔍 Detailed Diagnostics

### MongoDB Diagnostics

```bash
# Check MongoDB version
docker exec fyi-widget-mongodb mongosh --eval "db.version()"

# Check MongoDB server status
docker exec fyi-widget-mongodb mongosh --eval "db.serverStatus().version"

# Check database size
docker exec fyi-widget-mongodb mongosh --eval "
  use blog_qa_db;
  db.stats(1024*1024);  // Size in MB
"
```

### PostgreSQL Diagnostics

```bash
# Check PostgreSQL version
docker exec fyi-widget-postgres psql -U postgres -c "SELECT version();"

# Check database connections
docker exec fyi-widget-postgres psql -U postgres -c "
  SELECT count(*) as active_connections 
  FROM pg_stat_activity 
  WHERE datname = 'blog_qa_publishers';
"

# Check table sizes
docker exec fyi-widget-postgres psql -U postgres -d blog_qa_publishers -c "
  SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
  FROM pg_tables
  WHERE schemaname = 'public';
"
```

---

## ✅ Success Checklist

Your databases are working correctly if:

- [ ] Containers show "Up" status
- [ ] MongoDB `ping` returns `{ ok: 1 }`
- [ ] PostgreSQL `pg_isready` returns "accepting connections"
- [ ] Containers can ping each other (network connectivity)
- [ ] Can connect interactively to both databases
- [ ] Can create and read test data in both databases
- [ ] Logs show no errors
- [ ] Health checks pass (if configured)

---

## 🐛 Troubleshooting

### MongoDB Connection Fails

```bash
# Check authentication
docker logs fyi-widget-mongodb | grep -i auth

# Test with credentials
docker exec fyi-widget-mongodb mongosh -u admin -p --eval "db.runCommand('ping')"
```

### PostgreSQL Connection Fails

```bash
# Check if PostgreSQL is accepting connections
docker exec fyi-widget-postgres pg_isready -U postgres -v

# Check logs
docker logs fyi-widget-postgres | tail -20
```

### Network Issues

```bash
# Verify network exists
docker network ls | grep fyi-widget-network

# Check network details
docker network inspect fyi-widget-network

# Verify containers are on network
docker network inspect fyi-widget-network | grep -A 5 "Containers"
```

---

## 🚀 Quick Test Commands

```bash
# All-in-one test
docker ps | grep -E "mongodb|postgres" && \
docker exec fyi-widget-mongodb mongosh --eval "db.runCommand('ping')" --quiet && \
docker exec fyi-widget-postgres pg_isready -U postgres && \
echo "✅ All databases healthy!" || echo "❌ Issue detected"
```

