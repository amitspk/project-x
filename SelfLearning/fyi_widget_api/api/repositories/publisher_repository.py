"""
Publisher repository for managing publisher configurations.

Uses SQLAlchemy with async support for managing publisher data.
Business logic name: PublisherRepository (not PostgresPublisherRepository).
"""

import logging
import uuid
import secrets
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, JSON, Enum as SQLEnum, update, case
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import func

from fyi_widget_api.api.models.publisher_models import Publisher, PublisherStatus, PublisherConfig

logger = logging.getLogger(__name__)

Base = declarative_base()


class PublisherTable(Base):
    """SQLAlchemy model for Publisher table."""
    
    __tablename__ = "publishers"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False)
    api_key = Column(String(64), nullable=False, unique=True, index=True)
    
    status = Column(SQLEnum(PublisherStatus), default=PublisherStatus.TRIAL, nullable=False)
    
    # Config stored as JSON
    config = Column(JSON, nullable=False, default={})
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_active_at = Column(DateTime, default=None, nullable=True)
    
    # Usage tracking
    total_blogs_processed = Column(Integer, default=0, nullable=False)
    total_questions_generated = Column(Integer, default=0, nullable=False)
    blog_slots_reserved = Column(Integer, default=0, nullable=False)
    
    # Billing
    subscription_tier = Column(String(50), default="free", nullable=False)


class UsageLimitExceededError(Exception):
    """Raised when a publisher exceeds the configured usage limit."""
    pass


