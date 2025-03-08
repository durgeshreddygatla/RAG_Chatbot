import os
import logging
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .utils import create_faiss_index, rag_pipeline

logger = logging.getLogger(__name__)

# Store FAISS vectorstores in a dictionary (Key: Filename, Value: FAISS index)
vectorstores = {}

def home(request):
    return render(request, "index.html")


@csrf_exempt
@api_view(['POST'])
def upload_document(request):
    global vectorstores

    if "files" not in request.FILES:
        logger.error("No files uploaded in request!")
        return Response({"error": "No files uploaded!"}, status=400)

    files = request.FILES.getlist("files")  
    pdf_paths = []

    try:
        for file in files:
            if not file.name.lower().endswith(".pdf"):
                logger.error(f"Invalid file type: {file.name}")
                return Response({"error": "Only PDF files are allowed!"}, status=400)

            # Save uploaded file
            file_path = default_storage.save(f"uploads/{file.name}", file)
            full_path = default_storage.path(file_path)

            logger.info(f"File saved at: {full_path}")  # Debugging line
            pdf_paths.append(full_path)

        if not pdf_paths:
            logger.error("No valid PDF files found!")
            return Response({"error": "No valid PDF files found!"}, status=400)

        # Process PDFs and create FAISS index
        vectorstore = create_faiss_index(pdf_paths)
        
        if vectorstore is None:
            logger.error("FAISS index creation failed!")
            return Response({"error": "Failed to create FAISS index!"}, status=500)

        # Store FAISS index
        for file_path in pdf_paths:
            filename = os.path.basename(file_path)
            vectorstores[filename] = vectorstore

        return Response({"message": "Files uploaded and FAISS index created successfully!"})

    except Exception as e:
        logger.exception(f"Error processing PDFs: {str(e)}")
        return Response({"error": str(e)}, status=500)



@csrf_exempt
@api_view(['POST'])
def query_document(request):
    global vectorstores

    try:
        data = request.data
        question = data.get("query")

        if not question:
            logger.error("Query is missing in request!")
            return Response({"error": "No query provided!"}, status=400)

        if not vectorstores:
            logger.error("No FAISS indices available!")
            return Response({"error": "Please upload documents first!"}, status=400)

        # Query across all FAISS indices
        answers = {}
        for filename, vectorstore in vectorstores.items():
            answer = rag_pipeline(vectorstore, question)
            answers[filename] = answer or "No relevant answer found."

        return Response({"answers": answers})

    except Exception as e:
        logger.exception(f"Error during query processing: {str(e)}")
        return Response({"error": str(e)}, status=500)
