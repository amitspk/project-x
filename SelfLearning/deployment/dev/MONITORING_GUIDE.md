# Complete Monitoring Guide - Easy to Follow

**Welcome!** This guide will help you understand and use the monitoring system for your application. Everything is explained in simple terms.

---

## 📖 Table of Contents

1. [What is Monitoring?](#what-is-monitoring)
2. [Quick Start Guide](#quick-start-guide)
3. [How to Access Everything](#how-to-access-everything)
4. [Understanding the Dashboards](#understanding-the-dashboards)
5. [Understanding Alerts](#understanding-alerts)
6. [Common Tasks](#common-tasks)
7. [Troubleshooting](#troubleshooting)
8. [Frequently Asked Questions](#frequently-asked-questions)

---

## What is Monitoring?

Think of monitoring like a **health check system** for your application. Just like a doctor monitors your vital signs (heart rate, blood pressure), this system monitors:

- **Is the application running?** (Like checking if your heart is beating)
- **How fast is it responding?** (Like checking your pulse)
- **Are there any errors?** (Like checking for symptoms)
- **How much work is being done?** (Like checking activity level)

### What We're Monitoring

**Your Application Has Two Main Parts:**
1. **API Service** - Handles requests from users (like a waiter taking orders)
2. **Worker Service** - Processes background jobs (like a chef cooking)

**We're Watching:**
- How many requests are coming in
- How fast things are processing
- If anything breaks
- Resource usage (CPU, memory, disk space)

---

## Quick Start Guide

### First Time Setup

**Step 1: Access Grafana (The Main Dashboard)**
1. Open your web browser
2. Go to: `http://localhost:3000`
3. Login with:
   - Username: `admin`
   - Password: `admin` (you should change this!)
4. You'll see the Grafana home page

**Step 2: Find the System Overview Dashboard**
1. Click on **"Dashboards"** in the left menu (icon looks like four squares)
2. Click **"Browse"**
3. Search for **"System Overview"**
4. Click on it to open

**Step 3: Understanding What You See**
- Green = Good (everything working)
- Yellow = Warning (needs attention)
- Red = Critical (something is wrong)

---

## How to Access Everything

### 🌐 All the Web Interfaces

#### 1. Grafana (Main Dashboard - USE THIS MOST)
- **URL**: http://localhost:3000
- **Username**: admin
- **Password**: admin (change this!)
- **What it is**: Your main monitoring screen - shows graphs, charts, and status
- **When to use**: Daily check-ins, investigating issues

#### 2. Prometheus (Raw Metrics - Advanced)
- **URL**: http://localhost:9090
- **What it is**: Where all the numbers are stored
- **When to use**: Only if you need to query raw data (advanced)

#### 3. Alertmanager (Alerts Manager)
- **URL**: http://localhost:9093
- **What it is**: Shows active alerts and their status
- **When to use**: To see what alerts are firing

---

## Understanding the Dashboards

### 📊 Dashboard Overview

You have **9 dashboards** total. Think of them like different views:

#### 1. System Overview (START HERE)
**What it shows**: Big picture health check

**Top Section:**
- **System Health Status**: Is everything running? (Green = Good)
- **Active Critical Alerts**: How many urgent problems? (Should be 0)
- **Active Warning Alerts**: How many things need attention? (Should be low)
- **Total Services Up**: How many services are running? (Should be 2)

**Main Sections:**
- **API Request Rate**: How busy is the API? (Like customers per hour)
- **API Error Rate**: What percentage of requests fail? (Should be low, ideally 0%)
- **Worker Jobs Processed**: How many jobs completed? (Like tasks finished)
- **Worker Queue Size**: How many jobs waiting? (Like orders in queue - should be low)
- **CPU/Memory/Disk**: Resource usage (like fuel gauge - don't want it too high)

**Bottom Section:**
- **Recent Critical Alerts**: List of urgent problems (should be empty)
- **Service Uptime**: Which services are running
- **Business Metrics**: Key business numbers

**When to check**: First thing in the morning, when something seems wrong

---

#### 2. API Overview Dashboard
**What it shows**: Detailed API health

**Key Things to Look For:**
- **Request Rate**: Should show activity if API is being used
- **Error Rate**: Should be very low (< 1%)
- **Active Requests**: Current requests being processed
- **Response Time**: Should be fast (< 2 seconds)

**When to check**: When API seems slow or has errors

---

#### 3. API Business Metrics Dashboard
**What it shows**: Business-specific API activity

**Key Metrics:**
- **Q&A Requests**: How many questions users are asking
- **Questions Retrieved**: How many questions were fetched
- **Similarity Searches**: How many searches performed
- **Jobs Enqueued**: How many jobs were added to queue

**When to check**: To see how much the application is being used

---

#### 4. API Authentication Dashboard
**What it shows**: Login and authentication activity

**Key Things to Look For:**
- **Auth Success Rate**: Should be high (> 95%)
- **Failed Auth Attempts**: Should be low
- **Total Attempts**: Total login attempts

**When to check**: If there are security concerns or login issues

---

#### 5. API Performance Dashboard
**What it shows**: Speed and performance metrics

**Key Metrics:**
- **Latency Percentiles**: Response times (P50, P95, P99)
  - P50 = Half of requests faster than this
  - P95 = 95% of requests faster than this (most important)
  - P99 = 99% of requests faster than this
- **Throughput**: How many requests per second
- **Answer Word Count**: Average length of answers

**When to check**: When performance seems slow

---

#### 6. Worker Overview Dashboard
**What it shows**: Background job processing health

**Key Metrics:**
- **Jobs Processed Rate**: Jobs completed per second
- **Job Success Rate**: Should be high (> 95%)
- **Queue Size**: Jobs waiting (should be low, < 100)
- **Worker Uptime**: How long worker has been running
- **Processing Errors**: Should be low or zero

**When to check**: When jobs aren't processing or taking too long

---

#### 7. Worker LLM Operations Dashboard
**What it shows**: AI/LLM operation details

**Key Metrics:**
- **LLM Operations Rate**: How many AI calls per second
- **LLM Success Rate**: Should be high (> 95%)
- **Token Usage**: How many tokens used (affects cost)
- **Operation Duration**: How long AI operations take

**When to check**: When AI features seem slow or expensive

---

#### 8. Worker Crawl Operations Dashboard
**What it shows**: Web crawling activity

**Key Metrics:**
- **Crawl Success Rate**: Should be high (> 90%)
- **Crawl Duration**: How long crawls take
- **Content Size**: Size of content crawled
- **Word Count**: Number of words extracted

**When to check**: When crawling seems to fail or be slow

---

#### 9. Worker Content Generation Dashboard
**What it shows**: Content creation metrics

**Key Metrics:**
- **Questions Generated**: How many questions created
- **Embeddings Generated**: How many embeddings created
- **Blogs Processed**: How many blogs processed
- **Content by Publisher**: Breakdown by customer

**When to check**: To see content generation activity

---

## Understanding Alerts

### 🚨 What are Alerts?

Alerts are **automatic notifications** when something goes wrong. Think of them like smoke alarms - they warn you when there's a problem.

### Alert Types

#### Critical Alerts (Red - URGENT!)
These mean something serious is wrong and needs immediate attention:
- **APIDown**: API service stopped working
- **WorkerDown**: Worker service stopped working
- **WorkerQueueBacklogCritical**: Too many jobs waiting (> 500)
- **DatabaseDown**: Database stopped working

**What to do**: Check immediately, may need to restart services

#### Warning Alerts (Yellow - Attention Needed)
These mean something might become a problem:
- **APIHighErrorRate**: Too many errors (> 5%)
- **APIHighLatency**: API is slow (> 2 seconds)
- **WorkerQueueBacklog**: Queue is building up (> 100)
- **HighCPUUsage**: CPU usage is high (> 80%)

**What to do**: Monitor, may resolve itself, but investigate if it persists

### How Alerts Work

1. **Prometheus** checks conditions every 30 seconds
2. If condition is met for required duration → Alert fires
3. **Alertmanager** receives the alert
4. **Email is sent** to configured address
5. Alert shows up in Grafana and Alertmanager UI

### Viewing Alerts

**Method 1: Email (Easiest)**
- Check your email inbox
- Subject will say "CRITICAL" or "Warning"
- Email contains all details

**Method 2: Grafana System Overview**
- Look at top of dashboard
- See "Active Critical Alerts" count
- Check "Recent Critical Alerts" table

**Method 3: Prometheus UI**
- Go to http://localhost:9090/alerts
- See all alerts and their status

**Method 4: Alertmanager UI**
- Go to http://localhost:9093
- Click "Alerts" tab
- See all active alerts

---

## Common Tasks

### Daily Check Routine

**Morning Check (5 minutes):**
1. Open Grafana: http://localhost:3000
2. Go to **System Overview** dashboard
3. Check:
   - ✅ System Health Status = Green/UP
   - ✅ Active Critical Alerts = 0
   - ✅ Active Warning Alerts = Low or 0
   - ✅ All services showing "UP"
4. If everything green → You're good!
5. If anything red/yellow → See troubleshooting section

---

### When Something Goes Wrong

**Step 1: Check System Overview**
- See what's red/yellow
- Note the alert names

**Step 2: Check Your Email**
- Look for alert emails
- Read the description

**Step 3: Identify the Problem**
- Is it API? → Check API Overview dashboard
- Is it Worker? → Check Worker Overview dashboard
- Is it Resources? → Check CPU/Memory/Disk in System Overview

**Step 4: Common Fixes**

**Problem: API is Down**
```
Fix: Restart API service
Command: docker restart fyi-widget-api
Wait: 1-2 minutes, then check again
```

**Problem: Worker is Down**
```
Fix: Restart Worker service
Command: docker restart fyi-widget-worker-service
Wait: 1-2 minutes, then check again
```

**Problem: High Queue Size**
```
What it means: Jobs are piling up
Possible causes:
  - Worker is slow
  - Too many jobs being added
  - Worker crashed and restarted
Fix: Check Worker Overview dashboard for details
```

**Problem: High Error Rate**
```
What it means: Many requests are failing
Fix: Check API logs or API Overview dashboard
Command to see logs: docker logs fyi-widget-api --tail 100
```

**Problem: High CPU/Memory Usage**
```
What it means: System is using too many resources
Fix: May need to scale up or optimize
Check: Which service is using most resources
```

---

### Checking Logs

**Why**: Logs show detailed information about what's happening

**How to View Logs:**

**API Service Logs:**
```bash
docker logs fyi-widget-api --tail 50
```
Shows last 50 lines of API logs

**Worker Service Logs:**
```bash
docker logs fyi-widget-worker-service --tail 50
```
Shows last 50 lines of worker logs

**All Logs (via Loki):**
1. Go to Grafana
2. Click "Explore" in left menu
3. Select "Loki" as data source
4. Search for logs (e.g., `{container="fyi-widget-api"}`)

---

### Restarting Services

**When to restart**: If a service is down or not responding

**Restart API:**
```bash
docker restart fyi-widget-api
```

**Restart Worker:**
```bash
docker restart fyi-widget-worker-service
```

**Restart All Services:**
```bash
# From the deployment/dev directory
docker-compose restart
```

**Wait time**: Services usually restart in 30-60 seconds

---

## Troubleshooting

### Problem: Can't Access Grafana

**Symptoms:**
- Browser shows "Can't reach this page"
- Connection refused error

**Possible Causes:**
1. Grafana container not running
2. Wrong URL/port

**Fix:**
```bash
# Check if Grafana is running
docker ps | grep grafana

# If not running, start it
docker start fyi-widget-grafana

# Wait 10-15 seconds, then try again
```

---

### Problem: Dashboards Show "No Data" or "NaN"

**Symptoms:**
- Dashboard panels show "No data"
- Numbers show as "NaN"

**Possible Causes:**
1. No activity yet (normal for new setup)
2. Metrics endpoint not accessible
3. Prometheus not scraping

**Fix:**
1. **Generate some activity:**
   - Make API calls to your application
   - Enqueue some jobs
   - Wait a few minutes

2. **Check if metrics are being scraped:**
   - Go to Prometheus: http://localhost:9090/targets
   - All targets should show "UP" (green)

3. **If targets are down:**
   - Check service is running: `docker ps`
   - Check metrics endpoint: `curl http://localhost:8005/metrics`

---

### Problem: Alerts Not Firing

**Symptoms:**
- You know something is wrong, but no alert

**Possible Causes:**
1. Alert condition not met (threshold not exceeded)
2. Duration not long enough
3. Service is actually OK

**Fix:**
1. Check alert rules: http://localhost:9090/rules
2. Verify alert is configured correctly
3. Manually check if condition is met
4. Check Alertmanager logs: `docker logs fyi-widget-alertmanager`

---

### Problem: Not Receiving Email Alerts

**Symptoms:**
- Alerts are firing but no email received

**Possible Causes:**
1. Email configuration incorrect
2. Email in spam folder
3. SMTP credentials wrong

**Fix:**
1. **Check spam folder** in your email
2. **Verify email configuration:**
   - Check `alertmanager/alertmanager.yml`
   - Verify email addresses are correct
   - Verify SMTP password is correct (for Gmail, use App Password)
3. **Check Alertmanager logs:**
   ```bash
   docker logs fyi-widget-alertmanager | grep -i email
   ```
   Look for errors
4. **Restart Alertmanager:**
   ```bash
   docker restart fyi-widget-alertmanager
   ```

---

### Problem: High CPU/Memory Usage

**Symptoms:**
- System Overview shows high CPU/Memory (red or yellow)

**What to Do:**
1. **Identify which service:**
   - Check System Overview dashboard
   - See which service is using most

2. **Check for unusual activity:**
   - High request rate?
   - Many jobs processing?
   - Check logs for errors

3. **Short-term fix:**
   - Restart the service
   - May resolve temporary spike

4. **Long-term fix:**
   - May need more resources
   - May need to optimize code
   - May need to scale horizontally

---

### Problem: Dashboard Not Loading

**Symptoms:**
- Dashboard takes forever to load
- Shows timeout error

**Possible Causes:**
1. Prometheus is slow or down
2. Too much data to query
3. Network issues

**Fix:**
1. **Check Prometheus:**
   - Go to http://localhost:9090
   - Should load quickly

2. **Reduce time range:**
   - In Grafana, change from "Last 6 hours" to "Last 1 hour"
   - Easier to load less data

3. **Restart Prometheus:**
   ```bash
   docker restart fyi-widget-prometheus
   ```

---

## Frequently Asked Questions

### Q: How often should I check the dashboards?

**A:** 
- **Daily**: Quick morning check of System Overview (2-3 minutes)
- **When issues arise**: Check relevant detailed dashboard
- **Weekly**: Review trends and performance

### Q: What do the colors mean?

**A:**
- 🟢 **Green**: Everything is good, no action needed
- 🟡 **Yellow**: Warning - monitor but may resolve itself
- 🔴 **Red**: Critical - needs immediate attention

### Q: Why do I see "NaN" values?

**A:** 
- **Normal**: If there's no activity yet (no requests, no jobs)
- **Fix**: Generate some activity, wait a few minutes
- **Not a problem**: Just means no data to show yet

### Q: How do I know if something is really broken?

**A:** Look for:
- 🔴 Red indicators in System Overview
- Critical alerts in your email
- Services showing "DOWN" instead of "UP"
- Error rates > 5%

### Q: What's the difference between Prometheus and Grafana?

**A:**
- **Prometheus**: Stores the raw numbers (like a database)
- **Grafana**: Shows pretty graphs and dashboards (like a report)
- **You mostly use Grafana** - it's easier to understand

### Q: Can I change alert thresholds?

**A:** Yes! But be careful:
- **Location**: `prometheus/alerts.yml`
- **Warning**: Changing thresholds incorrectly can cause too many or too few alerts
- **Recommendation**: Adjust gradually and monitor results

### Q: How long are logs kept?

**A:** 
- **Loki logs**: 7 days (automatically deleted after)
- **Prometheus metrics**: 30 days (default)
- **Dashboard history**: Depends on how far back you scroll

### Q: What if I accidentally break something?

**A:**
- **Don't panic!** Most issues can be fixed
- **Restart services**: Often fixes temporary issues
- **Check logs**: Will tell you what went wrong
- **Rollback changes**: If you modified config files, restore from backup

### Q: How do I add more metrics?

**A:**
- Requires code changes to add instrumentation
- Edit metrics files: `fyi_widget_api/api/metrics.py` or `fyi_widget_worker_service/metrics.py`
- Restart the service
- Metrics appear automatically in Prometheus

---

## Quick Reference Card

### 🌐 Access URLs
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093

### 📊 Key Dashboards
- **System Overview**: Start here - overall health
- **API Overview**: API details
- **Worker Overview**: Worker details

### 🚨 Common Alerts
- **APIDown**: API stopped → Restart API
- **WorkerDown**: Worker stopped → Restart Worker
- **High Error Rate**: Many failures → Check logs

### 🔧 Common Commands
```bash
# Check if services are running
docker ps

# Restart API
docker restart fyi-widget-api

# Restart Worker
docker restart fyi-widget-worker-service

# View API logs
docker logs fyi-widget-api --tail 50

# View Worker logs
docker logs fyi-widget-worker-service --tail 50
```

### ✅ Healthy System Looks Like
- System Health: 🟢 Green
- Critical Alerts: 0
- Warning Alerts: Low
- Error Rate: < 1%
- Queue Size: < 100
- CPU/Memory: < 80%

---

## Getting Help

### If You're Stuck

1. **Check this guide first** - Most common issues are covered
2. **Check logs** - They often tell you what's wrong
3. **Check System Overview** - See what's red/yellow
4. **Check email alerts** - They explain what's wrong

### Useful Commands

**See all running services:**
```bash
docker ps
```

**See service status:**
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

**Check Prometheus targets:**
- Visit http://localhost:9090/targets
- All should be green/UP

**Check Alertmanager status:**
- Visit http://localhost:9093/#/status
- Should show "Active" receivers

---

## Summary

**What You Learned:**
- ✅ How to access monitoring dashboards
- ✅ What each dashboard shows
- ✅ How alerts work
- ✅ How to troubleshoot common issues
- ✅ Daily routine for checking system health

**Remember:**
- **Start with System Overview** - It tells you if anything is wrong
- **Green = Good, Red = Bad** - Simple!
- **Check email alerts** - They explain problems
- **Most issues can be fixed** by restarting services

**You're Ready!** Start monitoring your system with confidence. 🎉

---

*Last Updated: Auto-generated*
*For technical details, see other documentation files in this directory.*

