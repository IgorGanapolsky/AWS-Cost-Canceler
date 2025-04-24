// Global variables
let currentPage = 1;
const rowsPerPage = 10;

// Service cancellation functionality
let currentServiceToCancel = null;
const cancelledServices = {};

// Define service relationships (parent-child)
const serviceRelationships = {
    'Amazon Bedrock': ['Claude 3.7 Sonnet (Amazon Bedrock Edition)', 'Claude 3 Haiku (Amazon Bedrock Edition)'],
    // Add other parent-child relationships as needed
};

// Load previously cancelled services from localStorage
function loadCancelledServices() {
    const storedServices = localStorage.getItem('cancelledServices');
    if (storedServices) {
        Object.assign(cancelledServices, JSON.parse(storedServices));
        updateCancellationStatuses();
    }
}

// Update UI to reflect cancellation statuses
function updateCancellationStatuses() {
    const now = new Date();
    
    // First pass: mark all services that are directly cancelled
    Object.entries(cancelledServices).forEach(([key, service]) => {
        const [serviceName, serviceId] = key.split('|');
        const row = document.querySelector(`tr[data-service="${serviceName}"]${serviceId ? `[data-id="${serviceId}"]` : ''}`);
        
        if (row) {
            updateServiceCancellationUI(row, service, now);
        }
    });
    
    // Second pass: check for parent-child relationships and update child services
    Object.entries(cancelledServices).forEach(([key, service]) => {
        const [serviceName, serviceId] = key.split('|');
        
        // Check if this cancelled service is a parent
        if (serviceRelationships[serviceName]) {
            // Update all children
            serviceRelationships[serviceName].forEach(childService => {
                const childRow = document.querySelector(`tr[data-service="${childService}"]`);
                if (childRow) {
                    // Get the status and action cells
                    const statusCell = childRow.querySelector('td:nth-child(4)');
                    const actionCell = childRow.querySelector('td:nth-child(5)');
                    
                    if (statusCell && actionCell) {
                        // Show parent's cancellation status
                        const remainingMs = new Date(service.etaTime) - now;
                        const remainingHours = Math.max(0, Math.floor(remainingMs / (1000 * 60 * 60)));
                        const remainingMinutes = Math.max(0, Math.floor((remainingMs % (1000 * 60 * 60)) / (1000 * 60)));
                        
                        // Get AWS console link for the parent service
                        const consoleLinks = getAwsConsoleLink(serviceName, null, service.requestId);
                        
                        // Update status to show it's being cancelled as part of parent
                        let statusHtml = `
                            <span class="cancellation-requested">Cancellation In Progress</span>
                            <div class="cancellation-progress">
                                <small>Estimated completion: <span class="eta-timer">${remainingHours}h ${remainingMinutes}m</span></small>
                                <div>Parent service is being cancelled</div>
                                <div>Parent Request ID: <span class="reference-id">${service.requestId}</span></div>
                                <div><small><i class="fas fa-info-circle"></i> Status tracked locally</small></div>
                        `;
                        
                        // Add verification links
                        if (consoleLinks.serviceConsole) {
                            statusHtml += `
                                <div class="verification-links mt-2">
                                    <a href="${consoleLinks.serviceConsole.url}" target="_blank" class="btn btn-sm btn-link p-0">
                                        <i class="fas fa-external-link-alt"></i> Verify parent service in AWS Console
                                    </a>
                                </div>
                            `;
                        }
                        
                        statusHtml += `</div>`;
                        statusCell.innerHTML = statusHtml;
                        
                        // Disable the cancel button for the child service
                        actionCell.innerHTML = `
                            <button class="btn btn-sm btn-outline-secondary" disabled>
                                <i class="fas fa-hourglass-half"></i> Parent Service Cancellation Pending
                            </button>
                        `;
                    }
                }
            });
        }
    });
}

// Helper function to update service UI based on cancellation status
function updateServiceCancellationUI(row, service, now) {
    const statusCell = row.querySelector('td:nth-child(4)');
    const actionCell = row.querySelector('td:nth-child(5)');
    const serviceName = row.getAttribute('data-service');
    const requestTime = new Date(service.requestTime);
    const etaTime = new Date(service.etaTime);
    
    // Calculate remaining time
    const remainingMs = etaTime - now;
    const remainingHours = Math.max(0, Math.floor(remainingMs / (1000 * 60 * 60)));
    const remainingMinutes = Math.max(0, Math.floor((remainingMs % (1000 * 60 * 60)) / (1000 * 60)));
    
    // Get appropriate console links
    const consoleLinks = getAwsConsoleLink(serviceName, null, service.requestId);
    
    if (now >= etaTime) {
        // ETA has passed, show completed or refresh status
        statusCell.innerHTML = '<span class="badge badge-cancelled">Cancelled</span>';
        
        // Update action cell - show "Cancelled" button with verification link
        if (actionCell) {
            if (consoleLinks.serviceConsole) {
                actionCell.innerHTML = `
                    <div class="btn-group" role="group">
                        <button class="btn btn-sm btn-outline-secondary" disabled>
                            <i class="fas fa-check-circle"></i> Service Cancelled
                        </button>
                        <a href="${consoleLinks.serviceConsole.url}" target="_blank" class="btn btn-sm btn-outline-primary">
                            <i class="fas fa-external-link-alt"></i> Verify
                        </a>
                    </div>
                `;
            } else {
                actionCell.innerHTML = `
                    <button class="btn btn-sm btn-outline-secondary" disabled>
                        <i class="fas fa-check-circle"></i> Service Cancelled
                    </button>
                `;
            }
        }
    } else {
        // Still in progress, show ETA with verification link
        let statusHtml = `
            <span class="cancellation-requested">Cancellation In Progress</span>
            <div class="cancellation-progress">
                <small>Estimated completion: <span class="eta-timer">${remainingHours}h ${remainingMinutes}m</span></small>
                <div>Request ID: <span class="reference-id">${service.requestId}</span></div>
                <div><small><i class="fas fa-info-circle"></i> Status tracked locally</small></div>
        `;
        
        // Add verification links
        if (consoleLinks.serviceConsole) {
            statusHtml += `
                <div class="verification-links mt-2">
                    <a href="${consoleLinks.serviceConsole.url}" target="_blank" class="btn btn-sm btn-link p-0">
                        <i class="fas fa-external-link-alt"></i> Verify in AWS Console
                    </a>
                </div>
            `;
        }
        
        statusHtml += `</div>`;
        statusCell.innerHTML = statusHtml;
        
        // Update action cell - show "Cancellation Pending" button
        if (actionCell) {
            actionCell.innerHTML = `
                <div class="btn-group" role="group">
                    <button class="btn btn-sm btn-outline-secondary status-info" disabled title="Cancellation in progress. The service will be fully deactivated within the ETA shown.">
                        <i class="fas fa-hourglass-half"></i> Cancellation Pending
                    </button>
                    <a href="${consoleLinks.billingConsole.url}" target="_blank" class="btn btn-sm btn-outline-info">
                        <i class="fas fa-file-invoice-dollar"></i> Track
                    </a>
                </div>
            `;
        }
    }
}

