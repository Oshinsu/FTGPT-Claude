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
    render_document_preview
)
from app.ui.styles import load_custom_css
from app.config import settings
import uuid


# Configuration Streamlit
st.set_page_config(
    page_title="France Travail GPT - Assistant Emploi & Formation",
    page_icon="🇫🇷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Charger les styles personnalisés
load_custom_css()


def init_session_state():
    """Initialise l'état de session Streamlit."""
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": """👋 Bonjour ! Je suis votre assistant France Travail.
                
Je peux vous aider avec :
- 🔍 La recherche d'offres d'emploi
- 📄 La création de CV et lettres de motivation
- 🎓 L'orientation vers des formations
- 📋 Les démarches administratives
- 💡 Des conseils personnalisés

Comment puis-je vous aider aujourd'hui ?""",
                "timestamp": datetime.now()
            }
        ]
    
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = {}
    
    if "current_view" not in st.session_state:
        st.session_state.current_view = "chat"
    
    if "job_search_results" not in st.session_state:
        st.session_state.job_search_results = None
    
    if "generated_documents" not in st.session_state:
        st.session_state.generated_documents = []


async def process_user_input(user_input: str):
    """Traite l'entrée utilisateur de manière asynchrone."""
    # Ajouter le message utilisateur
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now()
    })
    
    # Placeholder pour la réponse
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("🤔 Je réfléchis...")
    
    try:
        # Traiter le message avec l'agent
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
                "tools_used": response.get("tools_used", [])
            }
        }
        st.session_state.messages.append(assistant_message)
        
        # Mettre à jour l'affichage
        message_placeholder.markdown(response["response"])
        
        # Si des offres d'emploi ont été trouvées, les stocker
        if "search_job_offers" in response.get("tools_used", []):
            # Parser les résultats depuis la réponse
            # (dans une vraie implémentation, on retournerait les données structurées)
            st.session_state.job_search_results = response.get("job_offers")
        
        # Si un document a été généré
        if "generate_document" in response.get("tools_used", []):
            st.session_state.generated_documents.append({
                "type": response.get("doc_type"),
                "path": response.get("doc_path"),
                "timestamp": datetime.now()
            })
        
    except Exception as e:
        error_message = f"❌ Désolé, une erreur s'est produite : {str(e)}"
        message_placeholder.markdown(error_message)
        st.session_state.messages.append({
            "role": "assistant",
            "content": error_message,
            "timestamp": datetime.now()
        })


