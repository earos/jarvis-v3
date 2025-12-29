"""
JARVIS v3 - Integration Management API
Provides endpoints for managing integration settings
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])

# Path to store integration overrides
INTEGRATIONS_FILE = Path("/opt/jarvis-v3/backend/data/integrations.json")

# Define sensitive field patterns that should be masked
SENSITIVE_FIELDS = {
    "password", "token", "api_key", "access_code", "token_value"
}


# Pydantic models for request/response
class IntegrationConfig(BaseModel):
    """Configuration for an integration"""
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)


class IntegrationUpdate(BaseModel):
    """Update request for an integration"""
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class IntegrationTestResult(BaseModel):
    """Result of testing an integration"""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


# Integration definitions with their fields
INTEGRATION_DEFINITIONS = {
    "anthropic": {
        "fields": ["api_key"],
        "env_prefix": "anthropic"
    },
    "unifi_network": {
        "fields": ["host", "username", "password", "site"],
        "env_prefix": "unifi"
    },
    "unifi_protect": {
        "fields": ["host", "username", "password"],
        "env_prefix": "protect"
    },
    "proxmox": {
        "fields": ["pve1_host", "token_name", "token_value"],
        "optional_fields": ["pve2_host"],
        "env_prefix": "proxmox"
    },
    "prometheus": {
        "fields": ["url"],
        "env_prefix": "prometheus"
    },
    "uptime_kuma": {
        "fields": ["url"],
        "env_prefix": "uptime_kuma"
    },
    "home_assistant": {
        "fields": ["url", "token"],
        "env_prefix": "home_assistant"
    },
    "portainer": {
        "fields": ["url", "api_key"],
        "env_prefix": "portainer"
    },
    "elevenlabs": {
        "fields": ["api_key", "voice_id"],
        "env_prefix": "elevenlabs"
    },
    "tavily": {
        "fields": ["api_key"],
        "env_prefix": "tavily"
    },
    "synology": {
        "fields": ["host", "user", "password"],
        "env_prefix": "synology"
    },
    "adguard": {
        "fields": ["url", "user", "password"],
        "env_prefix": "adguard"
    },
    "grafana": {
        "fields": ["url", "api_key"],
        "env_prefix": "grafana"
    },
    "nginx_proxy_manager": {
        "fields": ["url", "user", "password"],
        "env_prefix": "npm"
    },
    "starlink": {
        "fields": ["host"],
        "env_prefix": "starlink"
    },
    "bambu_printer": {
        "fields": ["host", "access_code"],
        "env_prefix": "bambu"
    },
    "prusa_printer": {
        "fields": ["host", "api_key"],
        "env_prefix": "prusa"
    },
}


def is_sensitive_field(field_name: str) -> bool:
    """Check if a field name indicates sensitive data"""
    field_lower = field_name.lower()
    return any(sensitive in field_lower for sensitive in SENSITIVE_FIELDS)


def mask_sensitive_value(value: Any) -> str:
    """Mask a sensitive value"""
    if value is None or value == "":
        return ""
    str_value = str(value)
    if len(str_value) <= 8:
        return "***"
    return f"{str_value[:4]}...{str_value[-4:]}"


def load_integration_overrides() -> Dict[str, Dict[str, Any]]:
    """Load integration overrides from JSON file"""
    if not INTEGRATIONS_FILE.exists():
        return {}
    
    try:
        with open(INTEGRATIONS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading integrations file: {e}")
        return {}


def save_integration_overrides(overrides: Dict[str, Dict[str, Any]]):
    """Save integration overrides to JSON file"""
    try:
        INTEGRATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(INTEGRATIONS_FILE, 'w') as f:
            json.dump(overrides, f, indent=2)
        logger.info(f"Saved integration overrides to {INTEGRATIONS_FILE}")
    except Exception as e:
        logger.error(f"Error saving integrations file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save integration settings: {str(e)}"
        )


def get_integration_config(name: str, mask_sensitive: bool = True) -> Dict[str, Any]:
    """
    Get configuration for a specific integration
    
    Args:
        name: Integration name
        mask_sensitive: Whether to mask sensitive fields
        
    Returns:
        Dictionary with integration configuration
    """
    if name not in INTEGRATION_DEFINITIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{name}' not found"
        )
    
    definition = INTEGRATION_DEFINITIONS[name]
    settings = get_settings()
    overrides = load_integration_overrides()
    
    config = {}
    
    # Handle multi-host integrations (like Proxmox)
    if "multi_host" in definition:
        for host_suffix in definition["multi_host"]:
            host_config = {}
            for field in definition["fields"]:
                # Build the attribute name: proxmox_pve1_host, proxmox_pve1_password, etc.
                attr_name = f"{definition['env_prefix']}_{host_suffix}_{field}"
                
                # Check overrides first
                override_key = f"{host_suffix}_{field}"
                if name in overrides and override_key in overrides[name]:
                    value = overrides[name][override_key]
                else:
                    # Fall back to settings
                    value = getattr(settings, attr_name, None)
                
                # Mask sensitive fields if requested
                if mask_sensitive and is_sensitive_field(field) and value:
                    value = mask_sensitive_value(value)
                
                host_config[field] = value
            
            config[host_suffix] = host_config
    else:
        # Regular single-instance integration
        for field in definition["fields"]:
            # Build the attribute name: unifi_host, unifi_username, etc.
            attr_name = f"{definition['env_prefix']}_{field}"
            
            # Check overrides first
            if name in overrides and field in overrides[name]:
                value = overrides[name][field]
            else:
                # Fall back to settings
                value = getattr(settings, attr_name, None)
            
            # Mask sensitive fields if requested
            if mask_sensitive and is_sensitive_field(field) and value:
                value = mask_sensitive_value(value)
            
            config[field] = value
    
    # Determine if integration is enabled (has required fields configured)
    enabled = any(v is not None and v != "" for v in _flatten_config(config).values())
    
    return {
        "name": name,
        "enabled": enabled,
        "config": config
    }


def _flatten_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten nested config for checking if values exist"""
    flat = {}
    for key, value in config.items():
        if isinstance(value, dict):
            flat.update(_flatten_config(value))
        else:
            flat[key] = value
    return flat