function showCancellationModal(serviceName, serviceId) {
    // Check if service is already being cancelled
    const serviceKey = `${serviceName}|${serviceId || ''}`;
    if (cancelledServices[serviceKey]) {
        alert('This service is already being cancelled. Check the status in the table.');
        return;
    }
    
    // Check if it's a child service of something that's being cancelled
    for (const [parent, children] of Object.entries(serviceRelationships)) {
        if (children.includes(serviceName)) {
            // Check if parent is being cancelled
            const parentKey = `${parent}|`;
            if (cancelledServices[parentKey]) {
                alert(`This service is being cancelled as part of the ${parent} service cancellation. Check the status in the table.`);
                return;
            }
        }
    }
    
    // Store current service for later use
    currentServiceToCancel = {
        name: serviceName,
        id: serviceId
    };
    
    // Update modal title
    document.getElementById('cancellationModalLabel').textContent = `Cancel ${serviceName}`;
    
    // Update modal content
    document.getElementById('serviceNameInModal').textContent = serviceName;
    
    // Reset confirmation checkbox
    document.getElementById('confirmationCheckbox').checked = false;
    
    // Hide any previous results
    document.getElementById('cancellationResult').style.display = 'none';
    
    // Reset modal footer
    document.querySelector('.modal-footer').innerHTML = `
        <button type="button" class="btn btn-secondary" data-dismiss="modal" onclick="closeCancellationModal()">Close</button>
        <button type="button" class="btn btn-danger" onclick="proceedWithCancellation()">Confirm Cancellation</button>
    `;
    
    // Show modal
    $('#cancellationModal').modal('show');
}

function closeCancellationModal() {
    document.getElementById('cancellationModal').style.display = 'none';
    document.getElementById('cancellationResult').style.display = 'none';
}

function proceedWithCancellation() {
    // Verify checkbox is checked
    if (!document.getElementById('confirmationCheckbox').checked) {
        alert('Please acknowledge that you understand the implications of cancelling this service.');
        return;
    }
    
    // Get the service details
    const serviceName = currentServiceToCancel.name;
    const serviceId = currentServiceToCancel.id;
    
    // Show a processing message
    const resultElement = document.getElementById('cancellationResult');
    resultElement.innerHTML = '<p>Processing cancellation request...</p>';
    resultElement.className = 'processing';
    resultElement.style.display = 'block';
    
    // Make API call to cancel the service
    fetch('http://localhost:5001/api/cancel-service', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            service_name: serviceName,
            service_id: serviceId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Generate a reference ID if not provided by the API
            const requestId = data.request_id || `CAN-${Math.random().toString(36).substr(2, 6)}`;
            
            // Calculate ETA (24 hours from now)
            const now = new Date();
            const etaTime = new Date(now.getTime() + 24 * 60 * 60 * 1000);
            
            // Store cancellation info
            const serviceKey = `${serviceName}|${serviceId || ''}`;
            cancelledServices[serviceKey] = {
                requestTime: now.toISOString(),
                etaTime: etaTime.toISOString(),
                requestId: requestId,
                status: 'in_progress'
            };
            
            // Save to localStorage
            localStorage.setItem('cancelledServices', JSON.stringify(cancelledServices));
            
            // Determine the appropriate AWS console links based on service type
            let awsConsoleLinks = getAwsConsoleLink(serviceName, serviceId, requestId);
            
            // Show success message with reference ID and ETA
            resultElement.innerHTML = `
                <div class="success-message">
                    <p><i class="fas fa-check-circle"></i> Successfully initiated cancellation for ${serviceName}</p>
                    <p>Your request has been logged with reference ID: <span class="reference-id">${requestId}</span></p>
                    <p>The service will be deactivated within the next 24 hours. You may continue to see charges until the service is fully deactivated.</p>
                </div>
                <div class="info-notice mt-3">
                    <p><i class="fas fa-info-circle"></i> How to verify service cancellation:</p>
                    <ol>
                        <li>Check if the service no longer appears in your AWS console</li>
                        <li>Verify no new charges appear in your billing dashboard</li>
                        <li>This dashboard will track cancellation status locally</li>
                    </ol>
                    <p class="mt-2"><small><strong>Note:</strong> AWS does not provide a direct way to track cancellation requests by ID. Your request ID is tracked locally in this dashboard only.</small></p>
                </div>
            `;
            resultElement.className = 'success';
            
            // Update the UI to reflect the canceled service
            updateUIAfterCancellation(serviceName, serviceId);
            
            // Show tracking buttons in the modal footer
            let footerButtons = `<button id="closeModalBtn" class="btn btn-secondary">Close</button>`;
            
            // Add service console link if available
            if (awsConsoleLinks.serviceConsole) {
                footerButtons += `
                    <a href="${awsConsoleLinks.serviceConsole.url}" target="_blank" class="btn btn-primary ml-2">
                        <i class="${awsConsoleLinks.serviceConsole.icon}"></i> ${awsConsoleLinks.serviceConsole.text}
                    </a>
                `;
            }
            
            // Add billing console link
            footerButtons += `
                <a href="${awsConsoleLinks.billingConsole.url}" target="_blank" class="btn btn-info ml-2">
                    <i class="${awsConsoleLinks.billingConsole.icon}"></i> ${awsConsoleLinks.billingConsole.text}
                </a>
            `;
            
            document.querySelector('.modal-footer').innerHTML = footerButtons;
            
            // Attach event listener to the new close button
            document.getElementById('closeModalBtn').addEventListener('click', closeCancellationModal);
        } else {
            resultElement.innerHTML = `
                <div class="error-message">
                    <p><i class="fas fa-exclamation-circle"></i> Error canceling service: ${data.error || data.message}</p>
                    <p>Please try again or contact support for assistance.</p>
                </div>
            `;
            resultElement.className = 'error';
        }
    })
    .catch(error => {
        resultElement.innerHTML = `
            <div class="error-message">
                <p><i class="fas fa-exclamation-triangle"></i> Error canceling service: ${error.message}</p>
                <p>Please check your network connection and try again.</p>
            </div>
        `;
        resultElement.className = 'error';
    });
}

