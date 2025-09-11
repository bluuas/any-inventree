from inventree.part import PartCategory, Part, Parameter, ParameterTemplate, PartRelated, BomItem
from inventree.company import Company, SupplierPart, ManufacturerPart
from inventree.base import Attachment
from inventree.stock import StockItem, StockLocation
import logging

logger = logging.getLogger('InvenTreeCLI')

class EntityCache:
    def __init__(self):
        self.caches = {
            Attachment: {},
            BomItem: {},
            Company: {},
            ManufacturerPart: {},
            Parameter: {},
            ParameterTemplate: {},
            Part: {},
            PartCategory: {},
            PartRelated: {},
            StockItem: {},
            StockLocation: {},
            SupplierPart: {},
        }

        # Lookup Table for identifiers per entity type
        self.IDENTIFIER_LUT = {
            Attachment: ['link', 'model_id'],
            BomItem: ['part', 'sub_part'],
            Company: ['name'],
            ManufacturerPart: ['MPN'],
            Parameter: ['part', 'template'],
            ParameterTemplate: ['name'],
            Part: ['name', 'category', 'revision'],
            PartCategory: ['name', 'parent'],
            PartRelated: ['part_1', 'part_2'],
            StockItem: ['part', 'supplier_part'],
            StockLocation: ['name'],
            SupplierPart: ['SKU'],
        }

    def populate(self, api, keys=None, chunk_size=1000):
        """
        Populate the cache with all or selected entities.
        If keys is None, populate all known entities.
        Only identifier fields are stored for each entity.
        """
        logger.info("Populating entity cache...")
        try:
            entity_types = keys if keys is not None else list(self.caches.keys())
            for entity_cls in entity_types:
                logger.info(f"Fetching {entity_cls.__name__}...")
                offset = 0
                self.caches[entity_cls] = {}
                while True:
                    items = entity_cls.list(api, limit=chunk_size, offset=offset)
                    if not items:
                        break
                    for item in items:
                        pk = getattr(item, 'pk', None)
                        if pk is None:
                            continue
                        attrs = {}
                        for attr in self.IDENTIFIER_LUT.get(entity_cls, []):
                            attrs[attr] = getattr(item, attr, None)
                        self.caches[entity_cls][pk] = attrs
                    if len(items) < chunk_size:
                        break
                    offset += chunk_size
                    break # just for testing
        except Exception as e:
            logger.error(f"Error populating cache: {e}")

    def get(self, entity_cls, default=None):
        return self.caches.get(entity_cls, default)

    def clear(self):
        self.caches.clear()

    def refresh(self, api, entity_cls):
        """Refresh a specific entity in the cache."""
        self.populate(api, keys=[entity_cls])

    def get_number_of_cached_items(self, entity_cls):
        """Return the number of cached items for a specific entity type."""
        return len(self.caches.get(entity_cls, {}))

# Singleton instance
entity_cache = EntityCache()