from django.db import models


class PlanCode(models.TextChoices):
    FREE = "FREE", "Бесплатный"
    STARTUP = "STARTUP", "Стартап"
    BUSINESS = "BUSINESS", "Бизнес"
    CORPORATION = "CORPORATION", "Корпорация"


class EntitlementKey(models.TextChoices):
    SALES_DEPARTMENT = "sales_department", "Sales department"
    SUPPORT_DEPARTMENT = "support_department", "Support department"
    CRM_API = "crm_api", "CRM API"
    PRODUCT_SALES_API = "product_sales_api", "Product Sales API"
    P2P_CALLS = "p2p_calls", "P2P calls"
    VOICE_AI = "voice_ai", "Voice AI"
    KNOWLEDGE_BASE = "knowledge_base", "Knowledge base"
    ONE_C_CONNECTOR = "one_c_connector", "1C connector"
    CUSTOMER_AUDIT = "customer_audit", "Customer audit"
    SSO_SAML = "sso_saml", "SSO/SAML"
    MANAGED_AI = "managed_ai", "Managed AI"
    BYOK_AI = "byok_ai", "BYOK AI"


class QuotaKey(models.TextChoices):
    AI_AGENT_SLOTS = "ai_agent_slots", "AI agent slots"
    PRODUCTS = "products", "Products"
    CLIENT_CONNECTIONS = "client_connections", "Client connections"
    NEW_DIALOGS_PER_PERIOD = "new_dialogs_per_period", "New dialogs per period"
    MANAGED_AI_CREDITS = "managed_ai_credits", "Managed AI credits"
    STORAGE_BYTES = "storage_bytes", "Storage bytes"
    CRM_API_REQUESTS_PER_WINDOW = "crm_api_requests_per_window", "CRM API requests"
    CONCURRENT_P2P_CALLS = "concurrent_p2p_calls", "Concurrent P2P calls"
    CONCURRENT_VOICE_SESSIONS = "concurrent_voice_sessions", "Concurrent voice sessions"
    AUDIT_RETENTION_DAYS = "audit_retention_days", "Audit retention days"
    SUPPORT_PORTALS = "support_portals", "Support portals"
