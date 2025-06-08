from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ContractType(str, Enum):
    """Types de contrats."""
    CDI = "CDI"
    CDD = "CDD"
    INTERIM = "MIS"
    ALTERNANCE = "SAI"
    STAGE = "STG"


class ExperienceLevel(str, Enum):
    """Niveaux d'expérience."""
    DEBUTANT = "D"
    EXPERIMENTE = "E"
    SENIOR = "S"


class JobOffer(BaseModel):
    """Modèle d'offre d'emploi France Travail."""
    id: str
    title: str = Field(..., alias="intitule")
    description: str
    company_name: str = Field(..., alias="entreprise.nom")
    location: str = Field(..., alias="lieuTravail.libelle")
    contract_type: ContractType = Field(..., alias="typeContrat")
    salary_description: Optional[str] = Field(None, alias="salaire.libelle")
    experience_required: ExperienceLevel = Field(..., alias="experienceExige")
    skills: List[str] = Field(default_factory=list, alias="competences")
    date_creation: datetime = Field(..., alias="dateCreation")
    date_update: datetime = Field(..., alias="dateActualisation")
    url: HttpUrl = Field(..., alias="origineOffre.urlOrigine")
    
    class Config:
        populate_by_name = True


class SearchOfferRequest(BaseModel):
    """Requête de recherche d'offres."""
    keywords: Optional[str] = Field(None, alias="motsCles")
    location: Optional[str] = Field(None, alias="commune")
    distance: Optional[int] = Field(10, ge=0, le=100)
    contract_types: Optional[List[ContractType]] = None
    experience_levels: Optional[List[ExperienceLevel]] = None
    min_salary: Optional[int] = None
    page: int = Field(0, ge=0)
    per_page: int = Field(20, ge=1, le=150)


class SearchOfferResponse(BaseModel):
    """Réponse de recherche d'offres."""
    total_results: int = Field(..., alias="totalResultats")
    offers: List[JobOffer] = Field(..., alias="resultats")
    
    class Config:
        populate_by_name = True


class AccessToken(BaseModel):
    """Token d'accès OAuth2."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str
    expires_at: datetime = Field(default_factory=datetime.now)
    
    def is_expired(self) -> bool:
        """Vérifie si le token est expiré."""
        return datetime.now() >= self.expires_at
