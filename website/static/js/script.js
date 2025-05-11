document.addEventListener('DOMContentLoaded', function() {
    // acest cod ruleaza dupa ce toata pagina html a fost incarcata si procesata de browser
    console.log("DOM fully loaded and parsed.");

    // --- functie ajutatoare pentru a lua valorile variabilelor css ---
    // variablename este numele variabilei css (ex: '--primary-text-color')
    // fallbackvalue este o valoare default daca variabila css nu este gasita
    function getCssVariable(variableName, fallbackValue) {
        // getcomputedstyle(document.documentelement) ia toate stilurile aplicate pe elementul radacina (html)
        // getpropertyvalue(variablename) ia valoarea specifica a variabilei
        const value = getComputedStyle(document.documentElement).getPropertyValue(variableName).trim(); // .trim() elimina spatiile goale de la inceput/sfarsit
        return value || fallbackValue; // returneaza valoarea gasita sau valoarea de fallback
    }

    // --- initializarea indicatorului (gauge) ---
    console.log("Attempting to initialize Gauge...");
    const gaugeTarget = document.getElementById('fearGreedGauge'); // gasim elementul canvas din html unde va fi desenat gauge-ul

    // verificam daca elementul canvas exista, daca biblioteca gauge.js este incarcata si daca avem datele pentru gauge
    // 'feargreeddata' este o variabila javascript care ar trebui definita in fisierul html, primind valoarea de la flask
    if (gaugeTarget && typeof Gauge !== 'undefined' && typeof fearGreedData !== 'undefined') {
        console.log("Gauge element, library, and data found.");
        // optiuni de configurare pentru aspectul si comportamentul gauge-ului
        const opts = {
            angle: -0.2, // unghiul de start al arcului gauge-ului
            lineWidth: 0.2, // grosimea liniei arcului
            radiusScale: 0.9, // cat de mare sa fie raza gauge-ului fata de container
            pointer: { length: 0.5, strokeWidth: 0.045, color: getCssVariable('--primary-text-color', '#e0e0e0') }, // stilul acului indicator
            limitMax: false, // daca sa arate o limita maxima
            limitMin: false, // daca sa arate o limita minima
            colorStart: '#6FADCF', // culoare de start pentru gradient (daca e folosit)
            colorStop: '#8FC0DA',  // culoare de stop pentru gradient
            strokeColor: getCssVariable('--card-bg-color', '#1a1a1e'), // culoarea fundalului arcului (partea necompletata)
            generateGradient: true, // daca sa genereze un gradient pentru arcul activ
            highDpiSupport: true, // suport pentru ecrane cu densitate mare de pixeli
            staticZones: [ // definim zonele colorate ale gauge-ului
                           // fiecare zona are o culoare ('strokestyle') si un interval (min, max)
               {strokeStyle: getCssVariable('--accent-red', "#ef4444"), min: 0, max: 25},   // rosu pentru "extreme fear"
               {strokeStyle: getCssVariable('--accent-orange', "#f59e0b"), min: 25, max: 45},  // portocaliu pentru "fear"
               {strokeStyle: getCssVariable('--secondary-text-color', "#6b7280"), min: 45, max: 55},  // gri pentru "neutral"
               {strokeStyle: getCssVariable('--accent-green', "#84cc16"), min: 55, max: 75},  // verde deschis pentru "greed"
               {strokeStyle: getCssVariable('--accent-green', "#22c55e"), min: 75, max: 100}  // verde inchis pentru "extreme greed"
            ],
            renderTicks: { // optiuni pentru gradatiile (liniutele) de pe gauge
                divisions: 5, divWidth: 0.8, divLength: 0.5, divColor: getCssVariable('--border-color', '#4a4a6e'),
                subDivisions: 4, subLength: 0.3, subWidth: 0.4, subColor: getCssVariable('--border-color', '#3a3a5e')
            }
        };
        try {
            const gauge = new Gauge(gaugeTarget).setOptions(opts); // cream un nou obiect gauge cu optiunile definite
            gauge.maxValue = 100; // valoarea maxima a gauge-ului
            gauge.setMinValue(0);  // valoarea minima
            gauge.animationSpeed = 32; // viteza animatiei cand se schimba valoarea

            // setam valoarea initiala a gauge-ului
            if (typeof fearGreedData === 'number' && !isNaN(fearGreedData)) { // verificam daca feargreeddata e un numar valid
                console.log("Setting Gauge value to:", fearGreedData);
                gauge.set(fearGreedData); // setam valoarea
            } else { // daca datele nu sunt valide
                 console.warn("Invalid or missing fearGreedData for gauge. Setting to default 50. Value was:", fearGreedData);
                gauge.set(50); // setam o valoare default (ex: neutru)
            }
            console.log("Gauge initialized successfully.");
        } catch (error) { // prindem orice eroare la initializarea gauge-ului
             console.error("Error initializing gauge:", error);
        }
    } else { // daca lipseste ceva necesar pentru gauge
        if (!gaugeTarget) console.error("Gauge canvas element 'fearGreedGauge' NOT FOUND!");
        if (typeof Gauge === 'undefined') console.error("Gauge.js library NOT LOADED!");
        if (typeof fearGreedData === 'undefined') console.error("Global variable 'fearGreedData' NOT FOUND!");
    }

    // --- initializarea graficelor (charts) ---
    console.log("Attempting to initialize Charts...");
    // verificam daca biblioteca chart.js este incarcata si daca avem datele necesare (timestamps, valori f&g, valori vix)
    // 'historytimestamps', 'historyfgvalues', 'historyvixvalues' sunt variabile javascript care ar trebui definite in html
    if (typeof Chart !== 'undefined' &&
        typeof historyTimestamps !== 'undefined' && Array.isArray(historyTimestamps) &&
        typeof historyFgValues !== 'undefined' && Array.isArray(historyFgValues) &&
        typeof historyVixValues !== 'undefined' && Array.isArray(historyVixValues))
    {
        console.log("Chart.js library and data arrays found.");

        // gasim elementele canvas din html unde vor fi desenate graficele
        const fgChartCtx = document.getElementById('fgHistoryChart')?.getContext('2d'); // pentru graficul f&g
        const vixChartCtx = document.getElementById('vixHistoryChart')?.getContext('2d'); // pentru graficul vix

        // continuam doar daca avem date de afisat in grafice
        if (historyTimestamps.length > 0 && (historyFgValues.length > 0 || historyVixValues.length > 0)) {
            console.log("Sufficient data found for charts.");

            // preluam culorile din variabilele css pentru a le folosi in grafice
            const chartTextColor = getCssVariable('--secondary-text-color', '#a0aec0');
            const chartGridColor = getCssVariable('--border-color', '#2a2d35');
            const chartLegendColor = getCssVariable('--primary-text-color', '#e8e8eb');
            const accentGreen = getCssVariable('--accent-green', '#22c55e');
            const accentBlue = getCssVariable('--accent-blue', '#38bdf8');
            const cardBgColor = getCssVariable('--card-bg-color', '#16181d'); // pentru fundalul tooltip-ului

            // optiuni comune pentru ambele grafice
            const commonChartOptions = {
                 responsive: true, // graficul se va redimensiona automat cu fereastra
                 maintainAspectRatio: false, // nu pastram un raport fix latime/inaltime, util pentru responsive
                 animation: { duration: 800, easing: 'easeInOutQuart' }, // animatie la incarcare/actualizare
                 scales: { // configurarea axelor
                     x: { // axa x (timpul)
                         ticks: { color: chartTextColor, maxRotation: 0, autoSkip: true, maxTicksLimit: 8, padding: 10 }, // stilul etichetelor de pe axa x
                         grid: { color: chartGridColor, display: false }, // liniile de grila verticale (le ascundem)
                         border: { display: true, color: chartGridColor } // linia axei x
                     },
                     y: { // axa y (valorile)
                         ticks: { color: chartTextColor, padding: 10, precision: 0 }, // stilul etichetelor de pe axa y, fara zecimale
                         grid: { color: chartGridColor, borderDash: [3, 3], drawBorder: false, zeroLineColor: chartGridColor, zeroLineWidth: 1 }, // linii de grila orizontale punctate
                         beginAtZero: false, // axa y nu incepe neaparat de la zero
                         border: { display: true, color: chartGridColor } // linia axei y
                     }
                 },
                 plugins: { // plugin-uri chart.js
                     legend: { // legenda graficului (ex: "fear & greed index")
                         labels: { color: chartLegendColor, font: { size: 13 }, boxWidth: 12, padding: 20 }
                     },
                     tooltip: { // casuta care apare la hover pe un punct din grafic
                         enabled: true,
                         backgroundColor: cardBgColor, // fundalul tooltip-ului
                         titleColor: chartLegendColor, // culoarea titlului din tooltip
                         bodyColor: chartLegendColor,  // culoarea textului din tooltip
                         boxPadding: 8,
                         padding: 12,
                         borderColor: chartGridColor,
                         borderWidth: 1,
                         cornerRadius: parseInt(getCssVariable('--border-radius-small', '6px')), // colturi rotunjite pentru tooltip
                         usePointStyle: true, // foloseste stilul punctului in legenda tooltip-ului
                         callbacks: { // functii pentru a personaliza textul din tooltip
                            label: function(context) {
                                let label = context.dataset.label || ''; // numele setului de date
                                if (label) { label += ': '; }
                                if (context.parsed.y !== null) { // valoarea y parsata
                                    label += context.parsed.y.toFixed(2); // afisam cu 2 zecimale
                                }
                                return label;
                            }
                        }
                     }
                 },
                 interaction: { mode: 'index', intersect: false, axis: 'x' }, // cum interactioneaza tooltip-ul (pe index, pe axa x)
                 elements: { // stilul elementelor graficului
                     point:{ radius: 0, hoverRadius: 5, hitRadius: 10, backgroundColor: accentBlue }, // punctele de pe linie (invizibile normal, apar la hover)
                     line: { borderWidth: 2.5, tension: 0.4 } // linia graficului (grosime, cat de curbata e)
                 }
             };

            // cream graficul pentru fear & greed index
            if (fgChartCtx) {
                console.log("Attempting to create F&G chart...");
                try {
                    new Chart(fgChartCtx, { // cream un nou obiect chart
                        type: 'line', // tipul graficului
                        data: { // datele pentru grafic
                            labels: historyTimestamps, // etichetele de pe axa x (timpul)
                            datasets: [{ // seturile de date (aici doar unul)
                                label: 'Fear & Greed Index', data: historyFgValues, // numele si valorile
                                borderColor: accentGreen, // culoarea liniei
                                // cream o culoare de fundal rgba pe baza culorii de accent, cu transparenta mica
                                backgroundColor: accentGreen.includes('rgba') ? accentGreen.replace(/[\d\.]+\)$/g, '0.1)') : 'rgba(34, 197, 94, 0.1)',
                                fill: 'origin', // umplem zona de sub linie pana la origine (axa x)
                                spanGaps: true, // daca sunt valori lipsa (null), linia va continua peste ele
                                pointHoverBackgroundColor: accentGreen // culoarea punctului la hover
                            }]
                        },
                        // optiunile specifice acestui grafic (mosteneste commonchartoptions si adauga min/max pentru axa y)
                        options: { ...commonChartOptions, scales: { ...commonChartOptions.scales, y: { ...commonChartOptions.scales.y, min: 0, max: 100 } } }
                    });
                    console.log("F&G Chart created successfully.");
                } catch (error) { console.error("Error creating F&G chart:", error); }
            } else { console.error("F&G chart canvas 'fgHistoryChart' NOT FOUND!"); }

            // cream graficul pentru vix index (similar cu cel f&g)
            if (vixChartCtx) {
                console.log("Attempting to create VIX chart...");
                 try {
                    new Chart(vixChartCtx, {
                        type: 'line',
                        data: {
                            labels: historyTimestamps,
                            datasets: [{
                                label: 'VIX Index', data: historyVixValues,
                                borderColor: accentBlue,
                                backgroundColor: accentBlue.includes('rgba') ? accentBlue.replace(/[\d\.]+\)$/g, '0.1)') : 'rgba(56, 189, 248, 0.1)',
                                fill: 'origin',
                                spanGaps: true,
                                pointHoverBackgroundColor: accentBlue
                            }]
                        },
                        options: commonChartOptions // folosim optiunile comune, fara min/max specific pe axa y
                    });
                     console.log("VIX Chart created successfully.");
                } catch(error) { console.error("Error creating VIX chart:", error) }
             } else { console.error("VIX chart canvas 'vixHistoryChart' NOT FOUND!"); }
        } else { // daca nu avem suficiente date pentru grafice
            console.warn("Not enough data points to draw charts. Timestamps:", historyTimestamps.length);
            const noDataMsg = 'Not enough data for chart.'; // mesajul de afisat
            const textColorForNoData = getCssVariable('--secondary-text-color', '#a0aec0'); // culoarea textului
            const fontForNoData = `16px ${getCssVariable('--font-primary', 'Inter, sans-serif')}`; // fontul textului
            // afisam mesajul pe canvas-ul graficului f&g
            if(fgChartCtx) { const ctx = fgChartCtx; ctx.font = fontForNoData; ctx.fillStyle = textColorForNoData; ctx.textAlign = "center"; ctx.fillText(noDataMsg, ctx.canvas.width/2, ctx.canvas.height/2); }
            // afisam mesajul pe canvas-ul graficului vix
            if(vixChartCtx) { const ctx = vixChartCtx; ctx.font = fontForNoData; ctx.fillStyle = textColorForNoData; ctx.textAlign = "center"; ctx.fillText(noDataMsg, ctx.canvas.width/2, ctx.canvas.height/2); }
        }
    } else { // daca lipsesc biblioteci sau datele globale pentru grafice
        if (typeof Chart === 'undefined') console.error("Chart.js library NOT LOADED!");
        if (typeof historyTimestamps === 'undefined' || !Array.isArray(historyTimestamps)) console.error("Chart data 'historyTimestamps' is missing or not an array!");
        if (typeof historyFgValues === 'undefined' || !Array.isArray(historyFgValues)) console.error("Chart data 'historyFgValues' is missing or not an array!");
        if (typeof historyVixValues === 'undefined' || !Array.isArray(historyVixValues)) console.error("Chart data 'historyVixValues' is missing or not an array!");
    }

    // --- functionalitate pentru exportul in pdf ---
    const exportPdfButton = document.getElementById('exportPdfButton'); // gasim butonul de export pdf
    if (exportPdfButton) { // daca butonul exista
        console.log("Export PDF button found.");
        exportPdfButton.addEventListener('click', function() { // adaugam un ascultator de eveniment pentru click
            console.log("Export to PDF button clicked.");
            const dashboardElement = document.querySelector('.dashboard-container'); // selectam elementul html pe care vrem sa-l transformam in imagine

            // verificam daca avem elementul si bibliotecile html2canvas si jspdf
            if (dashboardElement && typeof html2canvas !== 'undefined' && typeof jspdf !== 'undefined') {
                const originalButtonText = this.textContent; // salvam textul original al butonului
                this.textContent = 'Generating PDF...'; // schimbam textul butonului
                this.disabled = true; // dezactivam butonul cat timp se genereaza pdf-ul

                // optiuni pentru html2canvas
                const options = {
                    scale: 2, // marim scara pentru o rezolutie mai buna a imaginii
                    useCORS: true, // necesar daca ai imagini de pe alte domenii (nu e cazul aici)
                    logging: false, // seteaza pe true pentru a vedea log-uri de la html2canvas in consola
                    scrollX: 0, // porneste captura de la pozitia de scroll 0 pe orizontala
                    scrollY: -window.scrollY, // compenseaza scroll-ul vertical al paginii pentru a captura de la inceput
                    windowWidth: document.documentElement.scrollWidth, // foloseste latimea totala a documentului
                    windowHeight: document.documentElement.scrollHeight, // foloseste inaltimea totala a documentului
                    onclone: (documentClone) => { // functie care se ruleaza pe o clona a documentului inainte de a face "screenshot-ul"
                        // ascundem toate butoanele de control din pdf
                        const selectorsToHide = [
                            '.controls-row .export-pdf-button',    // butonul export pdf
                            '.controls-row .export-csv-button',    // butonul export csv
                            '.controls-row .pipeline-controls button', // toate butoanele din pipeline-controls
                            '#dateFilterForm button.filter-button', // butonul filter
                            '#dateFilterForm a.clear-button'        // link-ul clear
                        ];
                        selectorsToHide.forEach(selector => { // pentru fiecare selector din lista
                            documentClone.querySelectorAll(selector).forEach(el => { // gasim toate elementele
                                if(el) el.style.setProperty('display', 'none', 'important'); // le ascundem
                            });
                        });
                        // asiguram ca fundalul in pdf este cel corect
                        documentClone.body.style.backgroundColor = getCssVariable('--bg-color-darkest', '#0a0a0c');
                    }
                };

                html2canvas(dashboardElement, options).then(canvas => { // html2canvas transforma elementul in <canvas>
                    const imgData = canvas.toDataURL('image/png'); // convertim canvas-ul intr-un string de date imagine (png)
                    const { jsPDF } = window.jspdf; // luam constructorul jspdf

                    // dimensiuni standard a4 in milimetri
                    const pdfA4WidthMm = 210; const pdfA4HeightMm = 297;
                    // raportul de aspect al imaginii generate
                    const aspectRatio = canvas.width / canvas.height;
                    let pdfImgWidthMm, pdfImgHeightMm; // dimensiunile imaginii in pdf

                    // calculam dimensiunile imaginii in pdf pentru a se potrivi pe o pagina a4, pastrand proportiile
                    if (aspectRatio > (pdfA4WidthMm / pdfA4HeightMm)) { // daca imaginea e mai lata decat a4 portrait
                        pdfImgWidthMm = pdfA4WidthMm; pdfImgHeightMm = pdfA4WidthMm / aspectRatio;
                    } else { // daca imaginea e mai inalta sau la fel
                        pdfImgHeightMm = pdfA4HeightMm; pdfImgWidthMm = pdfA4HeightMm * aspectRatio;
                    }

                    // alegem orientarea pdf-ului (portrait sau landscape) in functie de dimensiunile imaginii
                    const orientation = pdfImgWidthMm > pdfImgHeightMm ? 'landscape' : 'portrait';
                    const pdf = new jsPDF(orientation, 'mm', 'a4'); // cream documentul pdf

                    // calculam offset-urile pentru a centra imaginea pe pagina pdf
                    const xOffset = (pdf.internal.pageSize.getWidth() - pdfImgWidthMm) / 2;
                    const yOffset = (pdf.internal.pageSize.getHeight() - pdfImgHeightMm) / 2;

                    // adaugam imaginea in pdf
                    pdf.addImage(imgData, 'PNG', xOffset > 0 ? xOffset : 0, yOffset > 0 ? yOffset : 0, pdfImgWidthMm, pdfImgHeightMm);
                    pdf.save('market_sentiment_dashboard.pdf'); // declansam descarcarea pdf-ului

                    this.textContent = originalButtonText; // restauram textul butonului
                    this.disabled = false; // reactivam butonul
                    console.log("PDF generated and download prompted.");
                }).catch(err => { // daca apare o eroare la generarea pdf-ului
                    console.error("Error generating PDF with html2canvas: ", err);
                    this.textContent = originalButtonText; // restauram butonul
                    this.disabled = false;
                    alert("Could not generate PDF. Check console for details.");
                });
            } else { // daca lipsesc elemente sau biblioteci
                if (!dashboardElement) console.error("Dashboard element '.dashboard-container' NOT FOUND!");
                if (typeof html2canvas === 'undefined') console.error("html2canvas library NOT LOADED!");
                if (typeof jspdf === 'undefined') console.error("jsPDF library NOT LOADED!");
                alert("PDF export functionality is not available. Required libraries might be missing.");
            }
        });
    } else {
        console.warn("Export PDF button 'exportPdfButton' NOT FOUND!");
    }

    // --- functionalitate pentru rularea scripturilor de pe server ---
    // gasim butoanele din html
    const runWebscrapeBtn = document.getElementById('runWebscrapeBtn');
    const runAnalyzeBtn = document.getElementById('runAnalyzeBtn');
    const runFullPipelineBtn = document.getElementById('runFullPipelineBtn');

    // functie care gestioneaza raspunsul de la server dupa ce un script a fost rulat
    function handleScriptRunResponse(responsePromise, buttonElement) {
        responsePromise
            .then(response => { // primul .then gestioneaza raspunsul http initial
                if (!response.ok) { // daca statusul http nu e 200 (ok)
                    // incercam sa citim un mesaj de eroare json din corpul raspunsului
                    return response.json().then(errData => {
                        throw new Error(errData.message || `Server error: ${response.status}`);
                    }).catch(() => { // daca corpul nu e json sau e gol
                        throw new Error(`Server error: ${response.status} - Could not parse error details.`);
                    });
                }
                return response.json(); // daca e ok, parsam json-ul
            })
            .then(data => { // al doilea .then lucreaza cu datele json parsate
                console.log("Server response:", data);
                alert(data.message || "Action completed. Status unknown."); // afisam mesajul de la server
                // daca actiunea a avut succes si a fost rulat analyzer-ul sau tot pipeline-ul
                if (data.status === "success" && buttonElement && (buttonElement.id === 'runAnalyzeBtn' || buttonElement.id === 'runFullPipelineBtn')) {
                    console.log("Data likely updated, reloading page in 1.5s...");
                    setTimeout(() => { window.location.reload(); }, 1500); // reincarcam pagina dupa 1.5 secunde
                }
            })
            .catch(error => { // daca apare orice eroare in lantul de .then
                console.error("Error in script run process:", error);
                alert(`Operation failed: ${error.message}`);
            })
            .finally(() => { // acest bloc se executa intotdeauna, indiferent de succes sau eroare
                if (buttonElement) { // daca avem un element buton
                    buttonElement.disabled = false; // reactivam butonul
                    buttonElement.textContent = buttonElement.dataset.originalText || "Run Action"; // restauram textul original
                }
            });
    }

    // functie care declanseaza rularea unui script pe server
    // endpointurl este url-ul flask care trebuie apelat (ex: '/run_webscrape')
    // buttonelement este butonul pe care s-a dat click
    // actionname este un nume descriptiv pentru actiune (ex: 'Scraper')
    function triggerScriptRun(endpointUrl, buttonElement, actionName) {
        if (buttonElement) { // daca avem un element buton
            buttonElement.dataset.originalText = buttonElement.textContent; // salvam textul curent al butonului
            buttonElement.disabled = true; // dezactivam butonul
            buttonElement.textContent = `Running ${actionName}...`; // schimbam textul butonului
        }

        // verificam daca url-ul endpoint-ului este definit (ar trebui sa fie din variabilele globale js din html)
        if (typeof endpointUrl === 'undefined' || !endpointUrl) {
            console.error(`Endpoint URL for ${actionName} is not defined! Check HTML script block.`);
            alert(`Configuration error: Endpoint for ${actionName} is missing.`);
            if (buttonElement) { // reactivam butonul daca e eroare de configurare
                buttonElement.disabled = false;
                buttonElement.textContent = buttonElement.dataset.originalText;
            }
            return; // oprim executia
        }

        // facem un request http de tip post catre endpoint-ul specificat
        const responsePromise = fetch(endpointUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' } // specificam tipul de continut, chiar daca nu trimitem body
        });
        handleScriptRunResponse(responsePromise, buttonElement); // gestionam raspunsul
    }

    // adaugam ascultatori de evenimente pentru butoanele de rulare scripturi
    // verificam si daca url-urile globale sunt definite (ex: runwebscrapeurl)
    if (runWebscrapeBtn && typeof runWebscrapeUrl !== 'undefined') {
        runWebscrapeBtn.addEventListener('click', function() {
            if (confirm("Run web scraper? This may take a few minutes.")) { // cerem confirmare
                triggerScriptRun(runWebscrapeUrl, this, 'Scraper'); // folosim url-ul global
            }
        });
    } else if(runWebscrapeBtn) { console.error("runWebscrapeUrl is not defined. Check index.html script block.");}


    if (runAnalyzeBtn && typeof runAnalyzeNewsUrl !== 'undefined') {
        runAnalyzeBtn.addEventListener('click', function() {
            if (confirm("Run AI analyzer? This uses API credits and may take time.")) {
                triggerScriptRun(runAnalyzeNewsUrl, this, 'Analyzer'); // folosim url-ul global
            }
        });
    } else if(runAnalyzeBtn) { console.error("runAnalyzeNewsUrl is not defined. Check index.html script block.");}


    if (runFullPipelineBtn && typeof runPipelineUrl !== 'undefined') {
        runFullPipelineBtn.addEventListener('click', function() {
            if (confirm("Refresh all data? This runs both scraper and analyzer.")) {
                triggerScriptRun(runPipelineUrl, this, 'Pipeline'); // folosim url-ul global
            }
        });
    } else if(runFullPipelineBtn) { console.error("runPipelineUrl is not defined. Check index.html script block.");}


    console.log("Script execution finished.");
});
