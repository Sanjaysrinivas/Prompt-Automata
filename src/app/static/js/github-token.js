// GitHub token management

function showGitHubTokenModal() {
    const modal = document.getElementById('github-token-modal');
    const tokenInput = document.getElementById('new-github-token');
    const statusDiv = document.getElementById('save-token-status');
    tokenInput.value = '';
    statusDiv.innerHTML = '';
    modal.classList.add('show');
}

function closeGitHubTokenModal() {
    const modal = document.getElementById('github-token-modal');
    modal.classList.remove('show');
}

function toggleTokenVisibility(button) {
    const input = button.closest('.input-group').querySelector('input');
    const icon = button.querySelector('i');
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}

async function loadGitHubToken() {
    const tokenDisplay = document.getElementById('github-token-display');
    
    try {
        const options = await getFetchOptions();
        const response = await fetch('/admin/github/token', options);
        const data = await response.json();
        
        if (response.ok && data.token) {
            const maskedToken = data.token.substring(0, 8) + '...' + data.token.substring(data.token.length - 8);
            tokenDisplay.innerHTML = `
                <div class="d-flex align-items-center">
                    <div class="flex-grow-1">
                        <strong>Current Token:</strong> 
                        <code>${maskedToken}</code>
                    </div>
                    <button class="btn btn-sm btn-outline-secondary ml-2" id="update-github-token-button">
                        <i class="fas fa-edit"></i> Update
                    </button>
                </div>`;
            
            // Re-attach event listener to the new update button
            const updateButton = document.getElementById('update-github-token-button');
            if (updateButton) {
                updateButton.addEventListener('click', showGitHubTokenModal);
            }
        } else {
            tokenDisplay.innerHTML = `
                <div class="alert alert-warning mb-0">
                    <i class="fas fa-exclamation-triangle"></i> No GitHub token configured
                </div>`;
        }
    } catch (error) {
        console.error('Error loading GitHub token:', error);
        tokenDisplay.innerHTML = `
            <div class="alert alert-danger mb-0">
                <i class="fas fa-exclamation-circle"></i> Error loading token: ${error.message}
            </div>`;
    }
}

async function saveGitHubToken(event) {
    event.preventDefault();
    
    const token = document.getElementById('new-github-token').value;
    const saveButton = event.submitter;
    const statusDiv = document.getElementById('save-token-status');
    
    try {
        if (!token) {
            throw new Error('GitHub token is required');
        }

        saveButton.disabled = true;
        saveButton.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Saving...';
        statusDiv.innerHTML = '';
        
        const options = await getFetchOptions('POST', { token });
        const response = await fetch('/admin/github/token', options);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to save GitHub token');
        }

        // Show success message with scopes
        statusDiv.innerHTML = `
            <div class="alert alert-success">
                <strong>✓ Token saved successfully</strong>
                ${data.scopes ? `<br>Scopes: ${data.scopes.join(', ')}` : ''}
            </div>`;
            
        // Update main token display
        await loadGitHubToken();
        
        // Close modal after 1.5s
        setTimeout(closeGitHubTokenModal, 1500);
        
    } catch (error) {
        console.error('Error saving GitHub token:', error);
        statusDiv.innerHTML = `
            <div class="alert alert-danger">
                <strong>⚠ Error:</strong> ${error.message}
            </div>`;
    } finally {
        saveButton.disabled = false;
        saveButton.textContent = 'Save Token';
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    try {
        await getAdminToken(); // Make sure we have the admin token
        
        // Load initial GitHub token
        loadGitHubToken();
        
        // Set up event listeners
        const addTokenButton = document.getElementById('add-github-token-button');
        if (addTokenButton) {
            addTokenButton.addEventListener('click', showGitHubTokenModal);
        }

        const closeButtons = [
            document.getElementById('close-github-token-modal'),
            document.getElementById('cancel-github-token-button')
        ];
        closeButtons.forEach(button => {
            if (button) {
                button.addEventListener('click', closeGitHubTokenModal);
            }
        });

        const toggleButton = document.getElementById('toggle-token-visibility-button');
        if (toggleButton) {
            toggleButton.addEventListener('click', function() {
                toggleTokenVisibility(this);
            });
        }

        const form = document.getElementById('new-github-token-form');
        if (form) {
            form.addEventListener('submit', saveGitHubToken);
        }
    } catch (error) {
        console.error('Failed to initialize GitHub token management:', error);
    }
});
