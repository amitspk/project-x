# DELETE Blog Endpoint - Updated to Use blog_id

**Status**: ✅ Updated and Deployed  
**Date**: October 27, 2025

## What Changed

The DELETE endpoint has been updated to use **`blog_id`** instead of `blog_url` for more efficient and direct deletion.

### Before
```
DELETE /api/v1/questions/by-url?blog_url=https://example.com/post
```

### After
```
DELETE /api/v1/questions/{blog_id}
```

## New Endpoint

**Endpoint**: `DELETE /api/v1/questions/{blog_id}`  
**Authentication**: Admin only (X-Admin-Key)  
**Method**: DELETE  

## Usage

### Basic Request
```bash
curl -X DELETE "http://localhost:8005/api/v1/questions/67193f3e2c8e0c3d4e5f6g7h" \
  -H "X-Admin-Key: admin-secret-key-change-in-production"
```

### Response
```json
{
  "status": "success",
  "status_code": 200,
  "message": "Blog and associated data deleted successfully",
  "result": {
    "blog_deleted": true,
    "questions_deleted": 5,
    "summary_deleted": true,
    "blog_id": "67193f3e2c8e0c3d4e5f6g7h"
  },
  "request_id": "req_abc123",
  "timestamp": "2025-10-27T17:30:00.123Z"
}
```

## Benefits of Using blog_id

✅ **More Efficient**: Direct database lookup by ID  
✅ **Faster**: No need for URL normalization  
✅ **Clearer**: Unique identifier for each blog  
✅ **RESTful**: Follows REST conventions (`/{resource_id}`)  
✅ **No Ambiguity**: blog_id is guaranteed unique  

## Parameters

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| `blog_id` | string | Path | Yes | MongoDB ObjectId of the blog |
| `X-Admin-Key` | string | Header | Yes | Admin API key |

## Error Responses

### 400 Bad Request - Invalid blog_id Format
```json
{
  "status": "error",
  "status_code": 400,
  "message": "Invalid blog_id format: abc123",
  "request_id": "req_abc123"
}
```

### 401 Unauthorized - Missing/Invalid Admin Key
```json
{
  "status": "error",
  "status_code": 401,
  "message": "Admin authentication required",
  "request_id": "req_abc123"
}
```

### 404 Not Found - Blog Doesn't Exist
```json
{
  "status": "error",
  "status_code": 404,
  "message": "Blog not found with id: 67193f3e2c8e0c3d4e5f6g7h",
  "request_id": "req_abc123"
}
```

## How to Get blog_id

### Method 1: From GET /questions/by-url
```bash
# Get blog info including blog_id
curl "http://localhost:8005/api/v1/questions/by-url?blog_url=https://example.com/post" \
  -H "X-API-Key: publisher-api-key"
```

Response includes `blog_id` in `blog_info`:
```json
{
  "result": {
    "blog_info": {
      "id": "67193f3e2c8e0c3d4e5f6g7h",  // ← This is the blog_id
      "title": "My Blog Post",
      "url": "https://example.com/post"
    }
  }
}
```

### Method 2: From Database
```javascript
// MongoDB query
db.raw_blog_content.find({ url: "https://example.com/post" })
// Returns document with _id field
```

## Code Examples

### Python
```python
import requests

def delete_blog(blog_id: str, admin_key: str):
    """Delete a blog by ID (Admin only)."""
    response = requests.delete(
        f'http://localhost:8005/api/v1/questions/{blog_id}',
        headers={'X-Admin-Key': admin_key}
    )
    return response.json()

# Get blog_id first
def get_blog_id(blog_url: str, publisher_key: str):
    """Get blog_id from URL."""
    response = requests.get(
        'http://localhost:8005/api/v1/questions/by-url',
        params={'blog_url': blog_url},
        headers={'X-API-Key': publisher_key}
    )
    data = response.json()
    return data['result']['blog_info']['id']

# Usage
blog_id = get_blog_id('https://myblog.com/post', 'publisher-key')
result = delete_blog(blog_id, 'admin-key')
print(f"Deleted {result['result']['questions_deleted']} questions")
```

