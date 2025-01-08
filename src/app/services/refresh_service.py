"""Service for handling fence content refresh operations."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from flask import session

from src.app.models.reference_models import FenceReference, ReferenceType
from src.app.services.global_token_counter import GlobalTokenCounter
from src.app.services.reference_service import ReferenceService
from src.app.services.token_service import TokenCountingService
from src.app.utils.exceptions import RefreshError

logger = logging.getLogger(__name__)


class RefreshService:
    """Service for managing fence content refresh operations."""

    def __init__(
        self,
        reference_service: ReferenceService,
        global_token_counter: GlobalTokenCounter,
    ):
        """Initialize the refresh service.

        Args:
            reference_service: Service for handling references
            global_token_counter: Service for managing global token counts
        """
        self.reference_service = reference_service
        self.global_token_counter = global_token_counter
        self.token_counting_service = TokenCountingService()

    async def refresh_block(self, block_id: str, content: str = None) -> dict[str, Any]:
        """Refresh a single fence block's content and token count.

        Args:
            block_id: ID of the fence block to refresh
            content: Current content of the block (optional)

        Returns:
            Dict containing updated content and token count

        Raises:
            RefreshError: If refresh operation fails
        """
        try:
            references = session.get("fence_references", {}).get(block_id, [])
            if content and "@[" in content:
                ref_matches = re.finditer(r"@\[([^:]+):([^\]]+)\]", content)
                references = [
                    {
                        "reference_type": match.group(1),
                        "reference_value": match.group(2),
                        "reference_metadata": {},
                    }
                    for match in ref_matches
                ]

            # Process references only for token counting
            reference_content = (
                await self._process_references(references) if references else ""
            )
            content_for_counting = (
                reference_content if reference_content else (content or "")
            )

            # Count tokens using the processed content
            token_count_result, _ = await self.token_counting_service.count_tokens(
                content_for_counting
            )

            # Update global token counter and get total
            await self.global_token_counter.update_block(block_id, token_count_result)
            total_tokens = self.global_token_counter.total_tokens

            # Return original content to preserve reference patterns
            return {
                "content": content or "",  # Return original content
                "token_count": token_count_result,
                "total_tokens": total_tokens,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error refreshing block {block_id}: {e!s}")
            raise RefreshError(f"Failed to refresh block {block_id}") from e

    async def refresh_all(
        self, blocks: list[str], contents: dict[str, str] = None
    ) -> dict[str, Any]:
        """Refresh multiple fence blocks.

        Args:
            blocks: List of block IDs to refresh
            contents: Dict mapping block IDs to their current content

        Returns:
            Dict containing refresh results for all blocks and total token count

        Raises:
            RefreshError: If global refresh operation fails
        """
        try:
            self.global_token_counter.reset()
            refresh_tasks = [
                self.refresh_block(
                    block_id, content=contents.get(block_id) if contents else None
                )
                for block_id in blocks
            ]
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*refresh_tasks, return_exceptions=True),
                    timeout=30,  # 30 second timeout
                )
            except asyncio.TimeoutError:
                logger.error("Refresh operation timed out after 30 seconds")
                raise RefreshError(
                    "Operation timed out. Please try refreshing blocks individually."
                )

            block_tokens = {}
            block_contents = {}
            total_tokens = 0

            for block_id, result in zip(blocks, results, strict=False):
                if isinstance(result, Exception):
                    logger.error(f"Error refreshing block {block_id}: {result!s}")
                else:
                    token_count = result["token_count"]
                    block_tokens[block_id] = token_count
                    block_contents[block_id] = result["content"]
                    total_tokens += token_count
            await self.global_token_counter.set_total_tokens(total_tokens)

            return {
                "status": "success",
                "total_tokens": total_tokens,
                "block_tokens": block_tokens,
                "contents": block_contents,
            }

        except Exception as e:
            logger.error(f"Error during global refresh: {e!s}")
            raise RefreshError("Failed to refresh all blocks") from e

    async def _process_references(self, references: list[dict[str, Any]]) -> str:
        """Process a list of references and return the combined content.

        Args:
            references: List of reference data

        Returns:
            Combined content from all references

        Raises:
            RefreshError: If reference processing fails
        """
        try:
            if not references:
                return ""
            fence_refs = []
            for ref in references:
                try:
                    ref_type = ReferenceType(ref.get("reference_type"))
                    fence_ref = FenceReference(
                        reference_type=ref_type,
                        reference_value=ref.get("reference_value", ""),
                        reference_metadata=ref.get("reference_metadata", {}),
                    )
                    fence_refs.append(fence_ref)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid reference data: {e}")
                    continue
            if not fence_refs:
                return ""
            contents = []
            for ref in fence_refs:
                content, error = await self.reference_service.get_reference_content(ref)
                if error:
                    logger.warning(f"Reference error: {error}")
                elif content:
                    contents.append(content)
            return "\n".join(contents)

        except Exception as e:
            logger.error(f"Error processing references: {e!s}")
            raise RefreshError("Failed to process references") from e
