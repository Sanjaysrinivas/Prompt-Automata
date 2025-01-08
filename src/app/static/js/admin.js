// Global state for request tracking
let inProgressOperations = {
    apiKey: false,
    variable: false,
    directory: false,
    endpoint: false,
    githubToken: false
};

// Get admin token from meta tag with retry
async function getAdminToken(retries = 3, delay = 100) {
    for (let i = 0; i < retries; i++) {
        const metaTag = document.querySelector('meta[name="admin-token"]');
        if (metaTag && metaTag.content) {
            return metaTag.content;
        }
        if (i < retries - 1) {
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
    throw new Error('Admin token not found after retries');
}

// Helper function to get common fetch options
async function getFetchOptions(method = 'GET', body = null) {
    const adminToken = await getAdminToken();
    if (!adminToken) {
        throw new Error('Admin token not found');
    }

    const options = {
        method,
        headers: {
            'X-Admin-Token': adminToken,
            'Content-Type': 'application/json'
        }
    };
    
    if (body) {
        options.body = JSON.stringify(body);
    }
    
    return options;
}

// Validation patterns
const VALIDATION_PATTERNS = {
    apiKey: {
        name: /^[a-zA-Z0-9][a-zA-Z0-9_-]{2,49}$/,
        key: /^[A-Za-z0-9\-._~]{32,128}$/
    },
    variable: {
        name: /^[a-zA-Z_][a-zA-Z0-9_]{2,49}$/
    },
    endpoint: {
        name: /^[a-zA-Z0-9][a-zA-Z0-9_-]{2,49}$/,
        url: /^https?:\/\/.+/
    }
};

// Helper function to sanitize input
function sanitizeInput(input, pattern) {
    return input.replace(new RegExp(`[^${pattern}]`, 'g'), '');
}

// Toggle password visibility
function toggleVisibility(button) {
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

// Get list element ID based on type
function getListElementId(type) {
    switch(type) {
        case 'apiKey':
            return 'api-keys-list';
        case 'variable':
            return 'variables-list';
        case 'directory':
            return 'directories-list';
        case 'endpoint':
            return 'endpoints-list';
        case 'githubToken':
            return 'github-tokens-table';
        default:
            throw new Error(`Unknown type: ${type}`);
    }
}

// Get endpoint URL based on type
function getEndpointUrl(type, id = null) {
    // Convert type to match backend expectations
    let backendType = type === 'variable' ? 'variables' : type;
    
    // Handle directory/directories case
    if (backendType === 'directory') {
        backendType = 'directories';
    }
    
    switch(backendType) {
        case 'apiKey':
            return id ? `api-keys/${id}` : 'api-keys';
        case 'variables':
            return id ? `variables/${id}` : 'variables';
        case 'directories':
            return id ? `directories/${id}` : 'directories';
        case 'endpoint':
            return id ? `endpoints/${id}` : 'endpoints';
        case 'githubToken':
            return id ? `github/tokens/${id}` : 'github/tokens';
        default:
            throw new Error(`Unknown type: ${type}`);
    }
}

// Get fields for table based on type
function getTableFields(type) {
    switch(type) {
        case 'apiKey':
            return ['name', 'key', 'created_at', 'updated_at'];
        case 'variable':
            return ['name', 'value', 'description'];
        case 'directory':
            return ['path', 'description', 'is_recursive'];
        case 'endpoint':
            return ['name', 'base_url', 'type', 'auth_type', 'rate_limit'];
        case 'githubToken':
            return ['name', 'value', 'created_at', 'updated_at'];
        default:
            throw new Error(`Unknown type: ${type}`);
    }
}

// Generic load function
async function loadItems(type) {
    try {
        // Use proper pluralization for directories
        const pluralType = type === 'directory' ? 'directories' : `${type}s`;
        console.log(`Loading ${pluralType}...`);
        
        const endpoint = getEndpointUrl(type);
        console.log(`Using endpoint: ${endpoint}`);
        const options = await getFetchOptions();
        console.log('Fetch options:', options);
        
        const response = await fetch(`/admin/${endpoint}`, options);
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const items = await response.json();
        console.log('Loaded items:', items);
        
        const fields = getTableFields(type);
        console.log('Table fields:', fields);
        
        const listElementId = getListElementId(type);
        console.log(`Looking for element with ID: ${listElementId}`);
        const listElement = document.getElementById(listElementId);
        if (listElement) {
            console.log(`Found list element with ID: ${listElementId}`);
            listElement.innerHTML = createTable(items, fields, type);
        } else {
            console.error(`Element with ID ${listElementId} not found`);
        }
    } catch (error) {
        console.error(`Error loading ${type}s:`, error);
        showError(`Failed to load ${type}s. ${error.message}`);
    }
}

// Generic create function
async function createItem(type, data, modal) {
    try {
        console.log(`Creating ${type} with data:`, data);
        
        if (inProgressOperations[type]) {
            console.log(`Operation already in progress for ${type}`);
            return;
        }
        
        inProgressOperations[type] = true;
        
        const endpoint = getEndpointUrl(type);
        console.log(`Using endpoint: /admin/${endpoint}`);
        
        const response = await fetch(`/admin/${endpoint}`, {
            ...await getFetchOptions('POST'),
            body: JSON.stringify(data)
        });
        
        console.log(`Response status: ${response.status}`);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`Error response: ${errorText}`);
            throw new Error(`Failed to create ${type}: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log(`Created ${type}:`, result);
        
        // Hide the modal
        hideModal(modal);
        
        // Reset the form
        const form = document.getElementById(`${type}-form`);
        if (form) {
            form.reset();
        }
        
        // Reload the table
        await loadItems(type);
        
        // Show success message
        const message = document.createElement('div');
        message.className = 'alert alert-success alert-dismissible fade show';
        message.innerHTML = `
            ${type} created successfully!
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(message, container.firstChild);
            setTimeout(() => message.remove(), 3000);
        }
    } catch (error) {
        console.error(`Error creating ${type}:`, error);
        showError(`Failed to create ${type}. ${error.message}`);
    } finally {
        inProgressOperations[type] = false;
    }
}

// Generic edit function
async function editItem(type, id) {
    try {
        console.log(`Editing ${type} with ID: ${id}`);
        
        // Use getEndpointUrl helper to get the correct URL
        const endpoint = getEndpointUrl(type, id);
        const options = await getFetchOptions();
        
        // Make the request with the correct URL and auth
        const response = await fetch(`/admin/${endpoint}`, options);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || `Failed to fetch ${type} details`);
        }
        
        const item = await response.json();
        console.log(`Fetched ${type} details:`, item);
        
        // Show modal and populate fields based on type
        switch (type) {
            case 'variable':
                document.getElementById('edit-variable-id').value = item.id;
                document.getElementById('edit-variable-name').value = item.name;
                document.getElementById('edit-variable-value').value = item.value;
                document.getElementById('edit-variable-description').value = item.description || '';
                showModal('edit-variable-modal');
                break;
                
            case 'directory':
                document.getElementById('dirPath').value = item.path;
                document.getElementById('dirDescription').value = item.description || '';
                document.getElementById('dirRecursive').checked = item.is_recursive;
                document.getElementById('directory-modal').dataset.editingId = item.id;
                
                // Update modal title to show we're editing
                document.querySelector('#directory-modal .admin-modal-title').textContent = 'Edit Directory';
                
                showModal('directory-modal');
                break;
                
            case 'endpoint':
                document.getElementById('edit-endpoint-id').value = item.id;
                document.getElementById('edit-endpoint-name').value = item.name;
                document.getElementById('edit-endpoint-url').value = item.url;
                document.getElementById('edit-endpoint-method').value = item.method;
                document.getElementById('edit-endpoint-description').value = item.description || '';
                showModal('edit-endpoint-modal');
                break;
                
            case 'githubToken':
                document.getElementById('edit-github-token-id').value = item.id;
                document.getElementById('editGithubTokenName').value = item.name;
                document.getElementById('edit-github-token-description').value = item.description || '';
                showModal('edit-github-token-modal');
                break;
                
            default:
                console.error(`Unsupported item type for editing: ${type}`);
                return;
        }
    } catch (error) {
        console.error(`Error editing ${type}:`, error);
        showError(error.message);
    }
}

