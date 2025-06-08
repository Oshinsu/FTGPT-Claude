from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts.prompt import PromptTemplate


# Prompt principal de l'agent
MAIN_AGENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Tu es un assistant intelligent spécialisé dans l'emploi et la formation professionnelle en France.
Tu es l'assistant virtuel de France Travail (ex-Pôle Emploi) et tu aides les utilisateurs avec :

1. La recherche d'offres d'emploi
2. Les conseils pour les CV et lettres de motivation  
3. L'orientation professionnelle et les formations
4. Les démarches administratives (inscription, actualisation, allocations)
5. Les droits et aides disponibles

Tu es bienveillant, professionnel et toujours orienté solutions. Tu adaptes ton langage au profil de l'utilisateur.
Tu as accès à l'API France Travail pour rechercher des offres en temps réel.

Contexte utilisateur:
{user_context}

Date du jour: {current_date}
"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Prompt pour l'analyse de profil
PROFILE_ANALYSIS_PROMPT = PromptTemplate(
    input_variables=["user_info", "objectives"],
    template="""Analyse le profil suivant et identifie les points clés pour l'orienter :

Informations utilisateur :
{user_info}

Objectifs déclarés :
{objectives}

Fournis une analyse structurée avec :
1. Synthèse du profil
2. Points forts identifiés
3. Axes d'amélioration
4. Recommandations personnalisées
5. Prochaines étapes concrètes
"""
)

# Prompt pour la génération de CV
CV_GENERATION_PROMPT = PromptTemplate(
    input_variables=["profile", "target_job", "experiences", "skills"],
    template="""Génère un CV professionnel optimisé pour le poste suivant :

Poste visé : {target_job}

Profil : {profile}
Expériences : {experiences}
Compétences : {skills}

Le CV doit être :
- Structuré et clair
- Adapté au poste visé
- Mettant en valeur les points forts
- Au format français standard
- Avec des verbes d'action

Génère le CV en format Markdown.
"""
)

# Prompt pour la lettre de motivation
COVER_LETTER_PROMPT = PromptTemplate(
    input_variables=["profile", "company", "job_offer", "motivations"],
    template="""Rédige une lettre de motivation personnalisée :

Entreprise : {company}
Offre d'emploi : {job_offer}
Profil candidat : {profile}
Motivations : {motivations}

La lettre doit :
- Être structurée en 3-4 paragraphes
- Montrer la connaissance de l'entreprise
- Mettre en avant l'adéquation profil/poste
- Exprimer une motivation authentique
- Respecter les codes professionnels français
"""
)

# Prompt pour les conseils de formation
TRAINING_ADVICE_PROMPT = PromptTemplate(
    input_variables=["current_skills", "target_job", "available_time", "budget"],
    template="""Recommande des formations adaptées :

Compétences actuelles : {current_skills}
Métier visé : {target_job}
Temps disponible : {available_time}
Budget : {budget}

Fournis :
1. Les compétences à acquérir en priorité
2. Les formations recommandées (courtes et longues)
3. Les organismes de formation pertinents
4. Les financements possibles (CPF, France Travail, etc.)
5. Un planning de formation réaliste
"""
)

# Prompt pour l'explication administrative
ADMIN_HELP_PROMPT = PromptTemplate(
    input_variables=["question", "user_situation", "context"],
    template="""Explique clairement la démarche administrative suivante :

Question : {question}
Situation utilisateur : {user_situation}
Contexte : {context}

Fournis :
1. Une explication simple et claire
2. Les étapes détaillées à suivre
3. Les documents nécessaires
4. Les délais à respecter
5. Les erreurs à éviter
6. Les contacts utiles

Utilise un langage accessible et bienveillant.
"""
)
