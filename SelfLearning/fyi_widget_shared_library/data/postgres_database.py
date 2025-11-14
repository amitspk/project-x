"""
PostgreSQL database manager for publisher configurations.

Uses SQLAlchemy with async support for managing publisher data.
"""

import logging
import uuid
import secrets
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import func

from ..models.publisher import Publisher, PublisherStatus, PublisherConfig

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


class PostgresPublisherRepository:
    """Repository for managing publisher data in PostgreSQL."""
    
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
        """Ensure use_grounding is included in config dict (backward compatibility)."""
        config_dict = config if config else {}
        if 'use_grounding' not in config_dict:
            config_dict['use_grounding'] = False
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
            total_blogs_processed=table_obj.total_blogs_processed,
            total_questions_generated=table_obj.total_questions_generated,
            blog_slots_reserved=getattr(table_obj, "blog_slots_reserved", 0) or 0,
            subscription_tier=table_obj.subscription_tier
        )
    
    async def create_publisher(self, publisher: Publisher) -> Publisher:
        """
        Create a new publisher.
        
        Args:
            publisher: Publisher object (without id and api_key)
        
        Returns:
            Created publisher with id and api_key
        """
        async with self.async_session_factory() as session:
            try:
                # Generate ID and API key
                publisher_id = str(uuid.uuid4())
                api_key = self._generate_api_key()
                
                # Create table object
                db_publisher = PublisherTable(
                    id=publisher_id,
                    name=publisher.name,
                    domain=publisher.domain,
                    email=publisher.email,
                    api_key=api_key,
                    status=publisher.status,
                    config=publisher.config.model_dump(),  # Use model_dump() to include all fields including use_grounding
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
    
    async def get_publisher_by_domain(self, domain: str) -> Optional[Publisher]:
        """Get publisher by domain."""
        # Normalize domain
        domain = domain.lower().strip()
        for prefix in ['https://', 'http://', 'www.']:
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
        domain = domain.rstrip('/')
        
        async with self.async_session_factory() as session:
            result = await session.execute(
                select(PublisherTable).where(PublisherTable.domain == domain)
            )
            db_publisher = result.scalar_one_or_none()
            return self._table_to_model(db_publisher) if db_publisher else None
    
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
                    if key == 'config' and isinstance(value, PublisherConfig):
                        setattr(db_publisher, key, value.model_dump())  # Use model_dump() to include all fields including use_grounding
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
                result = await session.execute(
                    select(PublisherTable)
                    .where(PublisherTable.id == publisher_id)
                    .with_for_update()
                )
                db_publisher = result.scalar_one_or_none()
                if not db_publisher:
                    return

                if db_publisher.blog_slots_reserved and db_publisher.blog_slots_reserved > 0:
                    db_publisher.blog_slots_reserved -= 1

                if processed:
                    db_publisher.total_blogs_processed += 1
                    db_publisher.total_questions_generated += questions_generated

                db_publisher.last_active_at = datetime.utcnow()

                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Failed to release blog slot: {e}")
                raise
    
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

