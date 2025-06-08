import httpx
from typing import List, Optional, Dict, Any
from app.api.auth import FranceTravailAuth
from app.api.models import SearchOfferRequest, SearchOfferResponse, JobOffer
from app.config import settings
from tenacity import retry, stop_after_attempt, wait_exponential


class FranceTravailAPI:
    """Client pour l'API France Travail."""
    
    def __init__(self):
        self.auth = FranceTravailAuth()
        self.base_url = f"{settings.france_travail_api_base_url}/offresdemploi/v2"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def search_offers(
        self, 
        request: SearchOfferRequest
    ) -> SearchOfferResponse:
        """
        Recherche des offres d'emploi.
        """
        token = await self.auth.get_access_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        # Construire les paramètres de requête
        params = self._build_search_params(request)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/offres/search",
                headers=headers,
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            
            data = response.json()
            return SearchOfferResponse(**data)
    
    async def get_offer_details(self, offer_id: str) -> JobOffer:
        """
        Récupère les détails d'une offre spécifique.
        """
        token = await self.auth.get_access_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/offres/{offer_id}",
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            
            return JobOffer(**response.json())
    
    def _build_search_params(self, request: SearchOfferRequest) -> Dict[str, Any]:
        """Construit les paramètres de recherche pour l'API."""
        params = {
            "range": f"{request.page * request.per_page}-{(request.page + 1) * request.per_page - 1}"
        }
        
        if request.keywords:
            params["motsCles"] = request.keywords
        
        if request.location:
            params["commune"] = request.location
            params["distance"] = request.distance
        
        if request.contract_types:
            params["typeContrat"] = ",".join(request.contract_types)
        
        if request.experience_levels:
            params["experience"] = ",".join(request.experience_levels)
        
        if request.min_salary:
            params["salaireMin"] = request.min_salary
        
        return params


# Instance singleton
france_travail_api = FranceTravailAPI()
