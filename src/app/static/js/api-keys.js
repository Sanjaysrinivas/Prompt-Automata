// Function to fetch and populate API keys
async function fetchAndPopulateApiKeys() {
    try {
        // First, fetch the admin token
        const tokenResponse = await fetch('/admin/token');
        if (!tokenResponse.ok) {
            throw new Error('Failed to fetch admin token');
        }
        const { token } = await tokenResponse.json();
        if (!token) {
            throw new Error('Admin token not found');
        }

        const response = await fetch('/admin/api-keys', {
            headers: {
                'X-Admin-Token': token,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to fetch API keys');
        }
        
        const apiKeys = await response.json();
        
        // Get the select element
        const select = document.getElementById('api-key-select');
        if (!select) return;

        // Clear existing options except the first one
        while (select.options.length > 1) {
            select.remove(1);
        }

        // Validate API keys data format
        if (!Array.isArray(apiKeys)) {
            console.error('Invalid API keys data format:', apiKeys);
            throw new Error('API keys data is not in the expected format');
        }

        // Add API keys to select
        if (apiKeys.length === 0) {
            const option = document.createElement('option');
            option.disabled = true;
            option.textContent = 'No API keys available';
            select.appendChild(option);
        } else {
            apiKeys.forEach(key => {
                if (!key || typeof key.id === 'undefined' || !key.name) {
                    console.warn('Invalid API key data:', key);
                    return;
                }
                const option = document.createElement('option');
                option.value = key.id;
                option.textContent = key.name;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error fetching API keys:', error);
        // Display error to user
        const select = document.getElementById('api-key-select');
        if (select) {
            const option = document.createElement('option');
            option.disabled = true;
            option.textContent = 'Error loading API keys';
            select.appendChild(option);
        }
    }
}

// Function to delete an API key
async function deleteApiKey(keyId) {
    try {
        // First, fetch the admin token
        const tokenResponse = await fetch('/admin/token');
        if (!tokenResponse.ok) {
            throw new Error('Failed to fetch admin token');
        }
        const { token } = await tokenResponse.json();
        if (!token) {
            throw new Error('Admin token not found');
        }

        const response = await fetch(`/admin/api-key/${keyId}`, {
            method: 'DELETE',
            headers: {
                'X-Admin-Token': token,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to delete API key');
        }

        // Refresh the API keys list
        await fetchAndPopulateApiKeys();
        
        // Show success message
        const successMsg = document.createElement('div');
        successMsg.className = 'fixed bottom-4 right-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded';
        successMsg.innerHTML = '<i class="fas fa-check mr-2"></i>API key deleted successfully!';
        document.body.appendChild(successMsg);
        
        // Remove success message after 3 seconds
        setTimeout(() => {
            successMsg.remove();
        }, 3000);
    } catch (error) {
        console.error('Error deleting API key:', error);
        alert('Failed to delete API key: ' + error.message);
    }
}

// Initialize when the document is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initial population of API keys
    fetchAndPopulateApiKeys();

    // Set up refresh interval (every 30 seconds)
    setInterval(fetchAndPopulateApiKeys, 30000);
});