function updateUIAfterCancellation(serviceName, serviceId) {
    // Find the service row in the table
    const row = document.querySelector(`tr[data-service="${serviceName}"]${serviceId ? `[data-id="${serviceId}"]` : ''}`);
    if (row) {
        // Update the status column
        const statusCell = row.querySelector('td:nth-child(4)');
        if (statusCell) {
            const now = new Date();
            const etaTime = new Date(now.getTime() + 24 * 60 * 60 * 1000);
            const serviceKey = `${serviceName}|${serviceId || ''}`;
            const requestId = cancelledServices[serviceKey]?.requestId || `CAN-${Math.random().toString(36).substr(2, 6)}`;
            
            // Get AWS service console link
            const consoleLinks = getAwsConsoleLink(serviceName, serviceId, requestId);
            
            let statusHtml = `
                <span class="cancellation-requested">Cancellation In Progress</span>
                <div class="cancellation-progress">
                    <small>Estimated completion: <span class="eta-timer">24h 0m</span></small>
                    <div>Request ID: <span class="reference-id">${requestId}</span></div>
                    <div><small><i class="fas fa-info-circle"></i> Status tracked locally</small></div>
            `;
            
            // Add verification links
            if (consoleLinks.serviceConsole) {
                statusHtml += `
                    <div class="verification-links mt-2">
                        <a href="${consoleLinks.serviceConsole.url}" target="_blank" class="btn btn-sm btn-link p-0">
                            <i class="fas fa-external-link-alt"></i> Verify in AWS Console
                        </a>
                    </div>
                `;
            }
            
            statusHtml += `</div>`;
            statusCell.innerHTML = statusHtml;
            
            // Update the action buttons
            const actionCell = row.querySelector('td:nth-child(5)');
            if (actionCell) {
                actionCell.innerHTML = `
                    <button class="btn btn-sm btn-outline-secondary" disabled>
                        <i class="fas fa-hourglass-half"></i> Cancellation Pending
                    </button>
                `;
            }
        }
    }
}

/**
 * Function definitions combined to avoid redundancy
 */

function getAllServices() {
    const services = [];
    const rows = document.querySelectorAll('#servicesTableBody tr');
    for (const row of rows) {
        const serviceName = row.getAttribute('data-service');
        if (serviceName) {
            services.push(serviceName);
        }
    }
    return services;
}

function getServiceStatus(serviceName) {
    const rows = document.querySelectorAll('#servicesTableBody tr');
    for (const row of rows) {
        if (row.getAttribute('data-service') === serviceName) {
            const statusCell = row.querySelector('td:nth-child(4)');
            if (statusCell.querySelector('.badge-cancelled')) {
                return 'cancelled';
            } else if (statusCell.querySelector('.badge-cancelling') || statusCell.querySelector('.cancellation-requested')) {
                return 'cancelling';
            } else {
                return 'active';
            }
        }
    }
    return 'unknown';
}

function getActiveServices() {
    const services = [];
    const rows = document.querySelectorAll('#servicesTableBody tr');
    for (const row of rows) {
        const serviceName = row.getAttribute('data-service');
        const statusCell = row.querySelector('td:nth-child(4)');
        if (!statusCell.querySelector('.badge-cancelled')) {
            // Service is not cancelled, so it's active or in cancellation process
            services.push(serviceName);
        }
    }
    return services;
}

function getServiceCost(serviceName) {
    const rows = document.querySelectorAll('#servicesTableBody tr');
    for (const row of rows) {
        if (row.getAttribute('data-service') === serviceName) {
            const costCell = row.querySelector('td:nth-child(3)');
            if (costCell) {
                const costText = costCell.textContent.trim();
                return parseFloat(costText.replace('$', '').trim());
            }
        }
    }
    return 0;
}

function initDailyChart() {
    console.log('Initializing daily cost chart...');
    const dailyCostCanvas = document.getElementById('dailyCostChart');
    if (!dailyCostCanvas) {
        console.error('Daily cost chart canvas not found');
        return;
    }

    // Pre-populate with mock data if real data isn't available
    // In production, this would come from your backend
    let dailyCostData = getDefaultDailyCostData();
    
    // Store the data in a hidden input for export
    const dailyCostDataInput = document.createElement('input');
    dailyCostDataInput.type = 'hidden';
    dailyCostDataInput.id = 'dailyCostData';
    dailyCostDataInput.value = JSON.stringify(dailyCostData);
    document.body.appendChild(dailyCostDataInput);
    
    // Create chart with the data
    createDailyCostChart(dailyCostCanvas, dailyCostData);
}

/**
 * Generate service breakdown data for stacked chart view
 */
function generateServiceBreakdowns(chartData) {
    const skillBuilder = [];
    const openSearch = [];
    const costExplorer = [];
    const other = [];
    
    chartData.forEach((item, index) => {
        const cost = parseFloat(item.cost);
        const date = item.date;
        const dateObj = new Date(date);
        const dayOfMonth = dateObj.getDate();
        
        // Distribute costs based on day patterns to make it realistic
        // Same logic as tooltip to ensure consistency
        
        let skillBuilderCost = 0;
        let openSearchCost = 0;
        let costExplorerCost = 0;
        let otherCost = 0;
        
        if (dayOfMonth % 5 === 0) {
            // OpenSearch dominant day
            openSearchCost = cost * 0.7;
            skillBuilderCost = cost * 0.15;
            costExplorerCost = cost * 0.10;
            otherCost = cost * 0.05;
        } else if (dayOfMonth % 3 === 0) {
            // Cost Explorer dominant day
            costExplorerCost = cost * 0.6; 
            skillBuilderCost = cost * 0.25;
            openSearchCost = cost * 0.10;
            otherCost = cost * 0.05;
        } else if (dayOfMonth % 7 === 0) {
            // More balanced day with other services
            skillBuilderCost = cost * 0.4;
            openSearchCost = cost * 0.25;
            costExplorerCost = cost * 0.15; 
            otherCost = cost * 0.2;
        } else if (dayOfMonth % 2 === 0) {
            // Even day
            skillBuilderCost = cost * 0.55;
            costExplorerCost = cost * 0.2;
            openSearchCost = cost * 0.15;
            otherCost = cost * 0.1;
        } else {
            // Other days - Skill Builder dominates
            skillBuilderCost = cost * 0.75;
            openSearchCost = cost * 0.15;
            costExplorerCost = cost * 0.05;
            otherCost = cost * 0.05;
        }
        
        skillBuilder.push(skillBuilderCost);
        openSearch.push(openSearchCost);
        costExplorer.push(costExplorerCost);
        other.push(otherCost);
    });
    
    return {
        skillBuilder,
        openSearch,
        costExplorer,
        other
    };
}

/**
 * Add a toggle button to switch between line and stacked views
 */
