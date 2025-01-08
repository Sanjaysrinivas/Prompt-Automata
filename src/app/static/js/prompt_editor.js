document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('prompt-form');
    const saveBtn = document.getElementById('save-btn');
    const previewBtn = document.getElementById('preview-btn');
    const titleInput = document.getElementById('prompt-title');
    const descriptionInput = document.getElementById('prompt-description');
    const tagsInput = document.getElementById('prompt-tags');
    const saveTemplateCheckbox = document.getElementById('save-template');
    
    async function savePrompt() {
        const fences = getFenceData();
        if (!validateForm(fences)) return;

        const providerSelect = document.getElementById('provider-select');
        const modelSelect = document.getElementById('model-select');
        
        console.debug('Selected provider:', providerSelect.value);
        console.debug('Selected model:', modelSelect.value);

        const promptData = {
            title: titleInput.value,
            content: '', // Content will be derived from fences
            description: descriptionInput.value,
            tags: tagsInput.value.split(',').map(tag => tag.trim()).filter(tag => tag),
            is_template: saveTemplateCheckbox.checked,
            provider: providerSelect.value,  
            model: modelSelect.value,        
            fences: fences.map((fence, index) => ({
                ...fence,
                position: index
            }))
        };

        console.debug('Saving prompt with data:', promptData);

        try {
            const response = await fetch('/prompts/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(promptData)
            });

            const data = await response.json();
            console.debug('Server response:', data);

            if (response.ok) {
                // If a redirect URL is provided, go to the generation page
                if (data.redirect) {
                    window.location.href = data.redirect;
                }
            } else {
                showError(data.error || 'Failed to save prompt');
            }
        } catch (error) {
            showError('Network error occurred while saving');
            console.error('Save error:', error);
        }
    }

    function validateForm(fences) {
        if (!titleInput.value) {
            showError('Title is required');
            return false;
        }
        if (!fences || fences.length === 0) {
            showError('At least one fence block is required');
            return false;
        }

        const providerSelect = document.getElementById('provider-select');
        const modelSelect = document.getElementById('model-select');
        
        if (!providerSelect.value) {
            showError('Please select a provider');
            return false;
        }
        
        if (!modelSelect.value) {
            showError('Please select a model');
            return false;
        }

        return true;
    }

    function getFenceData() {
        const fenceBlocks = document.querySelectorAll('.fence-block');
        return Array.from(fenceBlocks).map(block => {
            const nameInput = block.querySelector('.fence-name');
            const formatSelect = block.querySelector('.fence-format');
            const contentArea = block.querySelector('.fence-content-editor');
            const editor = contentArea ? contentArea.nextSibling.CodeMirror : null;
            
            if (!editor) {
                console.error('CodeMirror editor not found for fence block');
                return null;
            }

            return {
                name: nameInput.value,
                format: formatSelect.value,
                content: editor.getValue()
            };
        }).filter(Boolean); // Remove any null entries
    }

    function showError(message) {
        // You can implement your preferred error display method here
        alert(message);
    }

    // Event Listeners
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        savePrompt();
    });

    saveBtn.addEventListener('click', (e) => {
        e.preventDefault();
        savePrompt();
    });

    previewBtn.addEventListener('click', (e) => {
        e.preventDefault();
        // Implement preview functionality if needed
    });
});
