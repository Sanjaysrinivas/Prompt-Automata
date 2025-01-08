// Core functionality for fence blocks
import { showSuccess, showError } from './fence-ui.js';
import { countTokens, formatTokenCount } from './fence-tokens.js';
import { showReferencePicker } from './fence-references.js';
import { setupLibraryIntegration } from './fence-library.js';
import { tokenCounter } from './token-counter.js';
import { fenceAPI } from './fence-api.js';

// Model token capacity limits
const MODEL_CAPACITIES = {
    'claude': {
        name: 'Claude 3.5 Sonnet',
        capacity: 200000,
        color: '#7C3AED'
    },
    'gpt4': {
        name: 'GPT-01 Preview',
        capacity: 128000,
        color: '#10B981'
    },
    'gemini': {
        name: 'Gemini Pro',
        capacity: 32000,
        color: '#3B82F6'
    }
};

// Token count display states
const TOKEN_COUNT_STATES = {
    LOADING: '...',
    DEFAULT: '0',
    ERROR: 'Error'
};

// Default editor options
const EDITOR_OPTIONS = {
    lineNumbers: true,
    lineWrapping: true,
    mode: 'markdown',
    viewportMargin: Infinity,
    autoCloseBrackets: true,
    matchBrackets: true,
    theme: 'default',
    configureMouse: () => ({
        addEventListeners: (node, handlers) => {
            if (handlers.mousedown) node.addEventListener('mousedown', handlers.mousedown);
            if (handlers.touchstart) node.addEventListener('touchstart', handlers.touchstart, { passive: true });
            if (handlers.touchmove) node.addEventListener('touchmove', handlers.touchmove, { passive: true });
            if (handlers.mousewheel) node.addEventListener('mousewheel', handlers.mousewheel, { passive: true });
        }
    })
};

export class FenceBlock {
    constructor(element, options = {}) {
        this.element = element;
        this.editor = null;
        this.fileContents = new Map(); // Store file contents
        this.tokenCounts = new Map(); // Store token counts
        this.options = {
            ...EDITOR_OPTIONS,
            ...options
        };
        this.lastTokenCounts = {
            base: 0,
            references: 0,
            files: 0,
            total: 0,
            fileDetails: []
        };
        this.initialize();
    }

