from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import re
import unicodedata
from pathlib import Path
import hashlib
import json


def normalize_text(text: str) -> str:
    """
    Normalise un texte en supprimant les accents et caractères spéciaux.
    """
    # Supprimer les accents
    nfd_form = unicodedata.normalize('NFD', text)
    text_normalized = ''.join(
        char for char in nfd_form 
        if unicodedata.category(char) != 'Mn'
    )
    
    # Convertir en minuscules et supprimer les espaces multiples
    text_normalized = re.sub(r'\s+', ' ', text_normalized.lower().strip())
    
    return text_normalized


def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """
    Extrait les mots-clés significatifs d'un texte.
    """
    # Mots vides français à ignorer
    stop_words = {
        'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou', 
        'mais', 'donc', 'or', 'ni', 'car', 'que', 'qui', 'quoi', 'dont',
        'où', 'à', 'dans', 'pour', 'sur', 'avec', 'sans', 'sous', 'par'
    }
    
    # Normaliser et tokenizer
    normalized = normalize_text(text)
    words = re.findall(r'\b\w+\b', normalized)
    
    # Filtrer les mots
    keywords = [
        word for word in words 
        if len(word) >= min_length and word not in stop_words
    ]
    
    # Retourner les mots uniques
    return list(dict.fromkeys(keywords))


def format_date_french(date: datetime) -> str:
    """
    Formate une date en français.
    """
    months = [
        'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
        'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'
    ]
    
    day = date.day
    month = months[date.month - 1]
    year = date.year
    
    return f"{day} {month} {year}"


def calculate_date_range(
    period: str, 
    reference_date: Optional[datetime] = None
) -> tuple[datetime, datetime]:
    """
    Calcule une plage de dates selon une période donnée.
    
    Args:
        period: 'week', 'month', 'quarter', 'year'
        reference_date: Date de référence (par défaut aujourd'hui)
    
    Returns:
        Tuple (date_début, date_fin)
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    if period == 'week':
        start = reference_date - timedelta(days=reference_date.weekday())
        end = start + timedelta(days=6)
    
    elif period == 'month':
        start = reference_date.replace(day=1)
        if reference_date.month == 12:
            end = reference_date.replace(year=reference_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = reference_date.replace(month=reference_date.month + 1, day=1) - timedelta(days=1)
    
    elif period == 'quarter':
        quarter = (reference_date.month - 1) // 3
        start_month = quarter * 3 + 1
        start = reference_date.replace(month=start_month, day=1)
        end_month = start_month + 2
        if end_month > 12:
            end = reference_date.replace(year=reference_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = reference_date.replace(month=end_month + 1, day=1) - timedelta(days=1)
    
    elif period == 'year':
        start = reference_date.replace(month=1, day=1)
        end = reference_date.replace(month=12, day=31)
    
    else:
        raise ValueError(f"Période non supportée : {period}")
    
    return start, end


def sanitize_filename(filename: str) -> str:
    """
    Nettoie un nom de fichier pour être compatible avec tous les OS.
    """
    # Caractères interdits
    invalid_chars = '<>:"/\\|?*'
    
    # Remplacer les caractères interdits
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limiter la longueur
    max_length = 200
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = f"{name[:max_length-len(ext)-1]}.{ext}" if ext else name[:max_length]
    
    return filename


def generate_session_id(user_id: Optional[str] = None) -> str:
    """
    Génère un ID de session unique.
    """
    timestamp = datetime.now().isoformat()
    data = f"{timestamp}_{user_id or 'anonymous'}"
    
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def parse_salary_text(salary_text: str) -> Dict[str, Any]:
    """
    Parse un texte de salaire pour extraire les montants.
    
    Returns:
        Dict avec min, max, currency, period
    """
    # Patterns pour extraire les salaires
    patterns = [
        r'(\d+(?:\s?\d+)*)\s*(?:à|et|-)\s*(\d+(?:\s?\d+)*)\s*€',  # Range
        r'(\d+(?:\s?\d+)*)\s*€',  # Montant unique
        r'(\d+(?:\s?\d+)*)\s*euros?',  # En lettres
    ]
    
    result = {
        "min": None,
        "max": None,
        "currency": "EUR",
        "period": "month",
        "raw": salary_text
    }
    
    # Détecter la période
    if any(word in salary_text.lower() for word in ['heure', 'horaire', '/h']):
        result["period"] = "hour"
    elif any(word in salary_text.lower() for word in ['jour', 'journée', '/j']):
        result["period"] = "day"
    elif any(word in salary_text.lower() for word in ['an', 'année', 'annuel']):
        result["period"] = "year"
    
    # Extraire les montants
    for pattern in patterns:
        match = re.search(pattern, salary_text, re.IGNORECASE)
        if match:
            if len(match.groups()) == 2:
                # Range de salaire
                result["min"] = int(match.group(1).replace(' ', ''))
                result["max"] = int(match.group(2).replace(' ', ''))
            else:
                # Montant unique
                amount = int(match.group(1).replace(' ', ''))
                result["min"] = amount
                result["max"] = amount
            break
    
    return result


def chunk_text(text: str, max_length: int = 1000, overlap: int = 100) -> List[str]:
    """
    Découpe un texte long en chunks avec overlap.
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_length
        
        # Essayer de couper à la fin d'une phrase
        if end < len(text):
            last_period = text.rfind('.', start, end)
            if last_period > start:
                end = last_period + 1
        
        chunks.append(text[start:end])
        start = end - overlap
    
    return chunks


