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
    
    @classmethod
    def get_description(cls, error_code):
        """Get human-readable description for error code."""
        descriptions = {
            cls.SUCCESS: "Operation completed successfully",
            cls.API_ERROR: "API communication error",
            cls.CONFIGURATION_ERROR: "Configuration error",
            cls.FILE_ERROR: "File operation error",
            cls.INVALID_DATA: "Invalid data provided",
            cls.ENTITY_CREATION_FAILED: "Failed to create entity",
            cls.CATEGORY_ERROR: "Category operation error",
            cls.PART_CREATION_ERROR: "Part creation error",
            cls.PARAMETER_ERROR: "Parameter operation error",
            cls.SUPPLIER_ERROR: "Supplier/manufacturer operation error",
            cls.RELATIONS_ERROR: "Part relations error",
            cls.INVALID_NAME: "Invalid name provided",
            cls.INVALID_ASSEMBLY_DATA: "Invalid assembly data",
            cls.BOM_PROCESSING_ERROR: "BOM processing error",
        }
        return descriptions.get(error_code, f"Unknown error code: {error_code}")