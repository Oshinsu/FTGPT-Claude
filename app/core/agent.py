from typing import List, Optional, Dict, Any
from datetime import datetime
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.memory import ConversationSummaryBufferMemory
from langchain_openai import ChatOpenAI
from langchain_mistralai import ChatMistralAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from app.config import settings
from app.core.prompts import MAIN_AGENT_PROMPT
from app.core.tools import FRANCE_TRAVAIL_TOOLS
from app.core.chains import specialized_chains, get_llm
import asyncio


class FranceTravailAgent:
    """Agent principal pour l'assistant France Travail."""
    
    def __init__(self):
        self.llm = get_llm()
        self.tools = FRANCE_TRAVAIL_TOOLS
        self.memory = MemorySaver()
        self.specialized_chains = specialized_chains
        
        # Créer l'agent avec LangGraph pour une meilleure gestion d'état
        self.agent = self._create_agent()
        
    def _create_agent(self):
        """Crée l'agent ReAct avec LangGraph."""
        return create_react_agent(
            self.llm,
            tools=self.tools,
            checkpointer=self.memory,
            state_modifier=self._modify_state
        )
    
    def _modify_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Modifie l'état avant l'exécution."""
        # Ajouter le contexte système
        state["user_context"] = self._get_user_context(state.get("thread_id"))
        state["current_date"] = datetime.now().strftime("%d/%m/%Y")
        
        # Formater les messages avec le prompt système
        if "messages" in state:
            system_message = MAIN_AGENT_PROMPT.format_messages(
                user_context=state["user_context"],
                current_date=state["current_date"],
                chat_history=[],
                input="",
                agent_scratchpad=[]
            )[0]
            
            # Insérer le message système au début si pas déjà présent
            if not state["messages"] or state["messages"][0].type != "system":
                state["messages"].insert(0, system_message)
        
        return state
    
    def _get_user_context(self, thread_id: Optional[str]) -> str:
        """Récupère le contexte utilisateur depuis la session."""
        # Ici on pourrait récupérer le profil utilisateur depuis une DB
        # Pour l'instant on retourne un contexte par défaut
        return "Utilisateur non identifié - Première interaction"
    
    async def process_message(
        self,
        message: str,
        thread_id: str,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Traite un message utilisateur.
        
        Args:
            message: Message de l'utilisateur
            thread_id: ID de la conversation
            user_profile: Profil utilisateur optionnel
            
        Returns:
            Réponse structurée avec le message et les métadonnées
        """
        try:
            # Détecter l'intention pour routing vers chaînes spécialisées
            intent = await self._detect_intent(message)
            
            # Router vers une chaîne spécialisée si nécessaire
            if intent["specialized"]:
                response = await self._handle_specialized_request(
                    intent, 
                    message, 
                    user_profile
                )
                return {
                    "response": response,
                    "intent": intent["type"],
                    "specialized": True,
                    "thread_id": thread_id
                }
            
            # Sinon utiliser l'agent principal
            config = {"configurable": {"thread_id": thread_id}}
            
            # Préparer le message
            input_message = HumanMessage(content=message)
            
            # Invoquer l'agent
            result = await self.agent.ainvoke(
                {"messages": [input_message]},
                config=config
            )
            
            # Extraire la réponse
            response = result["messages"][-1].content
            
            return {
                "response": response,
                "intent": intent["type"],
                "specialized": False,
                "thread_id": thread_id,
                "tools_used": self._extract_tools_used(result)
            }
            
        except Exception as e:
            return {
                "response": f"Désolé, une erreur s'est produite. Pouvez-vous reformuler votre question ?",
                "error": str(e),
                "thread_id": thread_id
            }
    
    async def _detect_intent(self, message: str) -> Dict[str, Any]:
        """Détecte l'intention du message."""
        message_lower = message.lower()
        
        # Détection simple basée sur des mots-clés
        intents = {
            "job_search": ["emploi", "offre", "travail", "poste", "recrutement"],
            "cv_help": ["cv", "curriculum", "resume"],
            "cover_letter": ["lettre", "motivation", "candidature"],
            "training": ["formation", "apprendre", "cours", "certification"],
            "admin": ["inscription", "actualisation", "allocation", "droit", "aide"],
            "profile": ["profil", "bilan", "compétence", "orientation"]
        }
        
        for intent_type, keywords in intents.items():
            if any(keyword in message_lower for keyword in keywords):
                # Vérifier si c'est une demande spécialisée
                specialized_triggers = {
                    "cv_help": ["génère", "crée", "rédige"],
                    "cover_letter": ["écris", "rédige", "génère"],
                    "profile": ["analyse", "évalue", "bilan"]
                }
                
                specialized = False
                if intent_type in specialized_triggers:
                    specialized = any(
                        trigger in message_lower 
                        for trigger in specialized_triggers[intent_type]
                    )
                
                return {
                    "type": intent_type,
                    "specialized": specialized,
                    "confidence": 0.8
                }
        
        return {
            "type": "general",
            "specialized": False,
            "confidence": 0.5
        }
    
    async def _handle_specialized_request(
        self,
        intent: Dict[str, Any],
        message: str,
        user_profile: Optional[Dict[str, Any]]
    ) -> str:
        """Gère les requêtes spécialisées."""
        intent_type = intent["type"]
        
        if intent_type == "profile":
            return await self.specialized_chains.analyze_profile(
                user_info=str(user_profile or {}),
                objectives=message
            )
        
        elif intent_type == "cv_help":
            # Extraire les informations du message ou du profil
            return await self.specialized_chains.generate_cv(
                profile=str(user_profile or {}),
                target_job="À définir",
                experiences="À compléter",
                skills="À compléter"
            )
        
        elif intent_type == "cover_letter":
            return await self.specialized_chains.generate_cover_letter(
                profile=str(user_profile or {}),
                company="À préciser",
                job_offer=message,
                motivations="À développer"
            )
        
        elif intent_type == "training":
            return await self.specialized_chains.get_training_advice(
                current_skills="À définir",
                target_job="À préciser",
                available_time="À déterminer",
                budget="À préciser"
            )
        
        elif intent_type == "admin":
            return await self.specialized_chains.get_admin_help(
                question=message,
                user_situation=str(user_profile or {}),
                context=""
            )
        
        return "Je ne peux pas traiter cette demande spécialisée pour le moment."
    
    def _extract_tools_used(self, result: Dict[str, Any]) -> List[str]:
        """Extrait la liste des outils utilisés."""
        tools_used = []
        
        for message in result.get("messages", []):
            if hasattr(message, "tool_calls"):
                for tool_call in message.tool_calls:
                    tools_used.append(tool_call["name"])
        
        return tools_used
    
    async def get_conversation_summary(self, thread_id: str) -> str:
        """Récupère un résumé de la conversation."""
        # Récupérer l'historique depuis la mémoire
        state = await self.memory.aget(thread_id)
        
        if not state or "messages" not in state:
            return "Aucune conversation trouvée."
        
        # Créer un résumé avec le LLM
        summary_prompt = """Résume cette conversation en mettant en avant :
        - Les besoins exprimés
        - Les actions réalisées
        - Les prochaines étapes suggérées
        
        Conversation : {conversation}
        """
        
        messages_text = "\n".join([
            f"{msg.type}: {msg.content}" 
            for msg in state["messages"]
        ])
        
        summary = await self.llm.ainvoke(
            summary_prompt.format(conversation=messages_text)
        )
        
        return summary.content


# Instance singleton
agent = FranceTravailAgent()
