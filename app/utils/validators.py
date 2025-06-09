import re
from typing import Optional, List, Dict, Any
from datetime import datetime
import requests
from email_validator import validate_email, EmailNotValidError


class ValidationError(Exception):
    """Exception personnalisée pour les erreurs de validation."""
    pass


def validate_email_address(email: str) -> bool:
    """
    Valide une adresse email.
    """
    try:
        # Validation complète avec vérification DNS
        validation = validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def validate_phone_number(phone: str) -> bool:
    """
    Valide un numéro de téléphone français.
    """
    # Patterns pour les numéros français
    patterns = [
        r'^(?:(?:\+|00)33|0)\s*[1-9](?:[\s.-]*\d{2}){4}$',  # Format français
        r'^0[1-9]\d{8}$',  # Format simple
    ]
    
    # Nettoyer le numéro
    cleaned = re.sub(r'[\s.-]', '', phone)
    
    return any(re.match(pattern, cleaned) for pattern in patterns)


def validate_postal_code(postal_code: str) -> bool:
    """
    Valide un code postal français.
    """
    # Code postal français : 5 chiffres, peut commencer par 0
    pattern = r'^(?:0[1-9]|[1-9]\d)\d{3}$'
    return bool(re.match(pattern, postal_code.strip()))


def validate_siret(siret: str) -> bool:
    """
    Valide un numéro SIRET (14 chiffres avec clé de contrôle).
    """
    # Nettoyer le SIRET
    siret_clean = re.sub(r'\D', '', siret)
    
    if len(siret_clean) != 14:
        return False
    
    # Algorithme de Luhn pour vérifier la clé
    total = 0
    for i, digit in enumerate(siret_clean):
        d = int(digit)
        if i % 2 == 1:  # Position impaire (en partant de 0)
            d *= 2
            if d > 9:
                d -= 9
        total += d
    
    return total % 10 == 0


def validate_social_security_number(ssn: str) -> Dict[str, Any]:
    """
    Valide un numéro de sécurité sociale français.
    
    Returns:
        Dict avec is_valid et informations extraites
    """
    # Pattern pour le numéro de sécu
    pattern = r'^([12])\s*(\d{2})\s*(\d{2})\s*(\d{2})\s*(\d{3})\s*(\d{3})\s*(\d{2})$'
    
    # Nettoyer
    ssn_clean = ssn.strip()
    match = re.match(pattern, ssn_clean)
    
    if not match:
        return {"is_valid": False, "error": "Format invalide"}
    
    sex, year, month, dept, commune, order, key = match.groups()
    
    # Validation basique
    result = {
        "is_valid": True,
        "sex": "Homme" if sex == "1" else "Femme",
        "birth_year": f"19{year}" if int(year) > 30 else f"20{year}",
        "birth_month": month,
        "department": dept
    }
    
    # Vérifier le mois
    if not (1 <= int(month) <= 12):
        result["is_valid"] = False
        result["error"] = "Mois invalide"
    
    # Vérifier la clé de contrôle
    number_part = f"{sex}{year}{month}{dept}{commune}{order}"
    calculated_key = 97 - (int(number_part) % 97)
    
    if calculated_key != int(key):
        result["is_valid"] = False
        result["error"] = "Clé de contrôle invalide"
    
    return result


def validate_cv_data(cv_data: Dict[str, Any]) -> List[str]:
    """
    Valide les données d'un CV.
    
    Returns:
        Liste des erreurs trouvées
    """
    errors = []
    
    # Champs obligatoires
    required_fields = ["name", "email", "phone"]
    for field in required_fields:
        if not cv_data.get(field):
            errors.append(f"Le champ '{field}' est obligatoire")
    
    # Validation email
    if cv_data.get("email") and not validate_email_address(cv_data["email"]):
        errors.append("L'adresse email est invalide")
    
    # Validation téléphone
    if cv_data.get("phone") and not validate_phone_number(cv_data["phone"]):
        errors.append("Le numéro de téléphone est invalide")
    
    # Validation LinkedIn URL
    if cv_data.get("linkedin"):
        linkedin_pattern = r'^https?://(?:www\.)?linkedin\.com/in/[\w-]+/?$'
        if not re.match(linkedin_pattern, cv_data["linkedin"]):
            errors.append("L'URL LinkedIn est invalide")
    
    # Validation des expériences
    if cv_data.get("experiences"):
        for i, exp in enumerate(cv_data["experiences"]):
            if not exp.get("title"):
                errors.append(f"L'expérience {i+1} doit avoir un titre")
            if not exp.get("company"):
                errors.append(f"L'expérience {i+1} doit avoir une entreprise")
    
    return errors


