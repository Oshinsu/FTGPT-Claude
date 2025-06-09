import streamlit as st
import asyncio
from datetime import datetime
from pathlib import Path
from app.core.agent import agent
from app.ui.components import (
    render_header,
    render_chat_interface,
    render_sidebar,
    render_footer,
    render_job_offers,
    render_document_preview,
    render_onboarding_dialog
)
from app.ui.styles import load_custom_css, apply_theme
from app.config import settings
import uuid
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration Streamlit avec nouvelles features
st.set_page_config(
    page_title="France Travail GPT - Assistant Emploi & Formation",
    page_icon="🇫🇷",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://aide.francetravail.fr',
        'Report a bug': "https://github.com/byss-agency/france-travail-gpt/issues",
        'About': "# France Travail GPT\nAssistant IA pour l'emploi et la formation\n\nDéveloppé par Byss Agency"
    }
)

# Charger le thème et les styles
load_custom_css()
apply_theme()


def init_session_state():
    """Initialise l'état de session avec les nouvelles features."""
    # États de base
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Message de bienvenue initial
        welcome_message = {
            "role": "assistant",
            "content": """👋 Bonjour et bienvenue sur **France Travail GPT** !

Je suis votre assistant personnel pour tout ce qui concerne l'emploi et la formation. Je peux vous aider avec :

🔍 **Recherche d'emploi** - Trouvez des offres adaptées à votre profil  
📄 **CV & Lettres** - Création et optimisation de vos documents  
🎓 **Formation** - Orientation et financement  
📋 **Démarches** - Inscription, actualisation, allocations  
💡 **Conseils** - Stratégies et accompagnement personnalisé

💬 **Comment puis-je vous aider aujourd'hui ?**""",
            "timestamp": datetime.now(),
            "metadata": {"type": "welcome"}
        }
        st.session_state.messages.append(welcome_message)
    
    # Profil utilisateur enrichi
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = {
            "onboarded": False,
            "name": None,
            "email": None,
            "situation": None,
            "experience": None,
            "target_job": None,
            "skills": [],
            "preferences": {
                "contract_types": [],
                "locations": [],
                "remote": False
            }
        }
    
    # États de navigation
    if "current_view" not in st.session_state:
        st.session_state.current_view = "chat"
    
    # Données
    if "job_search_results" not in st.session_state:
        st.session_state.job_search_results = None
    
    if "generated_documents" not in st.session_state:
        st.session_state.generated_documents = []
    
    # Features flags
    if "features" not in st.session_state:
        st.session_state.features = {
            "auto_save": True,
            "notifications": True,
            "dark_mode": False,
            "compact_view": False
        }
    
    # Analytics
    if "analytics" not in st.session_state:
        st.session_state.analytics = {
            "session_start": datetime.now(),
            "interactions": 0,
            "tools_used": []
        }


# Nouveau : Fragment réutilisable pour le chat
@st.fragment(run_every=1)
def auto_scroll_chat():
    """Auto-scroll du chat vers le bas."""
    if st.session_state.get("new_message"):
        st.session_state.new_message = False
        st.rerun()


async def process_user_input(user_input: str):
    """Traite l'entrée utilisateur avec le nouvel agent."""
    # Analytics
    st.session_state.analytics["interactions"] += 1
    
    # Ajouter le message utilisateur
    user_message = {
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now()
    }
    st.session_state.messages.append(user_message)
    st.session_state.new_message = True
    
    # Placeholder pour la réponse avec nouveau spinner
    response_placeholder = st.empty()
    
    with response_placeholder.container():
        with st.spinner("🤔 Je réfléchis..."):
            try:
                # Appeler l'agent
                response = await agent.process_message(
                    message=user_input,
                    thread_id=st.session_state.thread_id,
                    user_profile=st.session_state.user_profile
                )
                
                # Ajouter la réponse
                assistant_message = {
                    "role": "assistant",
                    "content": response["response"],
                    "timestamp": datetime.now(),
                    "metadata": {
                        "intent": response.get("intent"),
                        "tools_used": response.get("tools_used", []),
                        "specialized": response.get("specialized", False)
                    }
                }
                st.session_state.messages.append(assistant_message)
                
                # Analytics
                if response.get("tools_used"):
                    st.session_state.analytics["tools_used"].extend(response["tools_used"])
                
                # Notifications pour certaines actions
                if "search_job_offers" in response.get("tools_used", []):
                    st.toast("🔍 Recherche d'offres terminée !", icon="✅")
                elif "generate_document" in response.get("tools_used", []):
                    st.toast("📄 Document généré avec succès !", icon="✅")
                
            except Exception as e:
                logger.error(f"Erreur lors du traitement : {str(e)}")
                error_message = {
                    "role": "assistant",
                    "content": f"❌ Désolé, une erreur s'est produite. Pouvez-vous reformuler votre question ?",
                    "timestamp": datetime.now(),
                    "metadata": {"error": str(e)}
                }
                st.session_state.messages.append(error_message)
                st.error("Une erreur s'est produite. Veuillez réessayer.")
    
    response_placeholder.empty()


