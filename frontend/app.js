/**
 * Functie Analysator - Frontend Logic
 * Vanilla JavaScript, geen frameworks
 */

const API_URL = 'api/analyseer';

/**
 * Start de analyse van de ingevoerde functie.
 */
async function analyseer() {
    const functieInput = document.getElementById('functie');
    const functie = functieInput.value.trim();

    if (!functie) {
        toonError('Voer een functie in om te analyseren.');
        return;
    }

    // Verzamel opties
    const toonAfgeleiden = [];
    if (document.getElementById('show-f1').checked) toonAfgeleiden.push("f'");
    if (document.getElementById('show-f2').checked) toonAfgeleiden.push("f''");
    if (document.getElementById('show-f3').checked) toonAfgeleiden.push("f'''");

    const xMinInput = document.getElementById('x-min');
    const xMaxInput = document.getElementById('x-max');
    const xMin = xMinInput.value ? parseFloat(xMinInput.value) : null;
    const xMax = xMaxInput.value ? parseFloat(xMaxInput.value) : null;

    // Toon loading state
    toonLoading(true);
    verbergError();
    verbergResultaat();

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                functie: functie,
                x_min: xMin,
                x_max: xMax,
                toon_afgeleiden: toonAfgeleiden,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Analyse mislukt');
        }

        const data = await response.json();
        toonResultaat(data);

    } catch (error) {
        toonError(error.message);
    } finally {
        toonLoading(false);
    }
}

/**
 * Toon de analyse resultaten.
 */
function toonResultaat(data) {
    const { analyse, grafiek, stappen } = data;

    // Grafiek
    document.getElementById('grafiek').src = grafiek;

    // Afgeleiden
    const afgeleidenDiv = document.getElementById('afgeleiden');
    afgeleidenDiv.innerHTML = `
        <p><strong>f'(x)</strong> = ${renderLatex(analyse.afgeleiden["f'"])}</p>
        <p><strong>f''(x)</strong> = ${renderLatex(analyse.afgeleiden["f''"])}</p>
        <p><strong>f'''(x)</strong> = ${renderLatex(analyse.afgeleiden["f'''"])}</p>
    `;

    // Nulpunten
    const nulpuntenDiv = document.getElementById('nulpunten');
    if (analyse.nulpunten.length > 0) {
        nulpuntenDiv.innerHTML = analyse.nulpunten
            .map(n => `<p>x = ${formatGetal(n)}</p>`)
            .join('');
    } else {
        nulpuntenDiv.innerHTML = '<p class="muted">Geen reële nulpunten</p>';
    }

    // Extrema
    const extremaDiv = document.getElementById('extrema');
    if (analyse.extrema.length > 0) {
        extremaDiv.innerHTML = analyse.extrema
            .map(e => `
                <div class="punt ${e.type}">
                    <div class="punt-type">${e.type}</div>
                    <div class="punt-coords">(${formatGetal(e.x)}, ${formatGetal(e.y)})</div>
                    <div class="punt-uitleg">${e.uitleg}</div>
                </div>
            `)
            .join('');
    } else {
        extremaDiv.innerHTML = '<p class="muted">Geen extrema gevonden</p>';
    }

    // Buigpunten
    const buigpuntenDiv = document.getElementById('buigpunten');
    if (analyse.buigpunten.length > 0) {
        buigpuntenDiv.innerHTML = analyse.buigpunten
            .map(b => `
                <div class="punt buigpunt">
                    <div class="punt-type">buigpunt</div>
                    <div class="punt-coords">(${formatGetal(b.x)}, ${formatGetal(b.y)})</div>
                    <div class="punt-uitleg">${b.uitleg}</div>
                </div>
            `)
            .join('');
    } else {
        buigpuntenDiv.innerHTML = '<p class="muted">Geen buigpunten gevonden</p>';
    }

    // Stappen (met LaTeX rendering)
    const stappenHtml = stappen
        .map(stap => wrapLatexInStap(stap))
        .join('<br>');
    document.getElementById('stappen').innerHTML = stappenHtml;

    // Toon resultaat sectie
    document.getElementById('resultaat').classList.remove('hidden');

    // Render KaTeX in afgeleiden en stappen
    if (typeof renderMathInElement === 'function') {
        const katexOptions = {
            delimiters: [
                { left: '$$', right: '$$', display: true },
                { left: '$', right: '$', display: false },
            ],
            throwOnError: false,
        };
        renderMathInElement(document.getElementById('afgeleiden'), katexOptions);
        renderMathInElement(document.getElementById('stappen'), katexOptions);
    } else {
        console.error('KaTeX renderMathInElement not loaded');
    }
}

/**
 * Wrap LaTeX expressies in een stap met $ delimiters.
 */
function wrapLatexInStap(stap) {
    // Bewaar leading spaces als &nbsp;
    const leadingSpaces = stap.match(/^(\s*)/)[1];
    const indent = leadingSpaces.replace(/ /g, '&nbsp;');
    stap = stap.trimStart();

    // Escape HTML
    stap = stap.replace(/</g, '&lt;').replace(/>/g, '&gt;');

    // Detecteer "f'(x) = ..." of "f''(x) = ..." patronen en wrap de LaTeX
    stap = stap.replace(
        /(f['′]{1,3}\(x\)\s*=\s*)(.+)$/,
        (match, prefix, latex) => `${prefix}$${latex}$`
    );

    // Detecteer "LaTeX: f(x) = ..." patroon
    stap = stap.replace(
        /(LaTeX:\s*f\(x\)\s*=\s*)(.+)$/,
        (match, prefix, latex) => `${prefix}$${latex}$`
    );

    return indent + stap;
}

/**
 * Converteer LaTeX string naar KaTeX-ready format.
 */
function renderLatex(latex) {
    return `$${latex}$`;
}

/**
 * Format een getal netjes.
 */
function formatGetal(n) {
    if (Number.isInteger(n)) {
        return n.toString();
    }
    // Rond af op 4 decimalen, verwijder trailing zeros
    return parseFloat(n.toFixed(4)).toString();
}

/**
 * Toon of verberg loading indicator.
 */
function toonLoading(show) {
    const loading = document.getElementById('loading');
    const button = document.getElementById('analyseer-btn');

    if (show) {
        loading.classList.remove('hidden');
        button.disabled = true;
    } else {
        loading.classList.add('hidden');
        button.disabled = false;
    }
}

/**
 * Toon error bericht.
 */
function toonError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

/**
 * Verberg error bericht.
 */
function verbergError() {
    document.getElementById('error').classList.add('hidden');
}

/**
 * Verberg resultaat sectie.
 */
function verbergResultaat() {
    document.getElementById('resultaat').classList.add('hidden');
}

/**
 * Stel een voorbeeldfunctie in.
 */
function setVoorbeeld(functie) {
    document.getElementById('functie').value = functie;
    analyseer();
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    // Enter toets om te analyseren
    document.getElementById('functie').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            analyseer();
        }
    });

    // Checkbox changes triggeren re-analyse indien resultaat zichtbaar is
    ['show-f1', 'show-f2', 'show-f3'].forEach(id => {
        document.getElementById(id).addEventListener('change', () => {
            if (!document.getElementById('resultaat').classList.contains('hidden')) {
                analyseer();
            }
        });
    });
});
