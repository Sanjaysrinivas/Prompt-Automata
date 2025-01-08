import { FenceBlock } from './fence-core.js';
import { showSuccess, showError } from './fence-ui.js';
import { showReferencePicker } from './fence-references.js';
import { FenceDragAndDrop } from './fence-dnd.js';
import { FileHandler } from './fence-file.js';
import { previewFenceContent } from './fence-preview.js';
import { initializeRefreshButtons } from './fence-tokens.js';

let sortableInstance = null;
let isInitialized = false;
let dndInstance = null;

export function initializeFenceEditor() {
    // Prevent multiple initializations
    if (isInitialized) {
        console.warn('Fence editor already initialized');
        return;
    }

    // Wait for CodeMirror to be available
    if (typeof CodeMirror === 'undefined') {
        console.warn('CodeMirror not loaded yet, retrying in 100ms...');
        setTimeout(initializeFenceEditor, 100);
        return;
    }

    // Initialize preview button
    const previewBtn = document.getElementById('preview-btn');
    if (previewBtn) {
        previewBtn.addEventListener('click', () => {
            console.log('Preview button clicked');
            previewFenceContent();
        });
    } else {
        console.error('Preview button not found');
    }

    // Initialize global fencing first
    initializeGlobalFencing();

    // Initialize drag and drop
    const fencesList = document.getElementById('fences-list');
    if (fencesList) {
        dndInstance = new FenceDragAndDrop(fencesList);
    }

    // Initialize block library
    if (typeof window.blockLibrary === 'undefined') {
        window.blockLibrary = new BlockLibrary();
    }
    // Initialize refresh buttons
    initializeRefreshButtons();

    const editor = {
        addFenceBlock: async function(blockData) {
            try {
                const template = document.getElementById('fence-block-template');
                const container = document.getElementById('fences-list');
                
                if (!template || !container) {
                    throw new Error('Required elements not found');
                }

                // Clone the template
                const clone = document.importNode(template.content, true);
                const newBlock = clone.querySelector('.fence-block');
                
                // Generate a unique ID for the fence block
                const blockId = 'fence-' + Date.now();
                newBlock.id = blockId;
                newBlock.dataset.blockId = blockId;  // Set the data-block-id attribute
                
                // Set the name and format first
                const nameInput = newBlock.querySelector('.fence-name');
                const formatSelect = newBlock.querySelector('.fence-format');
                if (nameInput) nameInput.value = blockData.name;
                if (formatSelect) formatSelect.value = blockData.format;

                // Initialize the new fence block
                const fenceBlock = new FenceBlock(newBlock);
                
                // Set content in CodeMirror editor
                if (fenceBlock.editor) {
                    fenceBlock.editor.setValue(blockData.content);
                    fenceBlock.editor.refresh();
                }

                // Add reference button handler
                const referenceBtn = newBlock.querySelector('.insert-reference-btn');
                if (referenceBtn && fenceBlock.editor) {
                    referenceBtn.addEventListener('click', () => showReferencePicker(fenceBlock.editor));
                }

                // Initialize file handler
                if (fenceBlock.editor) {
                    new FileHandler(fenceBlock, fenceBlock.editor);
                }

                // Make the new block draggable
                if (dndInstance) {
                    dndInstance.makeDraggable(newBlock);
                }

                // Append the new block
                container.appendChild(newBlock);
                
                // Initialize sortable if available
                if (typeof initializeSortable === 'function') {
                    initializeSortable();
                }
                
                // Update positions
                if (typeof updateFencePositions === 'function') {
                    updateFencePositions();
                }

                // Initialize with zero tokens but don't reset global counter
                const event = new CustomEvent('fenceTokenUpdate', {
                    detail: {
                        fenceId: newBlock.id,
                        tokenCount: 0,
                        isNewBlock: true  // Flag to indicate this is a new block
                    }
                });
                document.dispatchEvent(event);

                return newBlock;
            } catch (error) {
                console.error('Error creating fence block:', error);
                showError('Failed to create new fence block');
                return null;
            }
        }
    };

    // Initialize block library with editor reference
    if (typeof window.initializeBlockLibrary === 'function') {
        window.initializeBlockLibrary(editor);
    }

    // Initialize existing fence blocks first
    document.querySelectorAll('.fence-block').forEach(block => {
        try {
            // Generate a unique ID if it doesn't have one
            if (!block.id) {
                block.id = 'fence-' + Date.now();
            }
            
            const fenceBlock = new FenceBlock(block);
            
            // Add reference button handler
            const referenceBtn = block.querySelector('.insert-reference-btn');
            if (referenceBtn && fenceBlock.editor) {
                referenceBtn.addEventListener('click', () => showReferencePicker(fenceBlock.editor));
            }

            // Initialize file handler
            if (fenceBlock.editor) {
                new FileHandler(fenceBlock, fenceBlock.editor);
            }

            // Make block draggable
            if (dndInstance) {
                dndInstance.makeDraggable(block);
            }
        } catch (error) {
            console.error('Error initializing existing fence block:', error);
        }
    });

    // Add New Fence button handler
    const addFenceBtn = document.getElementById('add-fence-btn');
    if (addFenceBtn) {
        // Remove any existing listeners first
        const newClickHandler = async () => {
            try {
                const template = document.getElementById('fence-block-template');
                const container = document.getElementById('fences-list');
                
                if (!template || !container) {
                    throw new Error('Required elements not found. Make sure both fence-block-template and fences-list elements exist.');
                }

                // Clone the template
                const clone = document.importNode(template.content, true);
                const newBlock = clone.querySelector('.fence-block');
                
                // Generate a unique ID for the fence block
                const blockId = 'fence-' + Date.now();
                newBlock.id = blockId;
                newBlock.dataset.blockId = blockId;  // Set the data-block-id attribute
                
                // Initialize the new fence block
                const fenceBlock = new FenceBlock(newBlock);
                
                // Add reference button handler
                const referenceBtn = newBlock.querySelector('.insert-reference-btn');
                if (referenceBtn && fenceBlock.editor) {
                    referenceBtn.addEventListener('click', () => showReferencePicker(fenceBlock.editor));
                }

                // Initialize file handler
                if (fenceBlock.editor) {
                    new FileHandler(fenceBlock, fenceBlock.editor);
                }

                // Make the new block draggable
                if (dndInstance) {
                    dndInstance.makeDraggable(newBlock);
                }

                // Check if global fencing is enabled and apply settings
                const useGlobalFencing = document.getElementById('use-global-fencing');
                const globalFormatSelect = document.getElementById('global-fence-format');
                if (useGlobalFencing?.checked && globalFormatSelect) {
                    const formatSelect = newBlock.querySelector('.fence-format');
                    if (formatSelect) {
                        formatSelect.value = globalFormatSelect.value;
                        formatSelect.disabled = true;
                        formatSelect.classList.add('cursor-not-allowed', 'bg-gray-100', 'opacity-60');
                        formatSelect.parentElement.classList.add('pointer-events-none');
                    }
                }

                // Append the new block
                container.appendChild(newBlock);
                
                // Initialize sortable if available
                if (typeof initializeSortable === 'function') {
                    initializeSortable();
                }
                
                // Update positions
                if (typeof updateFencePositions === 'function') {
                    updateFencePositions();
                }

                // Initialize with zero tokens but don't reset global counter
                const event = new CustomEvent('fenceTokenUpdate', {
                    detail: {
                        fenceId: newBlock.id,
                        tokenCount: 0,
                        isNewBlock: true  // Flag to indicate this is a new block
                    }
                });
                document.dispatchEvent(event);

                // Dispatch event for new fence block
                const event2 = new CustomEvent('fenceBlockAdded', { detail: { block: newBlock } });
                document.dispatchEvent(event2);

            } catch (error) {
                console.error('Error adding new fence block:', error);
            }
        };
        
        addFenceBtn.addEventListener('click', newClickHandler);
    }

    isInitialized = true;
}

