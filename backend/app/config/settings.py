"""
JARVIS v3 Configuration
Pydantic Settings for type-safe configuration management
"""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    app_name: str = "JARVIS"
    version: str = "3.0.0"
    debug: bool = False
    
    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000", "http://192.168.10.100:3939"]
    
    # AI - Claude
    anthropic_api_key: str
    default_model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/jarvis.db"
    
    # Homelab Services
    prometheus_url: str = "http://192.168.10.104:9090"
    starlink_host: str = "192.168.100.1"
    grafana_url: str = "http://192.168.10.104:3000"
    grafana_api_key: Optional[str] = None
    uptime_kuma_url: str = "http://192.168.10.104:3001"
    
    # Proxmox (token auth)
    proxmox_pve1_host: str = "192.168.10.50"
    proxmox_pve2_host: str = "192.168.10.51"
    proxmox_user: str = "root@pam"
    proxmox_password: Optional[str] = None
    proxmox_token_name: Optional[str] = None
    proxmox_token_value: Optional[str] = None
    
    # UniFi
    unifi_host: str = "192.168.10.1"
    unifi_username: str = "jarvis"
    unifi_password: Optional[str] = None
    unifi_site: str = "default"
    
    # UniFi Protect
    protect_host: str = "192.168.20.250"
    protect_username: str = "jarvis"
    protect_password: Optional[str] = None
    
    # Home Assistant
    home_assistant_url: str = "http://192.168.10.227:8123"
    home_assistant_token: Optional[str] = None
    
    # Synology NAS
    synology_host: str = "192.168.10.104"
    synology_user: str = "admin"
    synology_password: Optional[str] = None

    # Portainer
    portainer_url: str = "https://192.168.10.104:9443"
    portainer_api_key: Optional[str] = None
    
    # 3D Printers
    bambu_host: Optional[str] = None
    bambu_access_code: Optional[str] = None
    prusa_host: Optional[str] = None
    prusa_api_key: Optional[str] = None
    
    # Nginx Proxy Manager
    npm_url: str = "http://192.168.10.104:81"
    npm_user: Optional[str] = None
    npm_password: Optional[str] = None
    
    # AdGuard Home
    adguard_url: str = "http://192.168.10.104:3000"
    adguard_user: Optional[str] = None
    adguard_password: Optional[str] = None
    
    # TTS - ElevenLabs
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: str = "onwK4e9ZLuTAKqWW03F9"  # Daniel
    
    # Research - Tavily
    tavily_api_key: Optional[str] = None
    
    # Location (for weather)
    location_lat: float = 50.921367
    location_lon: float = -1.579752
    location_timezone: str = "Europe/London"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance"""
    return Settings()