// Generic update function
async function updateItem(type, id, data) {
    try {
        console.log(`Updating ${type} with ID ${id}:`, data);
        
        if (inProgressOperations[type]) {
            console.log(`Operation already in progress for ${type}`);
            return;
        }
        
        inProgressOperations[type] = true;
        
        const endpoint = getEndpointUrl(type, id);
        console.log(`Using endpoint: /admin/${endpoint}`);
        
        const response = await fetch(`/admin/${endpoint}`, await getFetchOptions('PUT', data));
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`Error response: ${errorText}`);
            throw new Error(`Failed to update ${type}: ${response.statusText}`);
        }
        
        // Reload the items list
        await loadItems(type);
        
        // Show success message
        const successMessage = document.createElement('div');
        successMessage.className = 'alert alert-success';
        successMessage.textContent = `${type} updated successfully`;
        document.querySelector('.container').insertBefore(successMessage, document.querySelector('.container').firstChild);
        
        // Remove success message after 3 seconds
        setTimeout(() => {
            successMessage.remove();
        }, 3000);
        
    } catch (error) {
        console.error(`Error updating ${type}:`, error);
        showError(`Failed to update ${type}. ${error.message}`);
    } finally {
        inProgressOperations[type] = false;
    }
}

// Generic delete function
async function deleteItem(type, id) {
    if (!confirm(`Are you sure you want to delete this ${type}?`)) {
        return;
    }
    
    if (inProgressOperations[type]) {
        console.log(`Operation already in progress for ${type}`);
        return;
    }
    
    try {
        inProgressOperations[type] = true;
        const endpoint = getEndpointUrl(type, id);
        const response = await fetch(`/admin/${endpoint}`, await getFetchOptions('DELETE'));
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: `Failed to delete ${type}` }));
            throw new Error(errorData.error || `Failed to delete ${type}`);
        }
        
        await loadItems(type);
    } catch (error) {
        console.error(`Error deleting ${type}:`, error);
        showError(error.message);
    } finally {
        inProgressOperations[type] = false;
    }
}

// Helper function to show error messages
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger alert-dismissible fade show';
    errorDiv.role = 'alert';
    errorDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Find a suitable container for the error message
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(errorDiv, container.firstChild);
    }
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