function initializeGlobalFencing() {
    const useGlobalFencingCheckbox = document.getElementById('use-global-fencing');
    const globalFormatContainer = document.getElementById('global-fence-format-container');
    const globalFormatSelect = document.getElementById('global-fence-format');

    if (useGlobalFencingCheckbox && globalFormatContainer && globalFormatSelect) {
        // Function to update fence format selects based on global fencing state
        function updateFenceFormatSelects(isGlobalEnabled) {
            document.querySelectorAll('.fence-format').forEach(select => {
                // Disable/enable the select
                select.disabled = isGlobalEnabled;
                
                // Add/remove styles for visual feedback
                if (isGlobalEnabled) {
                    select.classList.add('cursor-not-allowed', 'bg-gray-100', 'opacity-60');
                    select.parentElement.classList.add('pointer-events-none');
                    select.value = globalFormatSelect.value;
                } else {
                    select.classList.remove('cursor-not-allowed', 'bg-gray-100', 'opacity-60');
                    select.parentElement.classList.remove('pointer-events-none');
                }
            });
        }

        useGlobalFencingCheckbox.addEventListener('change', function() {
            // Show/hide the global format dropdown
            globalFormatContainer.classList.toggle('hidden', !this.checked);
            
            // Update fence format selects
            updateFenceFormatSelects(this.checked);

            // Update preview content if needed
            const hasContent = Array.from(document.querySelectorAll('.fence-block')).some(block => {
                const textarea = block.querySelector('.fence-content-editor');
                const editor = textarea ? textarea.nextSibling.CodeMirror : null;
                return editor && editor.getValue().trim();
            });

            if (hasContent) {
                // Call previewPrompt but update the content silently
                const previewModal = document.getElementById('previewModal');
                const wasHidden = previewModal.classList.contains('hidden');
                
                if (typeof window.previewPrompt === 'function') {
                    window.previewPrompt(true); // Pass true to indicate silent update
                }
                
                // Restore modal state if it was hidden
                if (wasHidden) {
                    previewModal.classList.add('hidden');
                }
            }
        });

        // When global format changes, update all fence formats if global fencing is enabled
        globalFormatSelect.addEventListener('change', function() {
            if (useGlobalFencingCheckbox.checked) {
                updateFenceFormatSelects(true);
                const hasContent = Array.from(document.querySelectorAll('.fence-block')).some(block => {
                    const textarea = block.querySelector('.fence-content-editor');
                    const editor = textarea ? textarea.nextSibling.CodeMirror : null;
                    return editor && editor.getValue().trim();
                });

                if (hasContent) {
                    // Call previewPrompt but update the content silently
                    const previewModal = document.getElementById('previewModal');
                    const wasHidden = previewModal.classList.contains('hidden');
                    
                    if (typeof window.previewPrompt === 'function') {
                        window.previewPrompt(true); // Pass true to indicate silent update
                    }
                    
                    // Restore modal state if it was hidden
                    if (wasHidden) {
                        previewModal.classList.add('hidden');
                    }
                }
            }
        });

        // Also handle newly added fence blocks
        document.addEventListener('fenceBlockAdded', function() {
            if (useGlobalFencingCheckbox.checked) {
                updateFenceFormatSelects(true);
            }
        });
    }
}

function initializeSortable() {
    const fencesList = document.getElementById('fences-list');
    if (fencesList && window.Sortable) {
        sortableInstance = new window.Sortable(fencesList, {
            animation: 150,
            handle: '.drag-handle',
            onEnd: updateFencePositions
        });
    }
}

function updateFencePositions() {
    const fencesList = document.getElementById('fences-list');
    if (!fencesList) return;

    const blocks = fencesList.querySelectorAll('.fence-block');
    blocks.forEach((block, index) => {
        block.dataset.position = index;
        
        // Update input names with new position
        const nameInput = block.querySelector('.fence-name');
        const contentTextarea = block.querySelector('.fence-content-editor');
        const formatSelect = block.querySelector('.fence-format');
        
        if (nameInput) nameInput.name = `fences[${index}][name]`;
        if (contentTextarea) contentTextarea.name = `fences[${index}][content]`;
        if (formatSelect) formatSelect.name = `fences[${index}][format]`;
    });
}
