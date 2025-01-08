class FilePicker {
    constructor() {
        this.selectedFiles = new Set();
        this.lastSelectedFile = null;
        this.currentFiles = null;
        this.onFilesSelected = null; // Callback for handling selected files
        this.initializeElements();
        this.setupEventListeners();
        this.loadFiles();
    }

    initializeElements() {
        this.fileList = document.getElementById('file-list');
        this.previewCode = document.getElementById('preview-code');
        this.previewFilePath = document.getElementById('preview-file-path');
        this.searchInput = document.getElementById('file-search');
        this.filePathInput = document.getElementById('file-path');
    }

    setupEventListeners() {
        if (this.searchInput) {
            this.searchInput.addEventListener('input', () => this.filterFiles());
        }

        if (this.fileList) {
            this.fileList.addEventListener('click', async (event) => {
                const fileItem = event.target.closest('.file-item');
                if (!fileItem) return;

                const filePath = fileItem.dataset.path;
                if (!filePath) return;

                try {
                    await this.handleFileSelection(fileItem, filePath, event);
                } catch (error) {
                    console.error('Error handling file selection:', error);
                }
            });
        }
    }

    async handleFileSelection(fileItem, filePath, event) {
        const isCtrlPressed = event.ctrlKey || event.metaKey;
        const isShiftPressed = event.shiftKey;

        // Update token count display
        await this.updateTokenCount(fileItem, filePath);

        if (isCtrlPressed) {
            // Toggle selection of clicked file
            if (this.selectedFiles.has(filePath)) {
                this.selectedFiles.delete(filePath);
                fileItem.classList.remove('selected');
            } else {
                this.selectedFiles.add(filePath);
                fileItem.classList.add('selected');
            }
        } else if (isShiftPressed && this.lastSelectedFile) {
            // Select range of files
            const files = Array.from(this.fileList.children);
            const currentIndex = files.indexOf(fileItem);
            const lastIndex = files.findIndex(item => item.dataset.path === this.lastSelectedFile);
            
            const start = Math.min(currentIndex, lastIndex);
            const end = Math.max(currentIndex, lastIndex);

            // Clear previous selection
            this.selectedFiles.clear();
            files.forEach(item => item.classList.remove('selected'));

            // Select files in range
            for (let i = start; i <= end; i++) {
                const path = files[i].dataset.path;
                if (path) {
                    this.selectedFiles.add(path);
                    files[i].classList.add('selected');
                }
            }
        } else {
            // Single file selection
            this.selectedFiles.clear();
            this.fileList.querySelectorAll('.file-item').forEach(item => item.classList.remove('selected'));
            this.selectedFiles.add(filePath);
            fileItem.classList.add('selected');
        }

        this.lastSelectedFile = filePath;
        await this.previewFile(filePath);

        // Call the callback with selected files if it exists
        if (typeof this.onFilesSelected === 'function') {
            try {
                // Sort files consistently before calling callback
                const sortedFiles = Array.from(this.selectedFiles).sort((a, b) => a.localeCompare(b));
                await this.onFilesSelected(sortedFiles);
            } catch (error) {
                console.error('Error in files selected callback:', error);
            }
        }
    }

    async previewFile(path) {
        if (!path) {
            console.warn('Attempted to preview file with empty path');
            return;
        }

        try {
            const response = await fetch(`/api/preview/file?path=${encodeURIComponent(path)}`);
            if (!response.ok) {
                throw new Error(`Failed to load file content: ${response.status} ${response.statusText}`);
            }
            
            let data;
            try {
                data = await response.json();
            } catch (parseError) {
                console.error('Error parsing file preview JSON:', parseError);
                throw new Error('Failed to parse file content data');
            }

            if (!data || typeof data !== 'object') {
                throw new Error('Invalid file content data received');
            }
            
            // Safely handle path display
            this.previewFilePath.textContent = path || 'Unknown file';
            
            // Safely handle content
            const content = data.content || '';
            const tokenCount = data.tokenCount ?? 0;  // Use nullish coalescing for numeric values
            
            // Only append token count if it's a valid number
            if (typeof tokenCount === 'number' && !isNaN(tokenCount)) {
                this.previewFilePath.textContent += ` (${tokenCount} tokens)`;
            }
            
            this.previewCode.textContent = content;
            
            // Safely apply syntax highlighting
            if (window.hljs && this.previewCode) {
                try {
                    hljs.highlightElement(this.previewCode);
                } catch (highlightError) {
                    console.warn('Error applying syntax highlighting:', highlightError);
                }
            }
        } catch (error) {
            console.error('Error previewing file:', error);
            if (this.previewFilePath) {
                this.previewFilePath.textContent = path || 'Unknown file';
            }
            if (this.previewCode) {
                this.previewCode.textContent = `Error: ${error.message || 'Failed to load file content'}`;
            }
        }
    }

    async updateTokenCount(fileItem, filePath) {
        try {
            // Try to get existing token count element
            let tokenCountEl = fileItem.querySelector('.token-count');
            
            // Create token count element if it doesn't exist
            if (!tokenCountEl) {
                tokenCountEl = document.createElement('span');
                tokenCountEl.className = 'token-count';
                fileItem.appendChild(tokenCountEl);
            }

            // Show loading state
            tokenCountEl.textContent = 'Counting...';

            // Get token count using the existing countFileTokens function
            const tokenCount = await window.countFileTokens(filePath);
            
            // Update display
            tokenCountEl.textContent = `${tokenCount} tokens`;
        } catch (error) {
            console.error('Error updating token count:', error);
            // Remove token count element if it exists
            const tokenCountEl = fileItem.querySelector('.token-count');
            if (tokenCountEl) {
                tokenCountEl.remove();
            }
        }
    }

    filterFiles() {
        const searchTerm = (this.searchInput?.value || '').toLowerCase();
        const items = this.fileList?.getElementsByClassName('file-item') || [];
        
        Array.from(items).forEach(item => {
            if (!item) return;
            const fileName = item.textContent?.toLowerCase() || '';
            item.style.display = fileName.includes(searchTerm) ? '' : 'none';
        });
    }

    async loadFiles() {
        if (!this.fileList) {
            console.warn('File list element not found');
            return;
        }

        try {
            const response = await fetch('/api/files');
            if (!response.ok) {
                throw new Error(`Failed to load files: ${response.status} ${response.statusText}`);
            }
            
            let files;
            try {
                files = await response.json();
            } catch (parseError) {
                console.error('Error parsing files JSON:', parseError);
                throw new Error('Failed to parse files data');
            }

            if (!Array.isArray(files)) {
                throw new Error('Invalid files data received: expected an array');
            }
            
            // Filter out invalid file entries
            this.currentFiles = files.filter(file => {
                return file && typeof file === 'object' && 
                       typeof file.name === 'string' && 
                       typeof file.type === 'string' &&
                       typeof file.path === 'string';
            });
            
            // Sort files consistently before rendering
            this.currentFiles.sort((a, b) => {
                // First sort by type (directories first)
                if (a.type === 'directory' && b.type !== 'directory') return -1;
                if (a.type !== 'directory' && b.type === 'directory') return 1;
                
                // Then sort by name using localeCompare
                return (a.name || '').localeCompare(b.name || '');
            });
            
            this.renderFiles(this.currentFiles);
        } catch (error) {
            console.error('Error loading files:', error);
            if (this.fileList) {
                this.fileList.innerHTML = `<div class="error">Error: ${error.message || 'Failed to load files'}</div>`;
            }
        }
    }

    renderFiles(files) {
        if (!this.fileList || !Array.isArray(files)) return;

        this.fileList.innerHTML = '';
        files.forEach(file => {
            if (!file || typeof file !== 'object') return;

            const item = document.createElement('div');
            item.className = 'file-item';
            item.dataset.path = file.path || '';
            
            const icon = document.createElement('i');
            icon.className = file.type === 'directory' ? 'fas fa-folder' : 'fas fa-file';
            
            const text = document.createElement('span');
            text.textContent = file.name || 'Unnamed file';
            
            item.appendChild(icon);
            item.appendChild(text);
            this.fileList.appendChild(item);
        });
    }

    setFilesSelectedCallback(callback) {
        if (typeof callback !== 'function') {
            console.warn('Invalid callback provided to setFilesSelectedCallback');
            return;
        }
        this.onFilesSelected = callback;
    }
}

// Initialize FilePicker when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.filePicker = new FilePicker();
});
