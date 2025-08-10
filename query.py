from chromadb import PersistentClient
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import VectorStoreIndex

def get_query_engine(collection_name: str, embed_model):
    collection = PersistentClient(path="chroma_store").get_or_create_collection(collection_name)
    vector_store = ChromaVectorStore.from_collection(collection)
    return VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model).as_query_engine()