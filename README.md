# 🇫🇷 France Travail GPT

Assistant intelligent pour l'emploi et la formation professionnelle, développé par Byss Agency.

## 🎯 Fonctionnalités

- **🔍 Recherche d'emploi** : Accès en temps réel aux offres France Travail
- **📄 Génération de CV** : Création de CV optimisés selon le poste visé
- **✉️ Lettres de motivation** : Rédaction personnalisée et professionnelle
- **🎓 Orientation formation** : Conseils et recherche de formations adaptées
- **📋 Aide administrative** : Guide pour les démarches (inscription, allocations, etc.)
- **💬 Assistant conversationnel** : IA disponible 24/7 pour répondre à toutes vos questions

## 🚀 Installation

### Prérequis

- Python 3.12+
- Compte OpenAI avec clé API
- Identifiants API France Travail

### Installation rapide

```bash
# Cloner le projet
git clone https://github.com/your-org/france-travail-gpt.git
cd france-travail-gpt

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Copier et configurer l'environnement
cp .env.example .env
# Éditer .env avec vos clés API