def validate_job_search_criteria(criteria: Dict[str, Any]) -> List[str]:
    """
    Valide les critères de recherche d'emploi.
    """
    errors = []
    
    # Validation de la localisation
    if criteria.get("location"):
        # Vérifier si c'est un code postal
        if re.match(r'^\d{5}$', criteria["location"]):
            if not validate_postal_code(criteria["location"]):
                errors.append("Code postal invalide")
    
    # Validation de la distance
    if criteria.get("distance") is not None:
        if not (0 <= criteria["distance"] <= 100):
            errors.append("La distance doit être entre 0 et 100 km")
    
    # Validation des types de contrat
    valid_contracts = ["CDI", "CDD", "MIS", "SAI", "STG"]
    if criteria.get("contract_types"):
        invalid_contracts = [
            ct for ct in criteria["contract_types"] 
            if ct not in valid_contracts
        ]
        if invalid_contracts:
            errors.append(f"Types de contrat invalides : {', '.join(invalid_contracts)}")
    
    # Validation du salaire minimum
    if criteria.get("min_salary") is not None:
        if criteria["min_salary"] < 0:
            errors.append("Le salaire minimum ne peut pas être négatif")
    
    return errors


def validate_date_range(
    start_date: str, 
    end_date: str, 
    date_format: str = "%Y-%m-%d"
) -> Dict[str, Any]:
    """
    Valide une plage de dates.
    """
    result = {"is_valid": True, "errors": []}
    
    try:
        start = datetime.strptime(start_date, date_format)
        end = datetime.strptime(end_date, date_format)
        
        if start > end:
            result["is_valid"] = False
            result["errors"].append("La date de début doit être avant la date de fin")
        
        # Vérifier que les dates ne sont pas trop dans le futur
        max_future = datetime.now() + timedelta(days=365 * 2)
        if end > max_future:
            result["is_valid"] = False
            result["errors"].append("La date de fin est trop éloignée dans le futur")
        
        result["start"] = start
        result["end"] = end
        result["duration_days"] = (end - start).days
        
    except ValueError as e:
        result["is_valid"] = False
        result["errors"].append(f"Format de date invalide : {str(e)}")
    
    return result


def validate_file_upload(
    file_path: str, 
    allowed_extensions: List[str] = None,
    max_size_mb: float = 10
) -> Dict[str, Any]:
    """
    Valide un fichier uploadé.
    """
    import os
    
    result = {"is_valid": True, "errors": []}
    
    # Vérifier l'existence
    if not os.path.exists(file_path):
        result["is_valid"] = False
        result["errors"].append("Le fichier n'existe pas")
        return result
    
    # Vérifier l'extension
    if allowed_extensions:
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in allowed_extensions:
            result["is_valid"] = False
            result["errors"].append(
                f"Extension non autorisée. Extensions acceptées : {', '.join(allowed_extensions)}"
            )
    
    # Vérifier la taille
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > max_size_mb:
        result["is_valid"] = False
        result["errors"].append(
            f"Fichier trop volumineux ({file_size_mb:.1f} MB). Maximum : {max_size_mb} MB"
        )
    
    result["size_mb"] = file_size_mb
    result["extension"] = os.path.splitext(file_path)[1]
    
    return result


class InputSanitizer:
    """
    Classe pour nettoyer et sécuriser les entrées utilisateur.
    """
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """Supprime les balises HTML dangereuses."""
        # Liste des balises autorisées
        allowed_tags = ['b', 'i', 'u', 'strong', 'em', 'p', 'br']
        
        # Pattern pour détecter les balises
        tag_pattern = r'<(/?)(\w+)([^>]*)>'
        
        def replace_tag(match):
            closing = match.group(1)
            tag = match.group(2).lower()
            attrs = match.group(3)
            
            if tag in allowed_tags and not attrs:
                return f"<{closing}{tag}>"
            return ""
        
        return re.sub(tag_pattern, replace_tag, text)
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Nettoie un nom de fichier."""
        # Supprimer les caractères dangereux
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Supprimer les points au début
        filename = filename.lstrip('.')
        
        # Limiter la longueur
        max_length = 255
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            filename = name[:max_length - len(ext)] + ext
        
        return filename
    
    @staticmethod
    def sanitize_sql_input(text: str) -> str:
        """
        Nettoie une entrée pour éviter les injections SQL.
        Note: Utilisez toujours des requêtes paramétrées en plus !
        """
        # Échapper les caractères dangereux
        dangerous_chars = ["'", '"', ";", "--", "/*", "*/", "\\"]
        
        sanitized = text
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "")
        
        return sanitized.strip()
