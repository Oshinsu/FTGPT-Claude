from typing import List, Optional, Dict, Any
from langchain_community.vectorstores import Chroma, FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_mistralai import MistralAIEmbeddings
from langchain_core.documents import Document
from app.config import settings
from pathlib import Path
import json


class KnowledgeBase:
    """Gestionnaire de la base de connaissances vectorielle."""
    
    def __init__(self):
        self.embeddings = self._get_embeddings()
        self.vector_store = self._initialize_vector_store()
        self._load_initial_data()
    
    def _get_embeddings(self):
        """Retourne le modèle d'embeddings configuré."""
        if settings.model_provider == "openai":
            return OpenAIEmbeddings(
                api_key=settings.openai_api_key
            )
        elif settings.model_provider == "mistral":
            return MistralAIEmbeddings(
                api_key=settings.mistral_api_key
            )
        else:
            raise ValueError(f"Provider non supporté : {settings.model_provider}")
    
    def _initialize_vector_store(self):
        """Initialise le vector store."""
        persist_directory = settings.vector_store_path
        persist_directory.mkdir(parents=True, exist_ok=True)
        
        if settings.vector_store_type == "chromadb":
            return Chroma(
                collection_name="france_travail_knowledge",
                embedding_function=self.embeddings,
                persist_directory=str(persist_directory)
            )
        elif settings.vector_store_type == "faiss":
            faiss_path = persist_directory / "faiss_index"
            if faiss_path.exists():
                return FAISS.load_local(
                    str(faiss_path),
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
            else:
                return FAISS.from_documents(
                    documents=[],
                    embedding=self.embeddings
                )
        else:
            raise ValueError(f"Vector store non supporté : {settings.vector_store_type}")
    
    def _load_initial_data(self):
        """Charge les données initiales dans le vector store."""
        data_path = Path("app/knowledge/data")
        
        # Charger les FAQ
        if (data_path / "faq.json").exists():
            with open(data_path / "faq.json", "r", encoding="utf-8") as f:
                faq_data = json.load(f)
                self._add_faq_documents(faq_data)
        
        # Charger les guides
        if (data_path / "guides.json").exists():
            with open(data_path / "guides.json", "r", encoding="utf-8") as f:
                guides_data = json.load(f)
                self._add_guide_documents(guides_data)
        
        # Charger les formations
        if (data_path / "formations.json").exists():
            with open(data_path / "formations.json", "r", encoding="utf-8") as f:
                formations_data = json.load(f)
                self._add_formation_documents(formations_data)
    
    def _add_faq_documents(self, faq_data: List[Dict[str, Any]]):
        """Ajoute les documents FAQ."""
        documents = []
        for item in faq_data:
            doc = Document(
                page_content=f"Question: {item['question']}\nRéponse: {item['answer']}",
                metadata={
                    "source": "FAQ France Travail",
                    "category": item.get("category", "general"),
                    "type": "faq"
                }
            )
            documents.append(doc)
        
        if documents:
            self.vector_store.add_documents(documents)
    
    def _add_guide_documents(self, guides_data: List[Dict[str, Any]]):
        """Ajoute les documents guides."""
        documents = []
        for guide in guides_data:
            doc = Document(
                page_content=guide["content"],
                metadata={
                    "source": guide["title"],
                    "category": guide.get("category", "guide"),
                    "type": "guide",
                    "tags": guide.get("tags", [])
                }
            )
            documents.append(doc)
        
        if documents:
            self.vector_store.add_documents(documents)
    
    def _add_formation_documents(self, formations_data: List[Dict[str, Any]]):
        """Ajoute les documents formations."""
        documents = []
        for formation in formations_data:
            content = f"""
Formation: {formation['title']}
Organisme: {formation['provider']}
Durée: {formation['duration']}
Niveau: {formation['level']}
Description: {formation['description']}
Prérequis: {', '.join(formation.get('prerequisites', []))}
Débouchés: {', '.join(formation.get('outcomes', []))}
"""
            doc = Document(
                page_content=content,
                metadata={
                    "source": formation['provider'],
                    "category": "formation",
                    "type": "formation",
                    "level": formation['level'],
                    "duration": formation['duration']
                }
            )
            documents.append(doc)
        
        if documents:
            self.vector_store.add_documents(documents)
    
    def search(
        self, 
        query: str, 
        category: Optional[str] = None,
        k: int = 5
    ) -> List[Document]:
        """
        Recherche dans la base de connaissances.
        
        Args:
            query: Requête de recherche
            category: Catégorie spécifique (optionnel)
            k: Nombre de résultats
            
        Returns:
            Documents pertinents
        """
        if category:
            # Recherche avec filtre sur la catégorie
            filter_dict = {"category": category}
            return self.vector_store.similarity_search(
                query, 
                k=k,
                filter=filter_dict
            )
        else:
            return self.vector_store.similarity_search(query, k=k)
    
    def add_document(
        self, 
        content: str, 
        metadata: Dict[str, Any]
    ) -> None:
        """Ajoute un document à la base."""
        doc = Document(
            page_content=content,
            metadata=metadata
        )
        self.vector_store.add_documents([doc])
    
    def save(self):
        """Sauvegarde le vector store."""
        if settings.vector_store_type == "faiss":
            save_path = settings.vector_store_path / "faiss_index"
            self.vector_store.save_local(str(save_path))
        # ChromaDB persiste automatiquement


# Instance singleton
knowledge_base = KnowledgeBase()
