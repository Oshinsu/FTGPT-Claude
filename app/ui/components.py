import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import plotly.express as px
import pandas as pd
from streamlit_option_menu import option_menu


@st.dialog("Bienvenue sur France Travail GPT ! 🎉")
def render_onboarding_dialog():
    """Dialog d'onboarding pour les nouveaux utilisateurs."""
    st.markdown("""
    ### Configurons votre profil pour une expérience personnalisée
    
    Cela ne prendra que 2 minutes et nous permettra de mieux vous aider.
    """)
    
    # Étape 1 : Informations de base
    name = st.text_input("Comment vous appelez-vous ?", placeholder="Jean Dupont")
    email = st.text_input("Votre email", placeholder="jean.dupont@email.com")
    
    # Étape 2 : Situation
    situation = st.selectbox(
        "Quelle est votre situation actuelle ?",
        [
            "Demandeur d'emploi",
            "En poste (recherche active)",
            "En formation",
            "En reconversion",
            "Jeune diplômé",
            "Autre"
        ]
    )
    
    # Étape 3 : Objectif
    objective = st.text_area(
        "Quel est votre objectif principal ?",
        placeholder="Ex: Trouver un emploi de développeur web, me reconvertir dans le digital...",
        max_chars=200
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("➡️ Ignorer", use_container_width=True):
            st.session_state.user_profile["onboarded"] = True
            st.rerun()
    
    with col2:
        if st.button("✅ Valider", type="primary", use_container_width=True):
            if name and email:
                st.session_state.user_profile.update({
                    "onboarded": True,
                    "name": name,
                    "email": email,
                    "situation": situation,
                    "objective": objective
                })
                st.success("Profil créé avec succès !")
                st.balloons()
                st.rerun()
            else:
                st.error("Veuillez remplir au moins votre nom et email")


def render_header():
    """Affiche l'en-tête moderne avec navigation."""
    # Header avec gradient
    st.markdown(
        """
        <div class="main-header">
            <h1>🇫🇷 France Travail GPT</h1>
            <p>Votre assistant intelligent pour l'emploi et la formation</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Barre de navigation horizontale
    selected = option_menu(
        menu_title=None,
        options=["Chat", "Recherche", "CV", "Formation", "Documents", "Profil"],
        icons=["chat-dots", "search", "file-text", "mortarboard", "folder", "person"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal",
        styles={
            "container": {"padding": "0!important", "background-color": "#fafafa"},
            "icon": {"color": "#0053B3", "font-size": "20px"},
            "nav-link": {
                "font-size": "16px",
                "text-align": "center",
                "margin": "0px",
                "--hover-color": "#e8f0fe"
            },
            "nav-link-selected": {"background-color": "#0053B3"},
        }
    )
    
    # Mapper la sélection aux vues
    view_mapping = {
        "Chat": "chat",
        "Recherche": "job_search",
        "CV": "cv_builder",
        "Formation": "training",
        "Documents": "documents",
        "Profil": "profile"
    }
    
    if st.session_state.current_view != view_mapping[selected]:
        st.session_state.current_view = view_mapping[selected]
        st.rerun()


def render_sidebar():
    """Sidebar moderne avec widgets interactifs."""
    # Profil utilisateur avec avatar
    if st.session_state.user_profile.get("name"):
        st.markdown(
            f"""
            <div style="text-align: center; padding: 1rem; background: white; border-radius: 10px; margin-bottom: 1rem;">
                <div style="font-size: 3rem;">👤</div>
                <h3 style="margin: 0.5rem 0;">{st.session_state.user_profile['name']}</h3>
                <p style="color: #666; margin: 0;">{st.session_state.user_profile.get('situation', 'Non renseigné')}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Statistiques avec metrics
    st.markdown("### 📊 Vos statistiques")
    
    col1, col2 = st.columns(2)
    with col1:
        messages_today = len([
            m for m in st.session_state.messages 
            if m["timestamp"].date() == datetime.now().date()
        ])
        st.metric(
            "Messages aujourd'hui",
            messages_today,
            delta=f"+{messages_today}" if messages_today > 0 else "0"
        )
    
    with col2:
        st.metric(
            "Documents créés",
            len(st.session_state.generated_documents),
            delta="+1" if st.session_state.generated_documents else "0"
        )
    
    # Graphique d'activité
    if len(st.session_state.messages) > 1:
        df_activity = pd.DataFrame([
            {
                "Date": msg["timestamp"].date(),
                "Heure": msg["timestamp"].hour,
                "Type": msg["role"]
            }
            for msg in st.session_state.messages
        ])
        
        daily_activity = df_activity.groupby("Date").size().reset_index(name="Messages")
        
        if len(daily_activity) > 1:
            fig = px.line(
                daily_activity,
                x="Date",
                y="Messages",
                title="Activité quotidienne",
                height=200
            )
            fig.update_layout(
                showlegend=False,
                margin=dict(l=0, r=0, t=30, b=0)
            )
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Actions rapides avec boutons stylés
    st.markdown("### ⚡ Actions rapides")
    
    if st.button("🔄 Nouvelle conversation", use_container_width=True):
        if st.session_state.messages:
            with st.spinner("Sauvegarde de la conversation..."):
                # Sauvegarder l'ancienne conversation
                import asyncio
                asyncio.run(agent.clear_conversation(st.session_state.thread_id))
        
        # Réinitialiser
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.toast("Nouvelle conversation démarrée !", icon="🔄")
        st.rerun()
    
    if st.button("📥 Exporter l'historique", use_container_width=True):
        export_conversation()
    
    if st.button("🎯 Définir des alertes", use_container_width=True):
        st.info("Cette fonctionnalité arrive bientôt !")
    
    st.markdown("---")
    
    # Paramètres avec toggles modernes
    st.markdown("### ⚙️ Paramètres")
    
    # Dark mode toggle
    dark_mode = st.toggle(
        "Mode sombre",
        value=st.session_state.features.get("dark_mode", False),
        help="Active le thème sombre"
    )
    if dark_mode != st.session_state.features["dark_mode"]:
        st.session_state.features["dark_mode"] = dark_mode
        st.rerun()
    
    # Notifications
    notifications = st.toggle(
        "Notifications",
        value=st.session_state.features.get("notifications", True),
        help="Active les notifications toast"
    )
    st.session_state.features["notifications"] = notifications
    
    # Compact view
    compact = st.toggle(
        "Vue compacte",
        value=st.session_state.features.get("compact_view", False),
        help="Réduit l'espacement pour afficher plus de contenu"
    )
    st.session_state.features["compact_view"] = compact


def render_job_offer_card(offer: Dict[str, Any], index: int):
    """Affiche une carte d'offre d'emploi moderne."""
    with st.container():
        # Card container avec style
        card_html = f"""
        <div class="job-card" style="
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            transition: all 0.3s ease;
            cursor: pointer;
        ">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div style="flex: 1;">
                    <h3 style="margin: 0 0 0.5rem 0; color: #0053B3;">
                        {offer.get('title', 'Poste')}
                    </h3>
                    <p style="margin: 0.25rem 0; color: #666;">
                        <strong>{offer.get('company', 'Entreprise')}</strong> • 
                        📍 {offer.get('location', 'Localisation')}
                    </p>
                    <div style="display: flex; gap: 0.5rem; margin: 0.5rem 0;">
                        <span class="tag">{offer.get('contract', 'CDI')}</span>
                        <span class="tag">{offer.get('experience', 'Tous niveaux')}</span>
                        {f'<span class="tag salary">{offer.get("salary", "")}</span>' if offer.get('salary') else ''}
                    </div>
                </div>
                <div style="text-align: right;">
                    <p style="color: #999; font-size: 0.875rem; margin: 0;">
                        {offer.get('date', 'Aujourd\'hui')}
                    </p>
                </div>
            </div>
        </div>
        """
        
        st.markdown(card_html, unsafe_allow_html=True)
        
        # Actions
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            if st.button("👁️ Voir l'offre", key=f"view_{index}", use_container_width=True):
                st.session_state.selected_offer = offer
                if offer.get('url'):
                    st.markdown(f"[Ouvrir sur France Travail]({offer['url']})")
        
        with col2:
            if st.button("📄 Postuler", key=f"apply_{index}", use_container_width=True):
                st.session_state.current_view = "cv_builder"
                st.session_state.target_job = offer
                st.rerun()
        
        with col3:
            if st.button("⭐", key=f"save_{index}", use_container_width=True):
                st.toast("Offre sauvegardée !", icon="⭐")


def render_footer():
    """Footer moderne avec liens et informations."""
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(
            """
            <div style="text-align: center;">
                <h4>À propos</h4>
                <p style="font-size: 0.875rem; color: #666;">
                    Développé par Byss Agency<br>
                    Powered by LangChain & OpenAI
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            """
            <div style="text-align: center;">
                <h4>Ressources</h4>
                <p style="font-size: 0.875rem;">
                    <a href="#">Guide d'utilisation</a><br>
                    <a href="#">FAQ</a><br>
                    <a href="#">Tutoriels vidéo</a>
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col3:
        st.markdown(
            """
            <div style="text-align: center;">
                <h4>Légal</h4>
                <p style="font-size: 0.875rem;">
                    <a href="#">CGU</a><br>
                    <a href="#">Politique de confidentialité</a><br>
                    <a href="#">Mentions légales</a>
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col4:
        st.markdown(
            """
            <div style="text-align: center;">
                <h4>Contact</h4>
                <p style="font-size: 0.875rem;">
                    <a href="mailto:support@francetravail-gpt.fr">Support</a><br>
                    <a href="#">Signaler un bug</a><br>
                    <a href="#">Suggestions</a>
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Copyright
    st.markdown(
        """
        <div style="text-align: center; margin-top: 2rem; padding: 1rem; background: #f8f9fa;">
            <p style="margin: 0; color: #666; font-size: 0.875rem;">
                © 2025 France Travail GPT - Tous droits réservés | Version 1.0.0
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


def export_conversation():
    """Exporte la conversation avec formatage amélioré."""
    if not st.session_state.messages:
        st.warning("Aucune conversation à exporter")
        return
    
    # Préparer les données
    export_data = {
        "metadata": {
            "thread_id": st.session_state.thread_id,
            "export_date": datetime.now().isoformat(),
            "user_profile": st.session_state.user_profile,
            "message_count": len(st.session_state.messages),
            "session_duration": str(datetime.now() - st.session_state.analytics["session_start"])
        },
        "messages": [
            {
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg["timestamp"].isoformat(),
                "metadata": msg.get("metadata", {})
            }
            for msg in st.session_state.messages
        ],
        "analytics": st.session_state.analytics
    }
    
    # Format JSON avec indentation
    json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
    
    # Bouton de téléchargement stylé
    st.download_button(
        label="💾 Télécharger la conversation (JSON)",
        data=json_str,
        file_name=f"conversation_{st.session_state.thread_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        use_container_width=True
    )
    
    # Option d'export en texte
    text_export = "=== CONVERSATION FRANCE TRAVAIL GPT ===\n\n"
    text_export += f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
    text_export += f"Utilisateur: {st.session_state.user_profile.get('name', 'Anonyme')}\n"
    text_export += "=" * 40 + "\n\n"
    
    for msg in st.session_state.messages:
        role = "VOUS" if msg["role"] == "user" else "ASSISTANT"
        text_export += f"[{msg['timestamp'].strftime('%H:%M')}] {role}:\n"
        text_export += f"{msg['content']}\n"
        text_export += "-" * 40 + "\n\n"
    
    st.download_button(
        label="📄 Télécharger la conversation (TXT)",
        data=text_export,
        file_name=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
        use_container_width=True
    )
