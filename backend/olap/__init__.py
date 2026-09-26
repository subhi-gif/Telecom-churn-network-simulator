"""
Telecom OLAP Analytical Engine Package
Exposes multidimensional analysis operations for Customer Churn and Network Performance marts.
"""

from backend.olap.customer_olap import (
    CustomerOLAP,
    get_customer_dice,
    get_customer_drilldown,
    get_customer_rollup,
    get_customer_slice,
    get_customer_summary,
)
from backend.olap.network_olap import (
    NetworkOLAP,
    get_high_call_drop_cells,
    get_network_dice,
    get_network_drilldown,
    get_network_rollup,
    get_network_slice,
    get_network_summary,
)
from backend.olap.queries import (
    VALID_CONTRACTS,
    VALID_INTERNET_SERVICES,
    VALID_PAYMENT_METHODS,
    VALID_REGIONS,
    VALID_TECHNOLOGIES,
    VALID_TENURE_BANDS,
    VALID_TIME_LEVELS,
    execute_query,
    get_connection,
    get_default_db_path,
)

__all__ = [
    # Classes
    "CustomerOLAP",
    "NetworkOLAP",
    # Customer OLAP Functions
    "get_customer_summary",
    "get_customer_rollup",
    "get_customer_drilldown",
    "get_customer_slice",
    "get_customer_dice",
    # Network OLAP Functions
    "get_network_summary",
    "get_network_rollup",
    "get_network_drilldown",
    "get_network_slice",
    "get_network_dice",
    "get_high_call_drop_cells",
    # Query & Validation Utilities
    "get_connection",
    "get_default_db_path",
    "execute_query",
    "VALID_CONTRACTS",
    "VALID_INTERNET_SERVICES",
    "VALID_PAYMENT_METHODS",
    "VALID_TENURE_BANDS",
    "VALID_REGIONS",
    "VALID_TECHNOLOGIES",
    "VALID_TIME_LEVELS",
]
