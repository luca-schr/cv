from fastapi import APIRouter

from app.services.llm import check_ollama_status, load_llm_config

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/status")
def llm_status():
    return check_ollama_status()


@router.get("/config")
def llm_config():
    return load_llm_config()
