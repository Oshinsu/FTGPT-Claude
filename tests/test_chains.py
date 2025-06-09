import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.core.chains import (
    specialized_chains,
    profile_analysis_chain,
    cv_generation_chain,
    cover_letter_chain,
    training_advice_chain,
    admin_help_chain
)


@pytest.fixture
def mock_llm():
    """Mock du LLM pour les tests."""
    mock = AsyncMock()
    mock.ainvoke.return_value = Mock(content="Réponse générée par le LLM")
    return mock


@pytest.mark.asyncio
async def test_profile_analysis_chain(mock_llm):
    """Test la chaîne d'analyse de profil."""
    with patch('app.core.chains.get_llm', return_value=mock_llm):
        result = await specialized_chains.analyze_profile(
            user_info="Jean Dupont, 5 ans d'expérience en développement web",
            objectives="Devenir lead developer"
        )
        
        assert result is not None
        assert isinstance(result, str)
        mock_llm.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_cv_generation_chain(mock_llm):
    """Test la chaîne de génération de CV."""
    with patch('app.core.chains.get_llm', return_value=mock_llm):
        result = await specialized_chains.generate_cv(
            profile="Développeur Full Stack",
            target_job="Lead Developer",
            experiences="5 ans chez TechCorp",
            skills="Python, JavaScript, React"
        )
        
        assert result is not None
        assert isinstance(result, str)
        
        # Vérifier que les paramètres sont passés correctement
        call_args = mock_llm.ainvoke.call_args[0][0]
        assert "Lead Developer" in str(call_args)
        assert "Python, JavaScript, React" in str(call_args)


@pytest.mark.asyncio
async def test_cover_letter_chain(mock_llm):
    """Test la chaîne de génération de lettre de motivation."""
    mock_llm.ainvoke.return_value = Mock(
        content="Madame, Monsieur,\n\nJe suis vivement intéressé..."
    )
    
    with patch('app.core.chains.get_llm', return_value=mock_llm):
        result = await specialized_chains.generate_cover_letter(
            profile="Développeur Senior",
            company="TechCorp",
            job_offer="Lead Developer Full Stack",
            motivations="Passion pour les défis techniques"
        )
        
        assert result is not None
        assert "Madame, Monsieur" in result
        
        # Vérifier que tous les paramètres sont utilisés
        call_args = mock_llm.ainvoke.call_args[0][0]
        assert "TechCorp" in str(call_args)
        assert "Lead Developer Full Stack" in str(call_args)


@pytest.mark.asyncio
async def test_training_advice_chain(mock_llm):
    """Test la chaîne de conseils de formation."""
    mock_llm.ainvoke.return_value = Mock(
        content="Formations recommandées : 1. AWS Solutions Architect..."
    )
    
    with patch('app.core.chains.get_llm', return_value=mock_llm):
        result = await specialized_chains.get_training_advice(
            current_skills="Python, JavaScript",
            target_job="Cloud Architect",
            available_time="6 mois à temps partiel",
            budget="5000€ CPF"
        )
        
        assert result is not None
        assert "Formations recommandées" in result


@pytest.mark.asyncio
async def test_admin_help_chain(mock_llm):
    """Test la chaîne d'aide administrative."""
    mock_llm.ainvoke.return_value = Mock(
        content="Pour vous inscrire à France Travail : 1. Rendez-vous sur..."
    )
    
    with patch('app.core.chains.get_llm', return_value=mock_llm):
        result = await specialized_chains.get_admin_help(
            question="Comment m'inscrire à France Travail ?",
            user_situation="Demandeur d'emploi, premier contact",
            context="Licenciement économique"
        )
        
        assert result is not None
        assert "inscrire" in result.lower()


@pytest.mark.asyncio
async def test_chain_error_handling():
    """Test la gestion des erreurs dans les chaînes."""
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = Exception("Erreur LLM")
    
    with patch('app.core.chains.get_llm', return_value=mock_llm):
        with pytest.raises(Exception) as exc_info:
            await specialized_chains.analyze_profile(
                user_info="Test",
                objectives="Test"
            )
        
        assert "Erreur LLM" in str(exc_info.value)


@pytest.mark.parametrize("chain_method,params", [
    (
        "analyze_profile",
        {"user_info": "Info test", "objectives": "Objectifs test"}
    ),
    (
        "generate_cv",
        {
            "profile": "Profil test",
            "target_job": "Job test",
            "experiences": "Exp test",
            "skills": "Skills test"
        }
    ),
    (
        "get_training_advice",
        {
            "current_skills": "Skills actuelles",
            "target_job": "Job cible",
            "available_time": "Temps dispo",
            "budget": "Budget"
        }
    )
])
@pytest.mark.asyncio
async def test_all_chains_basic_functionality(mock_llm, chain_method, params):
    """Test basique de toutes les chaînes."""
    with patch('app.core.chains.get_llm', return_value=mock_llm):
        method = getattr(specialized_chains, chain_method)
        result = await method(**params)
        
        assert result is not None
        assert isinstance(result, str)
        assert mock_llm.ainvoke.called


@pytest.mark.asyncio
async def test_prompt_formatting():
    """Test le formatage des prompts."""
    # Test direct des prompts
    from app.core.prompts import PROFILE_ANALYSIS_PROMPT
    
    formatted = PROFILE_ANALYSIS_PROMPT.format(
        user_info="Test user",
        objectives="Test objectives"
    )
    
    assert "Test user" in formatted
    assert "Test objectives" in formatted
    assert "Synthèse du profil" in formatted


@pytest.mark.asyncio
async def test_chain_with_empty_inputs(mock_llm):
    """Test les chaînes avec des entrées vides."""
    with patch('app.core.chains.get_llm', return_value=mock_llm):
        # Test avec des chaînes vides
        result = await specialized_chains.analyze_profile(
            user_info="",
            objectives=""
        )
        
        assert result is not None
        # Le LLM devrait quand même être appelé
        assert mock_llm.ainvoke.called
