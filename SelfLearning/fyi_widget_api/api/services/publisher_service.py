"""Service layer for publisher operations."""

import logging
from typing import Dict, Optional, Tuple, List, Sequence
from urllib.parse import urlparse
from fastapi import HTTPException

from fyi_widget_api.api.repositories import PublisherRepository
from fyi_widget_api.api.models.publisher_models import (
    Publisher,
    PublisherCreateRequest,
    PublisherUpdateRequest,
    PublisherResponse,
    PublisherListResponse,
    PublisherStatus,
)
from fyi_widget_api.api.models import PublisherRegenerateApiKeyResponse
from fyi_widget_api.api.utils import extract_domain, normalize_url

logger = logging.getLogger(__name__)


class PublisherService:
    """Publisher service with constructor-injected dependencies."""

    def __init__(
        self,
        publisher_repo: PublisherRepository,
    ):
        self.publisher_repo = publisher_repo

    async def _enrich_publisher_with_widget_config(
        self,
        publisher: Publisher,
    ) -> Dict[str, any]:
        """Attach widget config from raw DB config; strip sensitive fields."""
        raw_config = await self.publisher_repo.get_publisher_raw_config_by_domain(
            publisher.domain,
            allow_subdomain=False,
        )

        publisher_dict = publisher.model_dump()
        if "config" in publisher_dict:
            config = publisher_dict["config"]
            config.pop("summary_temperature", None)
            config.pop("questions_temperature", None)
            config.pop("chat_temperature", None)
            config.pop("generate_summary", None)
            config.pop("generate_embeddings", None)

        if raw_config and isinstance(raw_config, dict):
            widget_config = raw_config.get("widget")
            if widget_config:
                publisher_dict.setdefault("config", {})["widget"] = widget_config
            else:
                publisher_dict.setdefault("config", {})["widget"] = {}
        else:
            publisher_dict.setdefault("config", {})["widget"] = {}

        return publisher_dict

    async def onboard_publisher(
        self,
        *,
        request: PublisherCreateRequest,
        request_id: str,
    ) -> Tuple[Dict, int, str]:
        existing = await self.publisher_repo.get_publisher_by_domain(request.domain)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Publisher with domain '{request.domain}' already exists",
            )

        publisher = Publisher(
            name=request.name,
            domain=request.domain,
            email=request.email,
            config=request.config,
            subscription_tier=request.subscription_tier,
        )

        config_dict = publisher.config.model_dump()
        config_dict["widget"] = request.widget_config
        created_publisher = await self.publisher_repo.create_publisher(publisher, config_dict)

        enriched_publisher = await self._enrich_publisher_with_widget_config(created_publisher)

        publisher_response = PublisherResponse(
            success=True,
            publisher=created_publisher,
            api_key=created_publisher.api_key,
            message="Publisher onboarded successfully",
        )
        response_dict = publisher_response.model_dump()
        response_dict["publisher"] = enriched_publisher
        return response_dict, 201, "Publisher onboarded successfully"

    async def get_publisher_metadata(
        self,
        *,
        blog_url: str,
        publisher: Publisher,
        request_id: str,
    ) -> Dict:
        blog_domain = extract_domain(blog_url)

        domain_publisher = await self.publisher_repo.get_publisher_by_domain(blog_domain, allow_subdomain=True)
        if not domain_publisher:
            raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "status_code": 404,
                "message": "Publisher not found for the provided blog URL",
                "error": {
                    "code": "NOT_FOUND",
                    "detail": f"No publisher found for domain: {blog_domain}",
                },
            },
        )

        raw_config = await self.publisher_repo.get_publisher_raw_config_by_domain(blog_domain, allow_subdomain=True) or {}
        widget_config = raw_config.get("widget", {}) if isinstance(raw_config, dict) else {}

        ad_variation = widget_config.get("adVariation")
        valid_ad_variations = ["adsenseForSearch", "adsenseDisplay", "googleAdManager"]
        if ad_variation and ad_variation not in valid_ad_variations:
            logger.warning(
                f"[{request_id}] ⚠️ Invalid adVariation '{ad_variation}' in widget config. Valid values: {', '.join(valid_ad_variations)}"
            )
            ad_variation = None

        result_data = {
            "domain": domain_publisher.domain,
            "publisher_id": domain_publisher.id,
            "publisher_name": domain_publisher.name,
            "useDummyData": widget_config.get("useDummyData"),
            "theme": widget_config.get("theme"),
            "currentStructure": widget_config.get("currentStructure"),
            "gaTrackingId": widget_config.get("gaTrackingId"),
            "gaEnabled": widget_config.get("gaEnabled"),
            "adVariation": ad_variation,
            "adsenseForSearch": None,
            "adsenseDisplay": None,
            "googleAdManager": None,
        }

        if ad_variation == "adsenseForSearch":
            result_data["adsenseForSearch"] = widget_config.get("adsenseForSearch")
        elif ad_variation == "adsenseDisplay":
            result_data["adsenseDisplay"] = widget_config.get("adsenseDisplay")
        elif ad_variation == "googleAdManager":
            result_data["googleAdManager"] = widget_config.get("googleAdManager")

        return result_data

    async def get_publisher(
        self,
        *,
        publisher_id: str,
    ) -> Dict:
        publisher = await self.publisher_repo.get_publisher_by_id(publisher_id)
        if not publisher:
            raise HTTPException(status_code=404, detail=f"Publisher not found: {publisher_id}")
        publisher.api_key = None
        enriched = await self._enrich_publisher_with_widget_config(publisher)
        response = PublisherResponse(success=True, publisher=publisher)
        response_dict = response.model_dump()
        response_dict["publisher"] = enriched
        return response_dict

    async def get_publisher_by_domain(
        self,
        *,
        domain: str,
    ) -> Dict:
        publisher = await self.publisher_repo.get_publisher_by_domain(domain, allow_subdomain=True)
        if not publisher:
            raise HTTPException(status_code=404, detail=f"Publisher not found for domain: {domain}")
        publisher.api_key = None
        enriched = await self._enrich_publisher_with_widget_config(publisher)
        response = PublisherResponse(success=True, publisher=publisher)
        response_dict = response.model_dump()
        response_dict["publisher"] = enriched
        return response_dict

    async def update_publisher(
        self,
        *,
        publisher_id: str,
        request: PublisherUpdateRequest,
        request_id: str,
    ) -> Dict:
        updates = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.email is not None:
            updates["email"] = request.email
        if request.status is not None:
            updates["status"] = request.status
        if request.subscription_tier is not None:
            updates["subscription_tier"] = request.subscription_tier

        widget_from_request = request.widget_config

        if request.config is not None or widget_from_request is not None:
            current_publisher = await self.publisher_repo.get_publisher_by_id(publisher_id)
            if not current_publisher:
                raise HTTPException(status_code=404, detail=f"Publisher not found: {publisher_id}")

            if request.config is not None:
                config_dict = request.config.model_dump()
            else:
                config_dict = current_publisher.config.model_dump()

            if widget_from_request is not None:
                config_dict["widget"] = widget_from_request
            else:
                existing_config = await self.publisher_repo.get_publisher_raw_config_by_domain(current_publisher.domain)
                if existing_config and isinstance(existing_config, dict) and "widget" in existing_config:
                    config_dict["widget"] = existing_config.get("widget", {})
            updates["config"] = config_dict

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        updated_publisher = await self.publisher_repo.update_publisher(publisher_id, updates)
        if not updated_publisher:
            raise HTTPException(status_code=404, detail=f"Publisher not found: {publisher_id}")
        updated_publisher.api_key = None

        enriched_publisher = await self._enrich_publisher_with_widget_config(updated_publisher)
        response = PublisherResponse(success=True, publisher=updated_publisher, message="Publisher updated successfully")
        response_dict = response.model_dump()
        response_dict["publisher"] = enriched_publisher
        return response_dict

    async def delete_publisher(
        self,
        *,
        publisher_id: str,
    ) -> Dict:
        publisher = await self.publisher_repo.get_publisher_by_id(publisher_id)
        if not publisher:
            raise HTTPException(status_code=404, detail=f"Publisher not found: {publisher_id}")

        await self.publisher_repo.update_publisher(publisher_id, {"status": PublisherStatus.INACTIVE})
        return {"success": True, "message": "Publisher deleted successfully"}

    async def reactivate_publisher(
        self,
        *,
        publisher_id: str,
        request_id: str,
    ) -> Dict:
        publisher = await self.publisher_repo.get_publisher_by_id(publisher_id)
        if not publisher:
            raise HTTPException(status_code=404, detail=f"Publisher not found: {publisher_id}")
        if publisher.status == PublisherStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Publisher is already active")

        await self.publisher_repo.update_publisher(publisher_id, {"status": PublisherStatus.ACTIVE})
        updated_publisher = await self.publisher_repo.get_publisher_by_id(publisher_id)
        updated_publisher.api_key = None
        enriched = await self._enrich_publisher_with_widget_config(updated_publisher)

        response = PublisherResponse(
            success=True,
            publisher=updated_publisher,
            message="Publisher reactivated successfully",
        )
        response_dict = response.model_dump()
        response_dict["publisher"] = enriched
        return response_dict

    async def list_publishers(
        self,
        *,
        status: Optional[PublisherStatus],
        page: int,
        page_size: int,
    ) -> Dict:
        publishers, total = await self.publisher_repo.list_publishers(status, page, page_size)
        for pub in publishers:
            pub.api_key = None

        list_response = PublisherListResponse(
            success=True,
            publishers=publishers,
            total=total,
            page=page,
            page_size=page_size,
        )
        response_dict = list_response.model_dump()
        enriched_publishers: List[Dict] = []
        for pub in publishers:
            enriched_publishers.append(await self._enrich_publisher_with_widget_config(pub))
        response_dict["publishers"] = enriched_publishers
        return response_dict

    async def get_publisher_config(
        self,
        *,
        publisher_id: str,
    ) -> Dict:
        publisher = await self.publisher_repo.get_publisher_by_id(publisher_id)
        if not publisher:
            raise HTTPException(status_code=404, detail=f"Publisher not found: {publisher_id}")

        raw_config = await self.publisher_repo.get_publisher_raw_config_by_domain(publisher.domain, allow_subdomain=False)
        config_dict = publisher.config.model_dump()
        config_dict.pop("summary_temperature", None)
        config_dict.pop("questions_temperature", None)
        config_dict.pop("chat_temperature", None)
        config_dict.pop("generate_summary", None)
        config_dict.pop("generate_embeddings", None)
        if raw_config and isinstance(raw_config, dict):
            config_dict["widget"] = raw_config.get("widget", {})
        else:
            config_dict["widget"] = {}

        return {
            "success": True,
            "config": config_dict,
        }

    async def regenerate_api_key(
        self,
        *,
        publisher_id: str,
        request_id: str,
    ) -> Dict:
        try:
            publisher, new_api_key = await self.publisher_repo.regenerate_api_key(publisher_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

        response = PublisherRegenerateApiKeyResponse(
            message="API key regenerated successfully",
            publisher=publisher,
            api_key=new_api_key,
        )
        response_dict = response.model_dump()
        response_dict["result"]["message"] = (
            "⚠️ IMPORTANT: Save this API key now - it won't be shown again! The old key has been invalidated."
        )
        return response_dict

    # ============================================================================
    # URL Whitelist Validation (Business Rules)
    # ============================================================================

    @staticmethod
    def is_url_whitelisted(url: str, whitelist: Optional[Sequence[str]]) -> bool:
        """Return True if the URL is allowed by the whitelist definition."""
        if not whitelist:
            return True

        normalized_url = normalize_url(url)
        parsed = urlparse(normalized_url)

        for raw in whitelist:
            if raw is None:
                continue

            entry = raw.strip()
            if not entry:
                continue

            if entry == "*":
                return True

            if "://" in entry:
                # Compare normalized URL prefixes when full URL is provided
                allowed = normalize_url(entry)
                if normalized_url.startswith(allowed):
                    return True
                continue

            # Handle domain or path fragments
            # If the entry looks like a path (/news/featured)
            if entry.startswith("/"):
                if parsed.path.startswith(entry):
                    return True
                continue

            # Attempt to treat the entry as a host/path without scheme
            candidate = normalize_url(f"https://{entry.lstrip('/')}")
            if normalized_url.startswith(candidate):
                return True

            # Fallback: substring match on path
            if entry.lower() in parsed.path.lower():
                return True

        return False

    @staticmethod
    def ensure_url_whitelisted(url: str, publisher: Publisher) -> None:
        """Raise HTTPException if the blog URL is not allowed for this publisher."""
        whitelist = getattr(publisher.config, "whitelisted_blog_urls", None)
        if PublisherService.is_url_whitelisted(url, whitelist):
            return

        raise HTTPException(
            status_code=403,
            detail="Blog URL is not whitelisted for this publisher.",
        )

