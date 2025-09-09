from inventree.part import PartCategory, Part, Parameter, ParameterTemplate, PartRelated, BomItem
from inventree.company import Company, SupplierPart, ManufacturerPart
from inventree.base import Attachment
from inventree.stock import StockItem, StockLocation

class EntityCache:
    def __init__(self):
        self.cache = {}

    caches = {
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

    def populate(self, api, keys=None):
        """
        Populate the cache with all or selected entities.
        If keys is None, populate all known entities.
        """
        entity_map = {
            'attachment': Attachment,
            'bomitem': BomItem,
            'company': Company,
            'manufacturerpart': ManufacturerPart,
            'parameter': Parameter,
            'part': Part,
            'partcategory': PartCategory,
            'partrelated': PartRelated,
            'supplierpart': SupplierPart
        }
        if keys is None:
            keys = entity_map.keys()
        for key in keys:
            self.cache[key] = entity_map[key].list(api)

    def get(self, key, default=None):
        return self.cache.get(key, default)

    def clear(self):
        self.cache.clear()

    def refresh(self, api, key):
        """Refresh a specific entity in the cache."""
        self.populate(api, keys=[key])

    def get_highest_pk(self, entity_type):
        """Get the highest primary key for a given entity type."""
        cache = self.caches.get(entity_type, {})
        if not cache:
            return None
        return max(cache.values())

# Singleton instance
entity_cache = EntityCache()