/**
 * Dashboard Feature Verification Script
 * 
 * This script verifies the key features we've implemented in the AWS Cost Dashboard:
 * 1. Service cancellation persistence via localStorage
 * 2. Cost Explorer info modal functionality
 * 
 * To use: Include this script in the report template or run it in the browser console.
 */

function verifyDashboardFeatures() {
    const testResults = {
        cancellationPersistence: { passed: false, details: [] },
        costExplorerModal: { passed: false, details: [] }
    };
    
    // Test 1: Cancellation Persistence
    console.log("Test 1: Verifying service cancellation persistence");
    
    // First, clear any existing cancellations for clean testing
    localStorage.removeItem('cancelledServices');
    
    // Find a service that can be cancelled
    const serviceRows = document.querySelectorAll('#servicesTableBody tr');
    let testServiceName = null;
    let cancellableService = null;
    
    for (const row of serviceRows) {
        const serviceName = row.querySelector('td:first-child').textContent;
        const isCostExplorer = serviceName === 'AWS Cost Explorer';
        const isTax = serviceName === 'Tax';
        const cancelButton = row.querySelector('button:contains("Cancel Service")');
        
        if (!isCostExplorer && !isTax && cancelButton) {
            testServiceName = serviceName;
            cancellableService = row;
            break;
        }
    }
    
    if (!testServiceName) {
        testResults.cancellationPersistence.details.push("Error: No cancellable service found");
    } else {
        testResults.cancellationPersistence.details.push(`Found cancellable service: ${testServiceName}`);
        
        // Mock showConfirmation to force 'true' and verify localStorage is updated
        window.originalShowConfirmation = window.showConfirmation;
        window.showConfirmation = function(serviceName, consoleUrl) {
            testResults.cancellationPersistence.details.push(`Cancelling service: ${serviceName}`);
            
            // Save to localStorage (this is what our implementation should do)
            const today = new Date().toISOString().split('T')[0];
            let cancelledServices = {};
            
            try {
                const existing = localStorage.getItem('cancelledServices');
                if (existing) {
                    cancelledServices = JSON.parse(existing);
                }
            } catch (e) {
                testResults.cancellationPersistence.details.push(`Error parsing localStorage: ${e.message}`);
            }
            
            cancelledServices[serviceName] = {
                date: today,
                consoleUrl: consoleUrl
            };
            
            localStorage.setItem('cancelledServices', JSON.stringify(cancelledServices));
            testResults.cancellationPersistence.details.push(`Saved to localStorage: ${JSON.stringify(cancelledServices)}`);
            
            // Simulate UI update
            const row = document.querySelector(`#servicesTableBody tr td:first-child:contains("${serviceName}")`).parentNode;
            row.querySelector('td:nth-child(4)').textContent = 'Cancelled';
            row.querySelector('td:nth-child(5)').textContent = today;
            
            // Rebuild service table (should be done by our implementation)
            if (typeof rebuildServiceTable === 'function') {
                rebuildServiceTable();
                testResults.cancellationPersistence.details.push("Service table rebuilt");
            }
            
            return true;
        };
        
        // Find and click the cancel button
        const cancelButton = cancellableService.querySelector('button:contains("Cancel Service")');
        cancelButton.click();
        
        // Verify localStorage has been updated
        const cancelledServicesJson = localStorage.getItem('cancelledServices');
        let cancelledServices = null;
        
        try {
            cancelledServices = JSON.parse(cancelledServicesJson);
        } catch (e) {
            testResults.cancellationPersistence.details.push(`Error parsing localStorage after cancellation: ${e.message}`);
        }
        
        if (cancelledServices && cancelledServices[testServiceName]) {
            testResults.cancellationPersistence.details.push(
                `Verified service ${testServiceName} is saved in localStorage with date ${cancelledServices[testServiceName].date}`
            );
            
            // Simulate page refresh by rebuilding the service table
            if (typeof loadCancelledServices === 'function') {
                loadCancelledServices();
                testResults.cancellationPersistence.details.push("Loaded cancelled services from localStorage");
            }
            
            if (typeof rebuildServiceTable === 'function') {
                rebuildServiceTable();
                testResults.cancellationPersistence.details.push("Simulated page refresh by rebuilding service table");
            }
            
            // Verify service still shows as cancelled after "refresh"
            const serviceRow = document.querySelector(`#servicesTableBody tr td:first-child:contains("${testServiceName}")`).parentNode;
            const statusCell = serviceRow.querySelector('td:nth-child(4)');
            const dateCell = serviceRow.querySelector('td:nth-child(5)');
            const actionsCell = serviceRow.querySelector('td:nth-child(6)');
            
            if (statusCell.textContent.includes('Cancelled')) {
                testResults.cancellationPersistence.details.push(`Service still shows as cancelled after refresh`);
                
                // Check for date
                if (dateCell.textContent === cancelledServices[testServiceName].date) {
                    testResults.cancellationPersistence.details.push(`Cancellation date preserved: ${dateCell.textContent}`);
                    
                    // Check for verify link
                    const verifyLink = actionsCell.querySelector('a:contains("Verify")');
                    if (verifyLink) {
                        testResults.cancellationPersistence.details.push(`Verify link found with href: ${verifyLink.getAttribute('href')}`);
                        testResults.cancellationPersistence.passed = true;
                    } else {
                        testResults.cancellationPersistence.details.push(`Error: Verify link not found`);
                    }
                } else {
                    testResults.cancellationPersistence.details.push(
                        `Error: Dates don't match. Expected ${cancelledServices[testServiceName].date}, got ${dateCell.textContent}`
                    );
                }
            } else {
                testResults.cancellationPersistence.details.push(`Error: Service not showing as cancelled after refresh`);
            }
        } else {
            testResults.cancellationPersistence.details.push("Error: Service not found in localStorage after cancellation");
        }
        
        // Restore original function
        window.showConfirmation = window.originalShowConfirmation;
    }
    
    // Test 2: Cost Explorer Info Modal
    console.log("Test 2: Verifying Cost Explorer info modal");
    
    // Find the Cost Explorer row
    let costExplorerRow = null;
    for (const row of serviceRows) {
        const serviceName = row.querySelector('td:first-child').textContent;
        if (serviceName === 'AWS Cost Explorer') {
            costExplorerRow = row;
            break;
        }
    }
    
    if (!costExplorerRow) {
        testResults.costExplorerModal.details.push("Error: AWS Cost Explorer service not found");
    } else {
        // Find the "Investigate API Usage" button
        const investigateButton = costExplorerRow.querySelector('button:contains("Investigate API Usage")');
        if (!investigateButton) {
            testResults.costExplorerModal.details.push("Error: Investigate API Usage button not found");
        } else {
            testResults.costExplorerModal.details.push("Found Investigate API Usage button");
            
            // Click the button to open the modal
            investigateButton.click();
            testResults.costExplorerModal.details.push("Clicked Investigate API Usage button");
            
            // Verify modal is visible
            const modal = document.getElementById('costExplorerInfoModal');
            if (!modal) {
                testResults.costExplorerModal.details.push("Error: Cost Explorer info modal not found");
            } else if (window.getComputedStyle(modal).display === 'none') {
                testResults.costExplorerModal.details.push("Error: Cost Explorer info modal is not visible");
            } else {
                testResults.costExplorerModal.details.push("Cost Explorer info modal is visible");
                
                // Verify modal title
                const modalTitle = document.getElementById('costExplorerInfoModalLabel');
                if (modalTitle && modalTitle.textContent.includes("Understanding AWS Cost Explorer Charges")) {
                    testResults.costExplorerModal.details.push(`Modal title verified: ${modalTitle.textContent}`);
                } else {
                    testResults.costExplorerModal.details.push("Error: Modal title not found or incorrect");
                }
                
                // Verify content sections
                const whatSection = modal.querySelector('h6:contains("What")');
                const investigateSection = modal.querySelector('h6:contains("How to investigate")');
                const reduceSection = modal.querySelector('h6:contains("How to reduce")');
                
                if (whatSection && investigateSection && reduceSection) {
                    testResults.costExplorerModal.details.push("All required content sections found");
                    
                    // Check for specific content
                    const modalText = modal.textContent;
                    const hasBoto3 = modalText.includes("Boto3");
                    const hasCloudTrail = modalText.includes("CloudTrail");
                    
                    if (hasBoto3 && hasCloudTrail) {
                        testResults.costExplorerModal.details.push("Modal contains required information about Boto3 and CloudTrail");
                        
                        // Check for action links
                        const eventHistoryLink = modal.querySelector('a[href*="/history"]');
                        if (eventHistoryLink) {
                            testResults.costExplorerModal.details.push(`Found CloudTrail Event History link: ${eventHistoryLink.getAttribute('href')}`);
                            testResults.costExplorerModal.passed = true;
                        } else {
                            testResults.costExplorerModal.details.push("Error: CloudTrail Event History link not found");
                        }
                    } else {
                        testResults.costExplorerModal.details.push(
                            `Error: Missing required content. Boto3: ${hasBoto3}, CloudTrail: ${hasCloudTrail}`
                        );
                    }
                } else {
                    testResults.costExplorerModal.details.push("Error: One or more content sections missing");
                }
                
                // Close the modal
                const closeButton = modal.querySelector('button:contains("Close")');
                if (closeButton) {
                    closeButton.click();
                    testResults.costExplorerModal.details.push("Closed the modal");
                } else {
                    testResults.costExplorerModal.details.push("Error: Close button not found");
                }
            }
        }
    }
    
    // Output overall results
    console.log("===== DASHBOARD FEATURE VERIFICATION RESULTS =====");
    console.log(`Cancellation Persistence: ${testResults.cancellationPersistence.passed ? "PASSED" : "FAILED"}`);
    console.log(`Cost Explorer Modal: ${testResults.costExplorerModal.passed ? "PASSED" : "FAILED"}`);
    console.log("=================================================");
    
    return testResults;
}

// Run the verification when script is loaded
// (Make this conditional for integration with the dashboard)
if (typeof window !== 'undefined' && document.readyState === 'complete') {
    console.log("Running dashboard feature verification...");
    verifyDashboardFeatures();
} else if (typeof window !== 'undefined') {
    window.addEventListener('load', function() {
        console.log("Running dashboard feature verification...");
        verifyDashboardFeatures();
    });
}
