from fastapi import APIRouter

from app.api.routes import concepts, documents, keywords, upload

api_router = APIRouter()
api_router.include_router(upload.router, tags=["upload"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(concepts.router, prefix="/concepts", tags=["concepts"])
api_router.include_router(keywords.router, prefix="/keywords", tags=["keywords"])
