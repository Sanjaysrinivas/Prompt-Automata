// Fence Library Integration
import { showSuccess, showError } from './fence-ui.js';

export function setupLibraryIntegration(fenceBlock) {
    const checkbox = fenceBlock.element.querySelector('.save-to-library-checkbox');
    if (!checkbox) return;

    checkbox.addEventListener('change', async (e) => {
        if (e.target.checked) {
            await saveToLibrary(fenceBlock);
        }
    });
}

async function saveToLibrary(fenceBlock) {
    try {
        const nameInput = fenceBlock.element.querySelector('.fence-name');
        const formatSelect = fenceBlock.element.querySelector('.fence-format');
        
        const blockData = {
            name: nameInput.value.trim() || 'Untitled Block',
            description: '', // Can be added later if needed
            content: fenceBlock.editor.getValue(),
            format: formatSelect.value,
            metadata: {} // Can be extended with additional metadata
        };

        const response = await fetch('/api/block-library', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(blockData)
        });

        if (!response.ok) {
            throw new Error('Failed to save block to library');
        }

        showSuccess('Block saved to library successfully!');
        
        // Refresh block library if it's open
        if (window.blockLibrary) {
            window.blockLibrary.loadBlocks();
        }
    } catch (error) {
        console.error('Error saving to library:', error);
        showError('Failed to save block to library');
        // Uncheck the checkbox on error
        const checkbox = fenceBlock.element.querySelector('.save-to-library-checkbox');
        if (checkbox) checkbox.checked = false;
    }
}
