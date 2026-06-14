"""
gracenote2epg.xmltv.credits - Cast and crew <credits> (DTD-ordered).
"""

import logging
from typing import Dict
from ..utils import HtmlUtils


class CreditsMixin:
    """Cast and crew <credits> (DTD-ordered)."""

    def _write_credits_dtd_compliant(
        self, fh, episode_data: Dict, use_extended_details: bool = True
    ):
        """Write cast and crew credits - DTD compliant with proper ordering"""
        # Only write credits if extended details are enabled
        if not use_extended_details:
            return

        credits = episode_data.get("epcredits")
        if credits and isinstance(credits, list):

            # Valid DTD roles in STRICT ORDER as required by DTD
            dtd_role_order = [
                "director",
                "actor",
                "writer",
                "adapter",
                "producer",
                "composer",
                "editor",
                "presenter",
                "commentator",
                "guest",
            ]

            # Map original roles to DTD roles
            role_mapping = {
                "director": "director",
                "actor": "actor",
                "writer": "writer",
                "adapter": "adapter",
                "producer": "producer",
                "composer": "composer",
                "editor": "editor",
                "presenter": "presenter",
                "commentator": "commentator",
                "guest": "guest",
                "voice": "actor",  # Map voice to actor
                "narrator": "presenter",  # Map narrator to presenter
                "host": "presenter",  # Map host to presenter
            }

            # Group credits by DTD role type
            grouped_credits = {role: [] for role in dtd_role_order}

            for credit in credits:
                if isinstance(credit, dict):
                    original_role = credit.get("role", "").lower()
                    name = credit.get("name", "")
                    character = credit.get("characterName", "")
                    asset_id = credit.get("assetId", "")

                    # Map to valid DTD role
                    if original_role in role_mapping and name:
                        dtd_role = role_mapping[original_role]
                        grouped_credits[dtd_role].append(
                            {
                                "name": name,
                                "character": character,
                                "asset_id": asset_id,
                                "original_role": original_role,
                            }
                        )

            # Check if we have any credits to write
            has_credits = any(len(credits_list) > 0 for credits_list in grouped_credits.values())

            if has_credits:
                fh.write("\t\t<credits>\n")

                # Write credits in DTD-required order
                for role in dtd_role_order:
                    credits_for_role = grouped_credits[role]

                    for credit_info in credits_for_role:
                        name = credit_info["name"]
                        character = credit_info["character"]
                        asset_id = credit_info["asset_id"]
                        original_role = credit_info["original_role"]

                        # DTD compliant format with compact image formatting
                        if character and role == "actor":
                            # Actor with character role
                            fh.write(f'\t\t\t<{role} role="{HtmlUtils.conv_html(character)}">')
                            fh.write(f"{HtmlUtils.conv_html(name)}")

                            # Add image directly after name without line break
                            if use_extended_details and asset_id:
                                photo_url = f"{self.ASSETS_BASE_URL}/g/{asset_id}.jpg"
                                fh.write(f'<image type="person">{photo_url}</image>')

                            fh.write(f"</{role}>\n")
                        else:
                            # Other roles or actors without character
                            fh.write(f"\t\t\t<{role}>")
                            fh.write(f"{HtmlUtils.conv_html(name)}")

                            # Add image directly after name without line break
                            if (
                                use_extended_details
                                and asset_id
                                and role in ["actor", "director", "presenter"]
                            ):
                                photo_url = f"{self.ASSETS_BASE_URL}/g/{asset_id}.jpg"
                                fh.write(f'<image type="person">{photo_url}</image>')

                            fh.write(f"</{role}>\n")

                        # Log mapping for visibility (debug level to avoid spam)
                        if original_role != role:
                            logging.debug(
                                "Credit mapped: %s (%s) -> %s (DTD compliant)",
                                name,
                                original_role,
                                role,
                            )

                fh.write("\t\t</credits>\n")