// Helper function to create tables
function createTable(items, fields, type) {
    if (!items || items.length === 0) {
        return `<tr><td colspan="${fields.length + 1}" class="text-center">No ${type}s present</td></tr>`;
    }

    let table = `
        <div class="table-responsive">
            <table class="table">
                <thead>
                    <tr>
                        ${fields.map(field => `<th>${field.charAt(0).toUpperCase() + field.slice(1)}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
    `;

    items.forEach(item => {
        // Convert api-keys to api-key for data-type attribute
        const dataType = type === 'api-keys' ? 'api-key' : type;
        table += `<tr data-id="${item.id}" data-type="${dataType}">`;
        fields.forEach(field => {
            if (typeof item[field] === 'boolean') {
                table += `<td><span class="badge ${item[field] ? 'badge-success' : 'badge-warning'}">${item[field]}</span></td>`;
            } else {
                table += `<td>${item[field] || ''}</td>`;
            }
        });
        table += '</tr>';
    });

    table += '</tbody></table></div>';
    return table;
}

// Function to load API token status
async function loadAPITokenStatus() {
    try {
        const options = await getFetchOptions();
        const response = await fetch('/api/llm/token/status', options);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const status = await response.json();
        
        // Update the UI based on status
        const tableBody = document.querySelector('#api-keys-list');
        if (!tableBody) return;

        let html = '';
        const providers = Object.keys(status);
        
        if (providers.length === 0 || !providers.some(p => status[p])) {
            html = `<tr><td colspan="2" class="text-center">No API keys present</td></tr>`;
        } else {
            html = providers.map(provider => {
                if (!status[provider]) return '';
                return `<tr>
                    <td>${provider}</td>
                    <td>
                        <div class="input-group">
                            <input type="password" class="form-control" value="********" readonly>
                            <button class="btn btn-danger" type="button" onclick="deleteAPIKey('${provider}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>`;
            }).filter(row => row).join('');
        }
        
        tableBody.innerHTML = html;
    } catch (error) {
        console.error('Error loading API token status:', error);
        showError(`Failed to load API token status: ${error.message}`);
    }
}

// Function to delete API key
async function deleteAPIKey(provider) {
    try {
        const options = await getFetchOptions('DELETE');
        const response = await fetch(`/api/llm/token?provider=${provider}`, options);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        await loadAPITokenStatus();
    } catch (error) {
        console.error('Error deleting API key:', error);
        showError(`Failed to delete API key: ${error.message}`);
    }
}

function createApiKeyRow(apiKey) {
    const row = document.createElement('tr');
    row.innerHTML = `
        <td>${apiKey.name}</td>
        <td>${apiKey.provider}</td>
        <td>
            <button class="btn btn-sm btn-danger delete-key" data-id="${apiKey.id}">
                <i class="fas fa-trash"></i>
            </button>
        </td>
    `;
    return row;
}

async function loadApiKeys() {
    try {
        const response = await fetch('/admin/api-keys');
        if (!response.ok) throw new Error('Failed to fetch API keys');
        
        const apiKeys = await response.json();
        const tbody = document.querySelector('#apiKeysTable tbody');
        tbody.innerHTML = '';
        
        apiKeys.forEach(key => {
            tbody.appendChild(createApiKeyRow(key));
        });

        // Add event listeners for delete buttons
        document.querySelectorAll('.delete-key').forEach(button => {
            button.onclick = async (e) => {
                e.preventDefault();
                const keyId = button.dataset.id;
                const response = await fetch(`/admin/api-keys/${keyId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    button.closest('tr').remove();
                    showAlert('API key deleted successfully', 'success');
                } else {
                    showAlert('Failed to delete API key', 'danger');
                }
            };
        });
    } catch (error) {
        console.error('Error loading API keys:', error);
        showAlert('Failed to load API keys', 'danger');
    }
}

async function handleApiKeySubmit(event) {
    event.preventDefault();
    const form = event.target;
    const provider = form.querySelector('[name="provider"]').value;
    const token = form.querySelector('[name="token"]').value;

    try {
        const response = await fetch('/admin/api-keys', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ provider, token })
        });

        if (!response.ok) throw new Error('Failed to save API key');

        showAlert('API key saved successfully', 'success');
        form.reset();
        await loadApiKeys();
    } catch (error) {
        console.error('Error saving API key:', error);
        showAlert('Failed to save API key', 'danger');
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    // Load all items
    await Promise.all([
        loadItems('variable'),
        loadItems('directory'),
        loadItems('endpoint'),
        loadItems('githubToken'),
        loadAPITokenStatus()
    ]);
    
    // Add button click handlers
    document.getElementById('add-variable-button')?.addEventListener('click', () => showModal('variable-modal'));
    document.getElementById('add-directory-button')?.addEventListener('click', () => showModal('directory-modal'));
    document.getElementById('add-endpoint-button')?.addEventListener('click', () => showModal('endpoint-modal'));
    document.getElementById('add-api-key-button')?.addEventListener('click', () => showModal('api-key-modal'));
    document.getElementById('add-github-token-button')?.addEventListener('click', () => showModal('github-token-modal'));
    
    // Add close button handlers
    document.querySelectorAll('.admin-modal-close').forEach(button => {
        button.addEventListener('click', () => {
            const modal = button.closest('.admin-modal');
            if (modal) {
                hideModal(modal.id);
            }
        });
    });
    
    // Add form submit handlers
    ['apiKey', 'variable', 'directory', 'endpoint', 'githubToken'].forEach(type => {
        const form = document.getElementById(`${type}-form`);
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(form);
                const data = Object.fromEntries(formData);
                await createItem(type, data, `${type}-modal`);
            });
        }
        
        const editForm = document.getElementById(`edit-${type}-form`);
        if (editForm) {
            editForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const id = editForm.querySelector(`#edit-${type}-id`).value;
                const formData = new FormData(editForm);
                const data = Object.fromEntries(formData);
                await updateItem(type, id, data);
            });
        }
    });
    
    // Add table row click handlers
    document.addEventListener('click', function(e) {
        const row = e.target.closest('tr[data-id]');
        if (row) {
            const id = row.getAttribute('data-id');
            const type = row.getAttribute('data-type');
            handleRowClick(e, id, type);
        }
    });

    // Add context menu handlers
    document.addEventListener('contextmenu', function(e) {
        const row = e.target.closest('tr[data-id]');
        if (row) {
            e.preventDefault();
            const id = row.getAttribute('data-id');
            const type = row.getAttribute('data-type');
            
            // Position and show context menu
            const menu = document.getElementById('contextMenu');
            menu.style.display = 'block';
            menu.style.left = e.pageX + 'px';
            menu.style.top = e.pageY + 'px';
            
            // Store the current item info for the menu actions
            menu.dataset.itemId = id;
            menu.dataset.itemType = type;
        }
    });

    // Hide context menu when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('#contextMenu')) {
            const menu = document.getElementById('contextMenu');
            menu.style.display = 'none';
        }
    });

    // Add context menu item handlers
    document.getElementById('edit-context-menu-item')?.addEventListener('click', function() {
        const menu = document.getElementById('contextMenu');
        const id = menu.dataset.itemId;
        const type = menu.dataset.itemType;
        if (id && type) {
            editItem(type, id);
            menu.style.display = 'none';
        }
    });

    document.getElementById('delete-context-menu-item')?.addEventListener('click', async function() {
        const menu = document.getElementById('contextMenu');
        const id = menu.dataset.itemId;
        const type = menu.dataset.itemType;
        if (id && type) {
            if (confirm(`Are you sure you want to delete this ${type}?`)) {
                await deleteItem(type, id);
                await loadItems(type);
            }
            menu.style.display = 'none';
        }
    });
});

