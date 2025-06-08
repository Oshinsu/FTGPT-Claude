import httpx
from typing import Optional
from datetime import datetime, timedelta
from app.config import settings
from app.api.models import AccessToken
import asyncio


class FranceTravailAuth:
    """Gestionnaire d'authentification OAuth2 pour l'API France Travail."""
    
    def __init__(self):
        self.client_id = settings.france_travail_client_id
        self.client_secret = settings.france_travail_client_secret
        self.base_url = settings.france_travail_api_base_url
        self._token_cache: Optional[AccessToken] = None
        self._lock = asyncio.Lock()
    
    async def get_access_token(self) -> str:
        """
        Obtient un token d'accès valide, utilise le cache si possible.
        """
        async with self._lock:
            if self._token_cache and not self._token_cache.is_expired():
                return self._token_cache.access_token
            
            # Générer un nouveau token
            self._token_cache = await self._request_new_token()
            return self._token_cache.access_token
    
    async def _request_new_token(self) -> AccessToken:
        """Demande un nouveau token à l'API."""
        url = "https://francetravail.io/connexion/oauth2/access_token"
        
        params = {
            "realm": "/partenaire"
        }
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "api_offresdemploiv2 o2dsoffre"
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params=params,
                data=data,
                headers=headers
            )
            response.raise_for_status()
            
            token_data = response.json()
            
            # Calculer l'expiration
            expires_at = datetime.now() + timedelta(
                seconds=token_data["expires_in"] - 60  # 1 minute de marge
            )
            
            return AccessToken(
                access_token=token_data["access_token"],
                token_type=token_data["token_type"],
                expires_in=token_data["expires_in"],
                scope=token_data["scope"],
                expires_at=expires_at
            )