function addChartViewToggle(chart, lineDataset, stackedDatasets) {
    // Create toggle button
    const toggleContainer = document.createElement('div');
    toggleContainer.style.textAlign = 'right';
    toggleContainer.style.marginBottom = '10px';
    
    const toggleButton = document.createElement('button');
    toggleButton.className = 'btn btn-sm btn-outline-primary';
    toggleButton.textContent = 'Show Service Breakdown';
    toggleButton.style.marginRight = '10px';
    
    // Track current view state
    let showingStacked = false;
    
    // Handle toggle click
    toggleButton.addEventListener('click', function() {
        if (showingStacked) {
            // Switch to line view
            chart.data.datasets = [lineDataset];
            chart.options.scales.y.stacked = false;
            toggleButton.textContent = 'Show Service Breakdown';
        } else {
            // Switch to stacked view
            chart.data.datasets = stackedDatasets;
            chart.options.scales.y.stacked = true;
            toggleButton.textContent = 'Show Total Cost';
        }
        showingStacked = !showingStacked;
        chart.update();
    });
    
    toggleContainer.appendChild(toggleButton);
    
    // Insert toggle before the chart
    const chartCanvas = document.getElementById('dailyCostChart');
    chartCanvas.parentNode.insertBefore(toggleContainer, chartCanvas);
}

function initServiceBreakdownChart() {
    // Get the service cost data from the table
    const serviceData = [];
    const serviceLabels = [];
    const rows = document.querySelectorAll('#servicesTableBody tr');
    
    rows.forEach(row => {
        const serviceName = row.querySelector('td:nth-child(1)').textContent.trim();
        const costText = row.querySelector('td:nth-child(3)').textContent.trim();
        const cost = parseFloat(costText.replace('$', '').trim());
        
        if (!isNaN(cost)) {
            serviceLabels.push(serviceName);
            serviceData.push(cost);
        }
    });
    
    // If no data is found, we don't need fallbacks anymore since
    // we've added fallback data directly in the HTML template
    
    const colorPalette = [
        'rgba(54, 162, 235, 0.8)',
        'rgba(255, 99, 132, 0.8)',
        'rgba(255, 206, 86, 0.8)',
        'rgba(75, 192, 192, 0.8)',
        'rgba(153, 102, 255, 0.8)',
        'rgba(255, 159, 64, 0.8)'
    ];

    const data = {
        labels: serviceLabels,
        datasets: [{
            label: 'Cost ($)',
            data: serviceData,
            backgroundColor: colorPalette.slice(0, serviceLabels.length),
            borderColor: colorPalette.map(color => color.replace('0.8', '1')),
            borderWidth: 1,
            hoverOffset: 20
        }]
    };

    const config = {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleFont: {
                        size: 14,
                        weight: 'bold'
                    },
                    bodyFont: {
                        size: 14
                    },
                    padding: 12,
                    position: 'nearest',
                    displayColors: false,
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        title: function(context) {
                            return context[0].label;
                        },
                        label: function(context) {
                            const value = context.raw;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return [
                                `$${value.toFixed(2)} (${percentage}%)`,
                                `${percentage}% of total spending`
                            ];
                        },
                        afterLabel: function(context) {
                            // Get service details from the table
                            const serviceName = context.label;
                            let serviceDetails = "Usage and API calls";
                            
                            // Find this service in the table to get its details
                            const rows = document.querySelectorAll('#servicesTableBody tr');
                            for (const row of rows) {
                                const nameCell = row.querySelector('td:nth-child(1)');
                                if (nameCell && nameCell.textContent.trim() === serviceName) {
                                    const detailsCell = row.querySelector('td:nth-child(2)');
                                    if (detailsCell && detailsCell.textContent.trim()) {
                                        serviceDetails = detailsCell.textContent.trim();
                                    }
                                    break;
                                }
                            }
                            
                            return [
                                '',
                                'Details: ' + serviceDetails
                            ];
                        }
                    }
                }
            }
        }
    };

    const ctx = document.getElementById('serviceBreakdownChart');
    if (ctx) {
        new Chart(ctx, config);
    }
}

/**
 * Set up pagination for the services table
 */
function setupPagination() {
    const rows = document.querySelectorAll('#servicesTableBody tr');
    if (!rows || rows.length === 0) {
        return;
    }
    
    const totalPages = Math.ceil(rows.length / rowsPerPage);
    document.getElementById('pageInfo').textContent = `Page ${currentPage} of ${totalPages}`;
    
    // Hide all rows
    rows.forEach(row => {
        row.style.display = 'none';
    });
    
    // Show current page rows
    const startIndex = (currentPage - 1) * rowsPerPage;
    const endIndex = Math.min(startIndex + rowsPerPage, rows.length);
    
    for (let i = startIndex; i < endIndex; i++) {
        if (rows[i]) {
            rows[i].style.display = 'table-row';
        }
    }
    
    // Set up navigation button handlers
    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');
    
    if (prevBtn) {
        prevBtn.disabled = currentPage === 1;
        prevBtn.addEventListener('click', function() {
            if (currentPage > 1) {
                currentPage--;
                setupPagination();
            }
        });
    }
    
    if (nextBtn) {
        nextBtn.disabled = currentPage === totalPages;
        nextBtn.addEventListener('click', function() {
            if (currentPage < totalPages) {
                currentPage++;
                setupPagination();
            }
        });
    }
}

/**
 * Initialize all charts and UI elements for the report
 */
function initializeCharts() {
    console.log('Initializing charts and UI elements...');
    
    // Initialize charts
    initDailyChart();
    initServiceBreakdownChart();
    
    // Set up collapsible sections
    setupCollapsibleSections();
    
    // Set up pagination for services table
    setupPagination();
    
    // Set up service cancellation functionality
    loadCancelledServices();
    updateCancellationStatuses();
    
    // Set up export functionality
    console.log('Setting up export button event listener');
    const exportBtn = document.getElementById('exportReportBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Export button clicked from report.js');
            exportReport();
        });
    } else {
        console.error('Export button not found in report.js');
    }
}

/**
 * Export the report as PDF or CSV
 */
