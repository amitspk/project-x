# Log Search Guide - How to Find Application Logs

This guide shows you how to search and view logs from your application using Grafana (Loki) and Docker.

---

## 🎯 Quick Start

### Option 1: Grafana Explore (Recommended)
1. Open http://localhost:3000
2. Click **"Explore"** icon (compass/navigation icon in left menu)
3. Select **"Loki"** as data source
4. Enter a query (see examples below)
5. Click **"Run query"**

### Option 2: Docker Logs (Quick Check)
```bash
# View last 50 lines of API logs
docker logs fyi-widget-api --tail 50

# View last 50 lines of Worker logs
docker logs fyi-widget-worker-service --tail 50

# Follow logs in real-time (like tail -f)
docker logs fyi-widget-api -f
```

---

## 📊 Searching Logs in Grafana (Loki)

### Basic Queries

#### 1. View All Logs from API Container
```
{container="fyi-widget-api"}
```

#### 2. View All Logs from Worker Container
```
{container="fyi-widget-worker-service"}
```

#### 3. View Logs from All Containers
```
{container=~".*"}
```

#### 4. View Logs by Container Name Pattern
```
{container=~"fyi-widget-.*"}
```

---

### Filtering by Log Level

#### View Only ERROR Logs
```
{container="fyi-widget-api"} |= "ERROR"
```

#### View Only WARNING Logs
```
{container="fyi-widget-api"} |= "WARNING"
```

#### View Only INFO Logs
```
{container="fyi-widget-api"} |= "INFO"
```

---

### Searching for Specific Text

#### Search for Specific Error
```
{container="fyi-widget-api"} |= "connection failed"
```

#### Search for Request IDs
```
{container="fyi-widget-api"} |= "request_id"
```

#### Search for Specific Endpoint
```
{container="fyi-widget-api"} |= "/api/v1/questions"
```

#### Search for Specific Publisher
```
{container="fyi-widget-api"} |= "momjunction"
```

---

### Advanced Queries

#### Combine Multiple Filters
```
{container="fyi-widget-api"} |= "ERROR" |= "database"
```
Shows: Error logs containing "database"

#### Exclude Certain Logs
```
{container="fyi-widget-api"} != "DEBUG"
```
Shows: All logs except DEBUG level

#### Search with Regex
```
{container="fyi-widget-api"} |~ "request_id.*[0-9]+"
```
Shows: Logs matching regex pattern

#### Filter by Multiple Containers
```
{container=~"fyi-widget-(api|worker-service)"} |= "ERROR"
```
Shows: Errors from both API and Worker

---

## 🔍 Common Search Scenarios

### 1. Find Errors from Last Hour
**Query:**
```
{container="fyi-widget-api"} |= "ERROR"
```
**Time Range:** Last 1 hour

### 2. Search for Specific User/Publisher Activity
**Query:**
```
{container="fyi-widget-api"} |= "publisher_key" |= "pub_E-"
```

### 3. Find Failed API Requests
**Query:**
```
{container="fyi-widget-api"} |= "HTTP" |= "500"
```

### 4. View Worker Job Processing
**Query:**
```
{container="fyi-widget-worker-service"} |= "Processing job"
```

### 5. Find Crawl Failures
**Query:**
```
{container="fyi-widget-worker-service"} |= "Crawl failed"
```

### 6. Search for LLM Errors
**Query:**
```
{container="fyi-widget-worker-service"} |= "LLM" |= "error"
```

### 7. Find Authentication Failures
**Query:**
```
{container="fyi-widget-api"} |= "authentication" |= "failed"
```

### 8. View Database Connection Issues
**Query:**
```
{container=~".*"} |= "database" |= "connection"
```

---

## 🐳 Using Docker Logs Directly

### View Recent Logs

**API Service:**
```bash
# Last 50 lines
docker logs fyi-widget-api --tail 50

# Last 100 lines
docker logs fyi-widget-api --tail 100

# Last 10 minutes
docker logs fyi-widget-api --since 10m
```

**Worker Service:**
```bash
# Last 50 lines
docker logs fyi-widget-worker-service --tail 50

# Last 100 lines
docker logs fyi-widget-worker-service --tail 100
```

### Follow Logs in Real-Time

**Watch API logs as they come in:**
```bash
docker logs fyi-widget-api -f
```
Press `Ctrl+C` to stop following

**Watch Worker logs:**
```bash
docker logs fyi-widget-worker-service -f
```

### Search in Docker Logs

**Search for errors in logs:**
```bash
docker logs fyi-widget-api 2>&1 | grep -i error
```

**Search for specific text:**
```bash
docker logs fyi-widget-api 2>&1 | grep "request_id"
```

**Search with context (show 5 lines before/after):**
```bash
docker logs fyi-widget-api 2>&1 | grep -i -C 5 "error"
```

### Export Logs to File

**Save API logs to file:**
```bash
docker logs fyi-widget-api > api_logs.txt
```