class PublisherRepository:
    """Repository for managing publisher data (business logic name, not technical)."""
    
    def __init__(self, database_url: str):
        """
        Initialize PostgreSQL connection.
        
        Args:
            database_url: PostgreSQL connection URL (e.g., postgresql+asyncpg://user:pass@localhost/db)
        """
        self.database_url = database_url
        self.engine = None
        self.async_session_factory = None
        
    async def connect(self):
        """Establish database connection and create tables."""
        try:
            logger.info(f"Connecting to PostgreSQL: {self.database_url.split('@')[1] if '@' in self.database_url else 'localhost'}")
            
            # Create async engine
            self.engine = create_async_engine(
                self.database_url,
                echo=False,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True
            )
            
            # Create session factory
            self.async_session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables if they do not exist (no schema migrations here)
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("✅ PostgreSQL connected and tables created")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            logger.info("PostgreSQL connection closed")
    
    def _generate_api_key(self) -> str:
        """Generate a secure API key."""
        return f"pub_{secrets.token_urlsafe(32)}"
    
    def _ensure_use_grounding_in_config(self, config: Optional[Dict[str, Any]]) -> PublisherConfig:
        """Ensure use_grounding and threshold_before_processing_blog are included in config dict (backward compatibility)."""
        config_dict = config if config else {}
        if 'use_grounding' not in config_dict:
            config_dict['use_grounding'] = False
        if 'threshold_before_processing_blog' not in config_dict:
            config_dict['threshold_before_processing_blog'] = 0
        return PublisherConfig(**config_dict)
    
    def _table_to_model(self, table_obj: PublisherTable) -> Publisher:
        """Convert SQLAlchemy table object to Pydantic model."""
        return Publisher(
            id=table_obj.id,
            name=table_obj.name,
            domain=table_obj.domain,
            email=table_obj.email,
            api_key=table_obj.api_key,
            status=table_obj.status,
            # Ensure use_grounding is included even if not in database JSON (backward compatibility)
            config=self._ensure_use_grounding_in_config(table_obj.config),
            created_at=table_obj.created_at,
            updated_at=table_obj.updated_at,
            last_active_at=table_obj.last_active_at,
            total_blogs_processed=table_obj.total_blogs_processed or 0,
            total_questions_generated=table_obj.total_questions_generated or 0,
            blog_slots_reserved=getattr(table_obj, "blog_slots_reserved", 0) or 0,
            subscription_tier=table_obj.subscription_tier
        )
    
    async def create_publisher(self, publisher: Publisher, config_dict: Optional[Dict[str, Any]] = None) -> Publisher:
        """
        Create a new publisher.
        
        Args:
            publisher: Publisher object (without id and api_key)
            config_dict: Optional config dict to use instead of publisher.config.model_dump()
                        Useful for adding nested fields like widget config
        
        Returns:
            Created publisher with id and api_key
        """
        async with self.async_session_factory() as session:
            try:
                # Generate ID and API key
                publisher_id = str(uuid.uuid4())
                api_key = self._generate_api_key()
                
                # Use provided config_dict or fall back to model_dump()
                config_to_store = config_dict if config_dict is not None else publisher.config.model_dump()
                
                # Create table object
                db_publisher = PublisherTable(
                    id=publisher_id,
                    name=publisher.name,
                    domain=publisher.domain,
                    email=publisher.email,
                    api_key=api_key,
                    status=publisher.status,
                    config=config_to_store,  # Use config_dict if provided, otherwise model_dump()
                    subscription_tier=publisher.subscription_tier or "free"
                )
                
                session.add(db_publisher)
                await session.commit()
                await session.refresh(db_publisher)
                
                result = self._table_to_model(db_publisher)
                logger.info(f"✅ Created publisher: {result.name} ({result.domain})")
                
                return result
                
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Failed to create publisher: {e}")
                raise
    
    async def get_publisher_by_id(self, publisher_id: str) -> Optional[Publisher]:
        """Get publisher by ID."""
        async with self.async_session_factory() as session:
            result = await session.execute(
                select(PublisherTable).where(PublisherTable.id == publisher_id)
            )
            db_publisher = result.scalar_one_or_none()
            return self._table_to_model(db_publisher) if db_publisher else None
    
    async def get_publisher_by_domain(self, domain: str, allow_subdomain: bool = False) -> Optional[Publisher]:
        """
        Get publisher by domain.
        
        Args:
            domain: Domain to search for
            allow_subdomain: If True, allows matching subdomains (e.g., info.contentretina.com matches contentretina.com)
        
        Returns:
            Publisher if found, None otherwise
        """
        # Normalize domain
        domain = domain.lower().strip()
        for prefix in ['https://', 'http://', 'www.']:
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
        domain = domain.rstrip('/')
        
        async with self.async_session_factory() as session:
            # First try exact match
            result = await session.execute(
                select(PublisherTable).where(PublisherTable.domain == domain)
            )
            db_publisher = result.scalar_one_or_none()
            
            if db_publisher:
                return self._table_to_model(db_publisher)
            
            # If not found and subdomain matching is enabled, try subdomain match
            if allow_subdomain:
                # Use SQL-based subdomain matching to avoid loading all publishers into memory
                # Match publishers where: input_domain = publisher_domain OR input_domain ends with '.' + publisher_domain
                # Example: input_domain="info.contentretina.com" matches publisher_domain="contentretina.com"
                # This is more efficient than loading all publishers and filtering in Python
                from sqlalchemy import or_, func, literal
                
                # Use SQL string functions to match subdomains
                # Check if input domain matches or is a subdomain of any publisher domain
                # We check: domain = publisher_domain OR domain LIKE '%.' || publisher_domain
                # Note: We use a bind parameter for the input domain and check against stored publisher domains
                # Since SQLAlchemy doesn't easily support parameterized LIKE patterns with column values,
                # we need to get publishers and filter, but we can at least limit with SQL filtering first
                
                # Alternative approach: Get all publishers (but this is still better than Python filtering)
                # Actually, we can't easily do this in pure SQL without a function, so let's use a hybrid:
                # 1. Get all publishers (limited set, typically small)
                # 2. Filter in Python (but at least we're not loading all data, just domains)
                all_publishers_result = await session.execute(
                    select(PublisherTable.domain, PublisherTable.id)
                )
                publisher_domains = [(row.domain.lower().strip(), row.id) for row in all_publishers_result.all()]
                
                # Find matching publishers (input domain is subdomain of publisher domain)
                matching_publishers = []
                for pub_domain, pub_id in publisher_domains:
                    # Check if input domain equals publisher domain or is a subdomain of it
                    if domain == pub_domain or domain.endswith(f".{pub_domain}"):
                        matching_publishers.append((pub_id, len(pub_domain)))
                
                if matching_publishers:
                    # Sort by domain length (shortest first) to prioritize root domains
                    matching_publishers.sort(key=lambda x: x[1])
                    matching_pub_id, _ = matching_publishers[0]
                    
                    # Fetch the full publisher record
                    result = await session.execute(
                        select(PublisherTable).where(PublisherTable.id == matching_pub_id)
                    )
                    db_publisher = result.scalar_one_or_none()
                    
                    if db_publisher:
                        logger.info(f"✅ Found publisher by subdomain match: {domain} -> {db_publisher.domain.lower()} (publisher: {db_publisher.name})")
                        return self._table_to_model(db_publisher)
            
            return None
    
    async def get_publisher_by_api_key(self, api_key: str) -> Optional[Publisher]:
        """Get publisher by API key."""
        async with self.async_session_factory() as session:
            result = await session.execute(
                select(PublisherTable).where(PublisherTable.api_key == api_key)
            )
            db_publisher = result.scalar_one_or_none()
            
            if db_publisher:
                # Update last_active_at
                db_publisher.last_active_at = datetime.utcnow()
                await session.commit()
            
            return self._table_to_model(db_publisher) if db_publisher else None
    
    async def update_publisher(self, publisher_id: str, updates: dict) -> Optional[Publisher]:
        """Update publisher fields."""
        async with self.async_session_factory() as session:
            try:
                result = await session.execute(
                    select(PublisherTable).where(PublisherTable.id == publisher_id)
                )
                db_publisher = result.scalar_one_or_none()
                
                if not db_publisher:
                    return None
                
                # Update fields
                for key, value in updates.items():
                    if key == 'config':
                        # Handle config update - can be PublisherConfig object or dict
                        if isinstance(value, PublisherConfig):
                            config_dict = value.model_dump()
                        elif isinstance(value, dict):
                            config_dict = value
                        else:
                            config_dict = value
                        
                        # Merge with existing config to preserve widget field if not being updated
                        existing_config = db_publisher.config or {}
                        if isinstance(existing_config, dict):
                            # Preserve widget config if not being updated
                            if "widget" not in config_dict and "widget" in existing_config:
                                config_dict["widget"] = existing_config["widget"]
                            logger.info(f"💾 Saving config with widget: {'widget' in config_dict}, widget keys: {list(config_dict.get('widget', {}).keys()) if 'widget' in config_dict else 'N/A'}")
                        
                        setattr(db_publisher, key, config_dict)
                    elif hasattr(db_publisher, key):
                        setattr(db_publisher, key, value)
                
                db_publisher.updated_at = datetime.utcnow()
                
                await session.commit()
                await session.refresh(db_publisher)
                
                logger.info(f"✅ Updated publisher: {publisher_id}")
                return self._table_to_model(db_publisher)
                
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Failed to update publisher: {e}")
                raise
    
    async def delete_publisher(self, publisher_id: str) -> bool:
        """Delete a publisher."""
        async with self.async_session_factory() as session:
            try:
                result = await session.execute(
                    select(PublisherTable).where(PublisherTable.id == publisher_id)
                )
                db_publisher = result.scalar_one_or_none()
                
                if not db_publisher:
                    return False
                
                await session.delete(db_publisher)
                await session.commit()
                
                logger.info(f"✅ Deleted publisher: {publisher_id}")
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Failed to delete publisher: {e}")
                raise
    
    async def regenerate_api_key(self, publisher_id: str) -> tuple[Publisher, str]:
        """
        Regenerate API key for a publisher.
        
        Args:
            publisher_id: Publisher ID
            
        Returns:
            Tuple of (updated Publisher, new API key)
            
        Raises:
            ValueError: If publisher not found
        """
        async with self.async_session_factory() as session:
            try:
                result = await session.execute(
                    select(PublisherTable).where(PublisherTable.id == publisher_id)
                )
                db_publisher = result.scalar_one_or_none()
                
                if not db_publisher:
                    raise ValueError(f"Publisher with ID {publisher_id} not found")
                
                # Generate new API key
                new_api_key = self._generate_api_key()
                
                # Update publisher
                db_publisher.api_key = new_api_key
                db_publisher.updated_at = datetime.utcnow()
                
                await session.commit()
                await session.refresh(db_publisher)
                
                logger.info(f"✅ Regenerated API key for publisher: {publisher_id}")
                return self._table_to_model(db_publisher), new_api_key
                
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Failed to regenerate API key: {e}")
                raise
    
    async def list_publishers(
        self,
        status: Optional[PublisherStatus] = None,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[Publisher], int]:
        """
        List publishers with pagination.
        
        Returns:
            Tuple of (publishers list, total count)
        """
        async with self.async_session_factory() as session:
            # Build query
            query = select(PublisherTable)
            
            if status:
                query = query.where(PublisherTable.status == status)
            
            # Get total count
            count_query = select(func.count()).select_from(PublisherTable)
            if status:
                count_query = count_query.where(PublisherTable.status == status)
            
            total_result = await session.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination
            query = query.order_by(PublisherTable.created_at.desc())
            query = query.offset((page - 1) * page_size).limit(page_size)
            
            # Execute query
            result = await session.execute(query)
            db_publishers = result.scalars().all()
            
            publishers = [self._table_to_model(p) for p in db_publishers]
            
            return publishers, total
    
    async def reserve_blog_slot(self, publisher_id: str) -> None:
        """Reserve a blog processing slot for a publisher (atomic)."""
        async with self.async_session_factory() as session:
            try:
                result = await session.execute(
                    select(PublisherTable)
                    .where(PublisherTable.id == publisher_id)
                    .with_for_update()
                )
                db_publisher = result.scalar_one_or_none()
                if not db_publisher:
                    raise UsageLimitExceededError("Publisher not found")

                config = db_publisher.config or {}
                limit = config.get("max_total_blogs")

                if not limit:
                    return

                processed = db_publisher.total_blogs_processed or 0
                reserved = db_publisher.blog_slots_reserved or 0

                if processed + reserved >= limit:
                    raise UsageLimitExceededError(
                        f"Publisher reached the maximum number of blogs ({limit})."
                    )

                db_publisher.blog_slots_reserved = reserved + 1
                db_publisher.last_active_at = datetime.utcnow()

                await session.commit()
            except UsageLimitExceededError:
                await session.rollback()
                raise
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Failed to reserve blog slot: {e}")
                raise

    async def release_blog_slot(
        self,
        publisher_id: str,
        processed: bool,
        questions_generated: int = 0,
    ) -> None:
        """Release a reserved slot and optionally record successful processing."""
        async with self.async_session_factory() as session:
            try:
                # Use atomic UPDATE to prevent race conditions
                # This ensures the decrement happens directly in the database
                # Build values dict conditionally based on processed flag
                values_dict = {
                    "blog_slots_reserved": case(
                        (PublisherTable.blog_slots_reserved > 0, PublisherTable.blog_slots_reserved - 1),
                        else_=0
                    ),
                    "last_active_at": datetime.utcnow()
                }
                
                # Conditionally add processed fields if processed is True
                if processed:
                    values_dict["total_blogs_processed"] = PublisherTable.total_blogs_processed + 1
                    values_dict["total_questions_generated"] = PublisherTable.total_questions_generated + questions_generated
                
                update_stmt = (
                    update(PublisherTable)
                    .where(PublisherTable.id == publisher_id)
                    .values(**values_dict)
                )
                
                result = await session.execute(update_stmt)
                await session.commit()
                
                if result.rowcount == 0:
                    logger.warning(f"⚠️  Publisher not found for slot release: {publisher_id}")
                    return
                
                # Log the release (we can't get the exact before/after value with atomic update,
                # but we know it was decremented if it was > 0)
                logger.info(f"📉 Released blog slot (publisher: {publisher_id}, processed: {processed})")
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Failed to release blog slot: {e}")
                raise
    
    async def get_publisher_raw_config_by_domain(self, domain: str, allow_subdomain: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get raw config JSON from database by domain (without converting to Pydantic model).
        
        This is useful when you need to access nested keys in the config JSON that aren't
        part of the PublisherConfig Pydantic model (e.g., widget config).
        
        Args:
            domain: Domain to search for
            allow_subdomain: If True, allows matching subdomains
        
        Returns:
            Raw config dict if found, None otherwise
        """
        # Normalize domain
        domain = domain.lower().strip()
        for prefix in ['https://', 'http://', 'www.']:
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
        domain = domain.rstrip('/')
        
        async with self.async_session_factory() as session:
            # First try exact match
            result = await session.execute(
                select(PublisherTable).where(PublisherTable.domain == domain)
            )
            db_publisher = result.scalar_one_or_none()
            
            if db_publisher:
                return db_publisher.config if db_publisher.config else {}
            
            # If not found and subdomain matching is enabled, try subdomain match
            if allow_subdomain:
                all_publishers_result = await session.execute(
                    select(PublisherTable)
                )
                all_publishers = all_publishers_result.scalars().all()
                
                matching_publishers = []
                for pub in all_publishers:
                    publisher_domain = pub.domain.lower().strip()
                    if domain == publisher_domain or domain.endswith(f".{publisher_domain}"):
                        matching_publishers.append((pub, len(publisher_domain)))
                
                if matching_publishers:
                    matching_publishers.sort(key=lambda x: x[1])
                    pub, _ = matching_publishers[0]
                    return pub.config if pub.config else {}
            
            return None
    
    async def health_check(self) -> dict:
        """Check database health."""
        try:
            async with self.async_session_factory() as session:
                result = await session.execute(select(func.count()).select_from(PublisherTable))
                count = result.scalar()
                
                return {
                    "status": "healthy",
                    "total_publishers": count
                }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