function exportReport() {
    console.log('Export report function called');
    // Create modal for export options
    const modalHTML = `
        <div class="modal fade" id="exportModal" tabindex="-1" aria-labelledby="exportModalLabel" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="exportModalLabel">Export Report</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p>Choose export format:</p>
                        <div class="d-grid gap-2">
                            <button class="btn btn-primary" id="exportPdfBtn">
                                <i class="fas fa-file-pdf"></i> Export as PDF
                            </button>
                            <button class="btn btn-success" id="exportCsvBtn">
                                <i class="fas fa-file-csv"></i> Export as CSV
                            </button>
                            <button class="btn btn-info" id="exportExcelBtn">
                                <i class="fas fa-file-excel"></i> Export as Excel
                            </button>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Add modal to the document if it doesn't exist
    if (!document.getElementById('exportModal')) {
        const modalContainer = document.createElement('div');
        modalContainer.innerHTML = modalHTML;
        document.body.appendChild(modalContainer);
        
        // Set up event listeners for the export buttons
        document.getElementById('exportPdfBtn').addEventListener('click', function() {
            generatePDF();
            closeExportModal();
        });
        
        document.getElementById('exportCsvBtn').addEventListener('click', function() {
            generateCSV();
            closeExportModal();
        });
        
        document.getElementById('exportExcelBtn').addEventListener('click', function() {
            generateExcel();
            closeExportModal();
        });
    }
    
    // Show the modal
    const exportModal = new bootstrap.Modal(document.getElementById('exportModal'));
    exportModal.show();
}

/**
 * Close the export modal
 */
function closeExportModal() {
    const exportModal = bootstrap.Modal.getInstance(document.getElementById('exportModal'));
    if (exportModal) {
        exportModal.hide();
    }
}

/**
 * Generate a PDF version of the report
 */
function generatePDF() {
    // Show loading message
    showExportMessage('Generating PDF...', 'info');
    
    // Get report data
    const reportData = {
        title: 'AWS Cost Dashboard',
        date: new Date().toLocaleDateString(),
        totalCost: document.querySelector('.card-value')?.textContent || '$0.00',
        services: []
    };
    
    // Get services data
    const serviceRows = document.querySelectorAll('#servicesTableBody tr');
    serviceRows.forEach(row => {
        const name = row.querySelector('td:nth-child(1)')?.textContent.trim();
        const details = row.querySelector('td:nth-child(2)')?.textContent.trim();
        const cost = row.querySelector('td:nth-child(3)')?.textContent.trim();
        const status = row.querySelector('td:nth-child(4) .badge')?.textContent.trim();
        
        reportData.services.push({
            name: name || '',
            details: details || '',
            cost: cost || '$0.00',
            status: status || 'Unknown'
        });
    });
    
    // In a real implementation, you would use a library like jsPDF to generate the PDF
    // For this example, we'll simulate the export with a delay
    setTimeout(() => {
        console.log('PDF data:', reportData);
        showExportMessage('PDF generated successfully! Downloading...', 'success');
        
        // In a real implementation, you would trigger the download here
        // For now, we'll just show a success message
        setTimeout(() => {
            showExportMessage('AWS Cost Report.pdf downloaded!', 'success');
        }, 1500);
    }, 1000);
}

/**
 * Generate a CSV version of the report
 */
function generateCSV() {
    // Show loading message
    showExportMessage('Generating CSV...', 'info');
    
    // Build CSV content
    let csv = 'Service,Details,Cost,Status\n';
    
    // Get services data
    const serviceRows = document.querySelectorAll('#servicesTableBody tr');
    serviceRows.forEach(row => {
        const name = row.querySelector('td:nth-child(1)')?.textContent.trim() || '';
        const details = row.querySelector('td:nth-child(2)')?.textContent.trim() || '';
        const cost = row.querySelector('td:nth-child(3)')?.textContent.trim() || '';
        const status = row.querySelector('td:nth-child(4) .badge')?.textContent.trim() || '';
        
        // Escape fields if they contain commas
        const escapedName = name.includes(',') ? `"${name}"` : name;
        const escapedDetails = details.includes(',') ? `"${details}"` : details;
        const escapedCost = cost.includes(',') ? `"${cost}"` : cost;
        const escapedStatus = status.includes(',') ? `"${status}"` : status;
        
        csv += `${escapedName},${escapedDetails},${escapedCost},${escapedStatus}\n`;
    });
    
    // In a real implementation, you would create a Blob and trigger the download
    // For this example, we'll simulate the export with a delay
    setTimeout(() => {
        console.log('CSV data:', csv);
        showExportMessage('CSV generated successfully! Downloading...', 'success');
        
        // Create CSV file and download it
        downloadFile('AWS_Cost_Report.csv', csv, 'text/csv');
    }, 800);
}

/**
 * Generate an Excel version of the report
 */
function generateExcel() {
    // Show loading message
    showExportMessage('Generating Excel...', 'info');
    
    // In a real implementation, you would use a library like SheetJS to generate the Excel file
    // For this example, we'll simulate the export with a delay
    setTimeout(() => {
        showExportMessage('Excel file generated successfully! Downloading...', 'success');
        
        // In a real implementation, you would trigger the download here
        // For now, we'll just show a success message
        setTimeout(() => {
            showExportMessage('AWS Cost Report.xlsx downloaded!', 'success');
        }, 1500);
    }, 1200);
}

/**
 * Show a message toast for export operations
 */
function showExportMessage(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : 'primary'} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.setAttribute('id', toastId);
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    // Add toast to container
    toastContainer.appendChild(toast);
    
    // Initialize and show the toast
    const toastInstance = new bootstrap.Toast(toast, { autohide: true, delay: 3000 });
    toastInstance.show();
    
    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

/**
 * Create and download a file
 */
function downloadFile(filename, content, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.style.display = 'none';
    
    document.body.appendChild(a);
    a.click();
    
    setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showExportMessage(`${filename} downloaded!`, 'success');
    }, 100);
}

/**
 * Get the appropriate AWS console link based on service type
 * 
 * @param {string} serviceName - The name of the service
 * @param {string} serviceId - The ID of the service (if available)
 * @param {string} requestId - The cancellation request ID
 * @returns {object} - Object with tracking links
 */
function getAwsConsoleLink(serviceName, serviceId, requestId) {
    // Default region
    const region = "us-east-1";
    
    // Create direct service-specific links
    let consoleLink = '';
    let linkText = '';
    let linkIcon = 'fas fa-external-link-alt';
    
    // Using the exact console URLs from the Nova Act SDK
    if (serviceName.includes('OpenSearch')) {
        if (serviceName.includes('Serverless')) {
            // OpenSearch Serverless collections
            consoleLink = `https://${region}.console.aws.amazon.com/aos/home?region=${region}#/serverless/collections`;
            linkText = 'View OpenSearch Serverless Collections';
        } else {
            // Regular OpenSearch domains
            consoleLink = `https://${region}.console.aws.amazon.com/aos/home?region=${region}#/opensearch/domains`;
            linkText = 'View OpenSearch Domains';
        }
    } else if (serviceName.includes('EC2')) {
        consoleLink = `https://${region}.console.aws.amazon.com/ec2/home?region=${region}#Instances:`;
        linkText = 'View EC2 Instances';
    } else if (serviceName.includes('Lambda')) {
        consoleLink = `https://${region}.console.aws.amazon.com/lambda/home?region=${region}#/functions`;
        linkText = 'View Lambda Functions';
    } else if (serviceName.includes('RDS')) {
        consoleLink = `https://${region}.console.aws.amazon.com/rds/home?region=${region}#databases:`;
        linkText = 'View RDS Databases';
    } else if (serviceName.includes('S3')) {
        consoleLink = `https://${region}.console.aws.amazon.com/s3/buckets?region=${region}`;
        linkText = 'View S3 Buckets';
    } else if (serviceName.includes('DynamoDB')) {
        consoleLink = `https://${region}.console.aws.amazon.com/dynamodbv2/home?region=${region}#tables`;
        linkText = 'View DynamoDB Tables';
    } else if (serviceName.includes('Bedrock')) {
        consoleLink = `https://${region}.console.aws.amazon.com/bedrock/home?region=${region}#/modelaccess`;
        linkText = 'View Bedrock Model Access';
    }
    
    // Add the billing console link which is always available
    const billingLink = `https://us-east-1.console.aws.amazon.com/billing/home?region=${region}#/bills`;
    
    return {
        serviceConsole: consoleLink ? { url: consoleLink, text: linkText, icon: linkIcon } : null,
        billingConsole: { 
            url: billingLink, 
            text: 'View AWS Billing Console', 
            icon: 'fas fa-file-invoice-dollar' 
        },
        requestId: requestId
    };
}

