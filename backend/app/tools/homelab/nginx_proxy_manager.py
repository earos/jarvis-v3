"""
Nginx Proxy Manager Tool for JARVIS v3
Query and manage Nginx Proxy Manager for proxy hosts, SSL certificates, and redirections
"""
import httpx
from typing import Dict, Any, Optional

from app.tools.base import BaseTool, ToolParameter, ToolDomain
from app.config.settings import get_settings

settings = get_settings()


class NginxProxyManagerTool(BaseTool):
    """Query Nginx Proxy Manager for proxy configuration and SSL certificates"""
    
    name = "nginx_proxy_manager"
    description = """Query Nginx Proxy Manager for proxy hosts, SSL certificates, redirections, and status. Use this to check which domains are proxied, view SSL certificate status, or list redirections."""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            description="Type of information to retrieve from Nginx Proxy Manager",
            enum=["proxy_hosts", "certificates", "redirections", "status"]
        )
    ]
    
    def __init__(self):
        self.base_url = settings.npm_url
        self.username = settings.npm_user
        self.password = settings.npm_password
        
        if not all([self.base_url, self.username, self.password]):
            raise ValueError("NPM_URL, NPM_USER, and NPM_PASSWORD must be configured")
        
        self._token: Optional[str] = None
    
    async def _get_auth_token(self, client: httpx.AsyncClient) -> str:
        """Authenticate with NPM and get access token"""
        if self._token:
            return self._token
        
        try:
            response = await client.post(
                f"{self.base_url}/api/tokens",
                json={
                    "identity": self.username,
                    "secret": self.password
                }
            )
            response.raise_for_status()
            data = response.json()
            self._token = data.get("token")
            
            if not self._token:
                raise ValueError("No token returned from NPM authentication")
            
            return self._token
        except Exception as e:
            raise ValueError(f"Failed to authenticate with NPM: {str(e)}")
    
    async def execute(self, action: str) -> Dict[str, Any]:
        """Execute Nginx Proxy Manager query"""
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            try:
                # Get authentication token
                token = await self._get_auth_token(client)
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                
                if action == "proxy_hosts":
                    response = await client.get(
                        f"{self.base_url}/api/nginx/proxy-hosts",
                        headers=headers
                    )
                    response.raise_for_status()
                    hosts = response.json()
                    
                    # Simplify the response
                    simplified_hosts = []
                    for host in hosts:
                        simplified_hosts.append({
                            "id": host.get("id"),
                            "domain_names": host.get("domain_names", []),
                            "forward_host": host.get("forward_host"),
                            "forward_port": host.get("forward_port"),
                            "forward_scheme": host.get("forward_scheme"),
                            "ssl_enabled": host.get("ssl_forced", False) or host.get("certificate_id") is not None,
                            "certificate_id": host.get("certificate_id"),
                            "enabled": host.get("enabled", True)
                        })
                    
                    return {
                        "success": True,
                        "action": "proxy_hosts",
                        "host_count": len(simplified_hosts),
                        "hosts": simplified_hosts
                    }
                
                elif action == "certificates":
                    response = await client.get(
                        f"{self.base_url}/api/nginx/certificates",
                        headers=headers
                    )
                    response.raise_for_status()
                    certs = response.json()
                    
                    # Simplify the response
                    simplified_certs = []
                    for cert in certs:
                        simplified_certs.append({
                            "id": cert.get("id"),
                            "nice_name": cert.get("nice_name"),
                            "domain_names": cert.get("domain_names", []),
                            "expires_on": cert.get("expires_on"),
                            "provider": cert.get("provider"),
                            "is_deleted": cert.get("is_deleted", False)
                        })
                    
                    return {
                        "success": True,
                        "action": "certificates",
                        "certificate_count": len(simplified_certs),
                        "certificates": simplified_certs
                    }
                
                elif action == "redirections":
                    response = await client.get(
                        f"{self.base_url}/api/nginx/redirection-hosts",
                        headers=headers
                    )
                    response.raise_for_status()
                    redirects = response.json()
                    
                    # Simplify the response
                    simplified_redirects = []
                    for redirect in redirects:
                        simplified_redirects.append({
                            "id": redirect.get("id"),
                            "domain_names": redirect.get("domain_names", []),
                            "forward_domain_name": redirect.get("forward_domain_name"),
                            "forward_http_code": redirect.get("forward_http_code"),
                            "preserve_path": redirect.get("preserve_path", False),
                            "enabled": redirect.get("enabled", True)
                        })
                    
                    return {
                        "success": True,
                        "action": "redirections",
                        "redirection_count": len(simplified_redirects),
                        "redirections": simplified_redirects
                    }
                
                elif action == "status":
                    # Get all information for a status overview
                    hosts_response = await client.get(
                        f"{self.base_url}/api/nginx/proxy-hosts",
                        headers=headers
                    )
                    hosts_response.raise_for_status()
                    hosts = hosts_response.json()
                    
                    certs_response = await client.get(
                        f"{self.base_url}/api/nginx/certificates",
                        headers=headers
                    )
                    certs_response.raise_for_status()
                    certs = certs_response.json()
                    
                    redirects_response = await client.get(
                        f"{self.base_url}/api/nginx/redirection-hosts",
                        headers=headers
                    )
                    redirects_response.raise_for_status()
                    redirects = redirects_response.json()
                    
                    # Count enabled vs total
                    enabled_hosts = sum(1 for h in hosts if h.get("enabled", True))
                    ssl_enabled_hosts = sum(1 for h in hosts if h.get("certificate_id") is not None)
                    
                    return {
                        "success": True,
                        "action": "status",
                        "proxy_hosts": {
                            "total": len(hosts),
                            "enabled": enabled_hosts,
                            "with_ssl": ssl_enabled_hosts
                        },
                        "certificates": {
                            "total": len(certs),
                            "active": sum(1 for c in certs if not c.get("is_deleted", False))
                        },
                        "redirections": {
                            "total": len(redirects),
                            "enabled": sum(1 for r in redirects if r.get("enabled", True))
                        }
                    }
                
                else:
                    return {
                        "success": False,
                        "error": f"Invalid action: {action}"
                    }
                    
            except httpx.HTTPStatusError as e:
                self._token = None  # Clear token on auth errors
                return {
                    "success": False,
                    "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }
