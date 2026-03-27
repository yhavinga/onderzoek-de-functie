"""Core SymPy analysis engine voor wiskundige functie analyse."""

from sympy import (
    Symbol,
    sympify,
    diff,
    solve,
    latex,
    N,
    oo,
    Abs,
    sin,
    cos,
    tan,
    log,
    exp,
    sqrt,
    pi,
    E,
    Function,
)
from sympy.core.numbers import Float, Integer, Rational
from sympy.calculus.util import continuous_domain
from sympy.sets import Interval, Union, FiniteSet
from sympy.printing.latex import LatexPrinter
import re
import multiprocessing as mp

from backend.models import Analyse, CritischPunt


x = Symbol("x", real=True)
SOLVE_TIMEOUT = 1.0  # seconden


# Nederlandse/Europese/ISO notatie: ln = base e, log = base 10
class ln(Function):
    """Natuurlijke logaritme (base e) - Nederlandse notatie."""

    @classmethod
    def eval(cls, arg):
        return log(arg)


class log10(Function):
    """Logaritme base 10 - voor interne representatie."""

    @classmethod
    def eval(cls, arg):
        return log(arg) / log(10)


class DutchLatexPrinter(LatexPrinter):
    """LaTeX printer met Nederlandse/ISO notatie voor logaritmes."""

    def _print_log(self, expr):
        # SymPy's log is natural log, output as \ln
        if len(expr.args) == 1:
            return r"\ln\left(%s\right)" % self._print(expr.args[0])
        else:
            # log with base: log(x, base)
            base = expr.args[1]
            if base == 10:
                return r"\log\left(%s\right)" % self._print(expr.args[0])
            return r"\log_{%s}\left(%s\right)" % (
                self._print(base),
                self._print(expr.args[0]),
            )

    def _print_Mul(self, expr):
        # Check for log(x)/log(10) pattern which is log base 10
        from sympy import Mul, Pow, Integer
        numer, denom = expr.as_numer_denom()
        if (
            denom.func == log
            and len(denom.args) == 1
            and denom.args[0] == 10
            and numer.func == log
            and len(numer.args) == 1
        ):
            return r"\log\left(%s\right)" % self._print(numer.args[0])
        # Check for 1/(x*log(10)) pattern which is derivative of log base 10
        if (
            expr.is_Mul
            and any(
                isinstance(arg, Pow) and arg.exp == -1 and arg.base.func == log and arg.base.args[0] == 10
                for arg in expr.args
                if isinstance(arg, Pow)
            )
        ):
            # Rewrite as 1/(x * ln(10)) pattern
            new_args = []
            for arg in expr.args:
                if isinstance(arg, Pow) and arg.exp == -1 and arg.base.func == log and arg.base.args[0] == 10:
                    new_args.append(Pow(log(10), -1))
                else:
                    new_args.append(arg)
            return super()._print_Mul(Mul(*new_args))
        return super()._print_Mul(expr)


def dutch_latex(expr):
    """Generate LaTeX met Nederlandse/ISO notatie."""
    return DutchLatexPrinter().doprint(expr)


def _solve_worker(expr_str, queue):
    """Worker functie voor multiprocessing solve."""
    x = Symbol("x", real=True)
    expr = sympify(expr_str, locals={"x": x})
    result = solve(expr, x)
    queue.put(result)


def _solve_met_timeout(expr, var, timeout: float = SOLVE_TIMEOUT) -> list:
    """Wrapper rond solve() met echte timeout via multiprocessing."""
    queue = mp.Queue()
    expr_str = str(expr)
    proc = mp.Process(target=_solve_worker, args=(expr_str, queue))
    proc.start()
    proc.join(timeout=timeout)

    if proc.is_alive():
        proc.terminate()
        proc.join()
        return []

    if not queue.empty():
        return queue.get()
    return []

# Toegestane functies voor veilige parsing
# Nederlandse/ISO notatie: ln = natural log (base e), log = log base 10
TOEGESTANE_FUNCTIES = {
    "sin": sin,
    "cos": cos,
    "tan": tan,
    "ln": log,  # ln(x) -> natural log
    "log": lambda arg: log(arg, 10),  # log(x) -> log base 10
    "exp": exp,
    "sqrt": sqrt,
    "abs": Abs,
    "pi": pi,
    "e": E,
}