@router.get("")
async def list_integrations():
    """
    List all available integrations with their current configuration.
    Sensitive fields (passwords, tokens, API keys) are masked.
    """
    integrations = []
    
    for name in sorted(INTEGRATION_DEFINITIONS.keys()):
        try:
            integration = get_integration_config(name, mask_sensitive=True)
            integrations.append(integration)
        except Exception as e:
            logger.error(f"Error loading integration {name}: {e}")
            integrations.append({
                "name": name,
                "enabled": False,
                "config": {},
                "error": str(e)
            })
    
    return {
        "integrations": integrations,
        "count": len(integrations)
    }


@router.get("/{name}")
async def get_integration(name: str):
    """
    Get configuration for a specific integration.
    Sensitive fields are masked.
    """
    return get_integration_config(name, mask_sensitive=True)


@router.put("/{name}")
async def update_integration(name: str, update: IntegrationUpdate):
    """
    Update configuration for a specific integration.
    
    Request body:
    {
        "enabled": true,
        "config": {
            "host": "192.168.10.1",
            "username": "admin",
            "password": "newpassword"
        }
    }
    
    For multi-host integrations like Proxmox:
    {
        "config": {
            "pve1": {
                "host": "192.168.10.50",
                "password": "newpassword"
            },
            "pve2": {
                "host": "192.168.10.51"
            }
        }
    }
    """
    if name not in INTEGRATION_DEFINITIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{name}' not found"
        )
    
    if update.config is None and update.enabled is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either 'config' or 'enabled' field"
        )
    
    # Load existing overrides
    overrides = load_integration_overrides()
    
    # Initialize integration overrides if not exists
    if name not in overrides:
        overrides[name] = {}
    
    # Update configuration if provided
    if update.config is not None:
        definition = INTEGRATION_DEFINITIONS[name]
        
        # Validate and update fields
        if "multi_host" in definition:
            # Multi-host integration (e.g., Proxmox)
            for host_suffix, host_config in update.config.items():
                if host_suffix not in definition["multi_host"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid host '{host_suffix}' for integration '{name}'"
                    )
                
                for field, value in host_config.items():
                    if field not in definition["fields"]:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid field '{field}' for integration '{name}'"
                        )
                    
                    # Store with composite key: pve1_host, pve2_password, etc.
                    override_key = f"{host_suffix}_{field}"
                    
                    # Don't store masked values (unchanged sensitive fields)
                    if is_sensitive_field(field) and value and "..." in str(value):
                        continue
                    
                    overrides[name][override_key] = value
        else:
            # Single-instance integration
            for field, value in update.config.items():
                if field not in definition["fields"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid field '{field}' for integration '{name}'"
                    )
                
                # Don't store masked values (unchanged sensitive fields)
                if is_sensitive_field(field) and value and "..." in str(value):
                    continue
                
                overrides[name][field] = value
    
    # Save overrides
    save_integration_overrides(overrides)
    
    # Return updated configuration (masked)
    return get_integration_config(name, mask_sensitive=True)


@router.get("/{name}/test")
async def test_integration(name: str):
    """
    Test an integration's connection and configuration.
    Returns success/failure status with details.
    """
    if name not in INTEGRATION_DEFINITIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{name}' not found"
        )
    
    # Get unmasked configuration for testing
    try:
        integration = get_integration_config(name, mask_sensitive=False)
    except Exception as e:
        return IntegrationTestResult(
            success=False,
            message=f"Failed to load configuration: {str(e)}"
        )
    
    if not integration["enabled"]:
        return IntegrationTestResult(
            success=False,
            message="Integration is not configured or enabled"
        )
    
    # Perform integration-specific tests
    try:
        result = await _test_integration(name, integration["config"])
        return result
    except Exception as e:
        logger.error(f"Error testing integration {name}: {e}", exc_info=True)
        return IntegrationTestResult(
            success=False,
            message=f"Test failed with error: {str(e)}"
        )


