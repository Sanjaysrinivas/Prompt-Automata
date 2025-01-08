// Initialize CodeMirror and other UI components
document.addEventListener('DOMContentLoaded', () => {
    const mainTextarea = document.getElementById('prompt-content');
    if (mainTextarea) {
        window.editor = CodeMirror.fromTextArea(mainTextarea, {
            mode: 'markdown',
            theme: 'monokai',
            lineNumbers: true,
            lineWrapping: true,
            matchBrackets: true,
            autoCloseBrackets: true,
            styleActiveLine: true,
            scrollbarStyle: 'simple'
        });
    }

    // File input handling
    const fileInput = document.getElementById('file-input');
    
    fileInput?.addEventListener('change', (event) => {
        const files = Array.from(event.target.files);
        if (!window.editor || files.length === 0) return;
        
        files.forEach(file => {
            const cursorPos = window.editor.getCursor();
            const fileName = file.name;
            const fileRef = `@[${fileName}]`;
            window.editor.replaceRange(fileRef, cursorPos);
            window.editor.setCursor(cursorPos.line, cursorPos.ch + fileRef.length);
        });
        
        // Reset file input
        fileInput.value = '';
    });
});

// Handle form submission
const form = document.getElementById('prompt-form');
if (form) {
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        
        try {
            // Disable submit button and show loading state
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Saving...';
            
            // Get form data
            const title = document.getElementById('prompt-title').value;
            const description = document.getElementById('prompt-description').value;
            const tags = document.getElementById('prompt-tags').value.split(',').map(tag => tag.trim()).filter(Boolean);
            const isTemplate = document.getElementById('save-template').checked;
            
            // Get fence content
            const fences = [];
            let hasValidationError = false;
            let errorMessage = '';

            document.querySelectorAll('.fence-block').forEach((block, index) => {
                const textarea = block.querySelector('.fence-content-editor');
                const editor = textarea ? textarea.nextSibling.CodeMirror : null;
                const formatSelect = block.querySelector('.fence-format');
                const nameInput = block.querySelector('.fence-name');
                
                if (editor && formatSelect && nameInput) {
                    const name = nameInput.value.trim();
                    const content = editor.getValue().trim();
                    
                    if (!name) {
                        hasValidationError = true;
                        errorMessage = `Fence block ${index + 1} is missing a name`;
                        nameInput.classList.add('border-red-500');
                        return;
                    }
                    
                    if (!content) {
                        hasValidationError = true;
                        errorMessage = `Fence block ${index + 1} is missing content`;
                        editor.getWrapperElement().classList.add('border-red-500');
                        return;
                    }

                    // Check for at least one reference in the content
                    const referencePattern = /@\[(var|github|api|file):[^\]]+\]/;
                    if (!referencePattern.test(content)) {
                        hasValidationError = true;
                        errorMessage = `Fence block ${index + 1} must contain at least one reference in the format @[type:name] where type is var, github, api, or file`;
                        editor.getWrapperElement().classList.add('border-red-500');
                        return;
                    }

                    fences.push({
                        position: index,
                        name: name,
                        format: formatSelect.value,
                        content: content
                    });
                }
            });

            if (hasValidationError) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
                alert(errorMessage);
                return;
            }

            // Prepare JSON data
            const jsonData = {
                title,
                description,
                tags,
                is_template: isTemplate,
                fences
            };
            
            // Get prompt ID if editing
            const promptId = document.getElementById('prompt-id')?.value;
            const url = promptId ? `/prompts/${promptId}` : '/prompts';
            
            // Submit form
            const response = await fetch(url, {
                method: promptId ? 'PUT' : 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(jsonData)
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            const result = await response.json();
            
            // Show success message
            const successMsg = document.createElement('div');
            successMsg.className = 'fixed bottom-4 right-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded';
            successMsg.innerHTML = '<i class="fas fa-check mr-2"></i>Prompt saved successfully!';
            document.body.appendChild(successMsg);
            
            // Remove success message after 3 seconds
            setTimeout(() => {
                successMsg.remove();
            }, 3000);
            
            // Redirect after success
            setTimeout(() => {
                window.location.href = '/prompts';
            }, 1000);
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to save prompt: ' + error.message);
        } finally {
            // Re-enable submit button and restore original text
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });
}
