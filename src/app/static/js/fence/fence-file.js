// File handling functionality for fence blocks
import { showSuccess, showError } from './fence-ui.js';
import { countTokens } from './fence-tokens.js';

export class FileHandler {
    constructor(block, editor) {
        this.block = block;
        this.editor = editor;
        this.element = block.element;
        this.initialize();
    }

    initialize() {
        this.setupFileInput();
        this.setupInsertButton();
    }

    setupFileInput() {
        // Create file input if it doesn't exist
        let fileInput = this.element.querySelector('.fence-file-input');
        if (!fileInput) {
            fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.className = 'fence-file-input hidden';
            fileInput.multiple = true;
            fileInput.accept = '*/*';
            this.element.appendChild(fileInput);
        }

        // Handle file selection
        fileInput.addEventListener('change', (e) => this.handleFileSelection(e));
    }

    setupInsertButton() {
        const insertBtn = this.element.querySelector('.insert-file-btn');
        if (insertBtn) {
            insertBtn.addEventListener('click', () => {
                const fileInput = this.element.querySelector('.fence-file-input');
                if (fileInput) {
                    fileInput.click();
                }
            });
        }
    }

    async handleFileSelection(e) {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;

        // Initialize fileContents if it doesn't exist
        if (!this.block.fileContents) {
            this.block.fileContents = new Map();
        }

        const cursor = this.editor.getCursor();
        for (const file of files) {
            try {
                // Read file content
                const content = await file.text();
                
                // Count tokens for the file content
                const response = await fetch('/api/count_text', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: content })
                });
                
                if (!response.ok) {
                    throw new Error(`Failed to count tokens: ${response.statusText}`);
                }

                const data = await response.json();
                const tokenCount = data.token_count || 0;

                // Store content and token count
                const fileData = {
                    content: content,
                    tokenCount: tokenCount
                };
                this.block.fileContents.set(file.name, fileData);
                
                // Insert file reference at cursor position
                const fileRef = `@[file:${file.name}]`;
                this.editor.replaceRange(fileRef + '\n', cursor);

                console.log(`File ${file.name} token count:`, tokenCount); // Debug log

                // Trigger token count update using the correct method
                if (typeof this.block.updateTokens === 'function') {
                    await this.block.updateTokens();
                } else {
                    console.warn('Token count update method not found');
                }

            } catch (error) {
                console.error('Error processing file:', error);
                showError(`Error processing file ${file.name}: ${error.message}`);
            }
        }

        // Reset file input
        e.target.value = '';
        showSuccess('Files referenced successfully');
    }
}
