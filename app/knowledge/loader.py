from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import pandas as pd
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    TextLoader,
    PDFLoader,
    CSVLoader,
    JSONLoader,
    UnstructuredWordDocumentLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging

logger = logging.getLogger(__name__)


class KnowledgeLoader:
    """
    Chargeur de documents pour la base de connaissances.
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
            length_function=len
        )
        
        # Mapping des extensions aux loaders
        self.loaders = {
            '.txt': TextLoader,
            '.pdf': PDFLoader,
            '.csv': CSVLoader,
            '.json': self._load_json,
            '.docx': UnstructuredWordDocumentLoader,
            '.doc': UnstructuredWordDocumentLoader
        }
    
    def load_document(self, file_path: Path) -> List[Document]:
        """
        Charge un document unique.
        """
        if not file_path.exists():
            logger.error(f"Fichier non trouvé : {file_path}")
            return []
        
        extension = file_path.suffix.lower()
        
        if extension not in self.loaders:
            logger.warning(f"Extension non supportée : {extension}")
            return []
        
        try:
            # Charger le document
            if extension == '.json':
                documents = self._load_json(file_path)
            else:
                loader_class = self.loaders[extension]
                loader = loader_class(str(file_path))
                documents = loader.load()
            
            # Découper en chunks
            chunks = self.text_splitter.split_documents(documents)
            
            # Ajouter des métadonnées
            for chunk in chunks:
                chunk.metadata.update({
                    "source": str(file_path),
                    "file_type": extension,
                    "file_name": file_path.name
                })
            
            logger.info(f"Chargé {len(chunks)} chunks depuis {file_path}")
            return chunks
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement de {file_path}: {str(e)}")
            return []
    
    def _load_json(self, file_path: Path) -> List[Document]:
        """
        Charge un fichier JSON personnalisé.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        documents = []
        
        # Gérer différentes structures JSON
        if isinstance(data, list):
            for item in data:
                content = self._extract_content_from_json(item)
                metadata = self._extract_metadata_from_json(item)
                documents.append(Document(
                    page_content=content,
                    metadata=metadata
                ))
        elif isinstance(data, dict):
            content = self._extract_content_from_json(data)
            metadata = self._extract_metadata_from_json(data)
            documents.append(Document(
                page_content=content,
                metadata=metadata
            ))
        
        return documents
    
    def _extract_content_from_json(self, item: Dict[str, Any]) -> str:
        """
        Extrait le contenu textuel d'un objet JSON.
        """
        # Champs prioritaires pour le contenu
        content_fields = [
            'content', 'text', 'description', 'answer', 
            'question', 'title', 'body', 'message'
        ]
        
        # Chercher le contenu principal
        for field in content_fields:
            if field in item and isinstance(item[field], str):
                content = item[field]
                
                # Ajouter d'autres champs importants
                if 'question' in item and field != 'question':
                    content = f"Question: {item['question']}\n{content}"
                
                return content
        
        # Si aucun champ prioritaire, convertir tout en texte
        return json.dumps(item, ensure_ascii=False, indent=2)
    
    def _extract_metadata_from_json(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrait les métadonnées d'un objet JSON.
        """
        # Champs à exclure du contenu mais à garder en métadonnées
        metadata_fields = [
            'id', 'category', 'tags', 'type', 'source', 
            'author', 'date', 'version', 'keywords'
        ]
        
        metadata = {}
        for field in metadata_fields:
            if field in item:
                metadata[field] = item[field]
        
        return metadata
    
    def load_directory(
        self, 
        directory_path: Path, 
        recursive: bool = True,
        extensions: Optional[List[str]] = None
    ) -> List[Document]:
        """
        Charge tous les documents d'un répertoire.
        """
        if not directory_path.exists() or not directory_path.is_dir():
            logger.error(f"Répertoire non trouvé : {directory_path}")
            return []
        
        all_documents = []
        
        # Pattern de recherche
        pattern = "**/*" if recursive else "*"
        
        for file_path in directory_path.glob(pattern):
            if file_path.is_file():
                # Filtrer par extension si spécifié
                if extensions and file_path.suffix.lower() not in extensions:
                    continue
                
                documents = self.load_document(file_path)
                all_documents.extend(documents)
        
        logger.info(f"Chargé {len(all_documents)} documents depuis {directory_path}")
        return all_documents
    
    def load_france_travail_data(self) -> List[Document]:
        """
        Charge les données spécifiques France Travail.
        """
        data_path = Path("app/knowledge/data")
        documents = []
        
        # Charger les FAQ
        faq_path = data_path / "faq.json"
        if faq_path.exists():
            faq_docs = self.load_document(faq_path)
            for doc in faq_docs:
                doc.metadata["data_type"] = "faq"
            documents.extend(faq_docs)
        
        # Charger les guides
        guides_path = data_path / "guides.json"
        if guides_path.exists():
            guide_docs = self.load_document(guides_path)
            for doc in guide_docs:
                doc.metadata["data_type"] = "guide"
            documents.extend(guide_docs)
        
        # Charger les formations
        formations_path = data_path / "formations.json"
        if formations_path.exists():
            formation_docs = self.load_document(formations_path)
            for doc in formation_docs:
                doc.metadata["data_type"] = "formation"
            documents.extend(formation_docs)
        
        return documents
    
    def process_csv_data(
        self, 
        csv_path: Path,
        text_columns: List[str],
        metadata_columns: Optional[List[str]] = None
    ) -> List[Document]:
        """
        Traite un fichier CSV en documents.
        """
        df = pd.read_csv(csv_path)
        documents = []
        
        for _, row in df.iterrows():
            # Construire le contenu
            content_parts = []
            for col in text_columns:
                if col in row and pd.notna(row[col]):
                    content_parts.append(f"{col}: {row[col]}")
            
            if not content_parts:
                continue
            
            content = "\n".join(content_parts)
            
            # Construire les métadonnées
            metadata = {
                "source": str(csv_path),
                "file_type": ".csv"
            }
            
            if metadata_columns:
                for col in metadata_columns:
                    if col in row and pd.notna(row[col]):
                        metadata[col] = row[col]
            
            documents.append(Document(
                page_content=content,
                metadata=metadata
            ))
        
        return documents
    
    def create_embeddings_dataset(
        self, 
        documents: List[Document]
    ) -> Dict[str, List[Any]]:
        """
        Prépare un dataset pour l'embedding.
        """
        dataset = {
            "texts": [],
            "metadatas": [],
            "ids": []
        }
        
        for i, doc in enumerate(documents):
            dataset["texts"].append(doc.page_content)
            dataset["metadatas"].append(doc.metadata)
            dataset["ids"].append(f"doc_{i}")
        
        return dataset


# Instance singleton
knowledge_loader = KnowledgeLoader()
