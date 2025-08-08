"""
Utilities for managing and resolving pending part relations after all parts are created.
"""
import logging
from utils.logging_utils import get_configured_level
from utils.entity_resolver import resolve_entity
from inventree.part import Part, PartRelated

logger = logging.getLogger('relation-utils')
logger.setLevel(get_configured_level() if callable(get_configured_level) else logging.INFO)

# Global list to store pending relations as tuples (part_1_pk, part_2_pk)
_pending_relations = []

def add_pending_relation(part_1_pk, part_2_name):
    """
    Add a pending relation between two part primary keys.
    """
    if not part_2_name:
        logger.warning(f"Attempted to add a pending relation with an empty part name for PK: {part_1_pk}")
        return
    _pending_relations.append((part_1_pk, part_2_name))
    logger.debug(f"Added pending relation: {part_1_pk} <-> {part_2_name}")

def resolve_pending_relations(api):
    """
    Create all pending part relations using resolve_entity.
    Should be called after all parts are created.
    """
    logger.info(f"Resolving {len(_pending_relations)} pending part relations...")

    # resolve all part names to their primary keys
    parts = Part.list(api)
    for part in parts:
        logger.info(f"Part: {part['name']} (PK: {part['pk']})")

    part_lookup = {part['name']: part['pk'] for part in parts}
    for part_1_pk, part_2_name in _pending_relations:
        part_2_pk = part_lookup.get(part_2_name)
        if part_2_pk is None:
            logger.warning(f"Part '{part_2_name}' not found. Skipping relation.")
            continue
        try:
            resolve_entity(api, PartRelated, {
                'part_1': part_1_pk,
                'part_2': part_2_pk,
            })
            logger.debug(f"Created relation: {part_1_pk} <-> {part_2_pk}")
        except Exception as e:
            logger.error(f"Failed to create relation {part_1_pk} <-> {part_2_pk}: {e}")

    # for part_1_pk, part_2_pk in _pending_relations:
    #     try:
    #         resolve_entity(api, PartRelated, {
    #             'part_1': part_1_pk,
    #             'part_2': part_2_pk,
    #         })
    #         logger.debug(f"Created relation: {part_1_pk} <-> {part_2_pk}")
    #     except Exception as e:
    #         logger.error(f"Failed to create relation {part_1_pk} <-> {part_2_pk}: {e}")
    _pending_relations.clear()
    logger.info("All pending part relations resolved.")
