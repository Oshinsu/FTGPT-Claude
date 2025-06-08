import streamlit as st
from datetime import datetime
from typing import List, Dict, Any, Optional
import json


def render_header():
    """Affiche l'en-tête de l'application."""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(
            """
            <div style="text-align: center; padding: 1rem 0;">
                <h1 style="color: #0053B3; margin: 0;">
                    🇫🇷 France Travail GPT
                </h1>
                <p style="color: #666; margin: 0.5rem 0;">
                    Votre assistant intelligent pour l'emploi et la formation
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    st.markdown("---")


def render_sidebar():
    """Affiche la barre latérale avec navigation et profil."""
    with st.sidebar:
        st.markdown("## 🧭 Navigation")
        
        # Menu de navigation
        menu_items = {
            "chat": "💬 Assistant",
            "job_search": "🔍 Recherche d'emploi",
            "cv_builder": "📄 Créer un CV",
            "training": "🎓 Formations",
            "documents": "📁 Mes documents"
        }
        
        for key, label in menu_items.items():
            if st.button(
                label,
                key=f"nav_{key}",
                use_container_width=True,
                type="primary" if st.session_state.current_view == key else "secondary"
            ):
                st.session_state.current_view = key
                st.rerun()
        
        st.markdown("---")
        
        # Profil utilisateur
        st.markdown("## 👤 Mon Profil")
        
        with st.expander("Informations personnelles", expanded=False):
            name = st.text_input(
                "Nom",
                value=st.session_state.user_profile.get("name", ""),
                key="profile_name"
            )
            
            email = st.text_input(
                "Email",
                value=st.session_state.user_profile.get("email", ""),
                key="profile_email"
            )
            
            situation = st.selectbox(
                "Situation",
                ["Demandeur d'emploi", "En poste", "En formation", "Autre"],
                index=0,
                key="profile_situation"
            )
            
            if st.button("💾 Sauvegarder", key="save_profile"):
                st.session_state.user_profile = {
                    "name": name,
                    "email": email,
                    "situation": situation
                }
                st.success("Profil sauvegardé !")
        
        st.markdown("---")
        
        # Statistiques
        st.markdown("## 📊 Statistiques")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Messages",
                len(st.session_state.messages)
            )
        
        with col2:
            st.metric(
                "Documents",
                len(st.session_state.generated_documents)
            )
        
        # Actions rapides
        st.markdown("## ⚡ Actions rapides")
        
        if st.button("🔄 Nouvelle conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()
        
        if st.button("💾 Exporter conversation", use_container_width=True):
            export_conversation()


def render_chat_interface():
    """Affiche l'interface de chat principale."""
    # Cette fonction est intégrée dans main.py
    pass


def render_job_offers(offers: List[Dict[str, Any]]):
    """Affiche les offres d'emploi."""
    st.markdown("### 📋 Offres d'emploi trouvées")
    
    if not offers:
        st.info("Aucune offre trouvée. Essayez de modifier vos critères.")
        return
    
    for i, offer in enumerate(offers):
        with st.expander(
            f"**{offer.get('title', 'Poste')}** - {offer.get('company', 'Entreprise')}",
            expanded=i < 3  # Expand first 3
        ):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**📍 Localisation :** {offer.get('location', 'Non précisé')}")
                st.markdown(f"**📄 Contrat :** {offer.get('contract', 'Non précisé')}")
                st.markdown(f"**💰 Salaire :** {offer.get('salary', 'Non précisé')}")
                st.markdown(f"**🎯 Expérience :** {offer.get('experience', 'Non précisé')}")
                st.markdown(f"**📅 Publié le :** {offer.get('created', 'Non précisé')}")
            
            with col2:
                st.link_button(
                    "Voir l'offre",
                    offer.get('url', '#'),
                    use_container_width=True
                )
                
                if st.button(
                    "📄 Générer CV",
                    key=f"cv_{offer.get('id', i)}",
                    use_container_width=True
                ):
                    st.session_state.current_view = "cv_builder"
                    st.session_state.target_job = offer.get('title', '')
                    st.rerun()


def render_document_preview(document: Dict[str, Any]):
    """Affiche un aperçu de document."""
    doc_type = document.get("type", "document")
    doc_path = document.get("path", "")
    timestamp = document.get("timestamp", datetime.now())
    
    icon = {
        "cv": "📄",
        "lettre_motivation": "✉️",
        "rapport": "📊"
    }.get(doc_type, "📄")
    
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        st.markdown(f"<h2 style='text-align: center;'>{icon}</h2>", unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"**{doc_type.replace('_', ' ').title()}**")
        st.caption(f"Créé le {timestamp.strftime('%d/%m/%Y à %H:%M')}")
    
    with col3:
        if st.button("📥 Télécharger", key=f"download_{doc_path}"):
            # Logique de téléchargement
            st.success("Téléchargement en cours...")


def render_footer():
    """Affiche le pied de page."""
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(
            """
            <small>
            Développé par Byss Agency<br>
            Powered by LangChain & OpenAI
            </small>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            """
            <small style='text-align: center; display: block;'>
            France Travail GPT v1.0<br>
            © 2025 Tous droits réservés
            </small>
            """,
            unsafe_allow_html=True
        )
    
    with col3:
        st.markdown(
            """
            <small style='text-align: right; display: block;'>
            <a href="#" style='text-decoration: none;'>Aide</a> | 
            <a href="#" style='text-decoration: none;'>CGU</a> | 
            <a href="#" style='text-decoration: none;'>Contact</a>
            </small>
            """,
            unsafe_allow_html=True
        )


def export_conversation():
    """Exporte la conversation en JSON."""
    conversation_data = {
        "thread_id": st.session_state.thread_id,
        "timestamp": datetime.now().isoformat(),
        "messages": [
            {
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg["timestamp"].isoformat()
            }
            for msg in st.session_state.messages
        ]
    }
    
    json_str = json.dumps(conversation_data, ensure_ascii=False, indent=2)
    
    st.download_button(
        label="💾 Télécharger la conversation",
        data=json_str,
        file_name=f"conversation_{st.session_state.thread_id[:8]}.json",
        mime="application/json"
    )