async def _test_integration(name: str, config: Dict[str, Any]) -> IntegrationTestResult:
    """
    Perform actual integration testing.
    This is a placeholder that can be extended with real connection tests.
    """
    import aiohttp
    import asyncio
    
    # URL-based service tests
    if name in ["prometheus", "uptime_kuma", "grafana", "adguard", "nginx_proxy_manager", "portainer"]:
        url = config.get("url")
        if not url:
            return IntegrationTestResult(
                success=False,
                message="URL not configured"
            )
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5), ssl=False) as response:
                    return IntegrationTestResult(
                        success=response.status < 500,
                        message=f"HTTP {response.status}" if response.status < 500 else f"Server error: HTTP {response.status}",
                        details={"status_code": response.status, "url": url}
                    )
        except asyncio.TimeoutError:
            return IntegrationTestResult(
                success=False,
                message="Connection timeout",
                details={"url": url}
            )
        except Exception as e:
            return IntegrationTestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                details={"url": url}
            )
    
    # Home Assistant test
    elif name == "home_assistant":
        url = config.get("url")
        token = config.get("token")
        
        if not url or not token:
            return IntegrationTestResult(
                success=False,
                message="URL or token not configured"
            )
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {token}"}
                async with session.get(f"{url}/api/", headers=headers, timeout=aiohttp.ClientTimeout(total=5), ssl=False) as response:
                    if response.status == 200:
                        data = await response.json()
                        return IntegrationTestResult(
                            success=True,
                            message=f"Connected to Home Assistant (v{data.get('version', 'unknown')})",
                            details={"version": data.get('version')}
                        )
                    else:
                        return IntegrationTestResult(
                            success=False,
                            message=f"Authentication failed: HTTP {response.status}"
                        )
        except Exception as e:
            return IntegrationTestResult(
                success=False,
                message=f"Connection failed: {str(e)}"
            )
    
    # Anthropic API test
    elif name == "anthropic":
        api_key = config.get("api_key")
        
        if not api_key:
            return IntegrationTestResult(
                success=False,
                message="API key not configured"
            )
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                }
                # Just test if the API key format is valid by hitting the messages endpoint with a minimal request
                # This will return an error but we can verify the key is accepted
                async with session.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json={"model": "claude-3-5-sonnet-20241022", "max_tokens": 1, "messages": []},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    # Even with invalid request, if key is valid we get 4xx, not 401
                    if response.status in [400, 422]:
                        return IntegrationTestResult(
                            success=True,
                            message="API key is valid"
                        )
                    elif response.status == 401:
                        return IntegrationTestResult(
                            success=False,
                            message="Invalid API key"
                        )
                    else:
                        return IntegrationTestResult(
                            success=True,
                            message=f"API accessible (HTTP {response.status})"
                        )
        except Exception as e:
            return IntegrationTestResult(
                success=False,
                message=f"Connection failed: {str(e)}"
            )
    
    # Starlink test
    elif name == "starlink":
        host = config.get("host")
        
        if not host:
            return IntegrationTestResult(
                success=False,
                message="Host not configured"
            )
        
        try:
            # Try to connect to Starlink gRPC endpoint (it should at least respond)
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, 9200))
            sock.close()
            
            if result == 0:
                return IntegrationTestResult(
                    success=True,
                    message="Starlink reachable on port 9200",
                    details={"host": host}
                )
            else:
                return IntegrationTestResult(
                    success=False,
                    message=f"Cannot connect to {host}:9200"
                )
        except Exception as e:
            return IntegrationTestResult(
                success=False,
                message=f"Connection failed: {str(e)}"
            )
    
    # For other integrations, just verify configuration exists
    else:
        # Check if all required fields are configured
        definition = INTEGRATION_DEFINITIONS[name]
        missing_fields = []
        
        if "multi_host" in definition:
            # Multi-host integration
            for host_suffix in definition["multi_host"]:
                if host_suffix not in config:
                    missing_fields.append(host_suffix)
                    continue
                
                host_config = config[host_suffix]
                for field in definition["fields"]:
                    if not host_config.get(field):
                        missing_fields.append(f"{host_suffix}.{field}")
        else:
            # Single-instance integration
            for field in definition["fields"]:
                if not config.get(field):
                    missing_fields.append(field)
        
        if missing_fields:
            return IntegrationTestResult(
                success=False,
                message=f"Missing required fields: {', '.join(missing_fields)}"
            )
        
        return IntegrationTestResult(
            success=True,
            message="Configuration appears valid (connection test not implemented for this integration)",
            details={"note": "This integration does not have a connection test implemented yet"}
        )