// Handle row click (show context menu)
function handleRowClick(e, id, type) {
    // Right click is handled by contextmenu event
    if (e.button !== 0) return;
    
    const menu = document.getElementById('contextMenu');
    menu.style.display = 'block';
    menu.style.left = e.pageX + 'px';
    menu.style.top = e.pageY + 'px';
    
    menu.dataset.itemId = id;
    menu.dataset.itemType = type;
}

// Close modal when clicking outside
document.addEventListener('click', function(event) {
    if (event.target.classList.contains('admin-modal')) {
        hideModal(event.target.id);
    }
});

// Modal functions
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    } else {
        console.error('Modal not found:', modalId);
    }
}

function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
    } else {
        console.error('Modal not found:', modalId);
    }
}

// GitHub Token Management
async function loadGitHubTokens() {
    await loadItems('githubToken');
}

async function createGitHubToken(event) {
    event.preventDefault();
    
    const name = document.getElementById('githubTokenName').value;
    const token = document.getElementById('githubToken').value;
    const description = document.getElementById('github-token-description').value;
    const validate = document.getElementById('validateGithubToken').checked;
    
    try {
        if (validate) {
            // Show validation status
            const statusDiv = document.getElementById('token-validation-status');
            statusDiv.style.display = 'block';
            statusDiv.textContent = 'Validating token...';
            statusDiv.className = 'alert alert-info';
            
            // Test token against GitHub API
            const response = await fetch('https://api.github.com/user', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/vnd.github.v3+json'
                }
            });
            
            if (!response.ok) {
                throw new Error('Invalid GitHub token');
            }
            
            statusDiv.textContent = 'Token validated successfully!';
            statusDiv.className = 'alert alert-success';
        }
        
        // Create the token using the API
        const data = {
            name: name,
            token: token,
            description: description || ''
        };
        
        await createItem('githubToken', data, 'github-token-modal');
        
        // Reset form and validation status
        document.getElementById('github-token-form').reset();
        const statusDiv = document.getElementById('token-validation-status');
        if (statusDiv) {
            statusDiv.style.display = 'none';
            statusDiv.textContent = '';
            statusDiv.className = 'alert';
        }
        
        // Close modal
        hideModal('github-token-modal');
    } catch (error) {
        console.error('Error creating GitHub token:', error);
        const statusDiv = document.getElementById('token-validation-status');
        if (statusDiv) {
            statusDiv.style.display = 'block';
            statusDiv.textContent = error.message;
            statusDiv.className = 'alert alert-danger';
        } else {
            showError(error.message);
        }
    }
}

async function editGitHubToken(event) {
    event.preventDefault();
    
    const id = document.getElementById('edit-github-token-id').value;
    const name = document.getElementById('editGithubTokenName').value;
    const token = document.getElementById('editGithubToken').value;
    const description = document.getElementById('edit-github-token-description').value;
    const validate = document.getElementById('editValidateGithubToken').checked;
    
    try {
        if (validate && token) {
            // Test token against GitHub API
            const response = await fetch('https://api.github.com/user', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/vnd.github.v3+json'
                }
            });
            
            if (!response.ok) {
                throw new Error('Invalid GitHub token');
            }
        }
        
        const data = {
            name: name,
            description: description
        };
        
        if (token) {
            data.value = token;
        }
        
        await updateItem('githubToken', id, data);
        hideModal('edit-github-token-modal');
    } catch (error) {
        console.error('Error updating GitHub token:', error);
        showError(error.message);
    }
}