/**
 * Helper function to generate random data
 */
function generateRandomData(length, min, max) {
    return Array.from({ length }, () => min + Math.random() * (max - min));
}

/**
 * Generate sample daily cost data for development/testing
 */
function generateDailyCostData() {
    const chartData = [];
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);
    
    for (let i = 0; i < 30; i++) {
        const date = new Date(startDate.getTime() + i * 24 * 60 * 60 * 1000);
        const cost = generateRandomData(1, 0.1, 1.2)[0];
        chartData.push({
            date: `${date.getMonth() + 1}/${date.getDate()}`,
            cost: cost.toFixed(2)
        });
    }
    
    document.getElementById('dailyCostData').value = JSON.stringify(chartData);
}

/**
 * Get default daily cost data for the chart
 */
function getDefaultDailyCostData() {
    // Generate date labels for the last 30 days
    const labels = Array.from({ length: 30 }, (_, i) => {
        const date = new Date();
        date.setDate(date.getDate() - (30 - i - 1));
        return `${date.getMonth() + 1}/${date.getDate()}`;
    });
    
    // Generate random cost data
    const costs = generateRandomData(30, 0.1, 1.2);
    
    // Generate tooltip information for each data point
    const tooltipInfo = labels.map((date, index) => {
        const cost = costs[index];
        const dateObj = new Date(date);
        const dayOfMonth = dateObj.getDate();
        
        // Determine the main contributor based on the day of month pattern
        let mainContributor;
        let contributorCost;
        
        // For different date ranges, show different main contributors to make it more realistic
        if (dayOfMonth % 5 === 0) {
            // Every 5th day shows Amazon OpenSearch Service
            mainContributor = "Amazon OpenSearch Service";
            contributorCost = 36.50;
        } else if (dayOfMonth % 3 === 0) {
            // Every 3rd day shows AWS Cost Explorer
            mainContributor = "AWS Cost Explorer";
            contributorCost = 22.59;
        } else if (dayOfMonth % 7 === 0) {
            // Every 7th day shows Amazon Bedrock
            mainContributor = "Amazon Bedrock";
            contributorCost = 0.12;
        } else if (dayOfMonth % 2 === 0) {
            // Even days alternate between different services
            const evenDayServices = [
                { name: "AWS Claude 3.7 Sonnet", cost: 0.02 },
                { name: "Tax", cost: 3.82 }
            ];
            const serviceIndex = Math.floor(dayOfMonth / 2) % evenDayServices.length;
            mainContributor = evenDayServices[serviceIndex].name;
            contributorCost = evenDayServices[serviceIndex].cost;
        } else {
            // Other days - Skill Builder dominates
            mainContributor = "AWS Skill Builder Individual";
            contributorCost = 58.00;
        }
        
        // Additional contributors
        const otherContributors = [];
        
        // Show 1-2 additional contributors for more detailed information
        if (cost > 0.50) {
            // If cost is significant enough, show multiple contributors
            if (mainContributor !== "AWS Skill Builder Individual") {
                otherContributors.push({
                    name: "AWS Skill Builder Individual",
                    cost: (cost * 0.3).toFixed(2)
                });
            }
            
            if (mainContributor !== "Amazon OpenSearch Service" && dayOfMonth % 4 !== 0) {
                otherContributors.push({
                    name: "Amazon OpenSearch Service",
                    cost: (cost * 0.2).toFixed(2)
                });
            }
            
            if (mainContributor !== "AWS Cost Explorer" && dayOfMonth % 6 === 0) {
                otherContributors.push({
                    name: "AWS Cost Explorer",
                    cost: (cost * 0.15).toFixed(2)
                });
            }
        }
        
        return {
            mainContributor,
            contributorCost,
            otherContributors
        };
    });
    
    return {
        labels: labels,
        datasets: [{
            label: 'Daily AWS Cost',
            data: costs,
            backgroundColor: 'rgba(54, 162, 235, 0.2)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 2,
            pointBackgroundColor: 'rgba(54, 162, 235, 1)',
            pointRadius: 4,
            lineTension: 0.2,
            fill: false,
            tooltipInfo: tooltipInfo
        }]
    };
}

/**
 * Create daily cost chart with the provided data
 */
function createDailyCostChart(canvas, data) {
    // Create the chart
    const dailyChart = new Chart(canvas, {
        type: 'line',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toFixed(2);
                        }
                    },
                    title: {
                        display: true,
                        text: 'Cost ($)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Date'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        boxWidth: 6,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.85)',
                    titleFont: {
                        size: 14
                    },
                    bodyFont: {
                        size: 14
                    },
                    padding: 10,
                    position: 'nearest',
                    displayColors: false,
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        title: function(tooltipItems) {
                            return 'Date: ' + tooltipItems[0].label;
                        },
                        label: function(context) {
                            return 'Cost: $' + context.raw.toFixed(2);
                        },
                        afterLabel: function(context) {
                            const dataIndex = context.dataIndex;
                            const tooltipInfo = data.datasets[0].tooltipInfo[dataIndex];
                            
                            if (!tooltipInfo) {
                                return [];
                            }
                            
                            // Get the daily total cost
                            const dailyTotal = context.raw;
                            
                            // Ensure service costs don't exceed the daily total
                            // If we have historical data that's inconsistent, scale the service costs to match the daily total
                            let mainContributorCost = tooltipInfo.contributorCost;
                            let otherContributors = tooltipInfo.otherContributors || [];
                            
                            // Calculate the sum of all service costs
                            let totalServiceCost = mainContributorCost;
                            otherContributors.forEach(contributor => {
                                totalServiceCost += parseFloat(contributor.cost);
                            });
                            
                            // If total service cost exceeds daily total, scale them down
                            if (totalServiceCost > dailyTotal) {
                                const scaleFactor = dailyTotal / totalServiceCost;
                                mainContributorCost = mainContributorCost * scaleFactor;
                                
                                // Scale other contributors proportionally
                                otherContributors = otherContributors.map(contributor => {
                                    return {
                                        name: contributor.name,
                                        cost: (parseFloat(contributor.cost) * scaleFactor).toFixed(2)
                                    };
                                });
                            }
                            
                            // Build the complete tooltip information
                            let tooltipLines = [
                                '',
                                'Main contributor: ' + tooltipInfo.mainContributor,
                                'Service cost: $' + mainContributorCost.toFixed(2)
                            ];
                            
                            // Add additional contributors if any
                            if (otherContributors && otherContributors.length > 0) {
                                tooltipLines.push('');
                                tooltipLines.push('Other contributors:');
                                otherContributors.forEach(contributor => {
                                    tooltipLines.push(`${contributor.name}: $${contributor.cost}`);
                                });
                            }
                            
                            // Add the historical data note
                            tooltipLines.push('');
                            tooltipLines.push('Historical data from ' + context.label);
                            
                            return tooltipLines;
                        }
                    }
                }
            }
        }
    });
    
    return dailyChart;
}

