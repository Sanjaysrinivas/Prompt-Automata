// Prompt editor functionality
document.addEventListener('DOMContentLoaded', function() {
    const editor = document.getElementById('prompt-editor');
    const previewBtn = document.getElementById('preview-btn');
    const saveBtn = document.getElementById('save-btn');
    const titleInput = document.getElementById('prompt-title');
    const form = document.getElementById('prompt-form');

    let previewMode = false;
    let originalContent = '';

    // Toggle preview mode
    previewBtn?.addEventListener('click', async function() {
        if (!previewMode) {
            // Save original content
            originalContent = editor.value;
            
            try {
                const response = await fetch('/prompts/preview', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        content: editor.value
                    })
                });

                if (!response.ok) {
                    throw new Error('Preview failed');
                }

                const data = await response.json();
                editor.value = data.content;
                previewBtn.textContent = 'Edit';
                editor.readOnly = true;
                previewMode = true;
            } catch (error) {
                console.error('Error previewing prompt:', error);
                alert('Failed to preview prompt. Please try again.');
            }
        } else {
            // Restore original content
            editor.value = originalContent;
            previewBtn.textContent = 'Preview';
            editor.readOnly = false;
            previewMode = false;
        }
    });

    // Save prompt by submitting the form
    saveBtn?.addEventListener('click', function() {
        if (!titleInput.value || !editor.value) {
            alert('Please provide both a title and content for the prompt.');
            return;
        }
        
        // Submit the form to trigger the form submit handler in editor.js
        form.requestSubmit();
    });

    // File browser integration
    const fileBrowser = document.getElementById('file-browser');
    fileBrowser?.addEventListener('click', function(event) {
        if (event.target.classList.contains('file-item')) {
            const filePath = event.target.dataset.path;
            // Insert file reference at cursor position
            const cursorPos = editor.selectionStart;
            const textBefore = editor.value.substring(0, cursorPos);
            const textAfter = editor.value.substring(cursorPos);
            editor.value = `${textBefore}@[${filePath}]${textAfter}`;
            editor.focus();
        }
    });
});
