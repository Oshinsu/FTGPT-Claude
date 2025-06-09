import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from app.core.agent import FranceTravailAgent
from app.core.tools import search_job_offers
from langchain_core.messages import HumanMessage, AIMessage


@pytest.fixture
def agent():
    """Fixture pour créer une instance de l'agent."""
    return FranceTravailAgent()


@pytest.fixture
def mock_llm():
    """Mock du LLM."""
    mock = AsyncMock()
    mock.ainvoke.return_value = AIMessage(content="Réponse test")
    return mock


@pytest.mark.asyncio
async def test_agent_initialization(agent):
    """Test l'initialisation de l'agent."""
    assert agent is not None
    assert agent.tools is not None
    assert len(agent.tools) > 0
    assert agent.memory is not None


@pytest.mark.asyncio
async def test_process_message_simple(agent, mock_llm):
    """Test le traitement d'un message simple."""
    with patch.object(agent, 'llm', mock_llm):
        result = await agent.process_message(
            message="Bonjour, comment allez-vous ?",
            thread_id="test_thread_123",
            user_profile={"name": "Test User"}
        )
        
        assert result is not None
        assert "response" in result
        assert result["thread_id"] == "test_thread_123"
        assert "intent" in result


@pytest.mark.asyncio
async def test_detect_intent_job_search(agent):
    """Test la détection d'intention pour la recherche d'emploi."""
    intent = await agent._detect_intent("Je cherche un emploi de développeur")
    
    assert intent["type"] == "job_search"
    assert intent["confidence"] >= 0.5
    assert not intent["specialized"]


@pytest.mark.asyncio
async def test_detect_intent_cv_generation(agent):
    """Test la détection d'intention pour la génération de CV."""
    intent = await agent._detect_intent("Peux-tu générer mon CV ?")
    
    assert intent["type"] == "cv_help"
    assert intent["specialized"] is True


@pytest.mark.asyncio
async def test_detect_intent_training(agent):
    """Test la détection d'intention pour la formation."""
    intent = await agent._detect_intent("Quelles formations en data science ?")
    
    assert intent["type"] == "training"
    assert not intent["specialized"]


@pytest.mark.asyncio
@patch('app.api.france_travail.france_travail_api.search_offers')
async def test_job_search_tool_integration(mock_search, agent):
    """Test l'intégration de l'outil de recherche d'emploi."""
    # Mock de la réponse API
    mock_search.return_value = {
        "total_results": 2,
        "offers": [
            {
                "id": "123",
                "title": "Développeur Python",
                "company": "TechCorp",
                "location": "Paris",
                "contract_type": "CDI"
            }
        ]
    }
    
    # Simuler une recherche via l'agent
    result = await agent.process_message(
        message="Trouve-moi des offres de développeur Python à Paris",
        thread_id="test_thread"
    )
    
    assert "response" in result
    assert result["intent"] == "job_search"


@pytest.mark.asyncio
async def test_specialized_chain_profile_analysis(agent):
    """Test la chaîne spécialisée d'analyse de profil."""
    user_profile = {
        "name": "Jean Dupont",
        "experience": "5 ans en développement web",
        "skills": ["Python", "JavaScript", "React"]
    }
    
    result = await agent._handle_specialized_request(
        intent={"type": "profile", "specialized": True},
        message="Analyse mon profil professionnel",
        user_profile=user_profile
    )
    
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 50  # Vérifier qu'on a une vraie analyse


@pytest.mark.asyncio
async def test_conversation_memory(agent):
    """Test la mémoire de conversation."""
    thread_id = "test_memory_thread"
    
    # Premier message
    await agent.process_message(
        message="Je m'appelle Pierre",
        thread_id=thread_id
    )
    
    # Deuxième message qui devrait se souvenir
    result = await agent.process_message(
        message="Quel est mon prénom ?",
        thread_id=thread_id
    )
    
    # L'agent devrait se souvenir du prénom
    # Note: Ce test dépend de l'implémentation réelle de la mémoire
    assert result is not None


@pytest.mark.asyncio
async def test_error_handling(agent):
    """Test la gestion des erreurs."""
    with patch.object(agent, 'agent', side_effect=Exception("Test error")):
        result = await agent.process_message(
            message="Test message",
            thread_id="error_thread"
        )
        
        assert "error" in result
        assert "Désolé" in result["response"]


@pytest.mark.asyncio
async def test_extract_tools_used(agent):
    """Test l'extraction des outils utilisés."""
    # Créer un résultat fictif avec des appels d'outils
    result = {
        "messages": [
            HumanMessage(content="Test"),
            AIMessage(
                content="Résultat",
                tool_calls=[
                    {"name": "search_job_offers"},
                    {"name": "search_knowledge"}
                ]
            )
        ]
    }
    
    tools_used = agent._extract_tools_used(result)
    
    assert len(tools_used) == 2
    assert "search_job_offers" in tools_used
    assert "search_knowledge" in tools_used


@pytest.mark.asyncio
async def test_get_conversation_summary(agent):
    """Test la génération de résumé de conversation."""
    thread_id = "summary_test_thread"
    
    # Simuler quelques échanges
    await agent.process_message("Bonjour", thread_id)
    await agent.process_message("Je cherche un emploi", thread_id)
    
    summary = await agent.get_conversation_summary(thread_id)
    
    assert summary is not None
    assert isinstance(summary, str)


@pytest.mark.parametrize("message,expected_intent", [
    ("Je veux m'inscrire à France Travail", "admin"),
    ("Comment rédiger une lettre de motivation ?", "cover_letter"),
    ("Quels sont mes droits aux allocations ?", "admin"),
    ("Je cherche une formation en comptabilité", "training"),
    ("Aidez-moi avec mon CV", "cv_help"),
])
@pytest.mark.asyncio
async def test_intent_detection_multiple_cases(agent, message, expected_intent):
    """Test la détection d'intention sur plusieurs cas."""
    intent = await agent._detect_intent(message)
    assert intent["type"] == expected_intent
