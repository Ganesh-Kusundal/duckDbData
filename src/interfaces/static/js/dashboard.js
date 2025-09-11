// Dashboard JavaScript

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    startAutoRefresh();
});

let refreshInterval;

// Initialize dashboard components
function initializeDashboard() {
    updateSystemMetrics();
    updateDatabaseStats();
    initializeCharts();
}

// Update system metrics
async function updateSystemMetrics() {
    try {
        const response = await fetch('/health/detailed');
        const data = await response.json();

        // Update CPU usage
        const cpuPercent = data.process.cpu_percent;
        document.getElementById('cpu-usage').textContent = cpuPercent.toFixed(1) + '%';

        // Update memory usage
        const memoryPercent = (data.process.memory_percent || 0);
        document.getElementById('memory-usage').textContent = memoryPercent.toFixed(1) + '%';

        // Update system info
        updateSystemInfo(data.system);

    } catch (error) {
        console.error('Failed to update system metrics:', error);
    }
}

// Update database statistics
async function updateDatabaseStats() {
    try {
        // This would need a database stats endpoint
        // For now, we'll show placeholder data
        document.getElementById('db-status').textContent = 'Connected';
        document.getElementById('total-records').textContent = '1,245,678';
        document.getElementById('active-scanners').textContent = '3';

    } catch (error) {
        console.error('Failed to update database stats:', error);
    }
}

// Initialize charts
function initializeCharts() {
    const ctx = document.getElementById('healthChart').getContext('2d');

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['CPU', 'Memory', 'Disk'],
            datasets: [{
                data: [45, 65, 25],
                backgroundColor: [
                    '#007bff',
                    '#28a745',
                    '#ffc107'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Update system information display
function updateSystemInfo(systemData) {
    // This would update various system info displays
    console.log('System info updated:', systemData);
}

// Start auto-refresh
function startAutoRefresh() {
    refreshInterval = setInterval(() => {
        updateSystemMetrics();
        updateDatabaseStats();
    }, 30000); // Refresh every 30 seconds
}

// Quick action functions
function runScanner() {
    alert('Scanner execution would be triggered here');
}

function ingestData() {
    alert('Data ingestion would be triggered here');
}

function viewLogs() {
    window.location.href = '/system';
}

function systemStatus() {
    window.location.href = '/system';
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});
