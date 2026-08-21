"""Jumia Seller API 接入层（P3-1/P3-2-A/P3-2-B：HTTP Client + dry-run payload + 健康检查 + 单 SKU 上传闭环）。"""
from src.jumia.api.account import get_shop_info
from src.jumia.api.auth import JumiaAuth, MissingCredential
from src.jumia.api.categories import get_attributes, get_categories
from src.jumia.api.client import JumiaClient, build_listing_payload
from src.jumia.api.errors import (
    AuthenticationError,
    InvalidCategoryError,
    JumiaAPIError,
    PermissionError,
    RateLimitError,
    UploadDisabledError,
    UploadLimitExceededError,
    map_http_error,
)
from src.jumia.api.health import JumiaHealthReport, check_health
from src.jumia.api.http_client import JumiaHttpClient
from src.jumia.api.inventory import build_inventory_payload, update_inventory
from src.jumia.api.offer import build_offer_payload, create_offer
from src.jumia.api.payload_validator import REQUIRED_FIELDS, validate_payload
from src.jumia.api.product_create import build_product_payload, create_product
from src.jumia.api.product_update import build_product_update_payload
from src.jumia.api.request_builder import PreparedRequest, RequestBuilder
from src.jumia.api.response_parser import ParsedResponse, ResponseParser
from src.jumia.api.retry import RetryConfig, RetryHandler, RetryResult
from src.jumia.api.upload_guard import UploadGuard, UploadGuardConfig
from src.jumia.api.uploader import JumiaUploader, UploadResult

__all__ = [
    # auth
    "JumiaAuth",
    "MissingCredential",
    # client
    "JumiaClient",
    "build_listing_payload",
    # http client (P3-2-B-1)
    "JumiaHttpClient",
    "PreparedRequest",
    "RequestBuilder",
    "ParsedResponse",
    "ResponseParser",
    "RetryConfig",
    "RetryHandler",
    "RetryResult",
    # payload builders
    "build_product_payload",
    "build_product_update_payload",
    "build_offer_payload",
    "build_inventory_payload",
    # upload functions (P3-2-B-2)
    "create_product",
    "create_offer",
    "update_inventory",
    # validator
    "validate_payload",
    "REQUIRED_FIELDS",
    # errors
    "JumiaAPIError",
    "AuthenticationError",
    "PermissionError",
    "RateLimitError",
    "InvalidCategoryError",
    "UploadDisabledError",
    "UploadLimitExceededError",
    "map_http_error",
    # health
    "JumiaHealthReport",
    "check_health",
    # upload guard + uploader (P3-2-B-2)
    "UploadGuard",
    "UploadGuardConfig",
    "JumiaUploader",
    "UploadResult",
    # category / account
    "get_categories",
    "get_attributes",
    "get_shop_info",
]