### JavaScript/TypeScript
```typescript
async function deleteBlog(blogId: string, adminKey: string) {
  const response = await fetch(
    `http://localhost:8005/api/v1/questions/${blogId}`,
    {
      method: 'DELETE',
      headers: {
        'X-Admin-Key': adminKey,
      },
    }
  );
  return response.json();
}

// Get blog_id first
async function getBlogId(blogUrl: string, publisherKey: string): Promise<string> {
  const response = await fetch(
    `http://localhost:8005/api/v1/questions/by-url?blog_url=${encodeURIComponent(blogUrl)}`,
    {
      headers: {
        'X-API-Key': publisherKey,
      },
    }
  );
  const data = await response.json();
  return data.result.blog_info.id;
}

// Usage
const blogId = await getBlogId('https://myblog.com/post', 'publisher-key');
const result = await deleteBlog(blogId, 'admin-key');
console.log(`Deleted ${result.result.questions_deleted} questions`);
```

### cURL
```bash
# Step 1: Get blog_id
BLOG_ID=$(curl -s "http://localhost:8005/api/v1/questions/by-url?blog_url=https://myblog.com/post" \
  -H "X-API-Key: $PUBLISHER_KEY" | jq -r '.result.blog_info.id')

# Step 2: Delete using blog_id
curl -X DELETE "http://localhost:8005/api/v1/questions/$BLOG_ID" \
  -H "X-Admin-Key: $ADMIN_KEY"
```

## Implementation Details

### Storage Service Changes
```python
async def delete_blog(self, blog_id: str) -> Dict[str, Any]:
    """Delete blog by blog_id instead of blog_url."""
    # Validates ObjectId format
    # Deletes from raw_blog_content, processed_questions, blog_summaries
    # Uses blog_id for all deletions
```

### API Endpoint Changes
```python
@router.delete("/{blog_id}")  # Path parameter instead of query
async def delete_blog_by_id(
    request: Request,
    blog_id: str  # From URL path
) -> Dict[str, Any]:
    """Admin-only deletion by blog_id."""
```

## Migration Notes

If you have existing scripts using the old endpoint:

**Old Way** (blog_url):
```bash
curl -X DELETE "http://localhost:8005/api/v1/questions/by-url?blog_url=$URL" \
  -H "X-Admin-Key: $KEY"
```

**New Way** (blog_id):
```bash
# First get blog_id from URL
BLOG_ID=$(curl -s "http://localhost:8005/api/v1/questions/by-url?blog_url=$URL" \
  -H "X-API-Key: $PUBLISHER_KEY" | jq -r '.result.blog_info.id')

# Then delete by ID
curl -X DELETE "http://localhost:8005/api/v1/questions/$BLOG_ID" \
  -H "X-Admin-Key: $KEY"
```

## Testing

### Test Valid Deletion
```bash
# 1. Get a valid blog_id
curl "http://localhost:8005/api/v1/questions/by-url?blog_url=https://test.com/post" \
  -H "X-API-Key: publisher-key"

# 2. Delete using the blog_id
curl -X DELETE "http://localhost:8005/api/v1/questions/67193f3e2c8e0c3d4e5f6g7h" \
  -H "X-Admin-Key: admin-secret-key-change-in-production"
```

### Test Invalid blog_id
```bash
curl -X DELETE "http://localhost:8005/api/v1/questions/invalid-id" \
  -H "X-Admin-Key: admin-secret-key-change-in-production"
# Should return 400 Bad Request
```

### Test Non-existent blog_id
```bash
curl -X DELETE "http://localhost:8005/api/v1/questions/507f1f77bcf86cd799439011" \
  -H "X-Admin-Key: admin-secret-key-change-in-production"
# Should return 404 Not Found
```

## Summary

✅ **Updated**: DELETE endpoint now uses blog_id  
✅ **Deployed**: Running in containers  
✅ **Efficient**: Direct ID-based deletion  
✅ **RESTful**: Follows REST conventions  
✅ **Admin-Protected**: X-Admin-Key required  

**New Endpoint**: `DELETE /api/v1/questions/{blog_id}`  
**Test it**: http://localhost:8005/docs

---

**Implementation Date**: October 27, 2025  
**Status**: Production Ready ✅

