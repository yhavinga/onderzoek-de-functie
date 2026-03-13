"""Pydantic models voor de Functie Analysator API."""

from pydantic import BaseModel, Field


class CritischPunt(BaseModel):
    """Een kritiek punt (extremum of buigpunt) van een functie."""

    x: float
    y: float
    type: str  # "maximum", "minimum", "buigpunt"
    uitleg: str  # Stap-voor-stap uitleg


class Analyse(BaseModel):
    """Volledige analyse van een wiskundige functie."""

    functie: str  # Originele input
    f_latex: str  # LaTeX representatie
    afgeleiden: dict[str, str]  # {"f'": "4x³-60x", "f''": "12x²-60", ...}
    nulpunten: list[float]
    extrema: list[CritischPunt]
    buigpunten: list[CritischPunt]
    domein: tuple[float, float]
    stappen: list[str]  # Educatieve uitleg


class AnalyseRequest(BaseModel):
    """Request model voor /api/analyseer endpoint."""

    functie: str = Field(..., description="Wiskundige functie om te analyseren")
    x_min: float | None = Field(None, description="Minimum x-waarde voor grafiek")
    x_max: float | None = Field(None, description="Maximum x-waarde voor grafiek")
    toon_afgeleiden: list[str] = Field(
        default_factory=list,
        description="Welke afgeleiden tonen: [\"f'\", \"f''\", \"f'''\"]",
    )


class AnalyseResponse(BaseModel):
    """Response model voor /api/analyseer endpoint."""

    analyse: Analyse
    grafiek: str  # Base64 encoded PNG
    stappen: list[str]
