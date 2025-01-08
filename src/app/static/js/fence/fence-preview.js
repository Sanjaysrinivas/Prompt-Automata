// Preview functionality for fence blocks
import { wrapContentInFormat } from './fence-format.js';
import { createModal, showSuccess, showError } from './fence-ui.js';

function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

export function previewFenceContent() {
    console.log('Preview function called');
    const fenceBlocks = document.querySelectorAll('.fence-block');
    let previewContent = '';

    fenceBlocks.forEach((block, index) => {
        const nameInput = block.querySelector('.fence-name');
        const formatSelect = block.querySelector('.fence-format');
        const editor = block.querySelector('.CodeMirror')?.CodeMirror;

        // Update CodeMirror instance to show scrollbar
        if (editor) {
            editor.setOption('scrollbarStyle', 'native');
            editor.setOption('viewportMargin', Infinity);
            editor.refresh();
        }

        if (nameInput && formatSelect && editor) {
            const name = nameInput.value.trim();
            const format = formatSelect.value;
            const content = editor.getValue().trim();

            console.log('Processing fence block:', { name, format });

            if (content) {
                // Add spacing between blocks
                if (index > 0) {
                    previewContent += '\n\n';
                }
                // Pass the name directly without modification
                previewContent += wrapContentInFormat(content, format, name);
            }
        }
    });

    if (!previewContent) {
        previewContent = 'No fence blocks';
        return;
    }

    console.log('Final preview content:', previewContent);

    // Create modal with preview content
    const modal = createModal({
        title: 'Preview',
        content: `
            <div class="space-y-4">
                <div class="text-sm text-gray-500">
                    This is how your fence blocks will be formatted when used. Any @[type:value] references will be replaced with their actual content.
                </div>
                <div style="max-height: 60vh; overflow-y: scroll;" class="custom-scrollbar">
                    <pre id="previewContent" class="whitespace-pre-wrap font-mono text-sm bg-gray-50 p-4 rounded-md border border-gray-200"></pre>
                </div>
            </div>
            <style>
                .custom-scrollbar::-webkit-scrollbar {
                    width: 8px;
                }
                .custom-scrollbar::-webkit-scrollbar-track {
                    background: #f1f1f1;
                    border-radius: 4px;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb {
                    background: #888;
                    border-radius: 4px;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover {
                    background: #555;
                }
            </style>
        `,
        width: 'w-3/4',
        maxHeight: 'max-h-[80vh]',
        headerButtons: createCopyButton()
    });

    modal.show();

    // Make the API call to get the preview content
    fetch('/prompts/preview', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            content: previewContent,
            fence_format: '',  // Not needed for the overall preview
            fence_name: ''     // Not needed for the overall preview
        })
    })
    .then(response => response.text())
    .then(data => {
        const previewElement = document.getElementById('previewContent');
        previewElement.textContent = data;
        
        // Force scrollbar to show by setting a minimum height
        if (previewElement.scrollHeight > previewElement.clientHeight) {
            previewElement.style.minHeight = '60vh';
        }
        setupCopyButton(data);
    })
    .catch(error => {
        console.error('Error fetching preview:', error);
        document.getElementById('previewContent').textContent = 'Error fetching preview content';
    });

}

function createCopyButton() {
    return `
        <button id="copyPreviewBtn" 
            class="p-2 text-gray-600 hover:text-blue-600 hover:bg-gray-100 rounded-full transition-colors" 
            title="Copy to Clipboard">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"/>
            </svg>
        </button>
    `;
}

function setupCopyButton(content) {
    const copyBtn = document.getElementById('copyPreviewBtn');
    if (copyBtn) {
        copyBtn.addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(content);
                showSuccess('Copied to clipboard!');
                
                // Visual feedback
                const icon = copyBtn.querySelector('svg');
                if (icon) {
                    icon.style.stroke = '#059669';
                    copyBtn.classList.add('bg-green-50');
                    
                    setTimeout(() => {
                        icon.style.stroke = 'currentColor';
                        copyBtn.classList.remove('bg-green-50');
                    }, 2000);
                }
            } catch (err) {
                console.error('Failed to copy:', err);
                showError('Failed to copy to clipboard');
            }
        });
    }
}
