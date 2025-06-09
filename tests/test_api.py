import pytest
from unittest.mock import Mock, patch, AsyncMock
import httpx
from datetime import datetime, timedelta
from app.api.france_travail import FranceTravailAPI
from app.api.auth import FranceTravailAuth
from app.api.models import (
    SearchOfferRequest, 
    SearchOfferResponse, 
    JobOffer,
    AccessToken,
    ContractType
)


@pytest.fixture
def auth():
    """Fixture pour l'authentification."""
    return FranceTravailAuth()


@pytest.fixture
def api():
    """Fixture pour l'API France Travail."""
    return FranceTravailAPI()


@pytest.fixture
def mock_token():
    """Mock d'un token d'accès."""
    return AccessToken(
        access_token="test_token_123",
        token_type="Bearer",
        expires_in=1800,
        scope="api_offresdemploiv2 o2dsoffre",
        expires_at=datetime.now() + timedelta(seconds=1800)
    )


@pytest.mark.asyncio
async def test_auth_get_access_token_new(auth, mock_token):
    """Test l'obtention d'un nouveau token."""
    with patch.object(auth, '_request_new_token', return_value=mock_token):
        token = await auth.get_access_token()
        
        assert token == "test_token_123"
        assert auth._token_cache is not None
        assert not auth._token_cache.is_expired()


@pytest.mark.asyncio
async def test_auth_get_access_token_cached(auth, mock_token):
    """Test l'utilisation du token en cache."""
    # Mettre un token en cache
    auth._token_cache = mock_token
    
    with patch.object(auth, '_request_new_token') as mock_request:
        token = await auth.get_access_token()
        
        assert token == "test_token_123"
        mock_request.assert_not_called()  # Ne doit pas demander un nouveau token


@pytest.mark.asyncio
async def test_auth_get_access_token_expired(auth, mock_token):
    """Test le renouvellement d'un token expiré."""
    # Créer un token expiré
    expired_token = AccessToken(
        access_token="old_token",
        token_type="Bearer",
        expires_in=0,
        scope="test",
        expires_at=datetime.now() - timedelta(seconds=60)
    )
    auth._token_cache = expired_token
    
    with patch.object(auth, '_request_new_token', return_value=mock_token):
        token = await auth.get_access_token()
        
        assert token == "test_token_123"
        assert auth._token_cache.access_token == "test_token_123"


