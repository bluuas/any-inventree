"""
Utilities for managing and resolving pending part relations after all parts are created.
"""
import logging
from utils.logging_utils import get_configured_level
from utils.entity_resolver import resolve_entity
from inventree.part import PartRelated

logger = logging.getLogger('relation-utils')
logger.setLevel(get_configured_level() if callable(get_configured_level) else logging.INFO)

# Global list to store pending relations as tuples (part_1_pk, part_2_pk)
_pending_relations = []

def add_pending_relation(part_1_pk, part_2_pk):
    """
    Add a pending relation between two part primary keys.
    """
    _pending_relations.append((part_1_pk, part_2_pk))
    logger.debug(f"Added pending relation: {part_1_pk} <-> {part_2_pk}")

def resolve_pending_relations(api):
    """
    Create all pending part relations using resolve_entity.
    Should be called after all parts are created.
    """
    logger.info(f"Resolving {len(_pending_relations)} pending part relations...")
    for part_1_pk, part_2_pk in _pending_relations:
        try:
            resolve_entity(api, PartRelated, {
                'part_1': part_1_pk,
                'part_2': part_2_pk,
            })
            logger.debug(f"Created relation: {part_1_pk} <-> {part_2_pk}")
        except Exception as e:
            logger.error(f"Failed to create relation {part_1_pk} <-> {part_2_pk}: {e}")
    _pending_relations.clear()
    logger.info("All pending part relations resolved.")
