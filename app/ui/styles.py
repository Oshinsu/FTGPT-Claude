import streamlit as st


def load_custom_css():
    """Charge les styles CSS personnalisés."""
    st.markdown("""
    <style>
    /* Couleurs France Travail */
    :root {
        --primary-color: #0053B3;
        --secondary-color: #00A6FB;
        --accent-color: #FF6B6B;
        --success-color: #00C896;
        --background-light: #F8F9FA;
        --text-primary: #2C3E50;
        --text-secondary: #6C757D;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        color: white;
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    /* Chat messages */
    .stChatMessage {
        border-radius: 15px;
        margin: 0.5rem 0;
        padding: 1rem;
        background-color: var(--background-light);
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        transition: all 0.3s ease;
        font-weight: 500;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 83, 179, 0.2);
    }
    
    /* Primary button */
    .stButton > button[kind="primary"] {
        background-color: var(--primary-color);
        color: white;
        border: none;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: var(--background-light);
    }
    
    /* Metrics */
    [data-testid="metric-container"] {
        background-color: white;
        border: 1px solid #E0E0E0;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: white;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        font-weight: 500;
    }
    
    /* Forms */
    [data-testid="stForm"] {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #E0E0E0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    /* Input fields */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 8px;
        border: 1px solid #CED4DA;
        padding: 0.75rem;
        transition: border-color 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 2px rgba(0, 83, 179, 0.1);
    }
    
    /* Success messages */
    .stSuccess {
        background-color: var(--success-color);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    /* Info messages */
    .stInfo {
        background-color: var(--secondary-color);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    /* Custom containers */
    .job-offer-card {
        background: white;
        border: 1px solid #E0E0E0;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }
    
    .job-offer-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    
    /* Mobile responsive */
    @media (max-width: 768px) {
        .stButton > button {
            width: 100%;
            margin: 0.25rem 0;
        }
        
        [data-testid="column"] {
            margin: 0.5rem 0;
        }
    }
    
    /* Loading animation */
    .loading-animation {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid rgba(0, 83, 179, 0.3);
        border-radius: 50%;
        border-top-color: var(--primary-color);
        animation: spin 1s ease-in-out infinite;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)


def apply_custom_theme():
    """Applique un thème personnalisé à l'application."""
    # Cette fonction pourrait être étendue pour gérer
    # différents thèmes (clair/sombre) selon les préférences
    pass
