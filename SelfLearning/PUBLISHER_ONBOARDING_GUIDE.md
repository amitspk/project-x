# Publisher Onboarding System

## Overview

The Publisher Onboarding System allows you to manage multiple publishers (blog platforms) with custom configurations for content processing. Each publisher can have:

- **Custom Question Count**: Number of Q&A pairs per blog
- **LLM Model Selection**: Choice of GPT or Claude models
- **Temperature & Tokens**: Fine-tune LLM generation
- **Processing Options**: Enable/disable summaries and embeddings
- **Rate Limits**: Daily blog processing limits
- **UI Customization**: Theme colors and icon styles
- **Subscription Tiers**: free, basic, pro, enterprise

## Architecture

```
┌─────────────────┐
│   API Service   │
│  (Port 8005)    │
│                 │
│  Publisher API  │◄──── PostgreSQL (Publisher Configs)
│  Job Queue API  │
└────────┬────────┘
         │
         │ Job Queue (MongoDB)
         │
         ▼
┌─────────────────┐
│ Worker Service  │
│                 │
│ 1. Fetch Config │◄──── PostgreSQL (by domain)
│ 2. Process Blog │
│ 3. Use Config   │
└─────────────────┘
```

## Database Schema

### PostgreSQL (`publishers` table)

```sql
CREATE TABLE publishers (
    id VARCHAR PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    api_key VARCHAR(64) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'trial',
    config JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP,
    total_blogs_processed INTEGER DEFAULT 0,
    total_questions_generated INTEGER DEFAULT 0,
    subscription_tier VARCHAR(50) DEFAULT 'free'
);
```

### Configuration Schema (`config` JSON field)

```json
{
  "questions_per_blog": 5,
  "llm_model": "gpt-4o-mini",
  "temperature": 0.7,
  "max_tokens": 2000,
  "generate_summary": true,
  "generate_embeddings": true,
  "daily_blog_limit": 100,
  "custom_question_prompt": null,
  "custom_summary_prompt": null,
  "ui_theme_color": "#6366f1",
  "ui_icon_style": "emoji"
}
```

## API Endpoints

### 1. Onboard Publisher

**POST** `/api/v1/publishers/onboard`

Create a new publisher account.

**Request:**
```json
{
  "name": "Tech Blog Inc",
  "domain": "techblog.com",
  "email": "admin@techblog.com",
  "config": {
    "questions_per_blog": 7,
    "llm_model": "gpt-4o-mini",
    "temperature": 0.8,
    "daily_blog_limit": 50
  },
  "subscription_tier": "pro"
}
```

**Response:**
```json
{
  "success": true,
  "publisher": {
    "id": "uuid-here",
    "name": "Tech Blog Inc",
    "domain": "techblog.com",
    "email": "admin@techblog.com",
    "status": "trial",
    "config": { ... },
    "created_at": "2024-01-01T00:00:00Z",
    "subscription_tier": "pro"
  },
  "api_key": "pub_xxxxxxxxxxxxxxxxxxxx",
  "message": "Publisher onboarded successfully"
}
```

**Note**: The `api_key` is only returned on creation. Store it securely!

### 2. Get Publisher by ID

**GET** `/api/v1/publishers/{publisher_id}`

Retrieve publisher details.

### 3. Get Publisher by Domain

**GET** `/api/v1/publishers/by-domain/{domain}`

Useful for checking if a domain is already onboarded.

### 4. Update Publisher

**PUT** `/api/v1/publishers/{publisher_id}`

**Headers**: `X-API-Key: pub_xxxx`

**Request:**
```json
{
  "config": {
    "questions_per_blog": 10,
    "llm_model": "gpt-4o"
  },
  "status": "active"
}
```

### 5. List Publishers

**GET** `/api/v1/publishers/?status=active&page=1&page_size=50`

List all publishers with pagination.

### 6. Get Publisher Config

**GET** `/api/v1/publishers/{publisher_id}/config`

Retrieve only the configuration object.

### 7. Delete Publisher (Soft Delete)

**DELETE** `/api/v1/publishers/{publisher_id}`

**Headers**: `X-API-Key: pub_xxxx`

Marks publisher as `inactive`.

## How It Works

### 1. Publisher Onboarding

```bash
# Onboard a new publisher
curl -X POST http://localhost:8005/api/v1/publishers/onboard \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Blog",
    "domain": "myblog.com",
    "email": "admin@myblog.com",
    "config": {
      "questions_per_blog": 8
    }
  }'
```

### 2. Blog Processing

```bash
# Process a blog (API extracts domain)
curl -X POST http://localhost:8005/api/v1/jobs/process \
  -H "Content-Type: application/json" \
  -d '{
    "blog_url": "https://myblog.com/my-post"
  }'
```

### 3. Worker Picks Up Job

```python
# Worker extracts domain from URL
domain = extract_domain("https://myblog.com/my-post")  # => "myblog.com"

# Worker fetches publisher config
publisher = await publisher_repo.get_publisher_by_domain(domain)

# Worker uses custom config
num_questions = publisher.config.questions_per_blog  # => 8
llm_model = publisher.config.llm_model              # => "gpt-4o-mini"

# Generate questions with custom settings
questions = await llm_service.generate_questions(
    content=content,
    title=title,
    num_questions=num_questions
)
```

### 4. Fallback Behavior

If a publisher is **not found** for a domain, the worker uses **default configuration**:

```python
default_config = PublisherConfig(
    questions_per_blog=5,
    llm_model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=2000,
    generate_summary=True,
    generate_embeddings=True
)
```

## Configuration Options

### LLM Models

