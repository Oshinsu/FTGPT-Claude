from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from langchain_core.pydantic_v1 import BaseModel, Field
from app.api.france_travail import france_travail_api
from app.api.models import SearchOfferRequest, ContractType, ExperienceLevel
from app.knowledge.vector_store import knowledge_base
from datetime import datetime
import json


class JobSearchInput(BaseModel):
    """Paramètres de recherche d'emploi."""
    keywords: Optional[str] = Field(None, description="Mots-clés de recherche")
    location: Optional[str] = Field(None, description="Ville ou code postal")
    distance: int = Field(10, description="Distance en km")
    contract_types: Optional[List[str]] = Field(None, description="Types de contrat")
    experience_level: Optional[str] = Field(None, description="Niveau d'expérience")
    page: int = Field(0, description="Page de résultats")


@tool("search_job_offers", args_schema=JobSearchInput, return_direct=False)
async def search_job_offers(
    keywords: Optional[str] = None,
    location: Optional[str] = None,
    distance: int = 10,
    contract_types: Optional[List[str]] = None,
    experience_level: Optional[str] = None,
    page: int = 0
) -> str:
    """
    Recherche des offres d'emploi sur France Travail.
    
    Args:
        keywords: Mots-clés pour la recherche
        location: Ville ou code postal
        distance: Rayon de recherche en km
        contract_types: Types de contrat (CDI, CDD, etc.)
        experience_level: Niveau d'expérience requis
        page: Page de résultats
    
    Returns:
        Les offres d'emploi trouvées
    """
    try:
        # Convertir les types de contrat
        contract_enum = None
        if contract_types:
            contract_enum = [ContractType(ct) for ct in contract_types if ct in ContractType.__members__]
        
        # Convertir le niveau d'expérience
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
        
        # Formater les résultats
        results = {
            "total": response.total_results,
            "page": page,
            "offers": []
        }
        
        for offer in response.offers[:5]:  # Limiter à 5 offres pour la lisibilité
            results["offers"].append({
                "id": offer.id,
                "title": offer.title,
                "company": offer.company_name,
                "location": offer.location,
                "contract": offer.contract_type,
                "salary": offer.salary_description,
                "experience": offer.experience_required,
                "created": offer.date_creation.strftime("%d/%m/%Y"),
                "url": str(offer.url)
            })
        
        return json.dumps(results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"Erreur lors de la recherche : {str(e)}"


class KnowledgeSearchInput(BaseModel):
    """Paramètres de recherche dans la base de connaissances."""
    query: str = Field(..., description="Question ou recherche")
    category: Optional[str] = Field(None, description="Catégorie (formation, aide, droit, etc.)")


@tool("search_knowledge", args_schema=KnowledgeSearchInput, return_direct=False)
def search_knowledge(query: str, category: Optional[str] = None) -> str:
    """
    Recherche dans la base de connaissances France Travail.
    
    Args:
        query: Question ou recherche
        category: Catégorie spécifique
    
    Returns:
        Informations pertinentes
    """
    try:
        results = knowledge_base.search(query, category=category, k=3)
        
        if not results:
            return "Aucune information trouvée dans la base de connaissances."
        
        formatted_results = []
        for doc in results:
            formatted_results.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Base de connaissances"),
                "category": doc.metadata.get("category", "Général")
            })
        
        return json.dumps(formatted_results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"Erreur lors de la recherche : {str(e)}"


class DocumentGenerationInput(BaseModel):
    """Paramètres pour la génération de documents."""
    doc_type: str = Field(..., description="Type de document (cv, lettre_motivation)")
    data: Dict[str, Any] = Field(..., description="Données pour la génération")


@tool("generate_document", args_schema=DocumentGenerationInput, return_direct=False)
def generate_document(doc_type: str, data: Dict[str, Any]) -> str:
    """
    Génère un document (CV ou lettre de motivation).
    
    Args:
        doc_type: Type de document à générer
        data: Données nécessaires à la génération
    
    Returns:
        Document généré ou lien vers le document
    """
    try:
        from app.utils.document_generator import DocumentGenerator
        
        generator = DocumentGenerator()
        
        if doc_type == "cv":
            document = generator.generate_cv(data)
        elif doc_type == "lettre_motivation":
            document = generator.generate_cover_letter(data)
        else:
            return f"Type de document non supporté : {doc_type}"
        
        # Sauvegarder et retourner le chemin
        file_path = generator.save_document(document, doc_type)
        
        return f"Document généré avec succès : {file_path}"
        
    except Exception as e:
        return f"Erreur lors de la génération : {str(e)}"


class AdminInfoInput(BaseModel):
    """Paramètres pour les informations administratives."""
    topic: str = Field(..., description="Sujet administratif")
    user_situation: Optional[str] = Field(None, description="Situation de l'utilisateur")


@tool("get_admin_info", args_schema=AdminInfoInput, return_direct=False)
def get_admin_info(topic: str, user_situation: Optional[str] = None) -> str:
    """
    Fournit des informations administratives détaillées.
    
    Args:
        topic: Sujet administratif (inscription, actualisation, allocations, etc.)
        user_situation: Situation spécifique de l'utilisateur
    
    Returns:
        Informations administratives pertinentes
    """
    # Base de données simplifiée des procédures
    admin_db = {
        "inscription": {
            "title": "Inscription à France Travail",
            "steps": [
                "1. Créer son espace personnel sur francetravail.fr",
                "2. Remplir le formulaire d'inscription en ligne",
                "3. Préparer les documents : pièce d'identité, CV, RIB",
                "4. Valider l'inscription et prendre RDV avec un conseiller",
                "5. Se présenter au RDV avec tous les documents"
            ],
            "documents": ["Pièce d'identité", "Justificatif de domicile", "CV", "RIB", "Carte vitale"],
            "delai": "RDV sous 5 jours ouvrés"
        },
        "actualisation": {
            "title": "Actualisation mensuelle",
            "steps": [
                "1. Se connecter à son espace personnel",
                "2. Cliquer sur 'M'actualiser'",
                "3. Déclarer sa situation du mois",
                "4. Indiquer les heures travaillées si activité",
                "5. Valider avant le 15 du mois"
            ],
            "period": "Entre le 28 et le 15 du mois suivant",
            "important": "L'actualisation conditionne le paiement des allocations"
        },
        "allocations": {
            "title": "Allocations chômage (ARE)",
            "conditions": [
                "Avoir travaillé au moins 6 mois sur les 24 derniers mois",
                "Être inscrit comme demandeur d'emploi",
                "Rechercher activement un emploi",
                "Être physiquement apte au travail",
                "Ne pas avoir atteint l'âge de la retraite"
            ],
            "calcul": "57% à 75% du salaire journalier de référence",
            "duree": "Variable selon l'âge et la durée de cotisation"
        }
    }
    
    info = admin_db.get(topic.lower(), {})
    
    if not info:
        return f"Pas d'information disponible sur : {topic}. Sujets disponibles : inscription, actualisation, allocations"
    
    result = {
        "topic": info.get("title", topic),
        "details": info,
        "user_situation": user_situation or "Situation générale"
    }
    
    return json.dumps(result, ensure_ascii=False, indent=2)


# Liste des outils disponibles
FRANCE_TRAVAIL_TOOLS = [
    search_job_offers,
    search_knowledge,
    generate_document,
    get_admin_info
]