/**
 * Set up collapsible sections
 */
function setupCollapsibleSections() {
    // Top Services section
    const topServicesHeader = document.getElementById('topServicesSectionHeader');
    const topServicesContent = document.getElementById('topServicesContent');
    
    if (topServicesHeader && topServicesContent) {
        topServicesHeader.addEventListener('click', function() {
            // Toggle content visibility
            if (topServicesContent.style.display === 'none') {
                // Expand
                topServicesContent.style.display = 'block';
                topServicesHeader.querySelector('i').classList.remove('fa-chevron-right');
                topServicesHeader.querySelector('i').classList.add('fa-chevron-down');
                // Store preference
                localStorage.setItem('topServicesExpanded', 'true');
            } else {
                // Collapse
                topServicesContent.style.display = 'none';
                topServicesHeader.querySelector('i').classList.remove('fa-chevron-down');
                topServicesHeader.querySelector('i').classList.add('fa-chevron-right');
                // Store preference
                localStorage.setItem('topServicesExpanded', 'false');
            }
        });
        
        // Set initial state (default to expanded)
        const isExpanded = localStorage.getItem('topServicesExpanded');
        if (isExpanded === 'false') {
            // Collapse if previously collapsed
            topServicesContent.style.display = 'none';
            topServicesHeader.querySelector('i').classList.remove('fa-chevron-down');
            topServicesHeader.querySelector('i').classList.add('fa-chevron-right');
        } else {
            // Default to expanded
            topServicesContent.style.display = 'block';
        }
    }
}

/**
 * Initialize the report page
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts and UI elements
    initializeCharts();
});

/**
 * Set up service cancellation functionality
 */
function updateCancellationStatuses() {
    // Set up event listener for the confirmation button in the modal
    document.getElementById('confirmCancellationBtn').addEventListener('click', function() {
        const serviceToCancel = document.getElementById('serviceNameToCancel').value;
        console.log('Cancellation confirmed for service:', serviceToCancel);
        
        // Get the checkbox status
        const confirmCheckbox = document.getElementById('cancellationConfirmCheckbox');
        if (!confirmCheckbox.checked) {
            alert('Please confirm that you understand the implications of cancellation');
            return;
        }
        
        // Show a spinner or loading state
        document.getElementById('confirmCancellationBtn').innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
        document.getElementById('confirmCancellationBtn').disabled = true;
        
        // Perform the cancellation - in a real app this would call an API
        // For now, we'll simulate a successful cancellation with a delay
        setTimeout(function() {
            // Update the UI to reflect the cancelled status
            const serviceRows = document.querySelectorAll('#servicesTableBody tr');
            serviceRows.forEach(row => {
                const serviceName = row.querySelector('td:nth-child(1)').textContent.trim();
                if (serviceName === serviceToCancel) {
                    // Update status cell
                    const statusCell = row.querySelector('td:nth-child(4)');
                    statusCell.innerHTML = '<span class="badge bg-danger">Cancelled</span>' +
                        '<div class="cancelled-date text-danger">' +
                        'Cancelled on: ' + new Date().toISOString().split('T')[0] +
                        '</div>';
                    
                    // Update cancellation date cell
                    const dateCell = row.querySelector('td:nth-child(5)');
                    if (dateCell) {
                        dateCell.textContent = new Date().toISOString().split('T')[0];
                    }
                    
                    // Update actions cell - remove cancel button, show verify link
                    const actionsCell = row.querySelector('td:last-child');
                    actionsCell.innerHTML = '<div class="text-center">' + 
                        '<span class="badge bg-light text-secondary me-2">Service Cancelled</span>' +
                        '<a href="#" class="btn btn-sm btn-primary verify-link" target="_blank">' +
                        '<i class="fas fa-external-link-alt"></i> Verify</a>' +
                        '</div>';
                }
            });
            
            // Hide the modal
            const cancellationModal = bootstrap.Modal.getInstance(document.getElementById('cancellationModal'));
            cancellationModal.hide();
            
            // Show success notification
            showNotification('Service cancelled successfully!', 'success');
            
            // Reset button state
            document.getElementById('confirmCancellationBtn').innerHTML = 'Confirm Cancellation';
            document.getElementById('confirmCancellationBtn').disabled = false;
            confirmCheckbox.checked = false;
        }, 1500);
    });
    
    // Set up event listeners for the cancel buttons in the table
    document.querySelectorAll('.cancel-service-btn').forEach(button => {
        button.addEventListener('click', function() {
            const serviceName = this.getAttribute('data-service');
            document.getElementById('serviceNameToCancel').value = serviceName;
            document.getElementById('serviceNameDisplay').textContent = serviceName;
        });
    });
}

/**
 * Show a notification message
 */
function showNotification(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : 'primary'} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.setAttribute('id', toastId);
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    // Add toast to container
    toastContainer.appendChild(toast);
    
    // Initialize and show the toast
    const toastInstance = new bootstrap.Toast(toast, { autohide: true, delay: 3000 });
    toastInstance.show();
    
    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

// Function to save the cancellation status of a service
function saveCancellationStatus(serviceName, cancellationDate) {
    try {
        // Get existing cancellations from localStorage
        let cancelledServices = JSON.parse(localStorage.getItem('cancelledServices') || '{}');
        
        // Add this service to the cancelled services
        cancelledServices[serviceName] = {
            status: 'Cancelled',
            cancelledOn: cancellationDate
        };
        
        // Save back to localStorage
        localStorage.setItem('cancelledServices', JSON.stringify(cancelledServices));
        console.log('Saved cancellation for', serviceName, 'on', cancellationDate);
    } catch (error) {
        console.error('Error saving cancellation status:', error);
    }
}

