from typing import List, Dict, Any, Optional, Type
from langchain_core.tools import BaseTool, ToolException
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from pydantic import BaseModel, Field, field_validator
from app.api.france_travail import france_travail_api
from app.api.models import SearchOfferRequest, ContractType, ExperienceLevel
from app.knowledge.vector_store import knowledge_base
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class JobSearchInput(BaseModel):
    """Input schema for job search tool."""
    keywords: Optional[str] = Field(None, description="Mots-clés de recherche (ex: développeur, commercial)")
    location: Optional[str] = Field(None, description="Ville ou code postal")
    distance: int = Field(default=30, ge=0, le=100, description="Rayon de recherche en km")
    contract_types: Optional[List[str]] = Field(None, description="Types de contrat (CDI, CDD, etc.)")
    experience_level: Optional[str] = Field(None, description="Niveau d'expérience (D=Débutant, E=Expérimenté, S=Senior)")
    page: int = Field(default=0, ge=0, description="Page de résultats")
    
    @field_validator('contract_types')
    @classmethod
    def validate_contract_types(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        valid_types = ["CDI", "CDD", "MIS", "SAI", "STG"]
        return [ct for ct in v if ct in valid_types]


class SearchJobOffersTool(BaseTool):
    """Tool for searching job offers on France Travail."""
    
    name: str = "search_job_offers"
    description: str = """Recherche des offres d'emploi sur France Travail.
    Utilise cet outil quand l'utilisateur cherche un emploi, demande des offres, ou veut voir les opportunités disponibles.
    Tu peux spécifier des mots-clés, une localisation, un type de contrat, etc."""
    args_schema: Type[BaseModel] = JobSearchInput
    return_direct: bool = False
    
    async def _arun(
        self,
        keywords: Optional[str] = None,
        location: Optional[str] = None,
        distance: int = 30,
        contract_types: Optional[List[str]] = None,
        experience_level: Optional[str] = None,
        page: int = 0,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """Execute the job search asynchronously."""
        try:
            # Convertir les types
            contract_enum = None
            if contract_types:
                contract_enum = [ContractType(ct) for ct in contract_types if ct in ContractType.__members__]
            
            exp_enum = None
            if experience_level and experience_level in ExperienceLevel.__members__:
                exp_enum = [ExperienceLevel(experience_level)]
            
            request = SearchOfferRequest(
                keywords=keywords,
                location=location,
                distance=distance,
                contract_types=contract_enum,
                experience_levels=exp_enum,
                page=page,
                per_page=10
            )
            
            response = await france_travail_api.search_offers(request)
            
            # Formater pour l'affichage
            if response.total_results == 0:
                return "Aucune offre trouvée avec ces critères. Essayez d'élargir votre recherche."
            
            result = f"🔍 **{response.total_results} offres trouvées**\n\n"
            
            for i, offer in enumerate(response.offers[:5], 1):
                result += f"**{i}. {offer.title}**\n"
                result += f"   📍 {offer.company_name} - {offer.location}\n"
                result += f"   📄 Contrat : {offer.contract_type}\n"
                if offer.salary_description:
                    result += f"   💰 Salaire : {offer.salary_description}\n"
                result += f"   🎯 Expérience : {offer.experience_required}\n"
                result += f"   📅 Publié le : {offer.date_creation.strftime('%d/%m/%Y')}\n"
                result += f"   🔗 [Voir l'offre]({offer.url})\n\n"
            
            if response.total_results > 5:
                result += f"_... et {response.total_results - 5} autres offres disponibles_"
            
            return result
            
        except Exception as e:
            raise ToolException(f"Erreur lors de la recherche d'offres : {str(e)}")
    
    def _run(self, *args, **kwargs):
        """Synchronous version not implemented."""
        raise NotImplementedError("Utilisez la version asynchrone de cet outil")


class KnowledgeSearchInput(BaseModel):
    """Input schema for knowledge base search."""
    query: str = Field(..., description="Question ou recherche dans la base de connaissances")
    category: Optional[str] = Field(None, description="Catégorie spécifique (formation, aide, droit, etc.)")
    limit: int = Field(default=3, ge=1, le=10, description="Nombre de résultats")


class SearchKnowledgeTool(BaseTool):
    """Tool for searching the France Travail knowledge base."""
    
    name: str = "search_knowledge"
    description: str = """Recherche dans la base de connaissances France Travail.
    Utilise cet outil pour trouver des informations sur :
    - Les démarches administratives (inscription, actualisation)
    - Les droits et allocations (ARE, aides)
    - Les formations disponibles
    - Les conseils emploi
    Ne PAS utiliser pour rechercher des offres d'emploi."""
    args_schema: Type[BaseModel] = KnowledgeSearchInput
    return_direct: bool = False
    
    def _run(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 3,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Execute the knowledge search."""
        try:
            results = knowledge_base.search(query, category=category, k=limit)
            
            if not results:
                return "Aucune information trouvée dans la base de connaissances sur ce sujet."
            
            formatted = "📚 **Informations trouvées :**\n\n"
            
            for i, doc in enumerate(results, 1):
                source = doc.metadata.get("source", "Base de connaissances")
                category = doc.metadata.get("category", "Général")
                
                formatted += f"**{i}. {source}** ({category})\n"
                formatted += f"{doc.page_content[:300]}...\n\n"
            
            return formatted
            
        except Exception as e:
            raise ToolException(f"Erreur lors de la recherche : {str(e)}")
    
    async def _arun(self, *args, **kwargs):
        """Async version calls sync version."""
        return self._run(*args, **kwargs)


class AdminInfoInput(BaseModel):
    """Input schema for administrative information."""
    topic: str = Field(..., description="Sujet administratif (inscription, actualisation, allocations)")
    user_situation: Optional[str] = Field(None, description="Situation spécifique de l'utilisateur")


class GetAdminInfoTool(BaseTool):
    """Tool for getting administrative information."""
    
    name: str = "get_admin_info"
    description: str = """Fournit des informations administratives détaillées France Travail.
    Utilise cet outil pour expliquer :
    - Les procédures d'inscription
    - L'actualisation mensuelle
    - Les allocations et leurs calculs
    - Les documents nécessaires
    - Les délais et dates importantes"""
    args_schema: Type[BaseModel] = AdminInfoInput
    return_direct: bool = False
    
    def _run(
        self,
        topic: str,
        user_situation: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Execute the admin info retrieval."""
        # Base de données administrative enrichie
        admin_info = {
            "inscription": {
                "title": "📝 Inscription à France Travail",
                "steps": [
                    "**Étape 1** : Préinscription en ligne sur francetravail.fr",
                    "**Étape 2** : Création de votre espace personnel",
                    "**Étape 3** : Remplissage du formulaire détaillé",
                    "**Étape 4** : Prise de RDV avec un conseiller (sous 5 jours)",
                    "**Étape 5** : Entretien d'inscription et validation"
                ],
                "documents": [
                    "✓ Pièce d'identité valide",
                    "✓ Justificatif de domicile < 3 mois",
                    "✓ RIB",
                    "✓ Carte vitale",
                    "✓ CV actualisé",
                    "✓ Certificats de travail"
                ],
                "important": "⚠️ L'inscription doit être faite dans les 12 mois suivant la fin du contrat"
            },
            "actualisation": {
                "title": "🔄 Actualisation mensuelle",
                "period": "**Quand** : Entre le 28 et le 15 du mois suivant",
                "steps": [
                    "1️⃣ Connectez-vous à votre espace personnel",
                    "2️⃣ Cliquez sur 'M'actualiser'",
                    "3️⃣ Déclarez votre situation du mois écoulé",
                    "4️⃣ Indiquez les heures travaillées et revenus",
                    "5️⃣ Validez avant le 15 (minuit)"
                ],
                "important": "⚠️ Sans actualisation = radiation + suspension des allocations"
            },
            "allocations": {
                "title": "💰 Allocations chômage (ARE)",
                "conditions": [
                    "✓ 6 mois travaillés (130j ou 910h) sur 24 mois",
                    "✓ Privation involontaire d'emploi",
                    "✓ Inscription et recherche active",
                    "✓ Aptitude physique au travail"
                ],
                "calcul": {
                    "formule": "ARE journalière = MAX(57% du SJR ; 40.4% du SJR + 12,47€)",
                    "minimum": "30,42€/jour",
                    "maximum": "75% du SJR"
                },
                "duree": "Jours travaillés × 1,4 (min 182j, max selon âge)"
            }
        }
        
        info = admin_info.get(topic.lower())
        
        if not info:
            topics_list = ", ".join(admin_info.keys())
            return f"Sujet non trouvé. Sujets disponibles : {topics_list}"
        
        # Formater la réponse
        response = f"## {info['title']}\n\n"
        
        if "steps" in info:
            response += "### 📋 Étapes :\n"
            for step in info["steps"]:
                response += f"{step}\n"
            response += "\n"
        
        if "documents" in info:
            response += "### 📄 Documents nécessaires :\n"
            for doc in info["documents"]:
                response += f"{doc}\n"
            response += "\n"
        
        if "conditions" in info:
            response += "### ✅ Conditions :\n"
            for cond in info["conditions"]:
                response += f"{cond}\n"
            response += "\n"
        
        if "calcul" in info:
            response += "### 🧮 Calcul :\n"
            for k, v in info["calcul"].items():
                response += f"**{k.capitalize()}** : {v}\n"
            response += "\n"
        
        if "important" in info:
            response += f"\n{info['important']}\n"
        
        if user_situation:
            response += f"\n📌 **Votre situation** : {user_situation}\n"
            response += "→ N'hésitez pas à préciser votre cas pour des conseils personnalisés."
        
        return response
    
    async def _arun(self, *args, **kwargs):
        """Async version calls sync version."""
        return self._run(*args, **kwargs)


class DocumentGenerationInput(BaseModel):
    """Input schema for document generation."""
    doc_type: str = Field(..., description="Type de document (cv, lettre_motivation)")
    data: Dict[str, Any] = Field(..., description="Données pour la génération")


class GenerateDocumentTool(BaseTool):
    """Tool for generating documents."""
    
    name: str = "generate_document"
    description: str = """Génère des documents professionnels (CV, lettres de motivation).
    Utilise cet outil UNIQUEMENT quand l'utilisateur demande explicitement de créer/générer un document.
    Ne PAS utiliser pour des conseils généraux sur les CV/lettres."""
    args_schema: Type[BaseModel] = DocumentGenerationInput
    return_direct: bool = False
    
    def _run(
        self,
        doc_type: str,
        data: Dict[str, Any],
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Execute document generation."""
        try:
            from app.utils.document_generator import DocumentGenerator
            
            generator = DocumentGenerator()
            
            if doc_type == "cv":
                file_path = generator.generate_cv(data)
                return f"✅ CV généré avec succès !\n📄 Fichier : {file_path.name}\n\nVous pouvez le télécharger depuis l'onglet 'Mes documents'."
            
            elif doc_type == "lettre_motivation":
                file_path = generator.generate_cover_letter(data)
                return f"✅ Lettre de motivation générée !\n📄 Fichier : {file_path.name}\n\nVous pouvez la télécharger depuis l'onglet 'Mes documents'."
            
            else:
                raise ValueError(f"Type de document non supporté : {doc_type}")
                
        except Exception as e:
            raise ToolException(f"Erreur lors de la génération : {str(e)}")
    
    async def _arun(self, *args, **kwargs):
        """Async version calls sync version."""
        return self._run(*args, **kwargs)


# Créer les instances des outils
FRANCE_TRAVAIL_TOOLS = [
    SearchJobOffersTool(),
    SearchKnowledgeTool(),
    GetAdminInfoTool(),
    GenerateDocumentTool()
]