// Function to load API token status
async function loadAPITokenStatus() {
    try {
        const options = await getFetchOptions();
        const response = await fetch('/api/llm/token/status', options);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const status = await response.json();
        
        // Update the UI based on status
        const tableBody = document.querySelector('#api-keys-list');
        if (!tableBody) return;

        let html = '';
        const providers = Object.keys(status);
        
        if (providers.length === 0 || !providers.some(p => status[p])) {
            html = `<tr><td colspan="2" class="text-center">No API keys present</td></tr>`;
        } else {
            html = providers.map(provider => {
                if (!status[provider]) return '';
                return `<tr>
                    <td>${provider}</td>
                    <td>
                        <div class="input-group">
                            <input type="password" class="form-control" value="********" readonly>
                            <button class="btn btn-danger" type="button" onclick="deleteAPIKey('${provider}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>`;
            }).filter(row => row).join('');
        }
        
        tableBody.innerHTML = html;
    } catch (error) {
        console.error('Error loading API token status:', error);
        showError(`Failed to load API token status: ${error.message}`);
    }
}

// Function to delete API key
async function deleteAPIKey(provider) {
    try {
        const options = await getFetchOptions('DELETE');
        const response = await fetch(`/api/llm/token?provider=${provider}`, options);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        await loadAPITokenStatus();
    } catch (error) {
        console.error('Error deleting API key:', error);
        showError(`Failed to delete API key: ${error.message}`);
    }
}

function createApiKeyRow(apiKey) {
    const row = document.createElement('tr');
    row.innerHTML = `
        <td>${apiKey.name}</td>
        <td>${apiKey.provider}</td>
        <td>
            <button class="btn btn-sm btn-danger delete-key" data-id="${apiKey.id}">
                <i class="fas fa-trash"></i>
            </button>
        </td>
    `;
    return row;
}

async function loadApiKeys() {
    try {
        const response = await fetch('/admin/api-keys');
        if (!response.ok) throw new Error('Failed to fetch API keys');
        
        const apiKeys = await response.json();
        const tbody = document.querySelector('#apiKeysTable tbody');
        tbody.innerHTML = '';
        
        apiKeys.forEach(key => {
            tbody.appendChild(createApiKeyRow(key));
        });

        // Add event listeners for delete buttons
        document.querySelectorAll('.delete-key').forEach(button => {
            button.onclick = async (e) => {
                e.preventDefault();
                const keyId = button.dataset.id;
                const response = await fetch(`/admin/api-keys/${keyId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    button.closest('tr').remove();
                    showAlert('API key deleted successfully', 'success');
                } else {
                    showAlert('Failed to delete API key', 'danger');
                }
            };
        });
    } catch (error) {
        console.error('Error loading API keys:', error);
        showAlert('Failed to load API keys', 'danger');
    }
}

async function handleApiKeySubmit(event) {
    event.preventDefault();
    const form = event.target;
    const provider = form.querySelector('[name="provider"]').value;
    const token = form.querySelector('[name="token"]').value;

    try {
        const response = await fetch('/admin/api-keys', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ provider, token })
        });

        if (!response.ok) throw new Error('Failed to save API key');

        showAlert('API key saved successfully', 'success');
        form.reset();
        await loadApiKeys();
    } catch (error) {
        console.error('Error saving API key:', error);
        showAlert('Failed to save API key', 'danger');
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    // Load all items
    await Promise.all([
        loadItems('variable'),
        loadItems('directory'),
        loadItems('endpoint'),
        loadItems('githubToken'),
        loadAPITokenStatus()
    ]);
    
    // Add button click handlers
    document.getElementById('add-variable-button')?.addEventListener('click', () => showModal('variable-modal'));
    document.getElementById('add-directory-button')?.addEventListener('click', () => showModal('directory-modal'));
    document.getElementById('add-endpoint-button')?.addEventListener('click', () => showModal('endpoint-modal'));
    document.getElementById('add-api-key-button')?.addEventListener('click', () => showModal('api-key-modal'));
    document.getElementById('add-github-token-button')?.addEventListener('click', () => showModal('github-token-modal'));
    
    // Add close button handlers
    document.querySelectorAll('.admin-modal-close').forEach(button => {
        button.addEventListener('click', () => {
            const modal = button.closest('.admin-modal');
            if (modal) {
                hideModal(modal.id);
            }
        });
    });
    
    // Add form submit handlers
    ['apiKey', 'variable', 'directory', 'endpoint', 'githubToken'].forEach(type => {
        const form = document.getElementById(`${type}-form`);
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(form);
                const data = Object.fromEntries(formData);
                await createItem(type, data, `${type}-modal`);
            });
        }
        
        const editForm = document.getElementById(`edit-${type}-form`);
        if (editForm) {
            editForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const id = editForm.querySelector(`#edit-${type}-id`).value;
                const formData = new FormData(editForm);
                const data = Object.fromEntries(formData);
                await updateItem(type, id, data);
            });
        }
    });
    
    // Add table row click handlers
    document.addEventListener('click', function(e) {
        const row = e.target.closest('tr[data-id]');
        if (row) {
            const id = row.getAttribute('data-id');
            const type = row.getAttribute('data-type');
            handleRowClick(e, id, type);
        }
    });

    // Add context menu handlers
    document.addEventListener('contextmenu', function(e) {
        const row = e.target.closest('tr[data-id]');
        if (row) {
            e.preventDefault();
            const id = row.getAttribute('data-id');
            const type = row.getAttribute('data-type');
            
            // Position and show context menu
            const menu = document.getElementById('contextMenu');
            menu.style.display = 'block';
            menu.style.left = e.pageX + 'px';
            menu.style.top = e.pageY + 'px';
            
            // Store the current item info for the menu actions
            menu.dataset.itemId = id;
            menu.dataset.itemType = type;
        }
    });

    // Hide context menu when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('#contextMenu')) {
            const menu = document.getElementById('contextMenu');
            menu.style.display = 'none';
        }
    });

    // Add context menu item handlers
    document.getElementById('edit-context-menu-item')?.addEventListener('click', function() {
        const menu = document.getElementById('contextMenu');
        const id = menu.dataset.itemId;
        const type = menu.dataset.itemType;
        if (id && type) {
            editItem(type, id);
            menu.style.display = 'none';
        }
    });

    document.getElementById('delete-context-menu-item')?.addEventListener('click', async function() {
        const menu = document.getElementById('contextMenu');
        const id = menu.dataset.itemId;
        const type = menu.dataset.itemType;
        if (id && type) {
            if (confirm(`Are you sure you want to delete this ${type}?`)) {
                await deleteItem(type, id);
                await loadItems(type);
            }
            menu.style.display = 'none';
        }
    });
});

