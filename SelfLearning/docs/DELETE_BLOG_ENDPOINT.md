# DELETE Blog Endpoint - Documentation

**Endpoint**: `DELETE /questions/by-url`  
**Status**: ✅ Implemented  
**Date**: October 27, 2025

## Overview

Delete a blog and all associated data (content, questions, summary) from the system. This is a **destructive operation** that cannot be undone.

## Authentication

**Admin Only**: Requires valid admin API key in `X-Admin-Key` header.

⚠️ This is a protected admin operation. Regular publishers cannot delete content.

## Request

### Method
```
DELETE /questions/by-url
```

### Headers
```
X-Admin-Key: <admin-api-key>
Content-Type: application/json
```

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `blog_url` | string | Yes | The full URL of the blog to delete |

### Example Request

```bash
curl -X DELETE "http://localhost:8000/questions/by-url?blog_url=https://example.com/my-blog-post" \
  -H "X-Admin-Key: admin-secret-key-change-in-production"
```

## Response

### Success Response (200)

```json
{
  "status": "success",
  "status_code": 200,
  "message": "Blog and associated data deleted successfully",
  "result": {
    "blog_deleted": true,
    "questions_deleted": 5,
    "summary_deleted": true,
    "blog_url": "https://example.com/my-blog-post"
  },
  "request_id": "req_abc123",
  "timestamp": "2025-10-27T14:30:00.123Z"
}
```

#### Result Fields

| Field | Type | Description |
|-------|------|-------------|
| `blog_deleted` | boolean | Whether the blog content was deleted |
| `questions_deleted` | integer | Number of questions deleted |
| `summary_deleted` | boolean | Whether the summary was deleted |
| `blog_url` | string | The URL of the deleted blog |

### Error Responses

#### 401 Unauthorized
```json
{
  "status": "error",
  "status_code": 401,
  "message": "Authentication required",
  "error": "X-API-Key header missing or invalid",
  "request_id": "req_abc123",
  "timestamp": "2025-10-27T14:30:00.123Z"
}
```


#### 404 Not Found
```json
{
  "status": "error",
  "status_code": 404,
  "message": "Blog not found",
  "error": "Blog not found: https://example.com/non-existent",
  "request_id": "req_abc123",
  "timestamp": "2025-10-27T14:30:00.123Z"
}
```

## What Gets Deleted

When you delete a blog, the following data is removed:

1. **Blog Content** (`raw_blog_content` collection)
   - Original blog text
   - Metadata (title, word count, etc.)
   - Timestamps

2. **Questions** (`processed_questions` collection)
   - All question-answer pairs
   - Question embeddings
   - Icons and metadata

3. **Summary** (`blog_summaries` collection)
   - Summary text
   - Key points
   - Summary embedding

## Security Features

✅ **Admin Authentication Required**: Must provide valid admin API key  
✅ **Restricted Access**: Only admins can delete content  
✅ **URL Normalization**: Automatic URL normalization  
✅ **Audit Logging**: All deletion requests are logged with admin credentials  
✅ **Request Tracking**: Unique request ID for tracing  
✅ **Destructive Protection**: Clear warnings about data loss  

## Use Cases

### 1. Remove Outdated Content
```bash
# Delete old blog that's been removed from site (Admin only)
curl -X DELETE "http://localhost:8000/questions/by-url?blog_url=https://myblog.com/old-post" \
  -H "X-Admin-Key: $ADMIN_KEY"
```

### 2. Fix Processing Errors
```bash
# Delete incorrectly processed blog to retry (Admin only)
curl -X DELETE "http://localhost:8000/questions/by-url?blog_url=https://myblog.com/blog-post" \
  -H "X-Admin-Key: $ADMIN_KEY"

# Then publisher can reprocess
curl -X GET "http://localhost:8000/questions/check-and-load?blog_url=https://myblog.com/blog-post" \
  -H "X-API-Key: $PUBLISHER_API_KEY"
```

### 3. Compliance (GDPR/Right to be Forgotten)
```bash
# Delete blog content per user request (Admin only)
curl -X DELETE "http://localhost:8000/questions/by-url?blog_url=https://myblog.com/user-content" \
  -H "X-Admin-Key: $ADMIN_KEY"
```

### 4. Bulk Deletion Script

```bash
#!/bin/bash
# Delete multiple blogs

URLS=(
  "https://myblog.com/post1"
  "https://myblog.com/post2"
  "https://myblog.com/post3"
)

for url in "${URLS[@]}"; do
  echo "Deleting: $url"
  curl -X DELETE "http://localhost:8000/questions/by-url?blog_url=$url" \
    -H "X-Admin-Key: $ADMIN_KEY"
  echo ""
done
```

## Code Examples

