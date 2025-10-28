# 📁 File Relevance Guide - 2-Service Architecture

**Last Updated**: October 13, 2025  
**Architecture**: 2-Service (Content Processing Service + API Gateway/BFF)

---

## ✅ ACTIVE & RELEVANT FILES

### 🚀 Content Processing Service (Port 8005)
**Primary service handling all blog processing operations**

```
content_processing_service/
├── api/
│   ├── __init__.py                    ✅ ACTIVE
│   ├── main.py                        ✅ ACTIVE - FastAPI app entry point
│   └── routers/
│       ├── __init__.py                ✅ ACTIVE
│       ├── health_router.py           ✅ ACTIVE - Health checks
│       ├── processing_router.py       ✅ ACTIVE - Blog processing
│       ├── questions_router.py        ✅ ACTIVE - Question retrieval
│       ├── search_router.py           ✅ ACTIVE - Similar blogs
│       └── qa_router.py               ✅ ACTIVE - Custom Q&A
│
├── core/
│   ├── __init__.py                    ✅ ACTIVE
│   └── config.py                      ✅ ACTIVE - Service configuration
│
├── data/
│   ├── __init__.py                    ✅ ACTIVE
│   └── database.py                    ✅ ACTIVE - MongoDB connection
│
├── models/
│   ├── __init__.py                    ✅ ACTIVE
│   └── schemas.py                     ✅ ACTIVE - Pydantic models
│
├── services/
│   ├── __init__.py                    ✅ ACTIVE
│   ├── crawler_service.py             ✅ ACTIVE - Web crawling
│   ├── llm_service.py                 ✅ ACTIVE - OpenAI operations
│   ├── storage_service.py             ✅ ACTIVE - MongoDB operations
│   └── pipeline_service.py            ✅ ACTIVE - Orchestration
│
├── run_server.py                      ✅ ACTIVE - Server entry point
├── requirements.txt                   ✅ ACTIVE - Dependencies
└── Dockerfile                         ✅ ACTIVE - Container config
```

**Purpose**: Handles all content processing:
- Web crawling
- LLM operations (summary, Q&A, embeddings)
- MongoDB storage
- Vector similarity search
- Custom question answering

---

### 🌐 Chrome Extension (UI Layer)
**JavaScript library for injecting questions on blog pages**

```
chrome-extension/
├── manifest.json                      ✅ ACTIVE - Extension config
├── popup.html                         ✅ ACTIVE - Extension popup
├── popup.js                           ✅ ACTIVE - Popup logic
├── content.js                         ✅ ACTIVE - Content script
├── background.js                      ✅ ACTIVE - Background service
├── auto-blog-question-injector.js    ✅ ACTIVE - Core library
├── config.js                          ✅ ACTIVE - API configuration
├── icons/                             ✅ ACTIVE - Extension icons
├── README.md                          ✅ ACTIVE - Documentation
└── INSTALL.md                         ✅ ACTIVE - Setup guide
```

**Alternative folder** (same library, different location):
```
ui-js/
├── auto-blog-question-injector.js    ⚠️  DUPLICATE - Use chrome-extension/ version
├── simple-question-injector.js       ⚠️  OLD - Not used anymore
└── README.md                          ⚠️  OLD
```

**Status**: Use `chrome-extension/` folder. The `ui-js/` folder is a legacy copy.

---

### 📚 Documentation Files

```
Root Level:
├── CHROME_EXTENSION_TEST_GUIDE.md     ✅ ACTIVE - Testing guide
├── 2-SERVICE_ARCHITECTURE_GUIDE.md    ✅ ACTIVE - Architecture overview
├── API_ENDPOINTS_AND_FLOWS.md         ✅ ACTIVE - API documentation
├── IMPLEMENTATION_COMPLETE.md         ✅ ACTIVE - Implementation summary
├── QUICK_START.md                     ✅ ACTIVE - Quick reference
├── HowToRunMainProject                ✅ ACTIVE - Run instructions
├── README.md                          ✅ ACTIVE - Project overview
└── requirements.txt                   ✅ ACTIVE - Main dependencies
```

---

## ⚠️ LEGACY FILES (Can Be Archived/Removed)

### 🗄️ Old Microservices (5-Service Architecture)

