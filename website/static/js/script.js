// --- START OF static/js/script.js ---
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded and parsed.");

    // --- Gauge Initialization ---
    console.log("Attempting to initialize Gauge...");
    const gaugeTarget = document.getElementById('fearGreedGauge');

    // Check if gauge element and Gauge library exist
    if (gaugeTarget && typeof Gauge !== 'undefined') {
        console.log("Gauge element and library found.");
        const opts = {
            angle: -0.2, lineWidth: 0.2, radiusScale: 0.9,
            pointer: { length: 0.5, strokeWidth: 0.045, color: '#e0e0e0' },
            limitMax: false, limitMin: false,
            colorStart: '#6FADCF', colorStop: '#8FC0DA', strokeColor: '#2a2a4e',
            generateGradient: true, highDpiSupport: true,
            staticZones: [ // Use colors defined in CSS variables if possible, or hardcode
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
            gauge.animationSpeed = 32; // Or 0 for no animation

            // fearGreedData should be defined and parsed in the HTML <script> block
            if (typeof fearGreedData === 'number' && !isNaN(fearGreedData)) {
                console.log("Setting Gauge value to:", fearGreedData);
                gauge.set(fearGreedData);
            } else {
                 console.warn("Invalid or missing fearGreedData for gauge. Setting to default 50. Value was:", fearGreedData);
                gauge.set(50); // Default to neutral if data is invalid
            }
            console.log("Gauge initialized successfully.");
        } catch (error) {
             console.error("Error initializing gauge:", error);
        }

    } else {
        // Log specific reasons for failure
        if (!gaugeTarget) console.error("Gauge canvas element 'fearGreedGauge' NOT FOUND!");
        if (typeof Gauge === 'undefined') console.error("Gauge.js library NOT LOADED!");
    }


    // --- Chart.js Initialization ---
    console.log("Attempting to initialize Charts...");
    // Check if Chart library and necessary data arrays exist and are arrays
    if (typeof Chart !== 'undefined' &&
        typeof historyTimestamps !== 'undefined' && Array.isArray(historyTimestamps) &&
        typeof historyFgValues !== 'undefined' && Array.isArray(historyFgValues) &&
        typeof historyVixValues !== 'undefined' && Array.isArray(historyVixValues))
    {
        console.log("Chart.js library and data arrays found.");
        console.log(`Data lengths: Timestamps=${historyTimestamps.length}, F&G=${historyFgValues.length}, VIX=${historyVixValues.length}`);

        const fgChartCtx = document.getElementById('fgHistoryChart')?.getContext('2d');
        const vixChartCtx = document.getElementById('vixHistoryChart')?.getContext('2d');

        // Proceed only if there's data to plot
        if (historyTimestamps.length > 0 && (historyFgValues.length > 0 || historyVixValues.length > 0)) {
            console.log("Sufficient data found for charts.");

            const commonChartOptions = {
                 responsive: true, maintainAspectRatio: false, animation: { duration: 500 }, // Add subtle animation
                 scales: {
                     x: { ticks: { color: '#9ca3af', maxRotation: 0, autoSkip: true, maxTicksLimit: 10 }, grid: { color: '#374151', display: false } },
                     y: { ticks: { color: '#9ca3af' }, grid: { color: '#374151' }, beginAtZero: false }
                 },
                 plugins: {
                     legend: { labels: { color: '#f9fafb', font: { size: 14 } } },
                     tooltip: { backgroundColor: 'rgba(31, 41, 55, 0.9)', titleColor: '#f9fafb', bodyColor: '#f9fafb', boxPadding: 6, padding: 10 }
                 },
                 interaction: { mode: 'index', intersect: false },
                 elements: { point:{ radius: 2, hoverRadius: 4 }, line: { borderWidth: 2, tension: 0.1 } } // Slightly larger points/hover
             };

            // Fear & Greed Chart
            if (fgChartCtx) {
                console.log("Attempting to create F&G chart...");
                try {
                    new Chart(fgChartCtx, {
                        type: 'line',
                        data: { labels: historyTimestamps, datasets: [{
                            label: 'Fear & Greed Index', data: historyFgValues, borderColor: '#84cc16', /* Greed */
                            backgroundColor: 'rgba(132, 204, 22, 0.1)', fill: false, spanGaps: true }]
                        },
                        options: { ...commonChartOptions, scales: { ...commonChartOptions.scales, y: { ...commonChartOptions.scales.y, min: 0, max: 100 } } }
                    });
                    console.log("F&G Chart created successfully.");
                } catch (error) { console.error("Error creating F&G chart:", error); }
            } else { console.error("F&G chart canvas 'fgHistoryChart' NOT FOUND!"); }

            // VIX Chart
            if (vixChartCtx) {
                console.log("Attempting to create VIX chart...");
                 try {
                    new Chart(vixChartCtx, {
                        type: 'line',
                        data: { labels: historyTimestamps, datasets: [{
                            label: 'VIX Index', data: historyVixValues, borderColor: '#38bdf8', /* VIX Blue */
                            backgroundColor: 'rgba(56, 189, 248, 0.1)', fill: false, spanGaps: true }]
                        },
                        options: commonChartOptions
                    });
                     console.log("VIX Chart created successfully.");
                } catch(error) { console.error("Error creating VIX chart:", error) }
             } else { console.error("VIX chart canvas 'vixHistoryChart' NOT FOUND!"); }

        } else {
            console.warn("Not enough data points to draw charts. Timestamps:", historyTimestamps.length);
            // Optionally display a message in the chart area
            if(fgChartCtx) fgChartCtx.fillText('Not enough data for chart.', 10, 50);
            if(vixChartCtx) vixChartCtx.fillText('Not enough data for chart.', 10, 50);
        }

    } else {
        // Log specific reasons why charts weren't initialized
        if (typeof Chart === 'undefined') console.error("Chart.js library NOT LOADED!");
        if (typeof historyTimestamps === 'undefined' || !Array.isArray(historyTimestamps)) console.error("Chart data 'historyTimestamps' is missing or not an array!");
        if (typeof historyFgValues === 'undefined' || !Array.isArray(historyFgValues)) console.error("Chart data 'historyFgValues' is missing or not an array!");
        if (typeof historyVixValues === 'undefined' || !Array.isArray(historyVixValues)) console.error("Chart data 'historyVixValues' is missing or not an array!");
    }

    console.log("Script execution finished.");
});
// --- END OF static/js/script.js ---