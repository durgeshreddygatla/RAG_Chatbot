import os
import json
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain_groq import ChatGroq
from langchain_core.documents import Document
import logging
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Accessing variables
groq_key = os.getenv('GROQ_API_KEY')
hf_key = os.getenv('HUGGINGFACE_API_KEY')

logger = logging.getLogger(__name__)

def process_pdfs(file_paths):
    """Load and process multiple PDFs, handling possible failures."""
    all_docs = []
    for file_path in file_paths:
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                continue

            loader = PyPDFLoader(file_path)
            docs = loader.load()

            if not docs:
                logger.warning(f"No text extracted from: {file_path}")
                continue

            all_docs.extend(docs)
        except Exception as e:
            logger.exception(f"Error loading PDF {file_path}: {str(e)}")

    return all_docs

def create_faiss_index(file_paths):
    """Create FAISS index using Hugging Face embeddings."""
    model_path = "models/all-MiniLM-L6-v2"

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at {model_path}. Ensure it's downloaded.")

    embeddings = HuggingFaceEmbeddings(model_name=model_path)

    # Process the PDFs
    docs = process_pdfs(file_paths)

    if not docs:
        logger.error("No valid documents found for indexing.")
        raise ValueError("No valid documents found for indexing.")

    # Ensure all docs are wrapped in `Document`
    processed_docs = [Document(page_content=text) if isinstance(text, str) else text for text in docs]

    # Create FAISS vectorstore
    vectorstore = FAISS.from_documents(processed_docs, embeddings)
    
    return vectorstore



def load_faiss_index(index_path="faiss_index"):
    """Load FAISS index if it exists, otherwise return None."""
    model_path = os.path.abspath("models/all-MiniLM-L6-v2")
    embeddings = HuggingFaceEmbeddings(model_name=model_path)

    if os.path.exists(index_path):
        print(f"Loading existing FAISS index from: {index_path}")
        return FAISS.load_local(index_path, embeddings)
    
    print("FAISS index not found, please upload documents first.")
    return None


def initialize_llm():
    """Initialize the LLM with Groq API."""

    if not groq_key:
        raise ValueError("Groq API key is missing. Set GROQ_API_KEY as an environment variable.")

    #print("Using DeepSeek-R1 via Groq API")
    return ChatGroq(
        model_name="deepseek-r1-distill-llama-70b",
        temperature=0.7,
        groq_api_key=groq_key
    )


def rag_pipeline(vectorstore, query):
    """Execute RAG pipeline with local LLM."""
    if vectorstore is None:
        raise ValueError("FAISS vectorstore is not initialized. Please upload documents first.")
    
    llm = initialize_llm()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever
    )
    
    try:
        response = qa_chain.invoke({"query": query})
        if not response or "result" not in response:
            return {"error": "No response generated from LLM."}

        result_text = response["result"]
        
        # Debugging log
        #print(f"RAG Response: {result_text}")

        think_end_index = result_text.find("</think>") + len("</think>") if "</think>" in result_text else -1
        final_response = result_text[think_end_index + 1:].strip()

        return {"answer": final_response}  # Ensure response is structured
    except Exception as e:
        return {"error": f"Error generating response: {str(e)}"}

