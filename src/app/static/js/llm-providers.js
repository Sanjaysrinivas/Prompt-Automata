// Provider models configuration
const providerModels = {
    anthropic: [
        { id: 'claude-3.5-sonnet', name: 'Claude 3.5 Sonnet' },
        { id: 'claude-3-haiku', name: 'Claude 3 Haiku' },
        { id: 'claude-3-opus', name: 'Claude 3 Opus' }
    ],
    openai: [
        { id: 'gpt-4', name: 'GPT-4' },
        { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo' },
        { id: 'gpt-4-turbo', name: 'GPT-4 Turbo' }
    ],
    google: [
        { id: 'gemini-1.5-pro-1m', name: 'Gemini 1.5 Pro' },
        { id: 'gemini-1.0-pro', name: 'Gemini 1.0 Pro' }
    ]
};

// Function to show error message
function showError(elementId, message) {
    const errorElement = document.getElementById(elementId);
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.remove('hidden');
    }
}

// Function to hide error message
function hideError(elementId) {
    const errorElement = document.getElementById(elementId);
    if (errorElement) {
        errorElement.classList.add('hidden');
    }
}

// Function to fetch and populate LLM providers
async function fetchAndPopulateProviders() {
    try {
        const response = await fetch('/api/llm/providers');
        if (!response.ok) {
            throw new Error('Failed to fetch providers');
        }
        
        const { providers } = await response.json();
        
        // Get the select element
        const select = document.getElementById('provider-select');
        if (!select) return;

        // Clear existing options except the first one
        while (select.options.length > 1) {
            select.remove(1);
        }

        // Hide any previous error
        hideError('provider-error');

        // Add providers to select
        if (Object.keys(providers).length === 0) {
            showError('provider-error', 'No providers available. Please check your configuration.');
            const option = document.createElement('option');
            option.disabled = true;
            option.textContent = 'No providers available';
            select.appendChild(option);
        } else {
            Object.entries(providers).forEach(([provider, info]) => {
                const option = document.createElement('option');
                option.value = provider;
                
                // Add a dot indicator for providers with tokens
                const hasToken = info.has_token ? '🟢' : '⚪';
                option.textContent = `${hasToken} ${provider.charAt(0).toUpperCase() + provider.slice(1)}`;
                
                // Disable options without tokens
                if (!info.has_token) {
                    option.disabled = true;
                }
                
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error fetching providers:', error);
        showError('provider-error', 'Error loading providers. Please try again.');
    }
}

// Function to populate models for a provider
function populateModels(provider) {
    const modelSelect = document.getElementById('model-select');
    const modelContainer = document.getElementById('model-select-container');
    
    // Clear existing options except the first one
    while (modelSelect.options.length > 1) {
        modelSelect.remove(1);
    }

    // Hide any previous error
    hideError('model-error');

    // Show the model select container
    modelContainer.classList.remove('hidden');

    // Get models for the selected provider
    const models = providerModels[provider] || [];

    if (models.length === 0) {
        showError('model-error', 'No models available for this provider');
        return;
    }

    // Add models to select
    models.forEach(model => {
        const option = document.createElement('option');
        option.value = model.id;
        option.textContent = model.name;
        modelSelect.appendChild(option);
    });
}

// Function to get token for selected provider
async function getProviderToken(provider) {
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

        const response = await fetch(`/api/llm/token/${provider}`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to fetch provider token');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error fetching provider token:', error);
        showError('provider-error', `Failed to get token for ${provider}. Please check your configuration.`);
        return null;
    }
}

// Function to generate completion
async function generateCompletion(provider, prompt) {
    try {
        // Hide any previous errors
        hideError('provider-error');
        hideError('model-error');

        const response = await fetch('/api/llm/completion', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                provider: provider,
                prompt: prompt
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to generate completion');
        }

        return await response.json();
    } catch (error) {
        console.error('Error generating completion:', error);
        showError('provider-error', error.message);
        return null;
    }
}

// Initialize when the document is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initial population of providers
    fetchAndPopulateProviders();

    // Add change event listener to provider select
    const providerSelect = document.getElementById('provider-select');
    if (providerSelect) {
        providerSelect.addEventListener('change', async (e) => {
            const provider = e.target.value;
            if (provider) {
                // Hide any previous errors
                hideError('provider-error');
                hideError('model-error');

                // Populate models for the selected provider
                populateModels(provider);
                
                // Get token for the provider
                const tokenData = await getProviderToken(provider);
                if (!tokenData || !tokenData.token) {
                    showError('provider-error', `No valid token found for ${provider}. Please add your API key.`);
                    return;
                }
            } else {
                // Hide model select if no provider is selected
                const modelContainer = document.getElementById('model-select-container');
                modelContainer.classList.add('hidden');
            }
        });
    }

    // Add change event listener to model select
    const modelSelect = document.getElementById('model-select');
    if (modelSelect) {
        modelSelect.addEventListener('change', (e) => {
            const model = e.target.value;
            if (model) {
                // Hide any previous error
                hideError('model-error');
            }
        });
    }

    // Add event listener for generate button
    const generateButton = document.getElementById('generate-button');
    if (generateButton) {
        generateButton.addEventListener('click', async () => {
            const provider = providerSelect.value;
            const promptInput = document.getElementById('prompt-input');
            
            if (!provider) {
                showError('provider-error', 'Please select a provider');
                return;
            }
            
            if (!promptInput || !promptInput.value.trim()) {
                showError('provider-error', 'Please enter a prompt');
                return;
            }

            try {
                // Show loading state
                generateButton.disabled = true;
                generateButton.textContent = 'Generating...';

                // Generate completion
                const result = await generateCompletion(provider, promptInput.value.trim());
                
                if (result) {
                    // Update response display
                    const responseDisplay = document.getElementById('response-display');
                    if (responseDisplay) {
                        responseDisplay.textContent = result.content;
                    }
                }
            } finally {
                // Reset button state
                generateButton.disabled = false;
                generateButton.textContent = 'Generate';
            }
        });
    }
});
