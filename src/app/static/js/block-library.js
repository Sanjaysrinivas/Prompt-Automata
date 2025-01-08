// Block Library Management
class BlockLibrary {
    constructor() {
        this.blocks = [];
        this.allBlocks = []; // Store all blocks separately
        this.fenceEditor = null; // Reference to fence editor
        this.loadBlocks();
        this.setupEventListeners();
    }

    initializeFenceEditor(editor) {
        this.fenceEditor = editor;
    }

    setupEventListeners() {
        // Search functionality
        const searchInput = document.getElementById('blockSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => this.filterBlocks(e.target.value));
        }

        // Category filters
        document.querySelectorAll('.category-filter').forEach(button => {
            button.addEventListener('click', () => {
                document.querySelectorAll('.category-filter').forEach(b => b.classList.remove('active', 'bg-blue-500', 'text-white'));
                button.classList.add('active', 'bg-blue-500', 'text-white');
                this.filterByCategory(button.textContent.trim());
            });
        });
    }

    async loadBlocks() {
        try {
            // First try to load from backend
            const response = await fetch('/api/block-library');
            if (response.ok) {
                this.blocks = await response.json();
                this.allBlocks = [...this.blocks]; // Store a copy
            } else {
                // Fallback to localStorage if backend fails
                const savedBlocks = localStorage.getItem('blockLibrary');
                if (savedBlocks) {
                    this.blocks = JSON.parse(savedBlocks);
                    this.allBlocks = [...this.blocks]; // Store a copy
                }
            }
        } catch (error) {
            console.error('Error loading blocks:', error);
            // Fallback to localStorage
            const savedBlocks = localStorage.getItem('blockLibrary');
            if (savedBlocks) {
                this.blocks = JSON.parse(savedBlocks);
                this.allBlocks = [...this.blocks]; // Store a copy
            }
        }
        this.updateUI();
    }

    createBlockElement(block) {
        const template = document.getElementById('blockItemTemplate');
        if (!template) return null;

        const clone = template.content.cloneNode(true);
        const blockElement = clone.querySelector('.block-item');

        // Set data-block-id for easier element identification
        blockElement.setAttribute('data-block-id', block.id);

        // Set block data
        blockElement.querySelector('.block-name').textContent = block.name || '';
        blockElement.querySelector('.block-format').textContent = block.format || 'fence';

        // Format date or show 'Invalid Date' if date is invalid
        const date = block.dateCreated ? new Date(block.dateCreated) : new Date();
        const dateStr = date instanceof Date && !isNaN(date) ? date.toLocaleDateString() : 'Invalid Date';
        blockElement.querySelector('.block-date').textContent = dateStr;

        // Set content preview with proper truncation
        const content = block.content || '';
        blockElement.querySelector('.block-content').textContent = content.length > 100 ? content.substring(0, 100) + '...' : content;

        // Add event listeners
        blockElement.querySelector('.use-block').addEventListener('click', () => this.useBlock(block.id));
        blockElement.querySelector('.export-block').addEventListener('click', () => this.exportSingleBlock(block));
        blockElement.querySelector('.delete-block').addEventListener('click', () => this.deleteBlock(block.id));

        return blockElement;
    }