def _normaliseer_input(expr_str: str) -> str:
    """Normaliseer input naar SymPy-compatibele syntax."""
    # Vervang ^ door ** voor machten
    expr_str = expr_str.replace("^", "**")
    # Voeg * toe tussen getal en x (bijv. 2x -> 2*x)
    expr_str = re.sub(r"(\d)([a-zA-Z])", r"\1*\2", expr_str)
    # Voeg * toe tussen ) en ( of ) en variabele
    expr_str = re.sub(r"\)(\()", r")*\1", expr_str)
    expr_str = re.sub(r"\)([a-zA-Z])", r")*\1", expr_str)
    return expr_str


def _naar_float(waarde) -> float | None:
    """Converteer SymPy waarde naar float, filter complexe getallen."""
    try:
        if waarde.is_real is False:
            return None
        float_val = float(N(waarde))
        if abs(float_val) > 1e10:  # Filter extreme waarden
            return None
        return float_val
    except (TypeError, ValueError, AttributeError):
        return None


def _filter_reeel(oplossingen: list) -> list[float]:
    """Filter alleen reële oplossingen en converteer naar floats."""
    resultaat = []
    for opl in oplossingen:
        val = _naar_float(opl)
        if val is not None:
            resultaat.append(round(val, 6))
    return sorted(set(resultaat))


def _bepaal_domein(f, kritieke_punten: list[float], x_bereik: tuple | None) -> tuple[float, float]:
    """Bepaal een geschikt x-bereik voor de grafiek."""
    if x_bereik:
        return x_bereik

    if not kritieke_punten:
        return (-10.0, 10.0)

    x_min = min(kritieke_punten)
    x_max = max(kritieke_punten)

    # Voeg padding toe
    breedte = max(x_max - x_min, 2.0)
    padding = breedte * 0.3

    return (round(x_min - padding, 2), round(x_max + padding, 2))