### Python
```python
import requests

def delete_blog(blog_url: str, admin_key: str):
    """Delete a blog and all associated data (Admin only)."""
    response = requests.delete(
        'http://localhost:8000/questions/by-url',
        params={'blog_url': blog_url},
        headers={'X-Admin-Key': admin_key}
    )
    return response.json()

# Usage (Admin only)
result = delete_blog(
    blog_url='https://myblog.com/post',
    admin_key='admin-secret-key'
)

print(f"Deleted: {result['result']['questions_deleted']} questions")
```

### JavaScript/TypeScript
```typescript
async function deleteBlog(blogUrl: string, adminKey: string) {
  const response = await fetch(
    `http://localhost:8000/questions/by-url?blog_url=${encodeURIComponent(blogUrl)}`,
    {
      method: 'DELETE',
      headers: {
        'X-Admin-Key': adminKey,
      },
    }
  );
  
  return response.json();
}

// Usage (Admin only)
const result = await deleteBlog(
  'https://myblog.com/post',
  'admin-secret-key'
);

console.log(`Deleted ${result.result.questions_deleted} questions`);
```

### cURL
```bash
# Admin only
curl -X DELETE \
  "http://localhost:8000/questions/by-url?blog_url=https://myblog.com/post" \
  -H "X-Admin-Key: admin-secret-key" \
  -H "Content-Type: application/json"
```

## Best Practices

### ✅ DO

- **Verify URL**: Double-check the URL before deleting
- **Check Response**: Verify the deletion summary
- **Log Deletions**: Keep audit trail of deleted content
- **Use in Scripts**: Automate bulk deletions carefully
- **Test First**: Test with non-production data first

### ❌ DON'T

- **Mass Delete Without Confirmation**: Could lose valuable data
- **Delete Without Backup**: Consider exporting data first
- **Share API Keys**: Keep API keys secure
- **Skip Error Handling**: Always handle errors properly
- **Delete by Guessing URLs**: Verify URLs exist first

## Testing

### Test with Existing Blog

1. **Check if blog exists**:
```bash
curl -X GET "http://localhost:8000/questions/by-url?blog_url=https://myblog.com/test" \
  -H "X-API-Key: $API_KEY"
```

2. **Delete the blog**:
```bash
curl -X DELETE "http://localhost:8000/questions/by-url?blog_url=https://myblog.com/test" \
  -H "X-API-Key: $API_KEY"
```

3. **Verify deletion** (should return 404):
```bash
curl -X GET "http://localhost:8000/questions/by-url?blog_url=https://myblog.com/test" \
  -H "X-API-Key: $API_KEY"
```

### Test Without Admin Key

Try to delete without admin key (should fail with 401):
```bash
curl -X DELETE "http://localhost:8000/questions/by-url?blog_url=https://myblog.com/test" \
  -H "X-API-Key: $PUBLISHER_API_KEY"  # Wrong - needs admin key!
```

## Troubleshooting

### Issue: "Blog not found" (404)
**Cause**: Blog URL doesn't exist in database  
**Solution**: Verify the exact URL in database or check if already deleted

### Issue: "Authentication required" (401)
**Cause**: Invalid or missing admin API key  
**Solution**: Ensure you're using X-Admin-Key header with valid admin credentials

### Issue: Partial deletion (some items not deleted)
**Cause**: Data might not exist (e.g., summary not generated)  
**Solution**: Check deletion result - this is normal if data was never created

## Related Endpoints

- `GET /questions/by-url` - Get questions for a blog
- `GET /questions/check-and-load` - Load or process blog
- `POST /publishers/onboard` - Onboard new publisher
- `GET /publishers/{id}` - Get publisher details

## Implementation Details

### Database Operations

The endpoint performs these MongoDB operations:

```javascript
// Delete blog content
db.raw_blog_content.deleteOne({ url: blog_url })

// Delete all questions
db.processed_questions.deleteMany({ blog_url: blog_url })

// Delete summary
db.blog_summaries.deleteOne({ blog_url: blog_url })
```

### Transaction Safety

⚠️ **Note**: Deletions are not wrapped in a transaction. If an error occurs mid-deletion:
- Some data may be deleted while other data remains
- Check the response to see what was deleted
- Rare edge case - usually all operations succeed or all fail

## Performance

- **Speed**: Fast for single blogs (~50-100ms)
- **Bulk**: Use scripts for bulk operations
- **Concurrent**: Safe for concurrent deletion requests
- **Impact**: Minimal impact on database

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2025-10-27 | 1.0 | Initial implementation |

---

**Endpoint**: `DELETE /questions/by-url`  
**Status**: ✅ Production Ready  
**Security**: ✅ Authenticated & Authorized  
**Destructive**: ⚠️ Yes - Cannot be undone

