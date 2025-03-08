from django.urls import path
from .views import home, upload_document, query_document

urlpatterns = [
    path('', home, name='home'),  # Serves the home page
    path('api/upload/', upload_document, name='upload_document'),  # Handles file uploads
    path('api/query/', query_document, name='query_document'),  # Handles queries
]
