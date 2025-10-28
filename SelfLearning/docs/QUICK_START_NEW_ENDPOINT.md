# 🚀 Quick Start: Check-and-Load Endpoint

## TL;DR

**New Endpoint**: `GET /api/v1/questions/check-and-load?blog_url={url}`

**What it does**: Intelligently checks if questions exist, returns them if available, or creates processing job if needed.

**Use this instead of**: Calling `/questions/by-url` → checking 404 → calling `/jobs/process`

---

## 🎯 For Publishers/UI Developers

### Single Call Pattern (Recommended)

```javascript
// Just call this one endpoint!
const response = await fetch(
  `/api/v1/questions/check-and-load?blog_url=${encodeURIComponent(pageUrl)}`,
  { headers: { 'X-API-Key': 'your_api_key' } }
);

const { result } = await response.json();

if (result.processing_status === 'ready') {
  // Questions are ready! Show them.
  displayQuestions(result.questions);
} else {
  // Processing started or in progress
  showMessage('Generating questions...');
  // Retry after 60 seconds
}
```

### With Auto-Retry (Production Ready)

```javascript
async function loadQuestionsWithRetry(blogUrl, apiKey, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    const response = await fetch(
      `/api/v1/questions/check-and-load?blog_url=${encodeURIComponent(blogUrl)}`,
      { headers: { 'X-API-Key': apiKey } }
    );
    
    const { result } = await response.json();
    
    if (result.processing_status === 'ready') {
      return result.questions; // Success!
    }
    
    // Wait 60 seconds before retry
    if (i < maxRetries - 1) {
      await new Promise(r => setTimeout(r, 60000));
    }
  }
  
  return null; // Timeout - show error message
}
```

---

## 📋 Response States (3 Possible)

### 1. `ready` - Questions Available ⚡
```json
{
  "result": {
    "processing_status": "ready",
    "questions": [{ /* 10 Q&A */ }],
    "blog_info": { /* metadata */ }
  }
}
```
**Action**: Display questions immediately

### 2. `processing` - Job Running ⏳
```json
{
  "result": {
    "processing_status": "processing",
    "job_id": "uuid-123"
  }
}
```
**Action**: Show "Processing..." and retry in 60s

### 3. `not_started` - Job Just Created 🚀
```json
{
  "result": {
    "processing_status": "not_started",
    "job_id": "uuid-456"
  }
}
```
**Action**: Show "Started processing..." and retry in 60s

---

## ⚡ Performance

- **90% of requests**: Fast path (~100ms)
- **10% of requests**: Job creation (~200ms)
- **Questions cached**: Instant loading on repeat visits

---

## 🧪 Test It

### cURL Example

```bash
# Replace with your API key and URL
curl -X GET \
  'http://localhost:8005/api/v1/questions/check-and-load?blog_url=https://example.com/article' \
  -H 'X-API-Key: pub_your_key_here'
```

### Browser Console

```javascript
fetch('/api/v1/questions/check-and-load?blog_url=' + encodeURIComponent(window.location.href), {
  headers: { 'X-API-Key': 'pub_your_key' }
})
.then(r => r.json())
.then(data => console.log(data.result.processing_status));
```

---

## 🔐 Authentication

**Required**: X-API-Key header

**Get your key**: Contact admin or check publisher dashboard

**Domain validation**: URL must match your registered domain

---

## ❌ Error Handling

```javascript
try {
  const response = await fetch(url, { headers: { 'X-API-Key': apiKey } });
  const data = await response.json();
  
  if (data.status === 'error') {
    if (data.status_code === 401) {
      console.error('Invalid API key');
    } else if (data.status_code === 403) {
      console.error('Domain not authorized');
    }
  }
} catch (error) {
  console.error('Network error:', error);
}
```

---

## 📚 Full Documentation

- **Detailed Guide**: `docs/CHECK_AND_LOAD_ENDPOINT.md`
- **Implementation Details**: `docs/SMART_ENDPOINT_IMPLEMENTATION.md`
- **Swagger UI**: `http://localhost:8005/docs`

---

## 🎉 That's It!

One endpoint. Three states. Simple and fast.

**Questions?** Check the full documentation or test it in Swagger UI.