// Handle row click (show context menu)
function handleRowClick(e, id, type) {
    // Right click is handled by contextmenu event
    if (e.button !== 0) return;
    
    const menu = document.getElementById('contextMenu');
    menu.style.display = 'block';
    menu.style.left = e.pageX + 'px';
    menu.style.top = e.pageY + 'px';
    
    menu.dataset.itemId = id;
    menu.dataset.itemType = type;
}

// Close modal when clicking outside
document.addEventListener('click', function(event) {
    if (event.target.classList.contains('admin-modal')) {
        hideModal(event.target.id);
    }
});

// Modal functions
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    } else {
        console.error('Modal not found:', modalId);
    }
}

function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
    } else {
        console.error('Modal not found:', modalId);
    }
}

// GitHub Token Management
async function loadGitHubTokens() {
    await loadItems('githubToken');
}

async function createGitHubToken(event) {
    event.preventDefault();
    
    const name = document.getElementById('githubTokenName').value;
    const token = document.getElementById('githubToken').value;
    const description = document.getElementById('github-token-description').value;
    const validate = document.getElementById('validateGithubToken').checked;
    
    try {
        if (validate) {
            // Show validation status
            const statusDiv = document.getElementById('token-validation-status');
            statusDiv.style.display = 'block';
            statusDiv.textContent = 'Validating token...';
            statusDiv.className = 'alert alert-info';
            
            // Test token against GitHub API
            const response = await fetch('https://api.github.com/user', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/vnd.github.v3+json'
                }
            });
            
            if (!response.ok) {
                throw new Error('Invalid GitHub token');
            }
            
            statusDiv.textContent = 'Token validated successfully!';
            statusDiv.className = 'alert alert-success';
        }
        
        // Create the token using the API
        const data = {
            name: name,
            token: token,
            description: description || ''
        };
        
        await createItem('githubToken', data, 'github-token-modal');
        
        // Reset form and validation status
        document.getElementById('github-token-form').reset();
        const statusDiv = document.getElementById('token-validation-status');
        if (statusDiv) {
            statusDiv.style.display = 'none';
            statusDiv.textContent = '';
            statusDiv.className = 'alert';
        }
        
        // Close modal
        hideModal('github-token-modal');
    } catch (error) {
        console.error('Error creating GitHub token:', error);
        const statusDiv = document.getElementById('token-validation-status');
        if (statusDiv) {
            statusDiv.style.display = 'block';
            statusDiv.textContent = error.message;
            statusDiv.className = 'alert alert-danger';
        } else {
            showError(error.message);
        }
    }
}

async function editGitHubToken(event) {
    event.preventDefault();
    
    const id = document.getElementById('edit-github-token-id').value;
    const name = document.getElementById('editGithubTokenName').value;
    const token = document.getElementById('editGithubToken').value;
    const description = document.getElementById('edit-github-token-description').value;
    const validate = document.getElementById('editValidateGithubToken').checked;
    
    try {
        if (validate && token) {
            // Test token against GitHub API
            const response = await fetch('https://api.github.com/user', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/vnd.github.v3+json'
                }
            });
            
            if (!response.ok) {
                throw new Error('Invalid GitHub token');
            }
        }
        
        const data = {
            name: name,
            description: description
        };
        
        if (token) {
            data.value = token;
        }
        
        await updateItem('githubToken', id, data);
        hideModal('edit-github-token-modal');
    } catch (error) {
        console.error('Error updating GitHub token:', error);
        showError(error.message);
    }
}