    async saveBlock(block) {
        try {
            // Try to save to backend first
            const response = await fetch('/api/block-library', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(block)
            });

            if (!response.ok) {
                throw new Error('Failed to save to server');
            }

            const savedBlock = await response.json();

            // Update local state
            this.blocks = [...this.blocks, savedBlock];
            this.allBlocks = [...this.blocks];
            localStorage.setItem('blockLibrary', JSON.stringify(this.blocks));

            // Update UI
            const libraryList = document.querySelector('.block-library-list');
            const blockElement = this.createBlockElement(savedBlock);
            if (libraryList && blockElement) {
                libraryList.appendChild(blockElement);
            }

            showSuccess('Block saved to library');
            return savedBlock;
        } catch (error) {
            console.error('Error saving block:', error);
            showError('Failed to save block to library');
            throw error;
        }
    }

    updateUI() {
        const libraryList = document.querySelector('.block-library-list');
        const emptyState = document.getElementById('emptyState');
        if (!libraryList) return;

        libraryList.innerHTML = '';

        if (!this.blocks || this.blocks.length === 0) {
            emptyState?.classList.remove('hidden');
            return;
        }

        emptyState?.classList.add('hidden');

        this.blocks.forEach(block => {
            const blockElement = this.createBlockElement(block);
            if (blockElement) {
                libraryList.appendChild(blockElement);
            }
        });
    }

    filterBlocks(searchTerm) {
        if (!searchTerm) {
            this.blocks = [...this.allBlocks];
            this.updateUI();
            return;
        }

        const filteredBlocks = this.allBlocks.filter(block =>
            block.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            block.content.toLowerCase().includes(searchTerm.toLowerCase())
        );

        const emptyState = document.getElementById('emptyState');

        if (filteredBlocks.length === 0) {
            emptyState?.classList.remove('hidden');
            if (emptyState) {
                emptyState.querySelector('h3').textContent = 'No matching blocks';
                emptyState.querySelector('p').textContent = 'Try a different search term';
            }
        } else {
            emptyState?.classList.add('hidden');
        }

        this.blocks = filteredBlocks;
        this.updateUI();
    }

    filterByCategory(category) {
        switch (category) {
            case 'Recently Added':
                this.blocks = [...this.allBlocks].sort((a, b) =>
                    new Date(b.dateCreated) - new Date(a.dateCreated)
                );
                break;
            case 'Most Used':
                this.blocks = [...this.allBlocks].sort((a, b) =>
                    (b.useCount || 0) - (a.useCount || 0)
                );
                break;
            default: // All Blocks
                this.blocks = [...this.allBlocks];
        }

        this.updateUI();
    }

    async useBlock(blockId) {
        const block = this.blocks.find(b => b.id === blockId);
        if (!block) {
            showError('Block not found');
            return;
        }

        if (!this.fenceEditor) {
            showError('Fence editor not initialized');
            return;
        }

        try {
            // Create a new fence block with the library block content
            this.fenceEditor.addFenceBlock({
                name: block.name,
                content: block.content,
                format: block.format
            });
            showSuccess('Block added successfully');
        } catch (error) {
            console.error('Error using block:', error);
            showError('Failed to add block');
        }
    }

    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    async importFromFile() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            try {
                const content = await file.text();
                const importedBlocks = JSON.parse(content);

                // Validate the imported blocks
                if (!Array.isArray(importedBlocks)) {
                    throw new Error('Invalid format: Expected an array of blocks');
                }

                // Validate each block has required fields
                importedBlocks.forEach(block => {
                    if (!block.name || !block.content || !block.format) {
                        throw new Error('Invalid block format: Each block must have name, content, and format');
                    }
                });

                try {
                    // Try to save to backend first
                    const response = await fetch('/api/block-library/import', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            blocks: importedBlocks.map(block => ({
                                name: block.name,
                                content: block.content,
                                format: block.format,
                                description: block.description || '',
                                metadata: block.metadata || {}
                            }))
                        })
                    });

                    if (!response.ok) {
                        const errorData = await response.json().catch(() => ({}));
                        throw new Error(errorData.error || 'Failed to save to server');
                    }

                    const savedBlocks = await response.json();
                    this.blocks = [...this.blocks, ...savedBlocks];
                    this.allBlocks = [...this.blocks];
                    localStorage.setItem('blockLibrary', JSON.stringify(this.blocks));

                    this.updateUI();
                    showSuccess(`Successfully imported ${savedBlocks.length} blocks`);
                } catch (error) {
                    console.error('Failed to save to server:', error);
                    showError(error.message || 'Failed to import blocks');
                }
            } catch (error) {
                console.error('Error importing blocks:', error);
                showError(error.message || 'Failed to import blocks');
            }
        };
        input.click();
    }

    async exportSelectedBlocks() {
        try {
            const response = await fetch('/api/block-library/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    block_ids: this.blocks.map(block => block.id.toString())
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || 'Failed to export blocks');
            }

            const blocks = await response.json();
            const blob = new Blob([JSON.stringify(blocks, null, 2)], { type: 'application/json' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `block-library-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            showSuccess('Blocks exported successfully');
        } catch (error) {
            console.error('Error exporting blocks:', error);
            showError(error.message || 'Failed to export blocks');
        }
    }

    exportBlocks() {
        try {
            // Get blocks to export
            const blocksToExport = this.blocks.map(block => ({
                name: block.name,
                content: block.content,
                format: block.format
            }));

            // Create blob and download
            const blob = new Blob([JSON.stringify(blocksToExport, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `block-library-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            showSuccess('Blocks exported successfully');
        } catch (error) {
            console.error('Error exporting blocks:', error);
            showError('Failed to export blocks');
        }
    }

    exportSingleBlock(block) {
        try {
            // Create a single block export
            const blockToExport = {
                name: block.name,
                content: block.content,
                format: block.format
            };

            // Create blob and download
            const blob = new Blob([JSON.stringify([blockToExport], null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `block-${block.name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            showSuccess('Block exported successfully');
        } catch (error) {
            console.error('Error exporting block:', error);
            showError('Failed to export block');
        }
    }

    async deleteBlock(blockId) {
        try {
            // Confirm deletion
            if (!confirm('Are you sure you want to delete this block?')) {
                return;
            }

            // Try to delete from backend first
            const response = await fetch(`/api/block-library/${blockId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Failed to delete from server');
            }

            // Update local state
            this.blocks = this.blocks.filter(block => block.id !== blockId);
            this.allBlocks = this.allBlocks.filter(block => block.id !== blockId);
            localStorage.setItem('blockLibrary', JSON.stringify(this.blocks));

            // Remove block element from UI
            const blockElement = document.querySelector(`[data-block-id="${blockId}"]`);
            if (blockElement) {
                blockElement.remove();
            }

            // Update UI if needed
            if (this.blocks.length === 0) {
                const emptyState = document.getElementById('emptyState');
                emptyState?.classList.remove('hidden');
            }

            showSuccess('Block deleted successfully');
        } catch (error) {
            console.error('Error deleting block:', error);
            showError('Failed to delete block');

            // Fallback: Delete from local storage only if server deletion fails
            this.blocks = this.blocks.filter(block => block.id !== blockId);
            this.allBlocks = this.allBlocks.filter(block => block.id !== blockId);
            localStorage.setItem('blockLibrary', JSON.stringify(this.blocks));

            // Remove block element from UI
            const blockElement = document.querySelector(`[data-block-id="${blockId}"]`);
            if (blockElement) {
                blockElement.remove();
            }

            // Update UI if needed
            if (this.blocks.length === 0) {
                const emptyState = document.getElementById('emptyState');
                emptyState?.classList.remove('hidden');
            }
        }
    }
}

// Utility functions for notifications
function showError(message) {
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-4 right-4 bg-red-500 text-white px-6 py-3 rounded shadow-lg z-50';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function showSuccess(message) {
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-6 py-3 rounded shadow-lg z-50';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// Toggle block library panel
function toggleBlockLibrary() {
    const panel = document.getElementById('blockLibraryPanel');
    if (panel) {
        panel.classList.toggle('translate-x-full');
    }
}

// Make toggleBlockLibrary available globally
window.toggleBlockLibrary = toggleBlockLibrary;

// Initialize block library when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.blockLibrary = new BlockLibrary();
});

// Make functions available globally
window.toggleBlockLibrary = toggleBlockLibrary;
window.initializeBlockLibrary = (editor) => {
    if (window.blockLibrary) {
        window.blockLibrary.initializeFenceEditor(editor);
    }
};
