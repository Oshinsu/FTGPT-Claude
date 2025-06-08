from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_mistralai import ChatMistralAI
from app.config import settings
from app.core.prompts import (
    PROFILE_ANALYSIS_PROMPT,
    CV_GENERATION_PROMPT,
    COVER_LETTER_PROMPT,
    TRAINING_ADVICE_PROMPT,
    ADMIN_HELP_PROMPT
)
from typing import Dict, Any


def get_llm():
    """Retourne le LLM configuré."""
    if settings.model_provider == "openai":
        return ChatOpenAI(
            model=settings.model_name,
            temperature=settings.model_temperature,
            api_key=settings.openai_api_key
        )
    elif settings.model_provider == "mistral":
        return ChatMistralAI(
            model=settings.model_name,
            temperature=settings.model_temperature,
            api_key=settings.mistral_api_key
        )
    else:
        raise ValueError(f"Provider non supporté : {settings.model_provider}")


# Chaîne pour l'analyse de profil
profile_analysis_chain = (
    PROFILE_ANALYSIS_PROMPT 
    | get_llm() 
    | StrOutputParser()
)

# Chaîne pour la génération de CV
cv_generation_chain = (
    CV_GENERATION_PROMPT
    | get_llm()
    | StrOutputParser()
)

# Chaîne pour les lettres de motivation
cover_letter_chain = (
    COVER_LETTER_PROMPT
    | get_llm()
    | StrOutputParser()
)

# Chaîne pour les conseils de formation
training_advice_chain = (
    TRAINING_ADVICE_PROMPT
    | get_llm()
    | StrOutputParser()
)

# Chaîne pour l'aide administrative
admin_help_chain = (
    ADMIN_HELP_PROMPT
    | get_llm()
    | StrOutputParser()
)


class SpecializedChains:
    """Gestionnaire des chaînes spécialisées."""
    
    @staticmethod
    async def analyze_profile(user_info: str, objectives: str) -> str:
        """Analyse un profil utilisateur."""
        return await profile_analysis_chain.ainvoke({
            "user_info": user_info,
            "objectives": objectives
        })
    
    @staticmethod
    async def generate_cv(
        profile: str, 
        target_job: str, 
        experiences: str, 
        skills: str
    ) -> str:
        """Génère un CV optimisé."""
        return await cv_generation_chain.ainvoke({
            "profile": profile,
            "target_job": target_job,
            "experiences": experiences,
            "skills": skills
        })
    
    @staticmethod
    async def generate_cover_letter(
        profile: str,
        company: str,
        job_offer: str,
        motivations: str
    ) -> str:
        """Génère une lettre de motivation."""
        return await cover_letter_chain.ainvoke({
            "profile": profile,
            "company": company,
            "job_offer": job_offer,
            "motivations": motivations
        })
    
    @staticmethod
    async def get_training_advice(
        current_skills: str,
        target_job: str,
        available_time: str,
        budget: str
    ) -> str:
        """Fournit des conseils de formation."""
        return await training_advice_chain.ainvoke({
            "current_skills": current_skills,
            "target_job": target_job,
            "available_time": available_time,
            "budget": budget
        })
    
    @staticmethod
    async def get_admin_help(
        question: str,
        user_situation: str,
        context: str = ""
    ) -> str:
        """Aide pour les démarches administratives."""
        return await admin_help_chain.ainvoke({
            "question": question,
            "user_situation": user_situation,
            "context": context
        })


# Instance singleton
specialized_chains = SpecializedChains()
