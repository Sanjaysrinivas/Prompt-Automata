// GitHub Token Management
document.addEventListener('DOMContentLoaded', function() {
    loadGitHubTokens();
    setupTokenForm();
});

function loadGitHubTokens() {
    fetch('/admin/github/tokens')
        .then(response => response.json())
        .then(tokens => {
            const tokensList = document.getElementById('github-tokens-list');
            tokensList.innerHTML = '';
            
            tokens.forEach(token => {
                const tokenElement = createTokenElement(token);
                tokensList.appendChild(tokenElement);
            });
        })
        .catch(error => {
            console.error('Error loading GitHub tokens:', error);
            showError('Failed to load GitHub tokens');
        });
}

function createTokenElement(token) {
    const div = document.createElement('div');
    div.className = 'list-group-item d-flex justify-content-between align-items-center';
    div.innerHTML = `
        <div>
            <h5 class="mb-1">${token.name}</h5>
            <p class="mb-1">Endpoint: ${token.endpoint}</p>
            <small class="text-muted">Last validated: ${token.last_validated || 'Never'}</small>
        </div>
        <div class="btn-group">
            <button class="btn btn-sm btn-outline-primary" onclick="validateToken('${token.id}')">
                <i class="fas fa-check"></i> Validate
            </button>
            <button class="btn btn-sm btn-outline-danger" onclick="deleteToken('${token.id}')">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `;
    return div;
}

function setupTokenForm() {
    const form = document.getElementById('github-token-form');
    if (!form) return;

    form.addEventListener('submit', createGitHubToken);
}

async function createGitHubToken(event) {
    event.preventDefault();
    
    const nameInput = document.getElementById('githubTokenName');
    const tokenInput = document.getElementById('githubTokenValue');
    const descInput = document.getElementById('githubTokenDescription');
    
    const name = nameInput.value.trim();
    const token = tokenInput.value.trim();
    const description = descInput ? descInput.value.trim() : '';
    
    if (!name || !token) {
        showError('Name and token are required');
        return;
    }
    
    try {
        // First ensure GitHub endpoint is set up
        await setupGitHubEndpoint();
        
        const response = await fetch('/admin/github/tokens', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                token: token,
                description: description
            })
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Failed to create GitHub token');
        }
        
        // Clear form
        nameInput.value = '';
        tokenInput.value = '';
        if (descInput) descInput.value = '';
        
        // Close modal
        closeModal('github-token-modal');
        
        // Refresh token list
        loadGitHubTokens();
        
        showSuccess('GitHub token created successfully');
    } catch (error) {
        console.error('Error creating GitHub token:', error);
        showError(error.message);
    }
}

async function setupGitHubEndpoint() {
    try {
        const response = await fetch('/admin/github/setup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to set up GitHub endpoint');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error setting up GitHub endpoint:', error);
        throw error;
    }
}

function validateToken(tokenId) {
    const statusElement = document.getElementById('token-validation-status');
    if (statusElement) {
        statusElement.style.display = 'block';
        statusElement.textContent = 'Validating token...';
    }

    fetch(`/admin/github/tokens/${tokenId}/validate`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess('Token validated successfully');
            loadGitHubTokens();
        } else {
            showError(data.message || 'Token validation failed');
        }
    })
    .catch(error => {
        console.error('Error validating token:', error);
        showError('Failed to validate token');
    })
    .finally(() => {
        if (statusElement) {
            statusElement.style.display = 'none';
        }
    });
}

function deleteToken(tokenId) {
    if (!confirm('Are you sure you want to delete this token?')) return;

    fetch(`/admin/github/tokens/${tokenId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            loadGitHubTokens();
            showSuccess('Token deleted successfully');
        } else {
            showError(data.message || 'Failed to delete token');
        }
    })
    .catch(error => {
        console.error('Error deleting token:', error);
        showError('Failed to delete token');
    });
}

function showSuccess(message) {
    // Implement your success notification logic here
    console.log('Success:', message);
}

function showError(message) {
    // Implement your error notification logic here
    console.error('Error:', message);
}
