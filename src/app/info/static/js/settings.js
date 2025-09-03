function generateReport() {
    // Show loading indicator (optional)
    const button = event.target;
    const originalText = button.textContent;
    button.textContent = 'Generating...';
    button.disabled = true;
    
    // Fetch the report from the endpoint
    fetch('/info/report')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to generate report');
            }
            // Get the filename from Content-Disposition header if available
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'user_report.csv';
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
                if (filenameMatch) {
                    filename = filenameMatch[1];
                }
            }
            return response.blob().then(blob => ({ blob, filename }));
        })
        .then(({ blob, filename }) => {
            // Create a temporary URL for the blob
            const url = window.URL.createObjectURL(blob);
            
            // Create a temporary anchor element and trigger download
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            
            // Clean up
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
            
            // Reset button
            button.textContent = originalText;
            button.disabled = false;
        })
        .catch(error => {
            console.error('Error downloading report:', error);
            alert('Failed to download report. Please try again.');
            
            // Reset button
            button.textContent = originalText;
            button.disabled = false;
        });
}

// Handle accessibility toggle change
document.getElementById('accessibilityToggle').addEventListener('change', function() {
    //const toggle = this;
    fetch('/info/accessibility', {
        method: 'GET'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to toggle accessibility');
        }
        return response.json();
    })
    .then(data => {
        window.location.href = data.redirect_url;
    })
});

// Handle accessibility toggle change
function restart() {
    //const toggle = this;
    fetch('/info/restart', {
        method: 'GET'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to toggle accessibility');
        }
        return response.json();
    })
    .then(data => {
        window.location.href = data.redirect_url;
    })
};