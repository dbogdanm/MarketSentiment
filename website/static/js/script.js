document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded and parsed.");

    function getCssVariable(variableName, fallbackValue) {
        const value = getComputedStyle(document.documentElement).getPropertyValue(variableName).trim();
        return value || fallbackValue;
    }

    // --- initialization of the gauge ---
    console.log("Attempting to initialize Gauge...");
    const gaugeTarget = document.getElementById('fearGreedGauge');

    if (gaugeTarget && typeof Gauge !== 'undefined' && typeof fearGreedData !== 'undefined') {
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
                gauge.set(fearGreedData);
            } else {
                gauge.set(50);
            }
        } catch (error) {
             console.error("Error initializing gauge:", error);
        }
    }

    // --- initialization of the charts ---
    if (typeof Chart !== 'undefined' &&
        typeof historyTimestamps !== 'undefined' && Array.isArray(historyTimestamps) &&
        typeof historyFgValues !== 'undefined' && Array.isArray(historyFgValues) &&
        typeof historyVixValues !== 'undefined' && Array.isArray(historyVixValues))
    {
        const fgChartCtx = document.getElementById('fgHistoryChart')?.getContext('2d');
        const vixChartCtx = document.getElementById('vixHistoryChart')?.getContext('2d');

        if (historyTimestamps.length > 0 && (historyFgValues.length > 0 || historyVixValues.length > 0)) {
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
                         cornerRadius: 6,
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
                new Chart(fgChartCtx, {
                    type: 'line',
                    data: {
                        labels: historyTimestamps,
                        datasets: [{
                            label: 'Fear & Greed Index', data: historyFgValues,
                            borderColor: accentGreen,
                            backgroundColor: 'rgba(34, 197, 94, 0.1)',
                            fill: 'origin',
                            spanGaps: true,
                            pointHoverBackgroundColor: accentGreen
                        }]
                    },
                    options: { ...commonChartOptions, scales: { ...commonChartOptions.scales, y: { ...commonChartOptions.scales.y, min: 0, max: 100 } } }
                });
            }

            if (vixChartCtx) {
                new Chart(vixChartCtx, {
                    type: 'line',
                    data: {
                        labels: historyTimestamps,
                        datasets: [{
                            label: 'VIX Index', data: historyVixValues,
                            borderColor: accentBlue,
                            backgroundColor: 'rgba(56, 189, 248, 0.1)',
                            fill: 'origin',
                            spanGaps: true,
                            pointHoverBackgroundColor: accentBlue
                        }]
                    },
                    options: commonChartOptions
                });
             }
        }
    }

    // --- export to pdf ---
    const exportPdfButton = document.getElementById('exportPdfButton');
    if (exportPdfButton) {
        exportPdfButton.addEventListener('click', function() {
            const dashboardElement = document.querySelector('main');
            if (dashboardElement && typeof html2canvas !== 'undefined' && typeof jspdf !== 'undefined') {
                const originalButtonText = this.textContent;
                this.textContent = 'Generating...';
                this.disabled = true;

                html2canvas(dashboardElement, { scale: 2 }).then(canvas => {
                    const imgData = canvas.toDataURL('image/png');
                    const { jsPDF } = window.jspdf;
                    const pdf = new jsPDF('l', 'mm', 'a4');
                    pdf.addImage(imgData, 'PNG', 10, 10, 280, 150);
                    pdf.save('dashboard.pdf');
                    this.textContent = originalButtonText;
                    this.disabled = false;
                });
            }
        });
    }

    // --- run server scripts ---
    function triggerScriptRun(endpointUrl, buttonElement, actionName) {
        if (buttonElement) {
            buttonElement.dataset.originalText = buttonElement.textContent;
            buttonElement.disabled = true;
            buttonElement.textContent = `Running ${actionName}...`;
        }

        fetch(endpointUrl, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status === "success") {
                    if (buttonElement) buttonElement.textContent = "Success!";
                    setTimeout(() => { window.location.reload(); }, 1000);
                } else {
                    alert(data.message || "Failed");
                    if (buttonElement) {
                        buttonElement.disabled = false;
                        buttonElement.textContent = buttonElement.dataset.originalText;
                    }
                }
            })
            .catch(error => {
                alert(`Error: ${error.message}`);
                if (buttonElement) {
                    buttonElement.disabled = false;
                    buttonElement.textContent = buttonElement.dataset.originalText;
                }
            });
    }

    document.getElementById('runWebscrapeBtn')?.addEventListener('click', function() {
        triggerScriptRun(runWebscrapeUrl, this, 'Scraper');
    });
    document.getElementById('runAnalyzeBtn')?.addEventListener('click', function() {
        triggerScriptRun(runAnalyzeNewsUrl, this, 'Analyzer');
    });
    document.getElementById('runFullPipelineBtn')?.addEventListener('click', function() {
        triggerScriptRun(runPipelineUrl, this, 'Pipeline');
    });

    // --- markdown rendering ---
    const aiSummaryDisplay = document.getElementById('aiSummaryDisplay');
    if (aiSummaryDisplay && typeof marked !== 'undefined') {
        const rawMarkdown = aiSummaryDisplay.textContent.trim();
        if (rawMarkdown && rawMarkdown !== 'No AI summary currently available.') {
            aiSummaryDisplay.innerHTML = marked.parse(rawMarkdown);
        }
    }
});
