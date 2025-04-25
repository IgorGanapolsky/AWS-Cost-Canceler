// Pay-as-you-go service override script
// This script ensures that pay-as-you-go services are always displayed correctly

// After document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Apply pay-as-you-go overrides
    setTimeout(applyPayAsYouGoOverrides, 100);
});

// Function to override status of pay-as-you-go services
function applyPayAsYouGoOverrides() {
    console.log("Applying pay-as-you-go service overrides");
    
    // List of pay-as-you-go services
    const payAsYouGoServices = [
        'Amazon Rekognition', 
        'Amazon Transcribe', 
        'Amazon Polly',
        'Amazon Textract',
        'Amazon Comprehend',
        'Amazon Translate',
        'Amazon Lex',
        'AWS CodeWhisperer',
        'Amazon Kendra'
    ];
    
    // Get all rows
    const rows = document.querySelectorAll('#servicesTableBody tr');
    
    // For each row
    rows.forEach(row => {
        const nameCell = row.querySelector('td:first-child');
        if (nameCell && payAsYouGoServices.includes(nameCell.textContent.trim())) {
            console.log("Found pay-as-you-go service:", nameCell.textContent.trim());
            
            // Override status cell
            const statusCell = row.querySelector('td:nth-child(4)');
            if (statusCell) {
                statusCell.innerHTML = '<span class="badge bg-info">Pay-As-You-Go</span>';
            }
            
            // Override date cell
            const dateCell = row.querySelector('td:nth-child(5)');
            if (dateCell) {
                dateCell.innerHTML = '<span class="text-info">Usage-based</span>';
            }
            
            // Override action cell
            const actionCell = row.querySelector('td:last-child');
            if (actionCell) {
                actionCell.innerHTML = `<button class="btn btn-sm btn-warning" onclick="showPayAsYouGoInfo('${nameCell.textContent.trim()}')">
                    <i class="fas fa-info-circle"></i> Manage Usage
                </button>`;
            }
        }
    });
}
