// Save functionality for fence blocks
import { showSuccess, showError } from './fence-ui.js';
import { fenceAPI } from './fence-api.js';

export class SaveHandler {
    constructor(block, editor) {
        this.block = block;
        this.editor = editor;
        this.initialize();
    }

    initialize() {
        this.setupSaveCheckbox();
    }

    setupSaveCheckbox() {
        // Create save checkbox if it doesn't exist
        const saveAsTemplateLabel = document.createElement('label');
        saveAsTemplateLabel.className = 'flex items-center space-x-2 mt-2';
        saveAsTemplateLabel.innerHTML = `
            <input type="checkbox" class="save-as-template form-checkbox h-4 w-4 text-blue-600">
            <span class="text-sm text-gray-700">Save as Template</span>
        `;
        
        // Add the checkbox after the name input
        const nameInput = this.block.querySelector('.fence-name');
        if (nameInput) {
            nameInput.parentNode.insertBefore(saveAsTemplateLabel, nameInput.nextSibling);
        }
        
        // Add auto-save functionality when checkbox is toggled
        const saveAsTemplateCheckbox = saveAsTemplateLabel.querySelector('.save-as-template');
        saveAsTemplateCheckbox.addEventListener('change', async (e) => {
            if (e.target.checked) {
                await this.saveToLibrary();
            }
        });
    }

    async saveToLibrary() {
        try {
            const nameInput = this.block.querySelector('.fence-name');
            const content = this.editor ? this.editor.getValue() : '';

            const blockData = {
                name: nameInput.value || 'Untitled Block',
                content: content,
                format: 'fence',
                description: '',
                metadata: {}
            };

            await fenceAPI.saveBlock(blockData);
            showSuccess('Block saved to library');
            
        } catch (error) {
            console.error('Error saving block:', error);
            showError('Failed to save block to library');
            
            // Uncheck the checkbox on error
            const checkbox = this.block.querySelector('.save-as-template');
            if (checkbox) {
                checkbox.checked = false;
            }
        }
    }

    static async saveAllMarkedBlocks() {
        const blocks = document.querySelectorAll('.fence-block');
        const markedBlocks = Array.from(blocks).filter(block => 
            block.querySelector('.save-as-template:checked')
        );

        if (markedBlocks.length === 0) {
            showError('No blocks marked for saving');
            return;
        }

        try {
            for (const block of markedBlocks) {
                const handler = new SaveHandler(block, block.editor);
                await handler.saveToLibrary();
            }
            
            showSuccess('All marked blocks saved to library');
            
            // Uncheck all checkboxes
            markedBlocks.forEach(block => {
                const checkbox = block.querySelector('.save-as-template');
                if (checkbox) {
                    checkbox.checked = false;
                }
            });
            
        } catch (error) {
            console.error('Error saving blocks:', error);
            showError('Failed to save some blocks to library');
        }
    }
}
