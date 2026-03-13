"""Matplotlib visualization voor functie analyse."""

import io
import base64

import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
from sympy import Symbol, sympify, lambdify, latex

from backend.models import Analyse
from backend.analyzer import TOEGESTANE_FUNCTIES, _normaliseer_input


x = Symbol("x", real=True)


def genereer_grafiek(
    analyse: Analyse,
    toon_afgeleiden: list[str] | None = None,
    formaat: str = "png",
    dpi: int = 150,
) -> str:
    """
    Genereer grafiek als base64 encoded image.

    Parameters:
        analyse: Analyse object met functie data
        toon_afgeleiden: Welke afgeleiden tonen ["f'", "f''", "f'''"]
        formaat: Output formaat ("png" of "svg")
        dpi: Resolutie (default 150 voor web)

    Returns:
        Data URI voor direct in <img src="...">
    """
    if toon_afgeleiden is None:
        toon_afgeleiden = []

    # Parse de originele functie (gebruik dezelfde normalisatie als analyzer)
    expr_str = _normaliseer_input(analyse.functie)
    f = sympify(expr_str, locals={"x": x, **TOEGESTANE_FUNCTIES})

    # Maak numpy-compatible functies
    f_np = lambdify(x, f, modules=["numpy"])

    # Genereer x-waarden
    x_min, x_max = analyse.domein
    x_vals = np.linspace(x_min, x_max, 1000)

    # Bereken y-waarden met foutafhandeling
    with np.errstate(divide="ignore", invalid="ignore"):
        y_vals = f_np(x_vals)
        y_vals = np.where(np.isfinite(y_vals), y_vals, np.nan)

    # Setup figuur
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor("white")

    # Kleuren voor curves
    kleuren = {
        "f": "#2563eb",   # Blauw
        "f'": "#dc2626",  # Rood
        "f''": "#16a34a", # Groen
        "f'''": "#9333ea", # Paars
    }

    # Plot hoofdfunctie
    ax.plot(x_vals, y_vals, color=kleuren["f"], linewidth=2, label=f"f(x) = ${analyse.f_latex}$")

    # Plot afgeleiden indien gewenst
    from sympy import diff
    f_current = f
    afgeleide_namen = ["f'", "f''", "f'''"]

    for i, naam in enumerate(afgeleide_namen):
        f_current = diff(f_current, x)
        if naam in toon_afgeleiden:
            try:
                f_afgeleide_np = lambdify(x, f_current, modules=["numpy"])
                y_afgeleide = f_afgeleide_np(x_vals)
                y_afgeleide = np.where(np.isfinite(y_afgeleide), y_afgeleide, np.nan)
                ax.plot(
                    x_vals,
                    y_afgeleide,
                    color=kleuren[naam],
                    linewidth=1.5,
                    linestyle="--",
                    label=f"{naam}(x) = ${analyse.afgeleiden[naam]}$",
                )
            except Exception:
                pass

    # Plot kritieke punten
    for extremum in analyse.extrema:
        marker = "^" if extremum.type == "minimum" else "v"
        kleur = "#16a34a" if extremum.type == "minimum" else "#dc2626"
        ax.plot(
            extremum.x,
            extremum.y,
            marker=marker,
            markersize=12,
            color=kleur,
            markeredgecolor="white",
            markeredgewidth=2,
            zorder=5,
        )
        ax.annotate(
            f"({extremum.x:.2f}, {extremum.y:.2f})\n{extremum.type}",
            xy=(extremum.x, extremum.y),
            xytext=(10, 10 if extremum.type == "minimum" else -25),
            textcoords="offset points",
            fontsize=9,
            color=kleur,
            fontweight="bold",
        )

    # Plot buigpunten
    for buig in analyse.buigpunten:
        ax.plot(
            buig.x,
            buig.y,
            marker="o",
            markersize=10,
            color="#f59e0b",
            markeredgecolor="white",
            markeredgewidth=2,
            zorder=5,
        )
        ax.annotate(
            f"({buig.x:.2f}, {buig.y:.2f})\nbuigpunt",
            xy=(buig.x, buig.y),
            xytext=(10, -20),
            textcoords="offset points",
            fontsize=9,
            color="#f59e0b",
            fontweight="bold",
        )

    # Plot nulpunten
    for nul in analyse.nulpunten:
        ax.plot(
            nul,
            0,
            marker="o",
            markersize=8,
            color="#6366f1",
            markeredgecolor="white",
            markeredgewidth=2,
            zorder=5,
        )

    # Styling
    ax.axhline(y=0, color="black", linewidth=0.5)
    ax.axvline(x=0, color="black", linewidth=0.5)
    ax.grid(True, alpha=0.3, linestyle="-", linewidth=0.5)

    ax.set_xlabel("x", fontsize=12)
    ax.set_ylabel("y", fontsize=12)
    ax.set_title(f"Analyse van f(x) = ${analyse.f_latex}$", fontsize=14, fontweight="bold")

    # Bepaal y-bereik slim
    valid_y = y_vals[np.isfinite(y_vals)]
    if len(valid_y) > 0:
        y_min, y_max = np.percentile(valid_y, [2, 98])
        y_padding = (y_max - y_min) * 0.1
        ax.set_ylim(y_min - y_padding, y_max + y_padding)

    ax.legend(loc="upper right", fontsize=10)

    plt.tight_layout()

    # Exporteer naar base64
    buffer = io.BytesIO()
    fig.savefig(buffer, format=formaat, dpi=dpi, facecolor="white", edgecolor="none")
    buffer.seek(0)
    plt.close(fig)

    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    mime_type = "image/png" if formaat == "png" else "image/svg+xml"

    return f"data:{mime_type};base64,{image_base64}"