**Save last hour of logs:**
```bash
docker logs fyi-widget-api --since 1h > api_logs_last_hour.txt
```

---

## 📝 LogQL Query Examples (Grafana/Loki)

### Time-Based Queries

**Logs from last 15 minutes:**
```
{container="fyi-widget-api"}
```
*Set time range to "Last 15 minutes" in Grafana*

**Logs from specific time:**
```
{container="fyi-widget-api"}
```
*Set custom time range in Grafana*

### Pattern Matching

**Find logs with JSON:**
```
{container="fyi-widget-api"} | json
```

**Extract specific fields:**
```
{container="fyi-widget-api"} | json | level="ERROR"
```

### Rate Queries

**Count errors per minute:**
```
sum(rate({container="fyi-widget-api"} |= "ERROR" [1m]))
```

---

## 🎯 Practical Examples

### Example 1: Find Why API is Slow

**Step 1: Search for slow requests**
```
{container="fyi-widget-api"} |= "duration" | json | duration > 1000
```

**Step 2: Look for database queries**
```
{container="fyi-widget-api"} |= "mongodb" |= "slow"
```

### Example 2: Investigate Job Failures

**Step 1: Find failed jobs**
```
{container="fyi-widget-worker-service"} |= "Job.*failed"
```

**Step 2: See error details**
```
{container="fyi-widget-worker-service"} |= "ERROR"
```

### Example 3: Track Specific Request

**Step 1: Find request ID in logs**
```
{container="fyi-widget-api"} |= "request_id" |= "abc123"
```

**Step 2: Follow the request through all logs**
```
{container=~".*"} |= "abc123"
```

---

## 🔧 Grafana Explore Interface Tips

### Time Range Selector
- Use top-right time selector
- Choose: "Last 5 minutes", "Last 1 hour", "Last 24 hours"
- Or select custom range

### Logs View Options
- **Logs**: Shows log lines
- **Table**: Shows logs in table format
- **Statistics**: Shows log count

### Useful Buttons
- **Refresh**: Auto-refresh logs
- **Download**: Export logs to file
- **Live**: Real-time log streaming

---

## 📊 Understanding Log Labels

When viewing logs in Grafana, you'll see labels like:
- `container`: Container name (fyi-widget-api, fyi-widget-worker-service)
- `image`: Docker image name
- `id`: Container ID

**Use these in queries:**
```
{container="fyi-widget-api", image=~".*"}
```

---

## 🚨 Common Issues

### No Logs Appearing

**Problem**: Queries return no results

**Solutions**:
1. **Check time range** - Make sure it covers when logs were generated
2. **Check container name** - Use exact name: `fyi-widget-api`
3. **Check if Loki is running**: `docker ps | grep loki`
4. **Check if Promtail is running**: `docker ps | grep promtail`
5. **Check Loki logs**: `docker logs fyi-widget-loki`

### Logs Not Updating

**Problem**: Logs are stale

**Solutions**:
1. Click **"Refresh"** button in Grafana
2. Enable **"Live"** mode in Grafana Explore
3. Check if Promtail is collecting: `docker logs fyi-widget-promtail`

### Too Many Logs

**Problem**: Query returns too many results

**Solutions**:
1. **Add filters**: `|= "ERROR"` or `|= "WARNING"`
2. **Narrow time range**: Use "Last 15 minutes" instead of "Last 24 hours"
3. **Filter by container**: Use `{container="fyi-widget-api"}`

---

## 💡 Quick Reference

### Essential Commands

**View API logs (Docker):**
```bash
docker logs fyi-widget-api --tail 50 -f
```

**View Worker logs (Docker):**
```bash
docker logs fyi-widget-worker-service --tail 50 -f
```

**Search logs in Grafana:**
```
{container="fyi-widget-api"} |= "ERROR"
```

**Find specific request:**
```
{container="fyi-widget-api"} |= "request_id_here"
```

### Common LogQL Patterns

| What You Want | LogQL Query |
|---------------|-------------|
| All API logs | `{container="fyi-widget-api"}` |
| Only errors | `{container="fyi-widget-api"} \|= "ERROR"` |
| Specific text | `{container="fyi-widget-api"} \|= "text"` |
| Multiple containers | `{container=~"fyi-widget-.*"}` |
| Exclude text | `{container="fyi-widget-api"} != "DEBUG"` |

---

## 📚 More Resources

- **LogQL Documentation**: https://grafana.com/docs/loki/latest/logql/
- **Grafana Explore Guide**: https://grafana.com/docs/grafana/latest/explore/

---

## ✅ Summary

**For Quick Checks:**
- Use `docker logs <container>` command

**For Deep Analysis:**
- Use Grafana Explore with LogQL queries

**Best Practice:**
- Use Grafana for centralized log search
- Use Docker logs for quick container-specific checks

---

*Happy Log Searching!* 🔍