- `gpt-4o-mini` (default, fast, cost-effective)
- `gpt-4o` (most capable)
- `gpt-3.5-turbo` (fast, cheap)
- `claude-3-5-sonnet-20241022`
- `claude-3-5-haiku-20241022`

### Questions Per Blog

- **Minimum**: 1
- **Maximum**: 20
- **Default**: 5
- **Recommended**: 5-10

### Temperature

- **Range**: 0.0 - 1.0
- **Default**: 0.7
- Lower = More deterministic
- Higher = More creative

### Max Tokens

- **Range**: 100 - 4000
- **Default**: 2000
- Higher = Longer responses, higher cost

### Subscription Tiers

- **free**: Limited usage
- **basic**: Standard features
- **pro**: Higher limits
- **enterprise**: Custom limits, priority support

## Testing

### Run Full Test Suite

```bash
chmod +x test_publisher_onboarding.sh
./test_publisher_onboarding.sh
```

### Manual Testing

```bash
# 1. Start services
./start_split_services.sh

# 2. Onboard Baeldung with 8 questions
curl -X POST http://localhost:8005/api/v1/publishers/onboard \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Baeldung",
    "domain": "baeldung.com",
    "email": "contact@baeldung.com",
    "config": {
      "questions_per_blog": 8
    }
  }'

# 3. Process a Baeldung blog
curl -X POST http://localhost:8005/api/v1/jobs/process \
  -H "Content-Type: application/json" \
  -d '{
    "blog_url": "https://www.baeldung.com/java-threadlocal"
  }'

# 4. Verify 8 questions (not default 5)
curl "http://localhost:8005/api/v1/questions/by-url?blog_url=https://www.baeldung.com/java-threadlocal"
```

## Production Deployment

### Environment Variables

```bash
# API Service
POSTGRES_URL=postgresql+asyncpg://user:pass@host:5432/db
MONGODB_URL=mongodb://host:27017
OPENAI_API_KEY=sk-xxxxx

# Worker Service
POSTGRES_URL=postgresql+asyncpg://user:pass@host:5432/db
MONGODB_URL=mongodb://host:27017
OPENAI_API_KEY=sk-xxxxx
```

### Docker Compose

```bash
# Start all services
docker-compose -f docker-compose.split-services.yml up -d

# Services:
# - MongoDB: 27017
# - PostgreSQL: 5432
# - API Service: 8005
# - Worker Service: (background)
```

### Health Checks

```bash
# Check API Service
curl http://localhost:8005/health

# Check PostgreSQL
curl http://localhost:8005/health | jq '.postgresql'
```

## Security

### API Key Management

1. **Storage**: API keys are hashed before storage (use `pub_` prefix)
2. **Access**: API keys required for updates and deletions
3. **Header**: `X-API-Key: pub_xxxxxxxxxxxxxx`

### Authentication

```bash
# Update with API key
curl -X PUT http://localhost:8005/api/v1/publishers/{id} \
  -H "X-API-Key: pub_xxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{"status": "active"}'
```

## Monitoring

### Usage Tracking

The system automatically tracks:
- `total_blogs_processed`
- `total_questions_generated`
- `last_active_at`

```bash
# Check usage
curl http://localhost:8005/api/v1/publishers/{id} | jq '.publisher | {
  total_blogs_processed,
  total_questions_generated,
  last_active_at
}'
```

### Rate Limiting

Configure `daily_blog_limit` to prevent abuse:

```json
{
  "config": {
    "daily_blog_limit": 100
  }
}
```

## Best Practices

1. **Start Small**: Begin with 5 questions per blog
2. **Test First**: Use trial mode before going active
3. **Monitor Costs**: Higher question counts = higher LLM costs
4. **Custom Prompts**: Use for domain-specific content
5. **Rate Limits**: Set appropriate daily limits
6. **Regular Updates**: Keep configs tuned to performance

## Troubleshooting

### Publisher Not Found

**Issue**: Worker uses default config
**Solution**: Check domain normalization (no `www`, no protocol)

```bash
# These are equivalent:
# https://www.example.com
# http://example.com
# example.com
```

### Wrong Question Count

**Issue**: Generated X questions but config says Y
**Solution**: Check worker logs for "Using config for publisher" message

### API Key Invalid

**Issue**: 403 Unauthorized
**Solution**: Ensure `X-API-Key` header is set correctly

## Examples

### E-commerce Blog (Product Reviews)

```json
{
  "name": "ShopBlog",
  "domain": "shopblog.com",
  "config": {
    "questions_per_blog": 6,
    "llm_model": "gpt-4o-mini",
    "temperature": 0.6,
    "custom_question_prompt": "Generate product-focused Q&A pairs..."
  }
}
```

### Technical Documentation

```json
{
  "name": "DevDocs",
  "domain": "devdocs.io",
  "config": {
    "questions_per_blog": 10,
    "llm_model": "gpt-4o",
    "temperature": 0.5,
    "custom_question_prompt": "Generate technical Q&A pairs..."
  }
}
```

### News Portal

```json
{
  "name": "NewsHub",
  "domain": "newshub.com",
  "config": {
    "questions_per_blog": 5,
    "llm_model": "gpt-3.5-turbo",
    "temperature": 0.8,
    "daily_blog_limit": 500
  }
}
```

## Roadmap

- [ ] Publisher dashboard UI
- [ ] Analytics and reporting
- [ ] Webhook notifications
- [ ] A/B testing for configs
- [ ] Multi-language support
- [ ] Custom embedding models
- [ ] Publisher API rate limiting
- [ ] Billing integration

## Support

For issues or questions:
- Check logs: `docker-compose logs api-service`
- Run health check: `curl http://localhost:8005/health`
- Test endpoint: `./test_publisher_onboarding.sh`