def calculate_match_score(
    profile: Dict[str, Any], 
    job_offer: Dict[str, Any]
) -> float:
    """
    Calcule un score de correspondance entre un profil et une offre.
    
    Returns:
        Score entre 0 et 1
    """
    score = 0.0
    weights = {
        "skills": 0.4,
        "experience": 0.3,
        "location": 0.2,
        "contract": 0.1
    }
    
    # Correspondance des compétences
    if profile.get("skills") and job_offer.get("skills"):
        profile_skills = set(normalize_text(s) for s in profile["skills"])
        job_skills = set(normalize_text(s) for s in job_offer["skills"])
        
        if job_skills:
            skill_match = len(profile_skills & job_skills) / len(job_skills)
            score += weights["skills"] * skill_match
    
    # Correspondance de l'expérience
    if profile.get("experience_years") and job_offer.get("experience_required"):
        exp_map = {"D": 0, "E": 3, "S": 5}  # Débutant, Expérimenté, Senior
        required_exp = exp_map.get(job_offer["experience_required"], 0)
        
        if profile["experience_years"] >= required_exp:
            score += weights["experience"]
        else:
            # Score partiel si proche
            score += weights["experience"] * (profile["experience_years"] / required_exp)
    
    # Correspondance de la localisation
    if profile.get("location") and job_offer.get("location"):
        if normalize_text(profile["location"]) == normalize_text(job_offer["location"]):
            score += weights["location"]
    
    # Correspondance du type de contrat
    if profile.get("contract_preferences") and job_offer.get("contract_type"):
        if job_offer["contract_type"] in profile["contract_preferences"]:
            score += weights["contract"]
    
    return min(score, 1.0)


def format_phone_number(phone: str) -> str:
    """
    Formate un numéro de téléphone français.
    """
    # Supprimer tous les caractères non numériques
    digits = re.sub(r'\D', '', phone)
    
    # Ajouter le préfixe français si nécessaire
    if len(digits) == 9:
        digits = '0' + digits
    elif len(digits) == 10 and digits[0] != '0':
        digits = '0' + digits
    
    # Formater en groupes de 2
    if len(digits) == 10:
        return ' '.join([digits[i:i+2] for i in range(0, 10, 2)])
    
    return phone  # Retourner l'original si format non reconnu


class ProgressTracker:
    """
    Classe pour suivre la progression d'une tâche.
    """
    def __init__(self, total_steps: int, description: str = ""):
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.start_time = datetime.now()
        self.steps_info = []
    
    def update(self, step_description: str = ""):
        """Met à jour la progression."""
        self.current_step += 1
        self.steps_info.append({
            "step": self.current_step,
            "description": step_description,
            "timestamp": datetime.now()
        })
    
    @property
    def progress(self) -> float:
        """Retourne la progression en pourcentage."""
        return (self.current_step / self.total_steps) * 100 if self.total_steps > 0 else 0
    
    @property
    def elapsed_time(self) -> timedelta:
        """Retourne le temps écoulé."""
        return datetime.now() - self.start_time
    
    @property
    def estimated_remaining_time(self) -> Optional[timedelta]:
        """Estime le temps restant."""
        if self.current_step == 0:
            return None
        
        avg_time_per_step = self.elapsed_time / self.current_step
        remaining_steps = self.total_steps - self.current_step
        
        return a
