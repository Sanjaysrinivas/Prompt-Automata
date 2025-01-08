// Drag and Drop functionality for fence blocks
import { showSuccess } from './fence-ui.js';

export class FenceDragAndDrop {
    constructor(container) {
        this.container = container;
        this.draggedElement = null;
        this.placeholder = null;
        this.initialize();
    }

    initialize() {
        // Add event listeners to the container
        this.container.addEventListener('dragstart', this.handleDragStart.bind(this));
        this.container.addEventListener('dragend', this.handleDragEnd.bind(this));
        this.container.addEventListener('dragover', this.handleDragOver.bind(this));
        this.container.addEventListener('drop', this.handleDrop.bind(this));

        // Make all fence blocks draggable
        this.initializeDraggableBlocks();
    }

    initializeDraggableBlocks() {
        const blocks = this.container.querySelectorAll('.fence-block');
        blocks.forEach(block => {
            this.makeDraggable(block);
        });
    }

    makeDraggable(block) {
        // Set draggable attribute
        block.draggable = true;

        // Add drag handle if it doesn't exist
        if (!block.querySelector('.drag-handle')) {
            const header = block.querySelector('.fence-header');
            if (header) {
                const dragHandle = document.createElement('div');
                dragHandle.className = 'drag-handle cursor-move px-2 text-gray-400 hover:text-gray-600';
                dragHandle.innerHTML = '<i class="fas fa-grip-vertical"></i>';
                header.insertBefore(dragHandle, header.firstChild);
            }
        }
    }

    handleDragStart(e) {
        const fenceBlock = e.target.closest('.fence-block');
        if (!fenceBlock) return;

        this.draggedElement = fenceBlock;
        
        // Create and style placeholder
        this.placeholder = document.createElement('div');
        this.placeholder.className = 'fence-placeholder border-2 border-dashed border-gray-300 rounded-lg my-4 bg-gray-50';
        this.placeholder.style.height = `${fenceBlock.offsetHeight}px`;

        // Add dragging class for visual feedback
        fenceBlock.classList.add('dragging');
        
        // Set drag image and transparency
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', ''); // Required for Firefox
        
        // Hide original element after a short delay
        setTimeout(() => {
            fenceBlock.style.opacity = '0.5';
        }, 0);
    }

    handleDragEnd(e) {
        if (!this.draggedElement) return;

        // Remove dragging styles
        this.draggedElement.classList.remove('dragging');
        this.draggedElement.style.opacity = '1';

        // Remove placeholder if it exists
        if (this.placeholder && this.placeholder.parentNode) {
            this.placeholder.parentNode.removeChild(this.placeholder);
        }

        this.draggedElement = null;
        this.placeholder = null;

        // Update positions and save order
        this.updatePositions();
    }

    handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';

        const fenceBlock = e.target.closest('.fence-block');
        if (!fenceBlock || fenceBlock === this.draggedElement) return;

        // Get the placeholder position
        const rect = fenceBlock.getBoundingClientRect();
        const midpoint = rect.top + rect.height / 2;
        const insertBefore = e.clientY < midpoint;

        // Move placeholder
        if (this.placeholder) {
            if (insertBefore) {
                fenceBlock.parentNode.insertBefore(this.placeholder, fenceBlock);
            } else {
                fenceBlock.parentNode.insertBefore(this.placeholder, fenceBlock.nextSibling);
            }
        }
    }

    handleDrop(e) {
        e.preventDefault();
        if (!this.draggedElement || !this.placeholder) return;

        // Insert the dragged element where the placeholder is
        this.placeholder.parentNode.insertBefore(this.draggedElement, this.placeholder);

        // Clean up
        this.handleDragEnd(e);

        // Show success message
        showSuccess('Fence block order updated');
    }

    updatePositions() {
        const blocks = this.container.querySelectorAll('.fence-block');
        blocks.forEach((block, index) => {
            block.dataset.position = index;
            const positionDisplay = block.querySelector('.fence-position');
            if (positionDisplay) {
                positionDisplay.textContent = `#${index + 1}`;
            }
        });
    }

    // Call this when adding new blocks
    addDraggableBlock(block) {
        this.makeDraggable(block);
        this.updatePositions();
    }
}
