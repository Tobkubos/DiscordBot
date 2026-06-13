from fastapi import APIRouter, HTTPException
from app.models.factcheck_schemas import FactCheckRequest, FactCheckResponse, FactCheckSource
from app.services.factcheck_service import search_web, analyze_with_gemini

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

    # 1. Przeszukiwanie sieci
    web_results = search_web(statement, max_results=5)
    if not web_results:
        return FactCheckResponse(
            verdict="SPORNE",
            explanation="Wyszukiwarka nie zwróciła żadnych wyników w internecie dla tego stwierdzenia, co uniemożliwia weryfikację.",
            confidence=0.0,
            sources=[]
        )

    # 2. Analiza przez LLM
    analysis = await analyze_with_gemini(statement, web_results)

    # 3. Przypisanie źródeł na podstawie decyzji LLM
    used_indices = analysis.get("sources_used_indices", [])
    used_sources = []
    
    for idx in used_indices:
        source_idx = idx - 1  # Korekta indeksu (model liczy od 1)
        if 0 <= source_idx < len(web_results):
            r = web_results[source_idx]
            used_sources.append(FactCheckSource(
                title=r["title"],
                url=r["url"],
                snippet=r["snippet"]
            ))

    # Jeśli model nie wskazał konkretnych indeksów, dajemy top 3 znalezione źródła
    if not used_sources:
        used_sources = [
            FactCheckSource(title=r["title"], url=r["url"], snippet=r["snippet"])
            for r in web_results[:3]
        ]

    return FactCheckResponse(
        verdict=analysis.get("verdict", "SPORNE"),
        explanation=analysis.get("explanation", "Brak szczegółowego uzasadnienia."),
        confidence=analysis.get("confidence", 0.5),
        sources=used_sources
    )