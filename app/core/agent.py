from typing import List, Optional, Dict, Any, Annotated, TypedDict
from datetime import datetime
import uuid
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_mistralai import ChatMistralAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from app.config import settings
from app.core.prompts import MAIN_AGENT_PROMPT
from app.core.tools import FRANCE_TRAVAIL_TOOLS
from app.core.chains import specialized_chains
import asyncio
import logging

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """État de l'agent pour LangGraph."""
    messages: Annotated[List[BaseMessage], add_messages]
    user_profile: Optional[Dict[str, Any]]
    current_intent: Optional[str]
    specialized_response: Optional[str]
    thread_id: str


class FranceTravailAgent:
    """Agent principal pour l'assistant France Travail - Version 2025."""
    
    def __init__(self):
        self.llm = self._get_llm()
        self.tools = FRANCE_TRAVAIL_TOOLS
        self.memory = MemorySaver()
        self.specialized_chains = specialized_chains
        
        # Créer le graphe LangGraph
        self.graph = self._create_graph()
        self.app = self.graph.compile(
            checkpointer=self.memory,
            interrupt_before=[],  # Pas d'interruption
            debug=settings.app_debug
        )
        
    def _get_llm(self):
        """Retourne le LLM configuré avec les tools."""
        if settings.model_provider == "openai":
            llm = ChatOpenAI(
                model=settings.model_name,
                temperature=settings.model_temperature,
                api_key=settings.openai_api_key,
                streaming=True
            )
        elif settings.model_provider == "mistral":
            llm = ChatMistralAI(
                model=settings.model_name,
                temperature=settings.model_temperature,
                api_key=settings.mistral_api_key,
                streaming=True
            )
        else:
            raise ValueError(f"Provider non supporté : {settings.model_provider}")
        
        # Bind tools to LLM
        return llm.bind_tools(self.tools)
    
    def _create_graph(self) -> StateGraph:
        """Crée le graphe LangGraph pour l'agent."""
        # Initialiser le graphe avec l'état
        workflow = StateGraph(AgentState)
        
        # Ajouter les nœuds
        workflow.add_node("detect_intent", self._detect_intent_node)
        workflow.add_node("route_request", self._route_request_node)
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.add_node("specialized", self._specialized_node)
        workflow.add_node("format_response", self._format_response_node)
        
        # Définir le flux
        workflow.add_edge(START, "detect_intent")
        workflow.add_edge("detect_intent", "route_request")
        
        # Routage conditionnel
        workflow.add_conditional_edges(
            "route_request",
            self._route_condition,
            {
                "agent": "agent",
                "specialized": "specialized"
            }
        )
        
        # Flux de l'agent
        workflow.add_conditional_edges(
            "agent",
            tools_condition,
            {
                "tools": "tools",
                "continue": "format_response"
            }
        )
        workflow.add_edge("tools", "agent")
        
        # Flux spécialisé
        workflow.add_edge("specialized", "format_response")
        
        # Fin
        workflow.add_edge("format_response", END)
        
        return workflow
    
    async def _detect_intent_node(self, state: AgentState) -> Dict[str, Any]:
        """Nœud pour détecter l'intention."""
        messages = state["messages"]
        if not messages:
            return {"current_intent": "general"}
        
        last_message = messages[-1].content if messages else ""
        
        # Prompt pour la détection d'intention
        intent_prompt = ChatPromptTemplate.from_messages([
            ("system", """Tu es un assistant qui détecte l'intention d'un message.
            
Catégories possibles :
- job_search : recherche d'emploi
- cv_help : aide pour CV (génération si demande explicite)
- cover_letter : lettre de motivation (génération si demande explicite)  
- training : formation et orientation
- admin : démarches administratives
- profile : analyse de profil (si demande d'analyse)
- general : autres questions

Réponds UNIQUEMENT avec la catégorie appropriée."""),
            ("human", "{message}")
        ])
        
        chain = intent_prompt | self.llm | StrOutputParser()
        intent = await chain.ainvoke({"message": last_message})
        
        return {"current_intent": intent.strip().lower()}
    
    def _route_condition(self, state: AgentState) -> str:
        """Condition de routage basée sur l'intention."""
        intent = state.get("current_intent", "general")
        last_message = state["messages"][-1].content.lower() if state["messages"] else ""
        
        # Mots-clés pour déclencher les chaînes spécialisées
        specialized_triggers = {
            "cv_help": ["génère", "crée", "rédige", "fais-moi"],
            "cover_letter": ["écris", "rédige", "génère", "prépare"],
            "profile": ["analyse", "évalue", "diagnostic", "bilan"]
        }
        
        if intent in specialized_triggers:
            if any(trigger in last_message for trigger in specialized_triggers[intent]):
                return "specialized"
        
        return "agent"
    
    async def _agent_node(self, state: AgentState) -> Dict[str, Any]:
        """Nœud principal de l'agent."""
        # Préparer le prompt système
        system_prompt = MAIN_AGENT_PROMPT.format(
            user_context=self._format_user_context(state["user_profile"]),
            current_date=datetime.now().strftime("%d/%m/%Y %H:%M"),
            chat_history=[],  # Géré par les messages
            input="",  # Pas utilisé ici
            agent_scratchpad=[]  # Géré par LangGraph
        )
        
        # Invoquer le LLM
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        response = await self.llm.ainvoke(messages)
        
        return {"messages": [response]}
    
    async def _specialized_node(self, state: AgentState) -> Dict[str, Any]:
        """Nœud pour les chaînes spécialisées."""
        intent = state.get("current_intent", "general")
        user_profile = state.get("user_profile", {})
        last_message = state["messages"][-1].content if state["messages"] else ""
        
        try:
            if intent == "profile":
                response = await self.specialized_chains.analyze_profile(
                    user_info=str(user_profile),
                    objectives=last_message
                )
            
            elif intent == "cv_help":
                response = await self.specialized_chains.generate_cv(
                    profile=str(user_profile),
                    target_job=user_profile.get("target_job", "À définir"),
                    experiences=user_profile.get("experiences", "À compléter"),
                    skills=user_profile.get("skills", "À compléter")
                )
            
            elif intent == "cover_letter":
                response = await self.specialized_chains.generate_cover_letter(
                    profile=str(user_profile),
                    company="À préciser dans votre message",
                    job_offer=last_message,
                    motivations="Basées sur votre profil"
                )
            
            else:
                response = "Je ne peux pas traiter cette demande spécialisée."
            
            return {"specialized_response": response}
            
        except Exception as e:
            logger.error(f"Erreur dans la chaîne spécialisée : {str(e)}")
            return {"specialized_response": f"Désolé, une erreur s'est produite : {str(e)}"}
    
    async def _route_request_node(self, state: AgentState) -> Dict[str, Any]:
        """Nœud de routage (ne modifie pas l'état)."""
        return {}
    
    async def _format_response_node(self, state: AgentState) -> Dict[str, Any]:
        """Nœud pour formater la réponse finale."""
        if state.get("specialized_response"):
            # Ajouter la réponse spécialisée comme message
            response_message = AIMessage(
                content=state["specialized_response"],
                metadata={"specialized": True, "intent": state.get("current_intent")}
            )
            return {"messages": [response_message]}
        
        # La réponse est déjà dans les messages
        return {}
    
    def _format_user_context(self, user_profile: Optional[Dict[str, Any]]) -> str:
        """Formate le contexte utilisateur."""
        if not user_profile:
            return "Utilisateur non identifié - Première interaction"
        
        context_parts = []
        if user_profile.get("name"):
            context_parts.append(f"Nom : {user_profile['name']}")
        if user_profile.get("situation"):
            context_parts.append(f"Situation : {user_profile['situation']}")
        if user_profile.get("experience"):
            context_parts.append(f"Expérience : {user_profile['experience']}")
        
        return " | ".join(context_parts) if context_parts else "Profil basique"
    
    async def process_message(
        self,
        message: str,
        thread_id: str,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Traite un message utilisateur avec le nouveau système LangGraph.
        """
        try:
            # Configuration pour LangGraph
            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": "main"
                }
            }
            
            # État initial
            initial_state = {
                "messages": [HumanMessage(content=message)],
                "user_profile": user_profile or {},
                "thread_id": thread_id
            }
            
            # Invoquer le graphe
            result = await self.app.ainvoke(initial_state, config)
            
            # Extraire la réponse
            final_message = result["messages"][-1]
            
            # Analyser les outils utilisés
            tools_used = []
            for msg in result["messages"]:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    tools_used.extend([tc["name"] for tc in msg.tool_calls])
            
            return {
                "response": final_message.content,
                "intent": result.get("current_intent", "general"),
                "specialized": bool(result.get("specialized_response")),
                "thread_id": thread_id,
                "tools_used": tools_used,
                "metadata": getattr(final_message, "metadata", {})
            }
            
        except Exception as e:
            logger.error(f"Erreur dans process_message : {str(e)}")
            return {
                "response": "Désolé, une erreur s'est produite. Pouvez-vous reformuler votre question ?",
                "error": str(e),
                "thread_id": thread_id
            }
    
    async def get_conversation_history(
        self, 
        thread_id: str,
        limit: Optional[int] = None
    ) -> List[BaseMessage]:
        """Récupère l'historique de conversation depuis le checkpoint."""
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            checkpoint = await self.memory.aget(config)
            if checkpoint and "messages" in checkpoint:
                messages = checkpoint["messages"]
                if limit:
                    return messages[-limit:]
                return messages
            return []
        except Exception as e:
            logger.error(f"Erreur récupération historique : {str(e)}")
            return []
    
    async def clear_conversation(self, thread_id: str) -> None:
        """Efface l'historique d'une conversation."""
        config = {"configurable": {"thread_id": thread_id}}
        await self.memory.adelete(config)
    
    async def get_conversation_summary(self, thread_id: str) -> str:
        """Génère un résumé de la conversation."""
        messages = await self.get_conversation_history(thread_id)
        
        if not messages:
            return "Aucune conversation trouvée."
        
        # Formater les messages pour le résumé
        conversation_text = "\n".join([
            f"{msg.type}: {msg.content[:200]}..." if len(msg.content) > 200 else f"{msg.type}: {msg.content}"
            for msg in messages
        ])
        
        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", """Résume cette conversation en mettant en avant :
            - Les besoins principaux exprimés
            - Les actions réalisées
            - Les résultats obtenus
            - Les prochaines étapes suggérées
            
            Sois concis mais complet."""),
            ("human", "Conversation :\n{conversation}")
        ])
        
        chain = summary_prompt | self.llm | StrOutputParser()
        summary = await chain.ainvoke({"conversation": conversation_text})
        
        return summary


# Instance singleton
agent = FranceTravailAgent()