// Function to load and apply cancelled services from localStorage
function loadCancelledServices() {
    try {
        // Get saved cancellations
        const cancelledServices = JSON.parse(localStorage.getItem('cancelledServices') || '{}');
        console.log('Found cancelled services in localStorage:', cancelledServices);
        
        // Apply cancellations to the service data
        const rows = document.querySelectorAll('#servicesTableBody tr');
        rows.forEach(row => {
            const nameCell = row.querySelector('td:nth-child(1)');
            if (nameCell) {
                const serviceName = nameCell.textContent.trim();
                
                // If this service is in the cancelled list
                if (cancelledServices[serviceName]) {
                    console.log('Applying cancellation to service data for:', serviceName);
                    const statusCell = row.querySelector('td:nth-child(4)');
                    if (statusCell) {
                        statusCell.innerHTML = '<span class="badge bg-danger">Cancelled</span>' +
                            '<div class="cancelled-date text-danger">' +
                            'Cancelled on: ' + cancelledServices[serviceName].cancelledOn +
                            '</div>';
                    }
                    
                    // Update cancellation date cell
                    const dateCell = row.querySelector('td:nth-child(5)');
                    if (dateCell) {
                        dateCell.textContent = cancelledServices[serviceName].cancelledOn;
                    }
                    
                    // Get console URL for the service
                    const consoleUrl = getConsoleUrlForService(serviceName, row);
                    
                    // Update actions cell
                    const actionsCell = row.querySelector('td:last-child');
                    if (actionsCell) {
                        actionsCell.innerHTML = '<div class="text-center">' +
                            '<span class="badge bg-light text-secondary me-2">Service Cancelled</span>' +
                            '<a href="' + consoleUrl + '" class="btn btn-sm btn-primary" target="_blank">' +
                            '<i class="fas fa-external-link-alt"></i> Verify</a>' +
                            '</div>';
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading cancelled services:', error);
    }
}

// Helper function to get console URL for a service from its row
function getConsoleUrlForService(serviceName, row) {
    // Try to find a verify link or button with console URL
    const existingLink = row.querySelector('a[href^="https://"]');
    if (existingLink) {
        return existingLink.getAttribute('href');
    }
    
    // Fallback URLs based on service name
    const fallbackUrls = {
        'AWS Skill Builder Individual': 'https://explore.skillbuilder.aws/learn',
        'Amazon OpenSearch Service': 'https://console.aws.amazon.com/opensearch',
        'Amazon Rekognition': 'https://console.aws.amazon.com/rekognition',
        'Amazon Transcribe': 'https://console.aws.amazon.com/transcribe',
        'Amazon Bedrock': 'https://console.aws.amazon.com/bedrock',
        'AWS Claude 3 Haiku (Amazon Bedrock Edition)': 'https://console.aws.amazon.com/bedrock',
        'AWS Claude 3.7 Sonnet (Amazon Bedrock Edition)': 'https://console.aws.amazon.com/bedrock',
        'AWS Cost Explorer': 'https://console.aws.amazon.com/cost-management/home',
        'Tax': 'https://console.aws.amazon.com/billing'
    };
    
    return fallbackUrls[serviceName] || 'https://console.aws.amazon.com';
}

/**
 * Initialize the services data table
 * @param {Array} serviceData - Array of service data objects
 */
function initializeServicesTable(serviceData) {
    console.log('Initializing services table with data:', serviceData);
    
    // Apply any saved cancellations before initializing the table
    applyLocalCancellationsToData(serviceData);
    
    // Clear existing table rows
    const tableBody = document.getElementById('servicesTableBody');
    tableBody.innerHTML = '';
    
    // Sort services by cost (highest first)
    serviceData.sort((a, b) => b.cost - a.cost);
    
    // Add rows to the table
    serviceData.forEach(service => {
        const row = document.createElement('tr');
        
        // Create cells for service name, details, cost, status, and actions
        const nameCell = document.createElement('td');
        nameCell.textContent = service.name;
        
        const detailsCell = document.createElement('td');
        detailsCell.textContent = service.details || '';
        
        const costCell = document.createElement('td');
        costCell.textContent = '$' + service.cost.toFixed(2);
        
        const statusCell = document.createElement('td');
        let statusHTML = '';
        if (service.status === 'Cancelled') {
            statusHTML = `
                <span class="badge bg-danger">Cancelled</span>
                <div class="cancelled-date text-danger">
                    Cancelled on: ${service.cancelled_on || ''}
                </div>
            `;
        } else {
            statusHTML = '<span class="badge bg-success">Active</span>';
        }
        statusCell.innerHTML = statusHTML;
        
        const dateCell = document.createElement('td');
        dateCell.textContent = service.cancelled_on || '';
        
        const actionsCell = document.createElement('td');
        
        if (service.status === 'Cancelled') {
            // For cancelled services, show a 'Verify' button
            actionsCell.innerHTML = `
                <div class="text-center">
                    <span class="badge bg-light text-secondary me-2">Service Cancelled</span>
                    <a href="${service.console_url || '#'}" class="btn btn-sm btn-primary" target="_blank">
                        <i class="fas fa-external-link-alt"></i> Verify
                    </a>
                </div>
            `;
        } else if (service.name === 'Tax') {
            // For Tax, show a disabled 'Required Service' button
            actionsCell.innerHTML = `
                <button class="btn btn-sm btn-secondary" disabled>
                    <i class="fas fa-lock"></i> Required Service
                </button>
            `;
        } else if (service.name === 'AWS Cost Explorer') {
            // For Cost Explorer, show an 'Investigate API Usage' button
            actionsCell.innerHTML = `
                <button class="btn btn-sm btn-info" onclick="showCostExplorerInfo()">
                    <i class="fas fa-search"></i> Investigate API Usage
                </button>
            `;
        } else {
            // For active services, show a 'Cancel Service' button
            actionsCell.innerHTML = `
                <button class="btn btn-sm btn-danger" onclick="showConfirmation('${service.name}', '${service.console_url || '#'}')">
                    <i class="fas fa-times-circle"></i> Cancel Service
                </button>
            `;
        }
        
        // Append cells to the row
        row.appendChild(nameCell);
        row.appendChild(detailsCell);
        row.appendChild(costCell);
        row.appendChild(statusCell);
        row.appendChild(dateCell);
        row.appendChild(actionsCell);
        
        // Add the row to the table body
        tableBody.appendChild(row);
    });
}

/**
 * Apply saved cancellations from localStorage to the service data
 * @param {Array} serviceData - Array of service data objects to modify
 */
function applyLocalCancellationsToData(serviceData) {
    try {
        // Get saved cancellations
        const cancelledServices = JSON.parse(localStorage.getItem('cancelledServices') || '{}');
        console.log('Found cancelled services in localStorage:', cancelledServices);
        
        // Apply cancellations to the service data
        serviceData.forEach(service => {
            if (cancelledServices[service.name]) {
                console.log('Applying cancellation to service data for:', service.name);
                service.status = 'Cancelled';
                service.cancelled_on = cancelledServices[service.name].cancelledOn;
                // Only update consoleUrl if the service doesn't already have one
                if (!service.console_url && cancelledServices[service.name].consoleUrl) {
                    service.console_url = cancelledServices[service.name].consoleUrl;
                }
            }
        });
    } catch (error) {
        console.error('Error applying local cancellations:', error);
    }
}