// Function to handle editing items
async function editItem(type, id) {
    try {
        console.log(`Editing ${type} with ID: ${id}`);
        
        // Fetch item details
        const endpoint = getEndpointUrl(type, id);
        const response = await fetch(`/admin/${endpoint}`);
        if (!response.ok) throw new Error(`Failed to fetch ${type} details`);
        
        const item = await response.json();
        console.log(`Fetched ${type} details:`, item);
        
        // Show modal and populate fields based on type
        switch (type) {
            case 'variable':
                document.getElementById('edit-variable-id').value = item.id;
                document.getElementById('edit-variable-name').value = item.name;
                document.getElementById('edit-variable-value').value = item.value;
                document.getElementById('edit-variable-description').value = item.description || '';
                showModal('edit-variable-modal');
                break;
                
            case 'directory':
                document.getElementById('dirPath').value = item.path;
                document.getElementById('dirDescription').value = item.description || '';
                document.getElementById('dirRecursive').checked = item.is_recursive;
                document.getElementById('directory-modal').dataset.editingId = item.id;
                
                // Update modal title to show we're editing
                document.querySelector('#directory-modal .admin-modal-title').textContent = 'Edit Directory';
                
                showModal('directory-modal');
                break;
                
            case 'endpoint':
                document.getElementById('edit-endpoint-id').value = item.id;
                document.getElementById('edit-endpoint-name').value = item.name;
                document.getElementById('edit-endpoint-url').value = item.url;
                document.getElementById('edit-endpoint-method').value = item.method;
                document.getElementById('edit-endpoint-description').value = item.description || '';
                showModal('edit-endpoint-modal');
                break;
                
            case 'githubToken':
                document.getElementById('edit-github-token-id').value = item.id;
                document.getElementById('editGithubTokenName').value = item.name;
                document.getElementById('edit-github-token-description').value = item.description || '';
                showModal('edit-github-token-modal');
                break;
                
            default:
                console.error(`Unsupported item type for editing: ${type}`);
                return;
        }
    } catch (error) {
        console.error(`Error editing ${type}:`, error);
        showError(error.message);
    }
}

// Function to handle variable update submission
async function handleVariableUpdate(event) {
    event.preventDefault();
    
    const form = event.target;
    const id = form.dataset.variableId;
    
    // Get the values directly from the form using FormData
    const formData = new FormData(form);
    const data = {
        name: formData.get('name'),
        value: formData.get('value'),
        description: formData.get('description')
    };
    
    await updateItem('variable', id, data);
    hideModal('edit-variable-modal');
}

// Add event listeners when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Variable edit form submission
    const editVariableForm = document.getElementById('edit-variable-form');
    if (editVariableForm) {
        editVariableForm.addEventListener('submit', handleVariableUpdate);
    }
    
    // Close edit variable modal
    const closeEditVariableModal = document.getElementById('close-edit-variable-modal');
    if (closeEditVariableModal) {
        closeEditVariableModal.addEventListener('click', () => hideModal('edit-variable-modal'));
    }

    const cancelEditVariableButton = document.getElementById('cancel-edit-variable-button');
    if (cancelEditVariableButton) {
        cancelEditVariableButton.addEventListener('click', () => hideModal('edit-variable-modal'));
    }
    
    // Directory form buttons
    const saveDirectoryButton = document.getElementById('save-directory-button');
    if (saveDirectoryButton) {
        saveDirectoryButton.addEventListener('click', saveDirectory);
    }
    
    const cancelDirectoryButton = document.getElementById('cancel-directory-button');
    if (cancelDirectoryButton) {
        cancelDirectoryButton.addEventListener('click', () => hideModal('directory-modal'));
    }
    
    // Directory modal close button
    const closeDirectoryButton = document.getElementById('close-directory-modal');
    if (closeDirectoryButton) {
        closeDirectoryButton.addEventListener('click', () => hideModal('directory-modal'));
    }
    
    // Add directory button
    const addDirectoryButton = document.getElementById('add-directory-button');
    if (addDirectoryButton) {
        addDirectoryButton.addEventListener('click', () => {
            document.getElementById('createDirectoryForm').reset();
            showModal('directory-modal');
        });
    }
});

// Toggle token visibility
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

// Helper function to safely parse JSON
function safeJSONParse(text, fieldName) {
    if (!text) return {};
    
    try {
        const parsed = JSON.parse(text);
        
        // Validate that the parsed result is an object
        if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
            throw new Error(`${fieldName} must be a valid JSON object`);
        }
        
        // Check for invalid values in the object
        for (const [key, value] of Object.entries(parsed)) {
            if (typeof value !== 'string' && typeof value !== 'number' && typeof value !== 'boolean') {
                throw new Error(`${fieldName} values must be strings, numbers, or booleans`);
            }
        }
        
        return parsed;
    } catch (e) {
        if (e instanceof SyntaxError) {
            throw new Error(`Invalid JSON format in ${fieldName}: ${e.message}`);
        }
        throw e;
    }
}

// Endpoints management
async function loadEndpoints() {
    await loadItems('endpoint');
}