```
llm_service/                           ❌ OBSOLETE - Merged into content_processing_service
├── api/                               ❌ OBSOLETE
├── core/                              ❌ OBSOLETE
├── providers/                         ❌ OBSOLETE
├── services/                          ❌ OBSOLETE
├── repositories/                      ❌ OBSOLETE
├── run_server.py                      ❌ OBSOLETE
├── Dockerfile                         ❌ OBSOLETE
└── requirements.txt                   ❌ OBSOLETE

web_crawler/                           ❌ OBSOLETE - Merged into content_processing_service
├── core/                              ❌ OBSOLETE
├── storage/                           ❌ OBSOLETE
├── config/                            ❌ OBSOLETE
├── example.py                         ❌ OBSOLETE
└── README.md                          ❌ OBSOLETE

vector_db_service/                     ❌ OBSOLETE - Merged into content_processing_service
├── api/                               ❌ OBSOLETE
├── data/                              ❌ OBSOLETE
├── models/                            ❌ OBSOLETE
├── core/                              ❌ OBSOLETE
└── requirements.txt                   ❌ OBSOLETE

blog_manager/                          ⚠️  PARTIALLY OBSOLETE
├── api/
│   ├── main.py                        ⚠️  OLD - Not used in 2-service arch
│   └── routers/
│       ├── blog_router.py             ⚠️  OLD - Use content_processing_service
│       ├── blog_router_v2.py          ⚠️  EXPERIMENTAL - Not fully implemented
│       ├── similar_blogs_router.py    ⚠️  OLD
│       ├── similar_blogs_router_v2.py ⚠️  EXPERIMENTAL
│       ├── qa_router.py               ⚠️  OLD
│       └── health_router.py           ⚠️  OLD
├── services/
│   ├── qa_service.py                  ⚠️  OLD
│   ├── similar_blogs_service.py       ⚠️  OLD
│   ├── content_service_client.py      ⚠️  EXPERIMENTAL - For API Gateway pattern
│   └── cache_service.py               ⚠️  EXPERIMENTAL - For API Gateway pattern
├── core/
│   ├── resilience.py                  ⚠️  EXPERIMENTAL - Circuit breaker
│   └── rate_limiting.py               ⚠️  EXPERIMENTAL - Rate limiting
└── data/
    └── database.py                    ⚠️  OLD
```

**Note**: `blog_manager/` was the original monolith. The v2 routers and new services were created for an API Gateway pattern but not fully migrated. The 2-service architecture uses `content_processing_service/` directly instead.

---

### 📝 Standalone Scripts (Old Workflow)

```
Root Level:
├── blog_processor.py                  ❌ OBSOLETE - Use content_processing_service
├── blog_processor_mongodb.py          ❌ OBSOLETE - Use content_processing_service
├── blog_question_generator.py         ❌ OBSOLETE - Merged into services
├── simple_question_generator.py       ❌ OBSOLETE - Merged into services
├── content_processor.py               ❌ OBSOLETE - Old standalone script
├── content_summarizer.py              ❌ OBSOLETE - Merged into llm_service
├── crawl_url.py                       ❌ OBSOLETE - Merged into crawler_service
├── debug_content_extraction.py        ❌ OBSOLETE - Debug script
├── final_demo.py                      ❌ OBSOLETE - Old demo
└── llm_chat.py                        ❌ OBSOLETE - Old chat script
```

---

### 📂 Old Documentation

```
Documentation:
├── BLOG_QUESTION_GENERATOR.md         ⚠️  OLD - Describes old workflow
├── ENHANCED_FEATURES.md               ⚠️  OLD - Old feature list
├── PROJECT_SUMMARY.md                 ⚠️  OLD - Outdated summary
├── REPOSITORY_LAYER.md                ⚠️  OLD - Old repository pattern
├── USAGE.md                           ⚠️  OLD - Outdated usage
├── MICROSERVICES_REFACTORING_PLAN.md  ⚠️  HISTORICAL - Planning doc
├── ARCHITECTURE_REVIEW_*.md           ⚠️  HISTORICAL - Review docs
├── REFACTORING_IMPLEMENTATION_PLAN.md ⚠️  HISTORICAL - Planning doc
├── IMPLEMENTATION_STATUS.md           ⚠️  HISTORICAL - Old status
├── LLM_SERVICE_*.md                   ⚠️  OLD - Old LLM service docs
├── RATE_LIMITING_IMPLEMENTATION.md    ⚠️  EXPERIMENTAL - Not used
└── TESTING_GUIDE.md                   ⚠️  OLD - Use CHROME_EXTENSION_TEST_GUIDE.md
```

---

### 🧪 Test & Benchmark Scripts

