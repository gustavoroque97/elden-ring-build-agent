import os
from typing import Dict
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.vectorstores import VectorStoreRetriever

def setup_retrievers(data_dir: str = "../data/rag_data", index_path: str = "../data/faiss_index") -> Dict[str, VectorStoreRetriever]:
    """
    Set up the FAISS vector store and category retrievers.
    
    This function loads markdown documents from the data directory, assigns categories
    based on folder names, creates a FAISS vector store, saves it locally, and generates
    specialized retrievers for each gear category.
    
    Parameters
    ----------
    data_dir : str, optional
        The path to the directory containing markdown files (default is '../data/rag_data').
    index_path : str, optional
        The path to save the FAISS vector store index (default is '../data/faiss_index').
        
    Returns
    -------
    Dict[str, VectorStoreRetriever]
        A dictionary mapping category names to their respective VectorStoreRetriever instances.
    """
    loader = DirectoryLoader(
        data_dir, 
        glob="**/*.md", 
        loader_cls=TextLoader, 
        show_progress=True
    )
    
    docs = loader.load()
    print(f"Loaded {len(docs)} documents!")
    
    for doc in docs:
        normalized_path = doc.metadata.get("source", "").replace("\\", "/")
        folder_name = normalized_path.split("/")[-2] 
        doc.metadata["category"] = folder_name
        
    print("Metadata tagging complete. Example:", docs[0].metadata)
    
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.from_documents(
        documents=docs,
        embedding=embeddings
    )
    
    # Ensure directory exists before saving
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    vectorstore.save_local(index_path)
    
    retrievers = {
        "classes": vectorstore.as_retriever(search_kwargs={"k": 1, "filter": {"category": "classes"}}),
        "weapons": vectorstore.as_retriever(search_kwargs={"k": 4, "filter": {"category": "weapons"}}),
        "armor": vectorstore.as_retriever(search_kwargs={"k": 1, "filter": {"category": "armors"}}),
        "talismans": vectorstore.as_retriever(search_kwargs={"k": 4, "filter": {"category": "talismans"}}),
        "spirit ashes": vectorstore.as_retriever(search_kwargs={"k": 2, "filter": {"category": "spirits"}}),
        "incantations": vectorstore.as_retriever(search_kwargs={"k": 4, "filter": {"category": "incantations"}}),
        "sorceries": vectorstore.as_retriever(search_kwargs={"k": 4, "filter": {"category": "sorceries"}}),
        "shields": vectorstore.as_retriever(search_kwargs={"k": 1, "filter": {"category": "shields"}}),
        "ammos": vectorstore.as_retriever(search_kwargs={"k": 2, "filter": {"category": "ammos"}})
    }
    
    print("Successfully built dedicated category retrievers!")
    return retrievers