    initialize() {
        try {
            // Wait for CodeMirror to be available
            if (typeof CodeMirror === 'undefined') {
                throw new Error('CodeMirror is not loaded. Please check script includes.');
            }

            const codeElement = this.element.querySelector('.fence-content-editor');
            if (!codeElement) {
                throw new Error('Code editor element not found in the fence block. Make sure the textarea has class "fence-content-editor".');
            }

            // Initialize CodeMirror
            this.editor = CodeMirror.fromTextArea(codeElement, this.options);

            // Set up reference completion detection
            let referenceTimeout = null;
            const referenceRegex = /@\[github:issue:([^\]]+)\]/;

            this.editor.on('change', async (cm, change) => {
                // Clear any pending reference check
                if (referenceTimeout) {
                    clearTimeout(referenceTimeout);
                }

                // Schedule a new reference check
                referenceTimeout = setTimeout(async () => {
                    const cursor = cm.getCursor();
                    const line = cm.getLine(cursor.line);

                    // Find any reference at or before cursor
                    const beforeCursor = line.substring(0, cursor.ch);
                    const match = beforeCursor.match(referenceRegex);

                    if (match) {
                        const [fullMatch, refValue] = match;
                        const endIndex = beforeCursor.indexOf(fullMatch) + fullMatch.length;

                        // Only proceed if cursor is right after the reference
                        if (cursor.ch === endIndex) {
                            try {
                                // Try to count tokens, which will validate and fetch the content
                                await this._countReferenceTokens('github:issue', refValue);

                                // If successful, add a small visual indicator
                                const pos = {
                                    line: cursor.line,
                                    ch: endIndex
                                };
                                const marker = document.createElement('span');
                                marker.className = 'reference-valid';
                                marker.textContent = '✓';
                                cm.setBookmark(pos, { widget: marker });

                                // Update token count
                                await this.updateTokenCount();
                            } catch (error) {
                                console.warn('Invalid reference:', error);
                            }
                        }
                    }
                }, 500); // Wait for 500ms of no typing
            });

            // Set initial size
            this.editor.setSize('100%', '200px');

            // Style the action icons
            this.styleActionIcons();

            // Create model capacity bars
            this.createModelBars();

            // Initialize token counting
            this.initializeTokenDisplay();

            // Setup event listeners
            this.setupEventListeners();

            // Setup library integration
            setupLibraryIntegration(this);

            // Ensure library checkbox is visible and properly styled
            const libraryCheckbox = this.element.querySelector('.save-to-library');
            if (libraryCheckbox) {
                libraryCheckbox.style.display = 'flex';
            }

            // Initial token count
            this.updateTokenCount();

        } catch (error) {
            console.error('Error initializing fence block:', error);
            showError('Failed to initialize fence block: ' + error.message);
            throw error;
        }
    }

    styleActionIcons() {
        // Add styles to head if not already present
        if (!document.getElementById('fence-icon-styles')) {
            const styles = document.createElement('style');
            styles.id = 'fence-icon-styles';
            styles.textContent = `
                .fence-action-icon {
                    transition: all 0.2s ease-in-out;
                    cursor: pointer;
                    padding: 4px;
                    border-radius: 4px;
                }
                .fence-action-icon:hover {
                    background-color: rgba(0, 0, 0, 0.05);
                }
                .save-to-library-icon {
                    color: #4F46E5;
                }
                .save-to-library-icon:hover {
                    color: #4338CA;
                }
                .link-icon {
                    color: #2563EB;
                }
                .link-icon:hover {
                    color: #1D4ED8;
                }
                .download-icon {
                    color: #059669;
                }
                .download-icon:hover {
                    color: #047857;
                }
                .delete-icon {
                    color: #DC2626;
                }
                .delete-icon:hover {
                    color: #B91C1C;
                }
                .token-display {
                    display: inline-flex;
                    align-items: center;
                    gap: 4px;
                    color: #6366F1;
                    transition: all 0.2s ease-in-out;
                    padding: 4px 8px;
                    border-radius: 6px;
                    cursor: pointer;
                }
                .token-display:hover {
                    background-color: rgba(99, 102, 241, 0.1);
                }
                .token-display svg {
                    color: #6366F1;
                }
                .token-display .token-count {
                    font-weight: 500;
                }
                .token-display:hover svg,
                .token-display:hover .token-count {
                    color: #4F46E5;
                }
            `;
            document.head.appendChild(styles);
        }

        // Add classes to icons
        const icons = {
            'save-to-library': '.save-to-library-icon',
            'copy-link': '.link-icon',
            'download': '.download-icon',
            'delete-fence': '.delete-icon'
        };

        Object.entries(icons).forEach(([action, className]) => {
            const icon = this.element.querySelector(`.${action}`);
            if (icon) {
                icon.classList.add('fence-action-icon');
                icon.classList.add(className.substring(1)); // Remove the dot from className
            }
        });

        // Style token display
        const tokenDisplay = this.element.querySelector('.token-display');
        if (tokenDisplay) {
            const tokenCount = tokenDisplay.querySelector('.token-count');
            if (tokenCount) {
                tokenCount.classList.add('token-count');
            }
        }
    }

    createModelBars() {
        const tokenPanel = this.element.querySelector('.token-panel');
        if (!tokenPanel) return;

        // Create container for model capacity bars
        const barsContainer = document.createElement('div');
        barsContainer.className = 'model-capacity-bars mt-4 space-y-4';

        const models = {
            'Claude 3.5 Sonnet': { color: '#7C3AED', capacity: 200000 },
            'GPT-01 Preview': { color: '#10B981', capacity: 128000 },
            'Gemini Pro': { color: '#3B82F6', capacity: 32000 }
        };

        Object.entries(models).forEach(([model, config]) => {
            const barHtml = `
                <div class="model-capacity-item">
                    <div class="flex justify-between items-center mb-1">
                        <span class="text-sm text-gray-600">${model}</span>
                        <div class="flex items-center space-x-2">
                            <span class="text-sm text-gray-500">0 / ${config.capacity.toLocaleString()}</span>
                            <span class="text-sm text-gray-400 model-percentage">(0%)</span>
                        </div>
                    </div>
                    <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div class="model-capacity-bar h-full transition-all duration-300" 
                             data-model="${model}"
                             style="width: 0%; background-color: ${config.color}">
                        </div>
                    </div>
                </div>
            `;
            barsContainer.insertAdjacentHTML('beforeend', barHtml);
        });

        // Find the model capacity bars section
        const modelSection = tokenPanel.querySelector('.space-y-3');
        if (modelSection) {
            // Clear any existing bars
            const existingBars = modelSection.querySelector('.model-capacity-bars');
            if (existingBars) {
                existingBars.innerHTML = '';
                existingBars.appendChild(barsContainer);
            } else {
                modelSection.appendChild(barsContainer);
            }
        }
    }

    initializeTokenDisplay() {
        const tokenDisplay = this.element.querySelector('.token-display');
        const tokenPanel = this.element.querySelector('.token-panel');

        if (tokenDisplay && tokenPanel) {
            tokenDisplay.addEventListener('click', () => {
                // Toggle popup visibility
                const isVisible = tokenPanel.style.display !== 'none';
                tokenPanel.style.display = isVisible ? 'none' : 'block';

                // Only update capacity bars if showing popup
                if (!isVisible) {
                    // Use the last known token counts
                    this.updateModelCapacityBars(this.lastTokenCounts);
                }
            });
        }
    }

    getCurrentCount(selector) {
        const element = this.element.querySelector(selector);
        return element ? parseInt(element.textContent) || 0 : 0;
    }

    setupEventListeners() {
        // Format change handler
        const formatSelect = this.element.querySelector('.fence-format');
        if (formatSelect) {
            formatSelect.addEventListener('change', () => this.updateTokenCount());
        }

        // Name change handler
        const nameInput = this.element.querySelector('.fence-name');
        if (nameInput) {
            nameInput.addEventListener('input', () => this.updateTokenCount());
        }

        // Editor change handler with debouncing
        if (this.editor) {
            let debounceTimer;
            this.editor.on('change', () => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => this.updateTokenCount(), 500);
            });
        }

        // Token display panel handlers
        const tokenSummary = this.element.querySelector('.token-count-summary');
        const tokenPanel = this.element.querySelector('.token-panel');
        const closePanel = this.element.querySelector('.close-panel');

        if (tokenSummary && tokenPanel) {
            tokenSummary.addEventListener('click', () => {
                tokenPanel.classList.toggle('hidden');
                this.updateModelCapacityBars();
            });
        }

        if (closePanel) {
            closePanel.addEventListener('click', (e) => {
                e.stopPropagation();
                tokenPanel.classList.add('hidden');
            });
        }

        // Close panel when clicking outside
        document.addEventListener('click', (e) => {
            if (tokenPanel && !tokenPanel.contains(e.target) && !tokenSummary.contains(e.target)) {
                tokenPanel.classList.add('hidden');
            }
        });

        // Delete button handler
        const deleteBtn = this.element.querySelector('.delete-fence');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => this.destroy());
        }

        // Reference button handler
        const referenceBtn = this.element.querySelector('.insert-reference-btn');
        if (referenceBtn && this.editor) {
            referenceBtn.addEventListener('click', () => {
                console.log('Reference button clicked');
                showReferencePicker(this.editor);
            });
        }
    }

    updateModelCapacityBars(counts = null) {
        // If no counts provided, use last known counts
        if (!counts) {
            counts = this.lastTokenCounts;
        }

        // Validate counts object and ensure we have a total
        if (!counts) {
            console.warn('No token counts available');
            return;
        }

        // Calculate total if not provided
        const totalTokens = counts.total || (counts.base || 0) + (counts.references || 0) + (counts.files || 0);
        if (typeof totalTokens !== 'number') {
            console.warn('Invalid total token count:', totalTokens);
            return;
        }

        const tokenPanel = this.element.querySelector('.token-panel');
        if (!tokenPanel) return;

        const modelBars = tokenPanel.querySelectorAll('.model-capacity-bar');
        if (!modelBars.length) return;

        const models = {
            'Claude 3.5 Sonnet': { capacity: 200000, color: '#7C3AED' },
            'GPT-01 Preview': { capacity: 128000, color: '#10B981' },
            'Gemini Pro': { capacity: 32000, color: '#3B82F6' }
        };

        modelBars.forEach(bar => {
            const model = bar.dataset.model;
            const config = models[model];
            if (config) {
                const percentage = (totalTokens / config.capacity) * 100;
                bar.style.width = `${Math.min(percentage, 100)}%`;

                // Update the count and percentage displays
                const item = bar.closest('.model-capacity-item');
                if (item) {
                    const countDisplay = item.querySelector('.text-gray-500');
                    const percentageDisplay = item.querySelector('.model-percentage');
                    if (countDisplay) {
                        countDisplay.innerHTML = `<span style="color: ${config.color}; font-weight: 500">${totalTokens.toLocaleString()} / ${config.capacity.toLocaleString()}</span>`;
                    }
                    if (percentageDisplay) {
                        percentageDisplay.innerHTML = `<span style="color: ${config.color}">(${percentage.toFixed(1)}%)</span>`;
                    }
                }

                console.log(`Model ${model}: ${totalTokens} / ${config.capacity} = ${percentage}%`);
            }
        });
    }

    async updateTokens() {
        try {
            const counts = await this.updateTokenCount();
            if (counts && typeof counts.total === 'number') {
                // Store the latest counts
                this.lastTokenCounts = counts;

                // Update token displays
                const elements = this.getTokenElements();
                if (elements.content) elements.content.textContent = formatTokenCount(counts.base);
                if (elements.references) elements.references.textContent = formatTokenCount(counts.references);
                if (elements.files) elements.files.textContent = formatTokenCount(counts.files);
                if (elements.total) {
                    elements.total.forEach(el => el.textContent = formatTokenCount(counts.total));
                }

                // Update model capacity bars if token panel is visible
                const tokenPanel = this.element.querySelector('.token-panel');
                if (tokenPanel && tokenPanel.style.display !== 'none') {
                    this.updateModelCapacityBars(counts);
                }
            }
        } catch (error) {
            console.error('Error updating tokens:', error);
        }
    }

    getTokenElements() {
        return {
            content: this.element.querySelector('.fence-token-count'),
            references: this.element.querySelector('.reference-token-count'),
            files: this.element.querySelector('.file-token-count'),
            total: this.element.querySelectorAll('.total-token-count'),
            fileList: this.element.querySelector('.file-token-list')
        };
    }

    async updateTokenCount() {
        const content = this.getValue();
        const elements = this.getTokenElements();

        try {
            // Reset counts if content is empty
            if (!content || content.trim() === '') {
                // Update all token displays to 0
                if (elements.content) elements.content.textContent = '0';
                if (elements.references) elements.references.textContent = '0';
                if (elements.files) elements.files.textContent = '0';
                if (elements.total) {
                    elements.total.forEach(el => el.textContent = '0');
                }
                if (elements.fileList) {
                    elements.fileList.style.display = 'none';
                }

                // Reset last token counts
                this.lastTokenCounts = {
                    base: 0,
                    references: 0,
                    files: 0,
                    total: 0,
                    fileDetails: []
                };

                // Update model capacity bars with reset counts
                this.updateModelCapacityBars(this.lastTokenCounts);

                // Emit token update event with 0 count
                const event = new CustomEvent('fenceTokenUpdate', {
                    detail: {
                        fenceId: this.element.id,
                        tokenCount: 0
                    }
                });
                document.dispatchEvent(event);

                return this.lastTokenCounts;
            }

            // Count base content tokens
            const baseTokenCount = await countTokens(content);

            // Count reference tokens
            let totalReferenceTokens = 0;
            const referencePattern = /@\[(api|var|ref|github:issue):([^[\]]+)\]/g;
            const referenceMatches = [...content.matchAll(referencePattern)];

            // Reset token counts
            this.lastTokenCounts = tokenCounter.initializeTokenCounts(baseTokenCount);

            // Process each reference
            for (const match of referenceMatches) {
                const refType = match[1];
                const refValue = match[2];

                try {
                    // Count tokens for this reference
                    const tokenCount = await this._countReferenceTokens(refType, refValue);
                    console.log(`Reference ${refType}:${refValue} token count:`, tokenCount);
                    
                    // Add to total reference tokens
                    totalReferenceTokens += tokenCount;
                } catch (error) {
                    console.error(`Error counting tokens for reference ${refType}:${refValue}:`, error);
                }
            }

            // Get file references from content
            const filePattern = /@\[file:(.*?)\]/g;
            let fileMatches = [...content.matchAll(filePattern)];
            let totalFileTokens = 0;
            let fileDetails = [];

            // Calculate file tokens
            for (const match of fileMatches) {
                const filePath = match[1].trim();
                const fileData = this.fileContents.get(filePath);

                if (fileData && typeof fileData.tokenCount === 'number') {
                    totalFileTokens += fileData.tokenCount;
                    fileDetails.push({
                        path: filePath,
                        count: fileData.tokenCount
                    });
                    console.log(`Adding file tokens for ${filePath}:`, fileData.tokenCount);
                } else {
                    console.log(`No token count found for file: ${filePath}`);
                }
            }

            // Update file list display
            if (elements.fileList) {
                if (fileDetails.length > 0) {
                    const listHtml = fileDetails.map(file => `
                        <div class="flex justify-between items-center py-1">
                            <span class="text-sm text-gray-600 truncate">${file.path}</span>
                            <span class="text-sm font-medium text-gray-900">${formatTokenCount(file.count)} tokens</span>
                        </div>
                    `).join('');
                    elements.fileList.innerHTML = listHtml;
                    elements.fileList.style.display = 'block';
                } else {
                    elements.fileList.style.display = 'none';
                }
            }

            // Calculate total and update displays
            const totalTokens = baseTokenCount + totalReferenceTokens + totalFileTokens;

            // Update all token displays
            if (elements.content) elements.content.textContent = formatTokenCount(baseTokenCount);
            if (elements.references) elements.references.textContent = formatTokenCount(totalReferenceTokens);
            if (elements.files) elements.files.textContent = formatTokenCount(totalFileTokens);
            if (elements.total) {
                elements.total.forEach(el => el.textContent = formatTokenCount(totalTokens));
            }

            // Update last token counts
            this.lastTokenCounts = {
                base: baseTokenCount,
                references: totalReferenceTokens,
                files: totalFileTokens,
                total: totalTokens,
                fileDetails: fileDetails
            };

            // Update model capacity bars
            this.updateModelCapacityBars(this.lastTokenCounts);

            // Emit token update event with total count
            const event = new CustomEvent('fenceTokenUpdate', {
                detail: {
                    fenceId: this.element.id,
                    tokenCount: totalTokens
                }
            });
            document.dispatchEvent(event);

            // Update token status for the entire fence block
            try {
                const response = await fetch('/api/token-status', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        block_id: this.element.id,
                        token_count: totalTokens
                    })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    console.error('Failed to update token status:', error);
                    throw new Error(error.error?.message || 'Failed to update token status');
                }

                // Update the global token counter with the response
                const data = await response.json();
                document.dispatchEvent(new CustomEvent('globalTokenUpdate', {
                    detail: {
                        totalTokens: data.total_tokens,
                        blockTokens: data.block_tokens
                    }
                }));
            } catch (error) {
                console.error('Error updating token status:', error);
            }

            return this.lastTokenCounts;

        } catch (error) {
            console.error('Error updating token count:', error);
            throw error;
        }
    }

    getValue() {
        return this.editor ? this.editor.getValue() : '';
    }

    setValue(content) {
        if (this.editor) {
            this.editor.setValue(content);
            this.updateTokenCount();
        }
    }

    getName() {
        const nameInput = this.element.querySelector('.fence-name');
        return nameInput ? nameInput.value : '';
    }

    getFormat() {
        const formatSelect = this.element.querySelector('.fence-format');
        return formatSelect ? formatSelect.value : 'markdown';
    }

    destroy() {
        try {
            // Remove the block from DOM
            this.element.remove();

            // Check if this was the last fence block
            const remainingBlocks = document.querySelectorAll('.fence-block');
            const isLastBlock = remainingBlocks.length === 0;

            // Emit a special event for block removal
            const event = new CustomEvent('fenceRemoved', {
                detail: {
                    fenceId: this.element.id,
                    isLastBlock: isLastBlock
                }
            });
            document.dispatchEvent(event);

            // Clean up CodeMirror instance
            if (this.editor) {
                this.editor.toTextArea();
            }
        } catch (error) {
            console.error('Error destroying fence block:', error);
        }
    }

    /**
     * Count tokens for a specific reference type
     * @private
     * @param {string} refType - Type of reference (github, file, etc)
     * @param {string} refValue - Value of the reference
     * @returns {Promise<number>} Token count
     */
    async _countReferenceTokens(refType, refValue) {
        switch (refType) {
            case 'var': {
                try {
                    // Get admin token from session
                    const tokenResponse = await fetch('/admin/token');
                    if (!tokenResponse.ok) {
                        throw new Error('Failed to get admin token');
                    }
                    const { token } = await tokenResponse.json();

                    const response = await fetch('/api/tokens/reference-count', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Admin-Token': token
                        },
                        body: JSON.stringify({
                            reference: `@[var:${refValue}]`
                        })
                    });
                    if (!response.ok) {
                        throw new Error('Failed to count variable tokens');
                    }
                    const data = await response.json();
                    return data.token_count;
                } catch (error) {
                    console.error('Error counting variable tokens:', error);
                    return 0;
                }
            }
            case 'github:issue': {
                try {
                    let owner, repo, number;
                    const fullFormatMatch = refValue.match(/^([^/]+)\/([^/]+)#(\d+)$/);
                    const simpleFormatMatch = refValue.match(/^(\d+)$/);

                    // Get default repo from dialog
                    const dialog = document.getElementById('reference-dialog');
                    const defaultRepo = dialog && dialog.dataset.defaultRepo ? 
                        JSON.parse(dialog.dataset.defaultRepo) : null;
                    
                    if (fullFormatMatch) {
                        [, owner, repo, number] = fullFormatMatch;
                    } else if (simpleFormatMatch && defaultRepo) {
                        owner = defaultRepo.owner;
                        repo = defaultRepo.repo;
                        number = simpleFormatMatch[1];
                    } else {
                        throw new Error('Invalid GitHub issue reference format');
                    }

                    // Get admin token from session
                    const tokenResponse = await fetch('/admin/token');
                    if (!tokenResponse.ok) {
                        throw new Error('Failed to get admin token');
                    }
                    const { token } = await tokenResponse.json();

                    const response = await fetch(`/api/github/issues/${owner}/${repo}/${number}/content`, {
                        headers: {
                            'X-Admin-Token': token
                        }
                    });
                    if (!response.ok) {
                        throw new Error('Failed to fetch issue content');
                    }
                    const data = await response.json();
                    return data.token_count; // Use token count from API response
                } catch (error) {
                    console.error('Error fetching issue content:', error);
                    return 0;
                }
            }
            // Add other reference types here as needed
            default:
                console.warn(`Unknown reference type: ${refType}`);
                return 0;
        }
    }
}