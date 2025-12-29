# Database Connection Architecture

## Current Design

### Connection Lifecycle Management

The **Worker** (entry point/orchestrator) is responsible for managing the database connection lifecycle:
- **Connects** to databases during `start()` method
- **Disconnects** from databases during shutdown
- **Passes connected database instances** to repositories

### Why This Pattern?

1. **Connection Pooling**: Multiple repositories share a single database connection pool
2. **Lifecycle Management**: The entry point controls when connections are established/closed
3. **Testability**: Database connections can be mocked at the worker level
4. **Separation of Concerns**:
   - **Worker**: Manages application lifecycle (when to connect/disconnect)
   - **Repositories**: Use the database (they don't manage connections)
   - **DatabaseManager**: Handles connection logic (how to connect)

### Architecture Layers

```
┌─────────────────────────────────────────┐
│  run_worker.py (Entry Point)           │
│  - Creates DatabaseManager              │
│  - Creates Worker with injected DB      │
│  - Manages application lifecycle        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  worker.py (BlogProcessingWorker)       │
│  - Receives DatabaseManager (injected)  │
│  - Manages connection lifecycle:        │
│    * Connects in start()                │
│    * Disconnects in cleanup             │
│  - Creates repositories with DB         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Repositories (JobRepository, etc.)     │
│  - Receive connected database instance  │
│  - Use database (no connection logic)   │
│  - Focus on data access logic           │
└─────────────────────────────────────────┘
```

### Why NOT in Repositories?

If repositories managed their own connections:
- ❌ Each repository would create its own connection (wasteful)
- ❌ No connection pooling (performance issues)
- ❌ Harder to coordinate connection lifecycle
- ❌ Difficult to share connections across repositories
- ❌ Testing becomes harder (can't easily inject mock connections)

### Dependency Injection Pattern

```python
# run_worker.py - Entry point creates dependencies
db_manager = DatabaseManager()
worker = BlogProcessingWorker(config=config, db_manager=db_manager)

# worker.py - Receives dependencies, manages lifecycle
async def start(self):
    await self.db_manager.connect(...)  # Lifecycle: connect
    
    # Create repositories with DB (ONE level: DB → Repository)
    self.job_repo = JobRepository(self.db_manager.database)
    self.storage = BlogContentRepository(self.db_manager.database)
    
    # Create services with repositories (NO DB passing: Repository → Service)
    threshold_service = ThresholdService(
        storage=self.storage,  # Repository, not DB
        job_repo=self.job_repo  # Repository, not DB
    )
    
async def stop(self):
    await self.db_manager.close()  # Lifecycle: disconnect

# repository.py - Receives connected database, uses it
class JobRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database  # Already connected

# service.py - Receives repositories, NOT database connections
class ThresholdService:
    def __init__(self, storage: BlogContentRepository, job_repo: JobRepository):
        self.storage = storage  # Repository interface, not DB
        self.job_repo = job_repo  # Repository interface, not DB
```

### Key Insight: No Multi-Layer DB Passing

**The database connection is NOT passed through multiple layers:**

1. **Worker → Repository**: DB passed (one level)
2. **Worker → Service**: Repository passed (different abstraction, not DB)
3. **Service → Repository**: Already has repository (no DB passing)

Services receive **repositories** (encapsulated data access), not raw database connections. This is the standard Repository Pattern and avoids the "passing DB through layers" problem.

### Comparison with API Service

The API service follows the same pattern:

```python
# main.py - FastAPI lifespan manages lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_manager.connect(...)  # Lifecycle: connect
    app.state.mongo_db = db_manager.database
    yield
    await db_manager.close()  # Lifecycle: disconnect

# deps.py - Dependency injection
def get_mongo_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.mongo_db  # Already connected

def get_job_repository(db: AsyncIOMotorDatabase = Depends(get_mongo_db)):
    return JobRepository(db)  # Inject connected DB
```

### Benefits

1. ✅ **Separation of Concerns**: Each layer has a clear responsibility
2. ✅ **Testability**: Can inject mock database managers/repositories
3. ✅ **Connection Pooling**: Single connection pool shared across repositories
4. ✅ **Lifecycle Control**: Entry point controls when connections are established
5. ✅ **Flexibility**: Can swap database implementations without changing repositories

### Testing

```python
# Test example with mocked database
mock_db_manager = Mock(spec=DatabaseManager)
mock_database = Mock(spec=AsyncIOMotorDatabase)
mock_db_manager.database = mock_database

worker = BlogProcessingWorker(config=config, db_manager=mock_db_manager)
# Can now test worker logic without real database
```

