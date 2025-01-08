// Token Counter UI Logic
import { fenceAPI } from './fence-api.js';

export class TokenCounter {
    constructor() {
        this.lastTokenCounts = null;
        this.initialized = false;
        this.blockTokens = new Map(); // Store token counts per block
        this.initialize();
    }

    initialize() {
        if (this.initialized) {
            return;
        }
        
        // Only reset if we don't have any existing counts
        if (!this.lastTokenCounts) {
            this.reset();
        }
        
        // Add page unload listener to preserve counts
        window.addEventListener('beforeunload', () => {
            try {
                sessionStorage.setItem('tokenCounts', JSON.stringify({
                    lastTokenCounts: this.lastTokenCounts,
                    blockTokens: Array.from(this.blockTokens.entries())
                }));
            } catch (e) {
                console.error('Failed to save token counts:', e);
            }
            this.initialized = false;
        });

        // Add page visibility change listener
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                try {
                    const stored = sessionStorage.getItem('tokenCounts');
                    if (stored) {
                        const { lastTokenCounts, blockTokens } = JSON.parse(stored);
                        this.lastTokenCounts = lastTokenCounts;
                        this.blockTokens = new Map(blockTokens);
                    }
                } catch (e) {
                    console.error('Failed to restore token counts:', e);
                    this.reset();
                }
                this.initialized = true;
            }
        });

        // Initialize on DOM content loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.initialized = true;
                this.initializeBlockListeners();
            });
        } else {
            this.initialized = true;
            this.initializeBlockListeners();
        }
    }

    reset() {
        this.lastTokenCounts = this.resetTokenCounts(0);
        this.blockTokens.clear();
        return this.lastTokenCounts;
    }

    resetTokenCounts(baseTokenCount = 0) {  
        return {
            base: baseTokenCount || 0,  
            references: 0,
            files: 0,
            total: baseTokenCount || 0,
            fileDetails: []
        };
    }

    initializeTokenCounts(baseTokenCount = 0) {  
        if (!this.lastTokenCounts) {
            this.lastTokenCounts = this.resetTokenCounts(baseTokenCount);
        } else {
            this.lastTokenCounts = {
                ...this.lastTokenCounts,
                base: baseTokenCount,
                total: (this.lastTokenCounts.references || 0) + 
                      (this.lastTokenCounts.files || 0) + 
                      baseTokenCount
            };
        }
        return this.lastTokenCounts;
    }

    updateBlockTokens(blockId, tokenCount) {
        this.blockTokens.set(blockId, tokenCount);
        return Array.from(this.blockTokens.values()).reduce((a, b) => a + b, 0);
    }

    getLastTokenCounts() {
        return this.lastTokenCounts || this.resetTokenCounts(0);  
    }

    getTotalTokens() {
        return Array.from(this.blockTokens.values()).reduce((a, b) => a + b, 0);
    }

    async updateTokenCount(block) {
        const content = block.querySelector('.fence-content');
        const countDisplay = block.querySelector('.token-count');
        if (!content || !countDisplay) return;

        try {
            const text = content.value;
            const references = this.extractReferences(text);
            
            // Get base token count
            const baseCount = await fenceAPI.countTokens(text);
            
            // Get reference token counts
            const referenceCounts = {};
            let totalReferenceTokens = 0;

            for (const ref of references) {
                const response = await fenceAPI.refreshBlock(block.dataset.blockId, { reference: ref });
                if (response.status === 'success') {
                    referenceCounts[ref] = response.token_count;
                    totalReferenceTokens += response.token_count;
                }
            }

            // Update block tokens
            const totalTokens = baseCount + totalReferenceTokens;
            this.updateBlockTokens(block.dataset.blockId, totalTokens);

            // Update UI
            this.updateTokenDisplay(block, {
                baseCount,
                totalReferenceTokens,
                totalTokens,
                referenceCounts
            });
        } catch (error) {
            console.error('Error updating token count:', error);
            countDisplay.textContent = 'Error counting tokens';
        }
    }

    extractReferences(text) {
        const referenceRegex = /@\[(api|var|file):[^\]]+\]/g;
        return text.match(referenceRegex) || [];
    }

    updateTokenDisplay(block, counts) {
        const container = block.querySelector('.token-count-container') || 
                         this.createTokenContainer(block);

        container.innerHTML = this.generateTokenHTML(counts);
    }

    createTokenContainer(block) {
        const container = document.createElement('div');
        container.className = 'token-count-container mt-2';
        const countDisplay = block.querySelector('.token-count');
        countDisplay.parentNode.insertBefore(container, countDisplay.nextSibling);
        return container;
    }

    generateTokenHTML({ baseCount, totalReferenceTokens, totalTokens, referenceCounts }) {
        let html = `
            <div class="token-info">
                <div class="content-count">${baseCount} content tokens</div>`;

        if (totalReferenceTokens > 0) {
            html += `<div class="reference-count">${totalReferenceTokens} reference tokens</div>`;
        }

        html += `<div class="total-count">${totalTokens} total tokens</div>`;

        if (Object.keys(referenceCounts).length > 0) {
            html += this.generateReferencesHTML(referenceCounts);
        }

        return html + '</div>';
    }

    generateReferencesHTML(referenceCounts) {
        const sortedRefs = Object.entries(referenceCounts)
            .sort(([a], [b]) => a.split(':')[0].localeCompare(b.split(':')[0]));

        return `
            <div class="references-list mt-1">
                <small class="text-muted">References (${sortedRefs.length}):</small>
                <ul class="list-unstyled mb-0 ps-3">
                    ${sortedRefs.map(([ref, count]) => {
                        const [type, value] = ref.replace('@[', '').split(':');
                        const displayType = this.getDisplayType(type);
                        return `
                            <li class="reference-item">
                                <small>
                                    <span class="reference-type text-gray-500">${displayType}:</span>
                                    <span class="reference-name text-primary">${value.replace(']', '')}</span>
                                    <span class="reference-tokens">(${count} tokens)</span>
                                </small>
                            </li>`;
                    }).join('')}
                </ul>
            </div>`;
    }

    getDisplayType(type) {
        const types = {
            'api': 'API',
            'var': 'Variable',
            'file': 'File'
        };
        return types[type] || type;
    }

    initializeBlockListeners() {
        document.querySelectorAll('.fence-block').forEach(block => {
            const content = block.querySelector('.fence-content');
            if (content) {
                content.addEventListener('input', () => this.updateTokenCount(block));
                this.updateTokenCount(block);
            }
        });
    }
}

// Create singleton instance
export const tokenCounter = new TokenCounter();