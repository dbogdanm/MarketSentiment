document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded and parsed.");

    function getCssVariable(variableName, fallbackValue) {
        const value = getComputedStyle(document.documentElement).getPropertyValue(variableName).trim();
        return value || fallbackValue;
    }

    console.log("Attempting to initialize Gauge...");
    const gaugeTarget = document.getElementById('fearGreedGauge');

    if (gaugeTarget && typeof Gauge !== 'undefined' && typeof fearGreedData !== 'undefined') {
        console.log("Gauge element, library, and data found.");
        const opts = {
            angle: -0.2,
            lineWidth: 0.2,
            radiusScale: 0.9,
            pointer: { length: 0.5, strokeWidth: 0.045, color: getCssVariable('--primary-text-color', '#e0e0e0') },
            limitMax: false,
            limitMin: false,
            colorStart: '#6FADCF',
            colorStop: '#8FC0DA',
            strokeColor: getCssVariable('--card-bg-color', '#1a1a1e'),
            generateGradient: true,
            highDpiSupport: true,
            staticZones: [
               {strokeStyle: getCssVariable('--accent-red', "#ef4444"), min: 0, max: 25},
               {strokeStyle: getCssVariable('--accent-orange', "#f59e0b"), min: 25, max: 45},
               {strokeStyle: getCssVariable('--secondary-text-color', "#6b7280"), min: 45, max: 55},
               {strokeStyle: getCssVariable('--accent-green', "#84cc16"), min: 55, max: 75},
               {strokeStyle: getCssVariable('--accent-green', "#22c55e"), min: 75, max: 100}
            ],
            renderTicks: {
                divisions: 5, divWidth: 0.8, divLength: 0.5, divColor: getCssVariable('--border-color', '#4a4a6e'),
                subDivisions: 4, subLength: 0.3, subWidth: 0.4, subColor: getCssVariable('--border-color', '#3a3a5e')
            }
        };
        try {
            const gauge = new Gauge(gaugeTarget).setOptions(opts);
            gauge.maxValue = 100;
            gauge.setMinValue(0);
            gauge.animationSpeed = 32;

            if (typeof fearGreedData === 'number' && !isNaN(fearGreedData)) {
                console.log("Setting Gauge value to:", fearGreedData);
                gauge.set(fearGreedData);
            } else {
                 console.warn("Invalid or missing fearGreedData for gauge. Setting to default 50. Value was:", fearGreedData);
                gauge.set(50);
            }
            console.log("Gauge initialized successfully.");
        } catch (error) {
             console.error("Error initializing gauge:", error);
        }
    } else {
        if (!gaugeTarget) console.error("Gauge canvas element 'fearGreedGauge' NOT FOUND!");
        if (typeof Gauge === 'undefined') console.error("Gauge.js library NOT LOADED!");
        if (typeof fearGreedData === 'undefined') console.error("Global variable 'fearGreedData' NOT FOUND!");
    }

    console.log("Attempting to initialize Charts...");

    if (typeof Chart !== 'undefined' &&
        typeof historyTimestamps !== 'undefined' && Array.isArray(historyTimestamps) &&
        typeof historyFgValues !== 'undefined' && Array.isArray(historyFgValues) &&
        typeof historyVixValues !== 'undefined' && Array.isArray(historyVixValues))
    {
        console.log("Chart.js library and data arrays found.");

        const fgChartCtx = document.getElementById('fgHistoryChart')?.getContext('2d');
        const vixChartCtx = document.getElementById('vixHistoryChart')?.getContext('2d');

        if (historyTimestamps.length > 0 && (historyFgValues.length > 0 || historyVixValues.length > 0)) {
            console.log("Sufficient data found for charts.");

            const chartTextColor = getCssVariable('--secondary-text-color', '#a0aec0');
            const chartGridColor = getCssVariable('--border-color', '#2a2d35');
            const chartLegendColor = getCssVariable('--primary-text-color', '#e8e8eb');
            const accentGreen = getCssVariable('--accent-green', '#22c55e');
            const accentBlue = getCssVariable('--accent-blue', '#38bdf8');
            const cardBgColor = getCssVariable('--card-bg-color', '#16181d');

            const commonChartOptions = {
                 responsive: true,
                 maintainAspectRatio: false,
                 animation: { duration: 800, easing: 'easeInOutQuart' },
                 scales: {
                     x: {
                         ticks: { color: chartTextColor, maxRotation: 0, autoSkip: true, maxTicksLimit: 8, padding: 10 },
                         grid: { color: chartGridColor, display: false },
                         border: { display: true, color: chartGridColor }
                     },
                     y: {
                         ticks: { color: chartTextColor, padding: 10, precision: 0 },
                         grid: { color: chartGridColor, borderDash: [3, 3], drawBorder: false, zeroLineColor: chartGridColor, zeroLineWidth: 1 },
                         beginAtZero: false,
                         border: { display: true, color: chartGridColor }
                     }
                 },
                 plugins: {
                     legend: {
                         labels: { color: chartLegendColor, font: { size: 13 }, boxWidth: 12, padding: 20 }
                     },
                     tooltip: {
                         enabled: true,
                         backgroundColor: cardBgColor,
                         titleColor: chartLegendColor,
                         bodyColor: chartLegendColor,
                         boxPadding: 8,
                         padding: 12,
                         borderColor: chartGridColor,
                         borderWidth: 1,
                         cornerRadius: parseInt(getCssVariable('--border-radius-small', '6px')),
                         usePointStyle: true,
                         callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) { label += ': '; }
                                if (context.parsed.y !== null) {
                                    label += context.parsed.y.toFixed(2);
                                }
                                return label;
                            }
                        }
                     }
                 },
                 interaction: { mode: 'index', intersect: false, axis: 'x' },
                 elements: {
                     point:{ radius: 0, hoverRadius: 5, hitRadius: 10, backgroundColor: accentBlue },
                     line: { borderWidth: 2.5, tension: 0.4 }
                 }
             };

            if (fgChartCtx) {
                console.log("Attempting to create F&G chart...");
                try {
                    new Chart(fgChartCtx, {
                        type: 'line',
                        data: {
                            labels: historyTimestamps,
                            datasets: [{
                                label: 'Fear & Greed Index', data: historyFgValues,
                                borderColor: accentGreen,
                                backgroundColor: accentGreen.includes('rgba') ? accentGreen.replace(/[\d\.]+\)$/g, '0.1)') : 'rgba(34, 197, 94, 0.1)',
                                fill: 'origin',
                                spanGaps: true,
                                pointHoverBackgroundColor: accentGreen
                            }]
                        },
                        options: { ...commonChartOptions, scales: { ...commonChartOptions.scales, y: { ...commonChartOptions.scales.y, min: 0, max: 100 } } }
                    });
                    console.log("F&G Chart created successfully.");
                } catch (error) { console.error("Error creating F&G chart:", error); }
            } else { console.error("F&G chart canvas 'fgHistoryChart' NOT FOUND!"); }

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
                        options: commonChartOptions
                    });
                     console.log("VIX Chart created successfully.");
                } catch(error) { console.error("Error creating VIX chart:", error) }
             } else { console.error("VIX chart canvas 'vixHistoryChart' NOT FOUND!"); }
        } else {
            console.warn("Not enough data points to draw charts. Timestamps:", historyTimestamps.length);
            const noDataMsg = 'Not enough data for chart.';
            const textColorForNoData = getCssVariable('--secondary-text-color', '#a0aec0');
            const fontForNoData = `16px ${getCssVariable('--font-primary', 'Inter, sans-serif')}`;
            if(fgChartCtx) { const ctx = fgChartCtx; ctx.font = fontForNoData; ctx.fillStyle = textColorForNoData; ctx.textAlign = "center"; ctx.fillText(noDataMsg, ctx.canvas.width/2, ctx.canvas.height/2); }
            if(vixChartCtx) { const ctx = vixChartCtx; ctx.font = fontForNoData; ctx.fillStyle = textColorForNoData; ctx.textAlign = "center"; ctx.fillText(noDataMsg, ctx.canvas.width/2, ctx.canvas.height/2); }
        }
    } else {
        if (typeof Chart === 'undefined') console.error("Chart.js library NOT LOADED!");
        if (typeof historyTimestamps === 'undefined' || !Array.isArray(historyTimestamps)) console.error("Chart data 'historyTimestamps' is missing or not an array!");
        if (typeof historyFgValues === 'undefined' || !Array.isArray(historyFgValues)) console.error("Chart data 'historyFgValues' is missing or not an array!");
        if (typeof historyVixValues === 'undefined' || !Array.isArray(historyVixValues)) console.error("Chart data 'historyVixValues' is missing or not an array!");
    }

    const exportPdfButton = document.getElementById('exportPdfButton');
    if (exportPdfButton) {
        console.log("Export PDF button found.");
        exportPdfButton.addEventListener('click', function() {
            console.log("Export to PDF button clicked.");
            const dashboardElement = document.querySelector('.dashboard-container');

            if (dashboardElement && typeof html2canvas !== 'undefined' && typeof jspdf !== 'undefined') {
                const originalButtonText = this.textContent;
                this.textContent = 'Generating PDF...';
                this.disabled = true;

                const options = {
                    scale: 2, useCORS: true, logging: false, scrollX: 0, scrollY: -window.scrollY,
                    windowWidth: document.documentElement.scrollWidth,
                    windowHeight: document.documentElement.scrollHeight,
                    onclone: (documentClone) => {
                        const selectorsToHide = [
                            '.controls-row .export-pdf-button',
                            '.controls-row .export-csv-button',
                            '.controls-row .pipeline-controls button',
                            '#dateFilterForm button.filter-button',
                            '#dateFilterForm a.clear-button'
                        ];
                        selectorsToHide.forEach(selector => {
                            documentClone.querySelectorAll(selector).forEach(el => {
                                if(el) el.style.setProperty('display', 'none', 'important');
                            });
                        });

                        documentClone.body.style.backgroundColor = getCssVariable('--bg-color-darkest', '#0a0a0c');
                    }
                };

                html2canvas(dashboardElement, options).then(canvas => {
                    const imgData = canvas.toDataURL('image/png');
                    const { jsPDF } = window.jspdf;
                    const pdfA4WidthMm = 210; const pdfA4HeightMm = 297;
                    const aspectRatio = canvas.width / canvas.height;
                    let pdfImgWidthMm, pdfImgHeightMm;

                    if (aspectRatio > (pdfA4WidthMm / pdfA4HeightMm)) {
                        pdfImgWidthMm = pdfA4WidthMm; pdfImgHeightMm = pdfA4WidthMm / aspectRatio;
                    } else {
                        pdfImgHeightMm = pdfA4HeightMm; pdfImgWidthMm = pdfA4HeightMm * aspectRatio;
                    }
                    const orientation = pdfImgWidthMm > pdfImgHeightMm ? 'landscape' : 'portrait';
                    const pdf = new jsPDF(orientation, 'mm', 'a4');
                    const xOffset = (pdf.internal.pageSize.getWidth() - pdfImgWidthMm) / 2;
                    const yOffset = (pdf.internal.pageSize.getHeight() - pdfImgHeightMm) / 2;
                    pdf.addImage(imgData, 'PNG', xOffset > 0 ? xOffset : 0, yOffset > 0 ? yOffset : 0, pdfImgWidthMm, pdfImgHeightMm);
                    pdf.save('market_sentiment_dashboard.pdf');
                    this.textContent = originalButtonText;
                    this.disabled = false;
                    console.log("PDF generated and download prompted.");
                }).catch(err => {
                    console.error("Error generating PDF with html2canvas: ", err);
                    this.textContent = originalButtonText;
                    this.disabled = false;
                    alert("Could not generate PDF. Check console for details.");
                });
            } else {
                if (!dashboardElement) console.error("Dashboard element '.dashboard-container' NOT FOUND!");
                if (typeof html2canvas === 'undefined') console.error("html2canvas library NOT LOADED!");
                if (typeof jspdf === 'undefined') console.error("jsPDF library NOT LOADED!");
                alert("PDF export functionality is not available. Required libraries might be missing.");
            }
        });
    } else {
        console.warn("Export PDF button 'exportPdfButton' NOT FOUND!");
    }

    const runWebscrapeBtn = document.getElementById('runWebscrapeBtn');
    const runAnalyzeBtn = document.getElementById('runAnalyzeBtn');
    const runFullPipelineBtn = document.getElementById('runFullPipelineBtn');

    function handleScriptRunResponse(responsePromise, buttonElement) {
        responsePromise
            .then(response => {
                if (!response.ok) {
                    return response.json().then(errData => {
                        throw new Error(errData.message || `Server error: ${response.status}`);
                    }).catch(() => {
                        throw new Error(`Server error: ${response.status} - Could not parse error details.`);
                    });
                }
                return response.json();
            })
            .then(data => {
                console.log("Server response:", data);
                alert(data.message || "Action completed. Status unknown.");
                if (data.status === "success" && buttonElement && (buttonElement.id === 'runAnalyzeBtn' || buttonElement.id === 'runFullPipelineBtn')) {
                    console.log("Data likely updated, reloading page in 1.5s...");
                    setTimeout(() => { window.location.reload(); }, 1500);
                }
            })
            .catch(error => {
                console.error("Error in script run process:", error);
                alert(`Operation failed: ${error.message}`);
            })
            .finally(() => {
                if (buttonElement) {
                    buttonElement.disabled = false;
                    buttonElement.textContent = buttonElement.dataset.originalText || "Run Action";
                }
            });
    }

    function triggerScriptRun(endpointUrl, buttonElement, actionName) {
        if (buttonElement) {
            buttonElement.dataset.originalText = buttonElement.textContent;
            buttonElement.disabled = true;
            buttonElement.textContent = `Running ${actionName}...`;
        }
        if (typeof endpointUrl === 'undefined' || !endpointUrl) {
            console.error(`Endpoint URL for ${actionName} is not defined! Check HTML script block.`);
            alert(`Configuration error: Endpoint for ${actionName} is missing.`);
            if (buttonElement) {
                buttonElement.disabled = false;
                buttonElement.textContent = buttonElement.dataset.originalText;
            }
            return;
        }
        const responsePromise = fetch(endpointUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        handleScriptRunResponse(responsePromise, buttonElement);
    }

    if (runWebscrapeBtn && typeof runWebscrapeUrl !== 'undefined') {
        runWebscrapeBtn.addEventListener('click', function() {
            if (confirm("Run web scraper? This may take a few minutes.")) {
                triggerScriptRun(runWebscrapeUrl, this, 'Scraper');
            }
        });
    } else if(runWebscrapeBtn) { console.error("runWebscrapeUrl is not defined. Check index.html script block.");}

    if (runAnalyzeBtn && typeof runAnalyzeNewsUrl !== 'undefined') {
        runAnalyzeBtn.addEventListener('click', function() {
            if (confirm("Run AI analyzer? This uses API credits and may take time.")) {
                triggerScriptRun(runAnalyzeNewsUrl, this, 'Analyzer');
            }
        });
    } else if(runAnalyzeBtn) { console.error("runAnalyzeNewsUrl is not defined. Check index.html script block.");}

    if (runFullPipelineBtn && typeof runPipelineUrl !== 'undefined') {
        runFullPipelineBtn.addEventListener('click', function() {
            if (confirm("Refresh all data? This runs both scraper and analyzer.")) {
                triggerScriptRun(runPipelineUrl, this, 'Pipeline');
            }
        });
    } else if(runFullPipelineBtn) { console.error("runPipelineUrl is not defined. Check index.html script block.");}

    console.log("Script execution finished.");
});

