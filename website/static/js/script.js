// --- START OF static/js/script.js ---
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded and parsed.");

    // --- Gauge Initialization ---
    console.log("Attempting to initialize Gauge...");
    const gaugeTarget = document.getElementById('fearGreedGauge');

    if (gaugeTarget && typeof Gauge !== 'undefined') {
        console.log("Gauge element and library found.");
        const opts = {
            angle: -0.2, lineWidth: 0.2, radiusScale: 0.9,
            pointer: { length: 0.5, strokeWidth: 0.045, color: '#e0e0e0' },
            limitMax: false, limitMin: false,
            colorStart: '#6FADCF', colorStop: '#8FC0DA', strokeColor: '#2a2a4e',
            generateGradient: true, highDpiSupport: true,
            staticZones: [
               {strokeStyle: "#ef4444", min: 0, max: 25},   // Extreme Fear - Red
               {strokeStyle: "#f59e0b", min: 25, max: 45},  // Fear - Orange
               {strokeStyle: "#6b7280", min: 45, max: 55},  // Neutral - Grey
               {strokeStyle: "#84cc16", min: 55, max: 75},  // Greed - Light Green
               {strokeStyle: "#22c55e", min: 75, max: 100}  // Extreme Greed - Green
            ],
            renderTicks: {
                divisions: 5, divWidth: 0.8, divLength: 0.5, divColor: '#4a4a6e',
                subDivisions: 4, subLength: 0.3, subWidth: 0.4, subColor: '#3a3a5e'
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
    }

    // --- Chart.js Initialization ---
    console.log("Attempting to initialize Charts...");
    if (typeof Chart !== 'undefined' &&
        typeof historyTimestamps !== 'undefined' && Array.isArray(historyTimestamps) &&
        typeof historyFgValues !== 'undefined' && Array.isArray(historyFgValues) &&
        typeof historyVixValues !== 'undefined' && Array.isArray(historyVixValues))
    {
        console.log("Chart.js library and data arrays found.");
        console.log(`Data lengths: Timestamps=${historyTimestamps.length}, F&G=${historyFgValues.length}, VIX=${historyVixValues.length}`);

        const fgChartCtx = document.getElementById('fgHistoryChart')?.getContext('2d');
        const vixChartCtx = document.getElementById('vixHistoryChart')?.getContext('2d');

        if (historyTimestamps.length > 0 && (historyFgValues.length > 0 || historyVixValues.length > 0)) {
            console.log("Sufficient data found for charts.");
            const commonChartOptions = {
                 responsive: true, maintainAspectRatio: false, animation: { duration: 500 },
                 scales: {
                     x: { ticks: { color: '#9ca3af', maxRotation: 0, autoSkip: true, maxTicksLimit: 10 }, grid: { color: '#374151', display: false } },
                     y: { ticks: { color: '#9ca3af' }, grid: { color: '#374151' }, beginAtZero: false }
                 },
                 plugins: {
                     legend: { labels: { color: '#f9fafb', font: { size: 14 } } },
                     tooltip: { backgroundColor: 'rgba(31, 41, 55, 0.9)', titleColor: '#f9fafb', bodyColor: '#f9fafb', boxPadding: 6, padding: 10 }
                 },
                 interaction: { mode: 'index', intersect: false },
                 elements: { point:{ radius: 2, hoverRadius: 4 }, line: { borderWidth: 2, tension: 0.1 } }
             };

            if (fgChartCtx) {
                console.log("Attempting to create F&G chart...");
                try {
                    new Chart(fgChartCtx, {
                        type: 'line',
                        data: { labels: historyTimestamps, datasets: [{
                            label: 'Fear & Greed Index', data: historyFgValues, borderColor: '#84cc16',
                            backgroundColor: 'rgba(132, 204, 22, 0.1)', fill: false, spanGaps: true }]
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
                        data: { labels: historyTimestamps, datasets: [{
                            label: 'VIX Index', data: historyVixValues, borderColor: '#38bdf8',
                            backgroundColor: 'rgba(56, 189, 248, 0.1)', fill: false, spanGaps: true }]
                        },
                        options: commonChartOptions
                    });
                     console.log("VIX Chart created successfully.");
                } catch(error) { console.error("Error creating VIX chart:", error) }
             } else { console.error("VIX chart canvas 'vixHistoryChart' NOT FOUND!"); }
        } else {
            console.warn("Not enough data points to draw charts. Timestamps:", historyTimestamps.length);
            if(fgChartCtx) { const ctx = fgChartCtx; ctx.font = "16px Arial"; ctx.fillStyle = "var(--secondary-text-color)"; ctx.textAlign = "center"; ctx.fillText('Not enough data for chart.', ctx.canvas.width/2, 50); }
            if(vixChartCtx) { const ctx = vixChartCtx; ctx.font = "16px Arial"; ctx.fillStyle = "var(--secondary-text-color)"; ctx.textAlign = "center"; ctx.fillText('Not enough data for chart.', ctx.canvas.width/2, 50); }
        }
    } else {
        if (typeof Chart === 'undefined') console.error("Chart.js library NOT LOADED!");
        if (typeof historyTimestamps === 'undefined' || !Array.isArray(historyTimestamps)) console.error("Chart data 'historyTimestamps' is missing or not an array!");
        if (typeof historyFgValues === 'undefined' || !Array.isArray(historyFgValues)) console.error("Chart data 'historyFgValues' is missing or not an array!");
        if (typeof historyVixValues === 'undefined' || !Array.isArray(historyVixValues)) console.error("Chart data 'historyVixValues' is missing or not an array!");
    }

    // --- Export to PDF Functionality ---
    const exportPdfButton = document.getElementById('exportPdfButton');
    if (exportPdfButton) {
        console.log("Export PDF button found.");
        exportPdfButton.addEventListener('click', function() {
            console.log("Export to PDF button clicked.");
            // Selectează elementul principal pe care vrei să-l exporți.
            // Poți alege '.dashboard-container' sau un element mai specific.
            const dashboardElement = document.querySelector('.dashboard-container');

            if (dashboardElement && typeof html2canvas !== 'undefined' && typeof jspdf !== 'undefined') {
                exportPdfButton.textContent = 'Generating PDF...';
                exportPdfButton.disabled = true;

                // Opțiuni pentru html2canvas
                const options = {
                    scale: 2, // Crește scala pentru o rezoluție mai bună
                    useCORS: true, // Important dacă ai imagini de pe alte domenii (nu e cazul aici)
                    logging: false, // Setează pe true pentru debugging html2canvas
                    scrollX: 0, // Asigură că începe de la scroll 0
                    scrollY: -window.scrollY, // Compensează scroll-ul paginii
                    windowWidth: document.documentElement.offsetWidth, // Folosește lățimea documentului
                    windowHeight: document.documentElement.offsetHeight, // Folosește înălțimea documentului
                    onclone: (documentClone) => {
                        // Ascunde butonul de export din clonă înainte de a face screenshot
                        const btnToHide = documentClone.getElementById('exportPdfButton');
                        if (btnToHide) {
                            btnToHide.style.display = 'none';
                        }
                        // Poți ascunde și alte elemente dacă nu vrei să apară în PDF
                    }
                };

                html2canvas(dashboardElement, options).then(canvas => {
                    const imgData = canvas.toDataURL('image/png');
                    const { jsPDF } = window.jspdf; // Asigură-te că accesezi corect constructorul

                    // Dimensiuni standard A4 în mm: 210 x 297
                    const pdfA4WidthMm = 210;
                    const pdfA4HeightMm = 297;

                    // Calculează raportul imaginii
                    const imgWidthPx = canvas.width;
                    const imgHeightPx = canvas.height;
                    const aspectRatio = imgWidthPx / imgHeightPx;

                    let pdfImgWidthMm, pdfImgHeightMm;

                    // Determină orientarea și dimensiunile imaginii în PDF
                    // pentru a se potrivi pe o pagină A4, păstrând proporțiile
                    if (aspectRatio > (pdfA4WidthMm / pdfA4HeightMm)) { // Imaginea e mai lată decât A4 portrait
                        pdfImgWidthMm = pdfA4WidthMm;
                        pdfImgHeightMm = pdfA4WidthMm / aspectRatio;
                    } else { // Imaginea e mai înaltă sau la fel
                        pdfImgHeightMm = pdfA4HeightMm;
                        pdfImgWidthMm = pdfA4HeightMm * aspectRatio;
                    }

                    // Creează PDF-ul. Poți alege orientarea în funcție de imagine.
                    // Dacă imaginea e foarte lată, 'landscape' poate fi mai bun.
                    const orientation = pdfImgWidthMm > pdfImgHeightMm ? 'landscape' : 'portrait';
                    const pdf = new jsPDF(orientation, 'mm', 'a4');

                    // Adaugă imaginea la PDF
                    // Centrează imaginea pe pagină dacă e mai mică decât A4
                    const xOffset = (pdf.internal.pageSize.getWidth() - pdfImgWidthMm) / 2;
                    const yOffset = (pdf.internal.pageSize.getHeight() - pdfImgHeightMm) / 2;

                    pdf.addImage(imgData, 'PNG', xOffset > 0 ? xOffset : 0, yOffset > 0 ? yOffset : 0, pdfImgWidthMm, pdfImgHeightMm);
                    pdf.save('market_sentiment_dashboard.pdf');

                    exportPdfButton.textContent = 'Export Dashboard to PDF';
                    exportPdfButton.disabled = false;
                    console.log("PDF generated and download prompted.");

                }).catch(err => {
                    console.error("Error generating PDF with html2canvas: ", err);
                    exportPdfButton.textContent = 'Export Dashboard to PDF';
                    exportPdfButton.disabled = false;
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

    console.log("Script execution finished.");
});
// --- END OF static/js/script.js ---