// Create endpoint
async function createEndpoint(event) {
    event.preventDefault();
    
    const name = document.getElementById('endpointName').value.trim();
    const base_url = document.getElementById('endpointBaseUrl').value.trim();
    const type = document.getElementById('endpointType').value.trim();
    const auth_type = document.getElementById('endpointAuthType').value.trim();
    const auth_token = document.getElementById('endpointAuthToken').value.trim();
    const rate_limit = document.getElementById('endpointRateLimit').value.trim();
    const headersText = document.getElementById('endpointHeaders').value.trim();

    try {
        // Parse and validate headers
        const headers = safeJSONParse(headersText, 'Headers');

        // Construct data object
        const data = {
            name,
            base_url,
            type,
            auth_type,
            auth_token,
            headers,
            rate_limit: rate_limit ? parseInt(rate_limit) : null
        };

        // Validate all input
        validateEndpointInput(data);

        // Send request
        await createItem('endpoint', data, 'endpoint-modal');
    } catch (error) {
        console.error('Error:', error.message);
        alert(error.message);
    }
}

// Endpoint validation patterns
const ENDPOINT_VALIDATION = {
    name: {
        pattern: /^[a-zA-Z0-9][a-zA-Z0-9_-]{2,49}$/,
        message: "Name must be 3-50 characters and contain only letters, numbers, dashes, and underscores"
    },
    base_url: {
        pattern: /^https?:\/\/[^\s/$.?#].[^\s]*$/i,
        message: "Base URL must be a valid HTTP(S) URL"
    },
    rate_limit: {
        min: 0,
        max: 1000000,
        message: "Rate limit must be between 0 and 1,000,000"
    }
};

// Helper function to validate endpoint input
function validateEndpointInput(data) {
    // Validate name
    if (!data.name || !ENDPOINT_VALIDATION.name.pattern.test(data.name)) {
        throw new Error(ENDPOINT_VALIDATION.name.message);
    }

    // Validate base URL
    if (!data.base_url || !ENDPOINT_VALIDATION.base_url.pattern.test(data.base_url)) {
        throw new Error(ENDPOINT_VALIDATION.base_url.message);
    }

    // Validate rate limit if provided
    if (data.rate_limit !== null) {
        const rate = parseInt(data.rate_limit);
        if (isNaN(rate) || rate < ENDPOINT_VALIDATION.rate_limit.min || rate > ENDPOINT_VALIDATION.rate_limit.max) {
            throw new Error(ENDPOINT_VALIDATION.rate_limit.message);
        }
    }

    // Validate required fields
    if (!data.type) {
        throw new Error("Endpoint type is required");
    }

    return true;
}

// Add input validation on form fields
document.addEventListener('DOMContentLoaded', function() {
    const endpointHeaders = document.getElementById('endpointHeaders');
    if (endpointHeaders) {
        endpointHeaders.addEventListener('input', function() {
            try {
                if (this.value.trim()) {
                    safeJSONParse(this.value, 'Headers');
                }
                this.setCustomValidity('');
            } catch (error) {
                this.setCustomValidity(error.message);
            }
        });
    }

    const endpointName = document.getElementById('endpointName');
    if (endpointName) {
        endpointName.addEventListener('input', function() {
            try {
                if (!ENDPOINT_VALIDATION.name.pattern.test(this.value)) {
                    this.setCustomValidity(ENDPOINT_VALIDATION.name.message);
                } else {
                    this.setCustomValidity('');
                }
            } catch (error) {
                this.setCustomValidity(error.message);
            }
        });
    }

    const endpointBaseUrl = document.getElementById('endpointBaseUrl');
    if (endpointBaseUrl) {
        endpointBaseUrl.addEventListener('input', function() {
            try {
                if (!ENDPOINT_VALIDATION.base_url.pattern.test(this.value)) {
                    this.setCustomValidity(ENDPOINT_VALIDATION.base_url.message);
                } else {
                    this.setCustomValidity('');
                }
            } catch (error) {
                this.setCustomValidity(error.message);
            }
        });
    }
});

window.saveDirectory = async function(event) {
    if (event) {
        event.preventDefault();
    }
    
    try {
        const directoryPath = document.getElementById('dirPath').value;
        const description = document.getElementById('dirDescription').value;
        const isRecursive = document.getElementById('dirRecursive').checked;

        console.log('Directory path:', directoryPath); // Debug log
        console.log('Description:', description); // Debug log
        console.log('Is recursive:', isRecursive); // Debug log

        if (!directoryPath) {
            showError('Directory path is required');
            return;
        }

        // Check if we're editing an existing directory
        const editingId = document.getElementById('directory-modal').dataset.editingId;
        const method = editingId ? 'PUT' : 'POST';
        const endpoint = editingId ? `/admin/directories/${editingId}` : '/admin/directories';

        const data = {
            path: directoryPath,
            description: description || '',
            is_recursive: isRecursive
        };

        console.log(`${method} to ${endpoint} with data:`, data); // Debug log

        // Get fetch options with admin token
        const options = await getFetchOptions(method);
        options.body = JSON.stringify(data);

        const response = await fetch(endpoint, options);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to save directory');
        }

        const result = await response.json();
        console.log(`${editingId ? 'Updated' : 'Created'} directory:`, result); // Debug log

        // Clear form and modal state
        document.getElementById('createDirectoryForm').reset();
        document.getElementById('directory-modal').dataset.editingId = '';
        hideModal('directory-modal');

        // Refresh the directory list
        await loadItems('directory');
    } catch (error) {
        console.error('Error saving directory:', error);
        showError(error.message);
    }
};