def render_chat_view():
    """Affiche la vue chat avec les nouvelles features."""
    st.markdown("### 💬 Assistant Conversationnel")
    
    # Boutons d'action rapide
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔍 Chercher un emploi", use_container_width=True):
            asyncio.run(process_user_input("Je cherche un emploi"))
    
    with col2:
        if st.button("📄 Créer mon CV", use_container_width=True):
            st.session_state.current_view = "cv_builder"
            st.rerun()
    
    with col3:
        if st.button("🎓 Trouver une formation", use_container_width=True):
            asyncio.run(process_user_input("Je cherche une formation"))
    
    with col4:
        if st.button("❓ Comment m'inscrire ?", use_container_width=True):
            asyncio.run(process_user_input("Comment m'inscrire à France Travail ?"))
    
    st.markdown("---")
    
    # Container de chat avec hauteur fixe
    chat_container = st.container(height=500)
    
    with chat_container:
        # Afficher les messages
        for idx, message in enumerate(st.session_state.messages):
            with st.chat_message(
                message["role"],
                avatar="🤖" if message["role"] == "assistant" else "👤"
            ):
                # Contenu principal
                st.markdown(message["content"])
                
                # Métadonnées et actions
                if message["role"] == "assistant" and "metadata" in message:
                    metadata = message["metadata"]
                    
                    # Afficher les outils utilisés
                    if metadata.get("tools_used"):
                        with st.expander("🔧 Détails de l'exécution", expanded=False):
                            st.caption(f"Outils : {', '.join(metadata['tools_used'])}")
                            st.caption(f"Intention : {metadata.get('intent', 'general')}")
                    
                    # Actions contextuelles
                    if metadata.get("intent") == "job_search":
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("📊 Voir plus d'offres", key=f"more_{idx}"):
                                st.session_state.current_view = "job_search"
                                st.rerun()
                        with col2:
                            if st.button("🔔 Créer une alerte", key=f"alert_{idx}"):
                                st.info("Fonctionnalité bientôt disponible !")
                
                # Timestamp
                st.caption(f"_{message['timestamp'].strftime('%H:%M')}_")
    
    # Zone de saisie avec placeholder dynamique
    placeholders = [
        "Recherchez un emploi de développeur à Paris...",
        "Comment rédiger une lettre de motivation ?",
        "Quelles formations en data science ?",
        "Aidez-moi à créer mon CV...",
        "Comment m'actualiser ce mois-ci ?"
    ]
    
    import random
    placeholder = random.choice(placeholders)
    
    # Input avec soumission sur Enter
    user_input = st.chat_input(
        placeholder=placeholder,
        key="chat_input",
        max_chars=1000
    )
    
    if user_input:
        asyncio.run(process_user_input(user_input))
        st.rerun()
    
    # Auto-scroll
    auto_scroll_chat()


def main():
    """Fonction principale avec architecture modernisée."""
    # Initialisation
    init_session_state()
    
    # Dialog d'onboarding pour les nouveaux utilisateurs
    if not st.session_state.user_profile["onboarded"]:
        render_onboarding_dialog()
    
    # Header moderne
    render_header()
    
    # Layout principal avec sidebar collapsible
    with st.sidebar:
        render_sidebar()
    
    # Container principal
    main_container = st.container()
    
    with main_container:
        # Navigation par tabs (nouvelle feature Streamlit)
        if st.session_state.current_view == "chat":
            render_chat_view()
        
        elif st.session_state.current_view == "job_search":
            from app.ui.views import render_job_search_view
            render_job_search_view()
        
        elif st.session_state.current_view == "cv_builder":
            from app.ui.views import render_cv_builder_view
            render_cv_builder_view()
        
        elif st.session_state.current_view == "training":
            from app.ui.views import render_training_view
            render_training_view()
        
        elif st.session_state.current_view == "documents":
            from app.ui.views import render_documents_view
            render_documents_view()
        
        elif st.session_state.current_view == "profile":
            from app.ui.views import render_profile_view
            render_profile_view()
    
    # Footer
    render_footer()
    
    # Analytics tracking (en arrière-plan)
    if st.session_state.features["auto_save"]:
        # Sauvegarder périodiquement l'état
        pass


if __name__ == "__main__":
    # Mode debug
    if settings.app_debug:
        st.sidebar.markdown("---")
        with st.sidebar.expander("🐛 Debug Info"):
            st.json({
                "thread_id": st.session_state.thread_id,
                "messages_count": len(st.session_state.messages),
                "profile": st.session_state.user_profile,
                "analytics": st.session_state.analytics
            })
    
    main()