```
Root Level:
├── test_2_service_architecture.sh     ✅ ACTIVE - Testing script
├── test_resilience_features.sh        ⚠️  EXPERIMENTAL - Circuit breaker tests
├── test_endpoints.sh                  ⚠️  OLD - For 5-service arch
├── benchmark_architectures.py         ⚠️  EXPERIMENTAL - Performance testing
├── verify_extension_ready.sh          ✅ ACTIVE - Extension verification
└── start_2_service_architecture.sh    ⚠️  EXPERIMENTAL - Docker Compose startup
```

---

### 🗃️ Data Directories

```
crawled_content/                       ⚠️  OLD - File-based storage (now MongoDB)
├── baeldung.com/
├── medium.com/
└── httpbin.org/

processed_content/                     ⚠️  OLD - File-based storage (now MongoDB)
├── *.questions.json
└── *.summary.json

test_output/                           ⚠️  OLD - Test artifacts
```

---

### 🐳 Docker & Infrastructure

```
docker-compose.yml                     ❌ OBSOLETE - Old 5-service setup
docker-compose.2-service.yml           ⚠️  EXPERIMENTAL - Not fully tested
mongo-init/                            ⚠️  OLD - MongoDB init scripts
├── init-db.js
mongodb_setup.sh                       ⚠️  OLD - Setup script
MONGODB_SETUP_GUIDE.md                 ⚠️  OLD
```

---

## 🎯 RECOMMENDED CLEANUP ACTIONS

### ✅ Safe to Archive (Move to `archive/` folder)

```bash
mkdir -p archive/{services,scripts,docs,docker}

# Old microservices
mv llm_service/ archive/services/
mv web_crawler/ archive/services/
mv vector_db_service/ archive/services/
mv blog_manager/ archive/services/

# Old standalone scripts
mv blog_processor*.py archive/scripts/
mv simple_question_generator.py archive/scripts/
mv content_*.py archive/scripts/
mv crawl_url.py archive/scripts/
mv debug_*.py archive/scripts/
mv final_demo.py archive/scripts/
mv llm_chat.py archive/scripts/

# Old documentation
mv BLOG_QUESTION_GENERATOR.md archive/docs/
mv ENHANCED_FEATURES.md archive/docs/
mv PROJECT_SUMMARY.md archive/docs/
mv REPOSITORY_LAYER.md archive/docs/
mv USAGE.md archive/docs/
mv MICROSERVICES_*.md archive/docs/
mv ARCHITECTURE_*.md archive/docs/
mv LLM_SERVICE_*.md archive/docs/

# Old Docker files
mv docker-compose.yml archive/docker/
mv mongo-init/ archive/docker/
mv mongodb_setup.sh archive/docker/
```

### ⚠️ Keep but Review

```bash
# These might be useful for reference
# Keep in root but mark as legacy:
- benchmark_architectures.py  # Performance testing
- test_resilience_features.sh # Circuit breaker experiments
- blog_manager/core/resilience.py  # Resilience patterns
```

### 🗑️ Safe to Delete

```bash
# Old test output and crawled data (regenerate if needed)
rm -rf test_output/
rm -rf crawled_content/
rm -rf processed_content/

# Duplicate UI library
rm -rf ui-js/

# Old test files
rm test_endpoints.sh
rm simple_mongodb_test.py
```

---

## 📊 FILE COUNT SUMMARY

### Current State
- **Total Files**: ~500+ files
- **Active Files**: ~80 files (16%)
- **Obsolete/Legacy**: ~420 files (84%)

### After Cleanup
- **Active Files**: ~80 files
- **Archived**: ~300 files (for reference)
- **Deleted**: ~120 files (test artifacts, duplicates)

---

## 🚀 MINIMAL SETUP FOR NEW DEPLOYMENT

If deploying fresh, you only need:

```
Required Files:
├── content_processing_service/        # Main service (22 files)
├── chrome-extension/                  # UI layer (12 files)
├── requirements.txt                   # Dependencies
├── README.md                          # Overview
├── HowToRunMainProject               # Instructions
├── CHROME_EXTENSION_TEST_GUIDE.md    # Testing
├── 2-SERVICE_ARCHITECTURE_GUIDE.md   # Architecture
└── API_ENDPOINTS_AND_FLOWS.md        # API docs

Total: ~40 core files
```

---

## 📝 NOTES

1. **Don't delete yet** - Archive first to preserve history
2. **Database**: All content now in MongoDB (no more JSON files)
3. **API Gateway**: Planned but not implemented (blog_manager/v2 routers)
4. **Resilience**: Circuit breaker code exists but not integrated
5. **The 2-service architecture is simpler and production-ready as-is**

---

**Last Review**: October 13, 2025  
**Architecture Version**: 2.0 (Consolidated Services)
