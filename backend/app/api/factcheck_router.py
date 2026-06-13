from fastapi import APIRouter, HTTPException
from app.models.factcheck_schemas import FactCheckRequest, FactCheckResponse, FactCheckSource
from app.services.factcheck_service import analyze_with_gemini_grounding

router = APIRouter()

@router.post(
    "/factcheck", 
    response_model=FactCheckResponse, 
    tags=["Fact-checking"],
    summary="Zweryfikuj prawdziwość stwierdzenia"
)
async def fact_check_endpoint(payload: FactCheckRequest):
    statement = payload.statement.strip()
    if len(statement) < 10:
        raise HTTPException(status_code=400, detail="Tekst do weryfikacji musi mieć co najmniej 10 znaków.")

    # Wywołujemy usługę integrującą Google Search i Gemini
    analysis = await analyze_with_gemini_grounding(statement)
    
    # Konwersja słowników na obiekty Pydantic
    formatted_sources = []
    for s in analysis.get("sources", []):
        formatted_sources.append(FactCheckSource(
            title=s["title"],
            url=s["url"],
            snippet=s["snippet"]
        ))
        
    return FactCheckResponse(
        verdict=analysis.get("verdict", "SPORNE"),
        explanation=analysis.get("explanation", "Brak szczegółowego uzasadnienia."),
        confidence=analysis.get("confidence", 0.5),
        sources=formatted_sources
    )