@pytest.mark.asyncio
async def test_auth_request_new_token_success(auth):
    """Test la requête d'un nouveau token avec succès."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "access_token": "new_token_456",
        "token_type": "Bearer",
        "expires_in": 1800,
        "scope": "api_offresdemploiv2"
    }
    mock_response.raise_for_status = Mock()
    
    with patch('httpx.AsyncClient.post', return_value=mock_response):
        token = await auth._request_new_token()
        
        assert token.access_token == "new_token_456"
        assert token.expires_in == 1800
        assert not token.is_expired()


@pytest.mark.asyncio
async def test_search_offers_success(api, mock_token):
    """Test la recherche d'offres avec succès."""
    # Mock de l'authentification
    with patch.object(api.auth, 'get_access_token', return_value="test_token"):
        # Mock de la réponse HTTP
        mock_response = Mock()
        mock_response.json.return_value = {
            "totalResultats": 42,
            "resultats": [
                {
                    "id": "123",
                    "intitule": "Développeur Python",
                    "entreprise": {"nom": "TechCorp"},
                    "lieuTravail": {"libelle": "Paris"},
                    "typeContrat": "CDI",
                    "experienceExige": "E",
                    "dateCreation": "2025-01-15T10:00:00Z",
                    "dateActualisation": "2025-01-16T10:00:00Z",
                    "origineOffre": {"urlOrigine": "https://example.com/job/123"}
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient.get', return_value=mock_response):
            request = SearchOfferRequest(
                keywords="Python",
                location="Paris",
                contract_types=[ContractType.CDI]
            )
            
            response = await api.search_offers(request)
            
            assert response.total_results == 42
            assert len(response.offers) == 1
            assert response.offers[0].title == "Développeur Python"
            assert response.offers[0].company_name == "TechCorp"


@pytest.mark.asyncio
async def test_search_offers_with_filters(api):
    """Test la construction des paramètres de recherche."""
    request = SearchOfferRequest(
        keywords="data scientist",
        location="75001",
        distance=20,
        contract_types=[ContractType.CDI, ContractType.CDD],
        experience_levels=["E", "S"],
        min_salary=45000,
        page=1,
        per_page=50
    )
    
    params = api._build_search_params(request)
    
    assert params["motsCles"] == "data scientist"
    assert params["commune"] == "75001"
    assert params["distance"] == 20
    assert params["typeContrat"] == "CDI,CDD"
    assert params["experience"] == "E,S"
    assert params["salaireMin"] == 45000
    assert params["range"] == "50-99"


@pytest.mark.asyncio
async def test_get_offer_details_success(api):
    """Test la récupération des détails d'une offre."""
    offer_id = "123456"
    
    with patch.object(api.auth, 'get_access_token', return_value="test_token"):
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": offer_id,
            "intitule": "Chef de projet IT",
            "entreprise": {"nom": "BigCorp"},
            "lieuTravail": {"libelle": "Lyon"},
            "typeContrat": "CDI",
            "salaire": {"libelle": "45-50K€"},
            "experienceExige": "S",
            "dateCreation": "2025-01-10T10:00:00Z",
            "dateActualisation": "2025-01-15T10:00:00Z",
            "origineOffre": {"urlOrigine": "https://example.com/job/123456"}
        }
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient.get', return_value=mock_response):
            offer = await api.get_offer_details(offer_id)
            
            assert offer.id == offer_id
            assert offer.title == "Chef de projet IT"
            assert offer.salary_description == "45-50K€"


@pytest.mark.asyncio
async def test_api_retry_on_failure(api):
    """Test le retry en cas d'échec."""
    with patch.object(api.auth, 'get_access_token', return_value="test_token"):
        # Simuler 2 échecs puis un succès
        mock_responses = [
            httpx.HTTPStatusError("Error", request=Mock(), response=Mock(status_code=500)),
            httpx.HTTPStatusError("Error", request=Mock(), response=Mock(status_code=500)),
            Mock(json=Mock(return_value={"totalResultats": 0, "resultats": []}), 
                 raise_for_status=Mock())
        ]
        
        with patch('httpx.AsyncClient.get', side_effect=mock_responses):
            request = SearchOfferRequest(keywords="test")
            response = await api.search_offers(request)
            
            assert response.total_results == 0


@pytest.mark.asyncio
async def test_api_timeout_handling(api):
    """Test la gestion du timeout."""
    with patch.object(api.auth, 'get_access_token', return_value="test_token"):
        with patch('httpx.AsyncClient.get', side_effect=httpx.TimeoutException("Timeout")):
            request = SearchOfferRequest(keywords="test")
            
            with pytest.raises(Exception):  # Le retry va échouer après 3 tentatives
                await api.search_offers(request)


def test_build_search_params_empty_request(api):
    """Test la construction de paramètres avec une requête vide."""
    request = SearchOfferRequest()
    params = api._build_search_params(request)
    
    assert "range" in params
    assert params["range"] == "0-19"  # Pagination par défaut
    assert "motsCles" not in params
    assert "commune" not in params


def test_access_token_expiration():
    """Test la vérification d'expiration du token."""
    # Token non expiré
    future_token = AccessToken(
        access_token="token",
        token_type="Bearer",
        expires_in=3600,
        scope="test",
        expires_at=datetime.now() + timedelta(hours=1)
    )
    assert not future_token.is_expired()
    
    # Token expiré
    past_token = AccessToken(
        access_token="token",
        token_type="Bearer",
        expires_in=0,
        scope="test",
        expires_at=datetime.now() - timedelta(hours=1)
    )
    assert past_token.is_expired()