def analyseer(expr_str: str, x_bereik: tuple[float, float] | None = None) -> Analyse:
    """
    Analyseer een wiskundige functie volledig.

    Parameters:
        expr_str: De functie als string (bijv. "x^4 - 30x^2")
        x_bereik: Optioneel (x_min, x_max) bereik voor de grafiek

    Returns:
        Analyse object met alle resultaten en stap-voor-stap uitleg
    """
    stappen = []

    # Stap 1: Parse en valideer input
    genormaliseerd = _normaliseer_input(expr_str)
    stappen.append(f"Stap 1: Functie parsen")
    stappen.append(f"  Input: f(x) = {expr_str}")

    try:
        f = sympify(genormaliseerd, locals={"x": x, **TOEGESTANE_FUNCTIES})
    except Exception as e:
        raise ValueError(f"Ongeldige functie: {e}")

    f_latex = dutch_latex(f)
    stappen.append(f"  LaTeX: f(x) = {f_latex}")

    # Stap 2: Bereken afgeleiden
    stappen.append("")
    stappen.append("Stap 2: Afgeleiden berekenen")

    f1 = diff(f, x)
    f2 = diff(f1, x)
    f3 = diff(f2, x)

    afgeleiden = {
        "f'": dutch_latex(f1),
        "f''": dutch_latex(f2),
        "f'''": dutch_latex(f3),
    }

    stappen.append(f"  f'(x) = {dutch_latex(f1)}")
    stappen.append(f"  f''(x) = {dutch_latex(f2)}")
    stappen.append(f"  f'''(x) = {dutch_latex(f3)}")

    # Stap 3: Vind nulpunten (f = 0)
    stappen.append("")
    stappen.append("Stap 3: Nulpunten vinden (f(x) = 0)")

    try:
        nulpunten_sym = _solve_met_timeout(f, x)
        nulpunten = _filter_reeel(nulpunten_sym)
    except Exception:
        nulpunten = []

    if nulpunten:
        nulpunten_str = ", ".join([f"x = {n}" for n in nulpunten])
        stappen.append(f"  Oplossingen: {nulpunten_str}")
    else:
        stappen.append("  Geen reële nulpunten gevonden (of timeout)")

    # Stap 4: Vind kritieke punten (f' = 0)
    stappen.append("")
    stappen.append("Stap 4: Kritieke punten vinden (f'(x) = 0)")

    try:
        kritieke_sym = _solve_met_timeout(f1, x)
        kritieke_x = _filter_reeel(kritieke_sym)
    except Exception:
        kritieke_x = []

    if kritieke_x:
        kritieke_str = ", ".join([f"x = {k}" for k in kritieke_x])
        stappen.append(f"  Oplossingen: {kritieke_str}")
    else:
        stappen.append("  Geen kritieke punten gevonden (of timeout)")

    # Stap 5: Classificeer extrema met tweede afgeleide test
    stappen.append("")
    stappen.append("Stap 5: Extrema classificeren (tweede afgeleide test)")

    extrema = []
    for x_val in kritieke_x:
        try:
            y_val = _naar_float(f.subs(x, x_val))
            f2_val = _naar_float(f2.subs(x, x_val))

            if y_val is None:
                continue

            if f2_val is not None and abs(f2_val) > 1e-10:
                if f2_val > 0:
                    punt_type = "minimum"
                    uitleg = f"f''({x_val}) = {round(f2_val, 4)} > 0 → lokaal minimum"
                else:
                    punt_type = "maximum"
                    uitleg = f"f''({x_val}) = {round(f2_val, 4)} < 0 → lokaal maximum"

                extrema.append(
                    CritischPunt(
                        x=round(x_val, 6),
                        y=round(y_val, 6),
                        type=punt_type,
                        uitleg=uitleg,
                    )
                )
                stappen.append(f"  ({round(x_val, 4)}, {round(y_val, 4)}): {uitleg}")
            else:
                # f'' = 0, gebruik hogere afgeleide of numerieke methode
                f3_val = _naar_float(f3.subs(x, x_val))
                if f3_val is not None and abs(f3_val) > 1e-10:
                    stappen.append(
                        f"  ({round(x_val, 4)}, {round(y_val, 4)}): f''=0, f'''≠0 → buigpunt (geen extremum)"
                    )
                else:
                    stappen.append(
                        f"  ({round(x_val, 4)}, {round(y_val, 4)}): f''=0, verdere analyse nodig"
                    )

        except Exception:
            continue

    if not extrema:
        stappen.append("  Geen extrema gevonden")

    # Stap 6: Vind buigpunten (f'' = 0)
    stappen.append("")
    stappen.append("Stap 6: Buigpunten vinden (f''(x) = 0)")

    try:
        buig_sym = _solve_met_timeout(f2, x)
        buig_x = _filter_reeel(buig_sym)
    except Exception:
        buig_x = []

    buigpunten = []
    for x_val in buig_x:
        try:
            y_val = _naar_float(f.subs(x, x_val))
            f3_val = _naar_float(f3.subs(x, x_val))

            if y_val is None:
                continue

            # Controleer tekenverandering van f''
            eps = 0.01
            f2_links = _naar_float(f2.subs(x, x_val - eps))
            f2_rechts = _naar_float(f2.subs(x, x_val + eps))

            if f2_links is not None and f2_rechts is not None:
                if f2_links * f2_rechts < 0:  # Tekenverandering
                    if f2_links < 0:
                        uitleg = f"f'' wisselt van negatief naar positief → buigpunt (concaaf → convex)"
                    else:
                        uitleg = f"f'' wisselt van positief naar negatief → buigpunt (convex → concaaf)"

                    buigpunten.append(
                        CritischPunt(
                            x=round(x_val, 6),
                            y=round(y_val, 6),
                            type="buigpunt",
                            uitleg=uitleg,
                        )
                    )
                    stappen.append(f"  ({round(x_val, 4)}, {round(y_val, 4)}): {uitleg}")
                else:
                    stappen.append(
                        f"  x = {round(x_val, 4)}: f''=0 maar geen tekenverandering → geen buigpunt"
                    )

        except Exception:
            continue

    if not buigpunten:
        stappen.append("  Geen buigpunten gevonden")

    # Bepaal domein voor grafiek
    alle_kritieke = nulpunten + [e.x for e in extrema] + [b.x for b in buigpunten]
    domein = _bepaal_domein(f, alle_kritieke, x_bereik)

    return Analyse(
        functie=expr_str,
        f_latex=f_latex,
        afgeleiden=afgeleiden,
        nulpunten=nulpunten,
        extrema=extrema,
        buigpunten=buigpunten,
        domein=domein,
        stappen=stappen,
    )