def main():
    """Fonction principale de l'application."""
    # Initialiser l'état de session
    init_session_state()
    
    # Header
    render_header()
    
    # Layout principal
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # Sidebar avec navigation et profil
        render_sidebar()
    
    with col2:
        # Vue principale selon la sélection
        if st.session_state.current_view == "chat":
            st.markdown("### 💬 Assistant Conversationnel")
            
            # Conteneur de chat
            chat_container = st.container()
            
            with chat_container:
                # Afficher l'historique des messages
                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
                        
                        # Afficher les métadonnées si disponibles
                        if "metadata" in message and message["role"] == "assistant":
                            metadata = message["metadata"]
                            if metadata.get("tools_used"):
                                st.caption(f"🔧 Outils utilisés : {', '.join(metadata['tools_used'])}")
            
            # Zone de saisie
            user_input = st.chat_input(
                "Posez votre question...",
                key="chat_input"
            )
            
            if user_input:
                # Traiter l'entrée de manière asynchrone
                asyncio.run(process_user_input(user_input))
                st.rerun()
        
        elif st.session_state.current_view == "job_search":
            st.markdown("### 🔍 Recherche d'Emploi")
            
            # Formulaire de recherche
            with st.form("job_search_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    keywords = st.text_input(
                        "Mots-clés",
                        placeholder="Ex: développeur, commercial, comptable..."
                    )
                    location = st.text_input(
                        "Localisation",
                        placeholder="Ville ou code postal"
                    )
                
                with col2:
                    contract_types = st.multiselect(
                        "Type de contrat",
                        ["CDI", "CDD", "Intérim", "Alternance", "Stage"]
                    )
                    distance = st.slider(
                        "Rayon de recherche (km)",
                        0, 100, 30
                    )
                
                search_button = st.form_submit_button(
                    "🔍 Rechercher",
                    use_container_width=True,
                    type="primary"
                )
            
            if search_button:
                # Construire la requête
                search_query = f"Recherche d'emploi : {keywords}"
                if location:
                    search_query += f" à {location}"
                if contract_types:
                    search_query += f" en {', '.join(contract_types)}"
                
                # Traiter avec l'agent
                asyncio.run(process_user_input(search_query))
            
            # Afficher les résultats si disponibles
            if st.session_state.job_search_results:
                render_job_offers(st.session_state.job_search_results)
        
        elif st.session_state.current_view == "cv_builder":
            st.markdown("### 📄 Générateur de CV")
            
            with st.form("cv_form"):
                st.markdown("#### Informations personnelles")
                col1, col2 = st.columns(2)
                
                with col1:
                    name = st.text_input("Nom complet")
                    email = st.text_input("Email")
                    phone = st.text_input("Téléphone")
                
                with col2:
                    address = st.text_input("Adresse")
                    linkedin = st.text_input("LinkedIn (optionnel)")
                    target_job = st.text_input("Poste visé")
                
                st.markdown("#### Expériences professionnelles")
                experiences = st.text_area(
                    "Décrivez vos expériences",
                    height=150,
                    placeholder="Une expérience par ligne avec : Poste - Entreprise - Période - Missions principales"
                )
                
                st.markdown("#### Compétences")
                skills = st.text_area(
                    "Listez vos compétences",
                    height=100,
                    placeholder="Séparez les compétences par des virgules"
                )
                
                generate_button = st.form_submit_button(
                    "📄 Générer le CV",
                    use_container_width=True,
                    type="primary"
                )
            
            if generate_button:
                # Construire la requête
                cv_request = f"""Génère un CV pour :
                Nom : {name}
                Email : {email}
                Téléphone : {phone}
                Poste visé : {target_job}
                Expériences : {experiences}
                Compétences : {skills}
                """
                
                asyncio.run(process_user_input(cv_request))
        
        elif st.session_state.current_view == "training":
            st.markdown("### 🎓 Formations & Orientation")
            
            # Questionnaire d'orientation
            st.markdown("#### Trouvez la formation qui vous correspond")
            
            current_situation = st.selectbox(
                "Votre situation actuelle",
                [
                    "Demandeur d'emploi",
                    "Salarié en reconversion",
                    "Étudiant",
                    "Entrepreneur",
                    "Autre"
                ]
            )
            
            domain = st.selectbox(
                "Domaine d'intérêt",
                [
                    "Informatique / Digital",
                    "Commerce / Vente",
                    "Industrie / Technique",
                    "Santé / Social",
                    "Administration / Gestion",
                    "Autre"
                ]
            )
            
            time_available = st.radio(
                "Temps disponible pour la formation",
                [
                    "Temps plein",
                    "Temps partiel",
                    "Soirs et week-ends",
                    "Formation courte (< 3 mois)"
                ]
            )
            
            if st.button("🎯 Obtenir des recommandations", type="primary"):
                training_query = f"""Je cherche une formation.
                Situation : {current_situation}
                Domaine : {domain}
                Disponibilité : {time_available}
                Recommande-moi des formations adaptées.
                """
                
                asyncio.run(process_user_input(training_query))
        
        elif st.session_state.current_view == "documents":
            st.markdown("### 📁 Mes Documents")
            
            if st.session_state.generated_documents:
                for doc in st.session_state.generated_documents:
                    render_document_preview(doc)
            else:
                st.info("Aucun document généré pour le moment.")
    
    # Footer
    render_footer()


if __name__ == "__main__":
    main()
