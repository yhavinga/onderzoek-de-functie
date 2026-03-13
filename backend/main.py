"""FastAPI backend voor de Functie Analysator."""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from backend.models import AnalyseRequest, AnalyseResponse
from backend.analyzer import analyseer
from backend.plotter import genereer_grafiek


app = FastAPI(
    title="Functie Analysator",
    description="Analyseer wiskundige functies met afgeleiden, extrema en buigpunten",
    version="1.0.0",
)

# CORS voor lokale ontwikkeling
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/analyseer", response_model=AnalyseResponse)
async def analyseer_functie(req: AnalyseRequest):
    """
    Analyseer een wiskundige functie.

    Berekent:
    - Eerste, tweede en derde afgeleide
    - Nulpunten
    - Extrema (maxima en minima)
    - Buigpunten
    - Grafiek met optionele afgeleiden overlay
    """
    try:
        # Bepaal x-bereik indien opgegeven
        x_bereik = None
        if req.x_min is not None and req.x_max is not None:
            x_bereik = (req.x_min, req.x_max)

        # Voer analyse uit
        analyse = analyseer(req.functie, x_bereik)

        # Genereer grafiek
        grafiek = genereer_grafiek(analyse, req.toon_afgeleiden)

        return AnalyseResponse(
            analyse=analyse,
            grafiek=grafiek,
            stappen=analyse.stappen,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analyse mislukt: {str(e)}",
        )


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


# Serve static frontend files
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
