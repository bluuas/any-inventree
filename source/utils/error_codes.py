"""
Centralized error codes for InvenTree operations.
"""

class ErrorCodes:
    # General success and failure codes
    SUCCESS = 0
    
    # Input/Data validation errors (1-9)
    INVALID_PK = 1
    INVALID_NAME = 2
    INVALID_DATA = 3
    INVALID_ASSEMBLY_DATA = 4
    
    # File operation errors (10-19)
    FILE_ERROR = 10
    
    # Configuration errors (20-29)
    CONFIGURATION_ERROR = 20
    
    # API and network errors (30-39)
    API_ERROR = 30
    
    # Entity creation and resolution errors (40-49)
    ENTITY_CREATION_FAILED = 40
    INVALID_ENTITY_TYPE = 41
    
    # Part-specific errors (50-59)
    PARAMETER_ERROR = 50
    NO_RELATIONS = 51
    PART_NOT_FOUND = 52
    NO_MANUFACTURER_PARTS = 53
    
    # Supplier and manufacturer errors (60-69)
    SUPPLIER_ERROR = 60
    
    # Category errors (70-79)
    CATEGORY_ERROR = 70
    
    # BOM processing errors (80-89)
    BOM_PROCESSING_ERROR = 80
    MPN_LOOKUP_ERROR = 81
    
    # Relation errors (90-99)
    RELATION_CREATION_FAILED = 90
    RELATIONS_ERROR = 91
    
    # Part creation composite errors (100-109)
    PART_CREATION_ERROR = 100