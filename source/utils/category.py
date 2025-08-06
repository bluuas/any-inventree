"""
Category and subcategory creation utilities for InvenTree.
"""
import logging
from .entity_resolver import resolve_entity
from inventree.part import PartCategory

logger = logging.getLogger('InvenTreeCLI')

def create_categories(api, category_levels, parent_pk=None):
    """
    Recursively create or resolve part categories from a list of category levels.
    At the lowest level, create three subcategories: generic, critical, specific.
    Returns a dict with their PKs for the lowest level.
    """
    if not category_levels:
        # At the lowest level, create generic, critical, specific
        subcategories = {}
        for sub in ['generic', 'critical', 'specific']:
            subcategories[sub] = resolve_entity(api, PartCategory, {'name': sub, 'parent': parent_pk})
        return subcategories
    else:
        # Create/resolve this level, then recurse
        this_level = category_levels[0]
        if not this_level or str(this_level).lower() == 'nan':
            return None
        this_pk = resolve_entity(api, PartCategory, {'name': this_level, 'parent': parent_pk, 'structural': True})
        return create_categories(api, category_levels[1:], parent_pk=this_pk)
