# Publisher Onboarding - Quick Reference Card

## 🚀 Start Services

```bash
# Start with Docker
docker-compose -f docker-compose.split-services.yml up -d

# OR start locally
./start_split_services.sh

# Check health
curl http://localhost:8005/health
```

## 📝 Onboard a Publisher

```bash
curl -X POST http://localhost:8005/api/v1/publishers/onboard \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Baeldung",
    "domain": "baeldung.com",
    "email": "contact@baeldung.com",
    "config": {
      "questions_per_blog": 8,
      "llm_model": "gpt-4o-mini",
      "temperature": 0.75,
      "daily_blog_limit": 100
    },
    "subscription_tier": "enterprise"
  }'
```

**Response**: Save the `api_key`! It's only returned once.

## 🔍 Get Publisher Info

```bash
# By ID
curl http://localhost:8005/api/v1/publishers/{publisher_id}

# By Domain
curl http://localhost:8005/api/v1/publishers/by-domain/baeldung.com

# Config Only
curl http://localhost:8005/api/v1/publishers/{publisher_id}/config

# List All
curl "http://localhost:8005/api/v1/publishers/?page=1&page_size=50"
```

## ✏️ Update Publisher

```bash
curl -X PUT http://localhost:8005/api/v1/publishers/{publisher_id} \
  -H "Content-Type: application/json" \
  -H "X-API-Key: pub_xxxxxxxxxxxxxx" \
  -d '{
    "config": {
      "questions_per_blog": 10
    },
    "status": "active"
  }'
```

## 🗑️ Delete Publisher (Soft Delete)

```bash
curl -X DELETE http://localhost:8005/api/v1/publishers/{publisher_id} \
  -H "X-API-Key: pub_xxxxxxxxxxxxxx"
```

## 📦 Process a Blog

```bash
# The worker will automatically use the publisher's config
curl -X POST http://localhost:8005/api/v1/jobs/process \
  -H "Content-Type: application/json" \
  -d '{
    "blog_url": "https://www.baeldung.com/java-threadlocal"
  }'
```

## ⚙️ Configuration Options

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| `questions_per_blog` | 1-20 | 5 | Q&A pairs to generate |
| `llm_model` | enum | `gpt-4o-mini` | LLM model to use |
| `temperature` | 0.0-1.0 | 0.7 | Generation randomness |
| `max_tokens` | 100-4000 | 2000 | Max response length |
| `generate_summary` | bool | `true` | Generate summaries |
| `generate_embeddings` | bool | `true` | Generate embeddings |
| `daily_blog_limit` | int | 100 | Daily processing cap |
| `ui_theme_color` | hex | `#6366f1` | UI primary color |

## 🔑 LLM Models

- `gpt-4o-mini` - Fast, cost-effective (default)
- `gpt-4o` - Most capable, highest quality
- `gpt-3.5-turbo` - Fastest, cheapest
- `claude-3-5-sonnet-20241022` - Anthropic's best
- `claude-3-5-haiku-20241022` - Anthropic's fast

## 🧪 Run Tests

```bash
# Full test suite
./test_publisher_onboarding.sh

# Manual verification
# 1. Onboard Baeldung with 8 questions
# 2. Process a blog
# 3. Verify 8 questions (not 5) were generated
curl "http://localhost:8005/api/v1/questions/by-url?blog_url=https://www.baeldung.com/java-threadlocal" | jq '.questions | length'
```

## 🏥 Health & Monitoring

```bash
# API Service health
curl http://localhost:8005/health | jq '.'

# Check PostgreSQL
curl http://localhost:8005/health | jq '.postgresql'

# Job queue stats
curl http://localhost:8005/api/v1/jobs/stats
```

## 🐛 Troubleshooting

### Publisher Not Found (Using Defaults)
**Issue**: Worker logs show "Publisher not found for domain"
**Solution**: Onboard the publisher or check domain normalization
```bash
# These are equivalent:
# https://www.example.com
# http://example.com  
# example.com
```

### Wrong Question Count
**Issue**: Blog has X questions but config says Y
**Solution**: Check worker logs for "Using config for publisher" message

### 403 Unauthorized
**Issue**: Update/delete fails with 403
**Solution**: Include `X-API-Key` header with correct API key

## 📊 Example Use Cases

### High-Quality Tech Blog
```json
{
  "questions_per_blog": 10,
  "llm_model": "gpt-4o",
  "temperature": 0.6,
  "max_tokens": 3000
}
```

### Fast News Site
```json
{
  "questions_per_blog": 3,
  "llm_model": "gpt-3.5-turbo",
  "temperature": 0.8,
  "daily_blog_limit": 500
}
```

### Precise Documentation
```json
{
  "questions_per_blog": 8,
  "llm_model": "gpt-4o-mini",
  "temperature": 0.5,
  "max_tokens": 2000
}
```

## 📚 Documentation

- **Full Guide**: `PUBLISHER_ONBOARDING_GUIDE.md`
- **Summary**: `PUBLISHER_ONBOARDING_SUMMARY.md`
- **API Docs**: http://localhost:8005/docs

## ✅ Checklist for New Publishers

- [ ] Start services (`docker-compose up -d`)
- [ ] Onboard publisher (`POST /publishers/onboard`)
- [ ] Save API key securely
- [ ] Configure questions, model, temperature
- [ ] Set daily limits
- [ ] Process test blog
- [ ] Verify correct question count
- [ ] Monitor usage tracking
- [ ] Test Chrome extension (if applicable)

---

**Need Help?**
- Check logs: `docker-compose logs api-service`
- Run tests: `./test_publisher_onboarding.sh`
- Read guide: `PUBLISHER_ONBOARDING_GUIDE.md`

