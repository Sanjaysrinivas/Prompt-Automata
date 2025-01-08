// Token status management
class TokenStatus {
    constructor() {
        this.tokenCounterCard = document.querySelector('[data-token-counter]');
        if (!this.tokenCounterCard) {
            console.warn('Token counter card not found');
            return;
        }

        this.totalTokensElement = this.tokenCounterCard.querySelector('[data-total-tokens]');
        this.modelBars = {};
        this.modelCounts = {};
        
        // Initialize model elements using data attributes
        const models = ['gemini', 'gpt', 'claude'];
        models.forEach(model => {
            this.modelBars[model] = this.tokenCounterCard.querySelector(`.model-bar[data-model="${model}"]`);
            this.modelCounts[model] = this.tokenCounterCard.querySelector(`.model-count[data-model="${model}"]`);
        });

        this.modelLimits = {
            'gemini': 200000,  // Gemini Pro limit
            'gpt': 128000,     // GPT-4 limit
            'claude': 200000   // Claude 3.5 Sonnet limit
        };

        this.totalTokens = 0;
        this.sessionId = null;
        this.setupEventListeners();
        
        // Initialize session on page load
        window.addEventListener('load', async () => {
            console.log('Page loaded - initializing token counter');
            await this.resetTokenStatus();
            await this.checkSessionAndTokens();
        });
        
        // Periodically check session but less frequently
        setInterval(() => this.checkSessionAndTokens(), 60000);
    }

    setupEventListeners() {
        // Listen for token updates from fence blocks
        document.addEventListener('fenceTokenUpdate', (event) => {
            console.log('Received fenceTokenUpdate event:', event.detail);
            const { fenceId, tokenCount, isNewBlock } = event.detail;
            if (!fenceId || typeof tokenCount !== 'number') {
                console.error('Invalid fence token update:', event.detail);
                return;
            }
            
            // Don't update for new blocks
            if (isNewBlock) {
                console.log('New block added, skipping UI update');
                return;
            }
            
            // Update block tokens in token counter
            this.updateBlockTokens(fenceId, tokenCount);
        });

        // Listen for global token updates
        document.addEventListener('globalTokenUpdate', (event) => {
            console.log('Received globalTokenUpdate event:', event.detail);
            const { totalTokens, blockTokens } = event.detail;
            
            if (!totalTokens && !blockTokens) {
                console.error('Invalid global token update:', event.detail);
                return;
            }
            
            // Update the UI with the provided total
            this.totalTokens = totalTokens;
            this.updateUI(totalTokens);
        });

        // Listen for fence removal
        document.addEventListener('fenceRemoved', async (event) => {
            console.log('Received fenceRemoved event:', event.detail);
            const { fenceId, isLastBlock } = event.detail;
            if (!fenceId) {
                console.error('Invalid fence removal event:', event.detail);
                return;
            }

            try {
                // First notify backend about block removal
                await fetch('/api/token-status/remove', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ blockId: fenceId })
                });

                // Then update local UI
                this.updateBlockTokens(fenceId, 0);
                const totalTokens = this.getTotalTokens();
                
                // Update UI with new total
                this.totalTokens = totalTokens;
                this.updateUI(totalTokens);
            } catch (error) {
                console.error('Failed to handle fence removal:', error);
            }
        });

        console.log('Token status event listeners initialized');
    }

    async updateBlockTokens(blockId, tokenCount) {
        try {
            const response = await fetch('/api/token-status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    block_id: blockId,
                    token_count: tokenCount
                })
            });

            if (!response.ok) {
                throw new Error('Failed to update token count');
            }

            const data = await response.json();
            this.totalTokens = data.total_tokens;
            return data.total_tokens;
        } catch (error) {
            console.error('Error updating block tokens:', error);
        }
    }

    async removeBlock(blockId) {
        try {
            const response = await fetch('/api/token-status/remove', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    block_id: blockId
                })
            });

            if (!response.ok) {
                throw new Error('Failed to remove block token count');
            }

            const data = await response.json();
            
            // Only reset if this was the last block
            const remainingBlocks = document.querySelectorAll('.fence-block');
            if (remainingBlocks.length === 0) {
                console.log('Last block removed - resetting counter');
                this.resetUI();
            } else {
                console.log('Block removed - updating total:', data.total_tokens);
                this.totalTokens = data.total_tokens;
                this.updateUI(data.total_tokens);
            }
        } catch (error) {
            console.error('Error removing block:', error);
        }
    }

    async checkSessionAndTokens() {
        try {
            const response = await fetch('/api/token-status');
            if (!response.ok) {
                throw new Error('Failed to fetch token status');
            }
            const data = await response.json();
            
            // Only update session ID if we don't have one
            if (!this.sessionId) {
                console.log('Initializing session ID');
                this.sessionId = data.session_id;
            }

            // Update with session data if we have tokens
            if (data.total_tokens !== undefined) {
                this.totalTokens = data.total_tokens;
                this.updateUI(data.total_tokens);
            }
        } catch (error) {
            console.error('Error checking session:', error);
        }
    }

    async resetTokenStatus() {
        try {
            const response = await fetch('/api/token-status/reset', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            if (!response.ok) {
                throw new Error('Failed to reset token status');
            }
            const data = await response.json();
            this.sessionId = data.session_id;
            this.totalTokens = 0;
            this.updateUI(0);
            console.log('Token status reset successfully');
        } catch (error) {
            console.error('Error resetting token status:', error);
        }
    }

    showError(message) {
        // Simple error notification
        console.warn('Token Status Error:', message);
        // You can implement a more sophisticated error notification system here
    }

    resetUI() {
        console.log('Resetting token counter UI');
        this.totalTokens = 0;
        
        // Reset all UI elements
        if (this.totalTokensElement) {
            this.totalTokensElement.textContent = '0';
        }

        // Clear all block-specific token displays
        document.querySelectorAll('[data-block-tokens]').forEach(element => {
            element.textContent = '0';
        });

        // Reset model bars and counts
        Object.keys(this.modelBars).forEach(model => {
            if (this.modelBars[model]) {
                this.modelBars[model].style.width = '0%';
                this.modelBars[model].classList.remove('near-limit', 'limit-exceeded');
            }
            if (this.modelCounts[model]) {
                const formattedLimit = (this.modelLimits[model] / 1000).toFixed(0) + 'K';
                this.modelCounts[model].textContent = `0 / ${formattedLimit} (0.0%)`;
                this.modelCounts[model].classList.remove('text-red-600');
            }
        });
        
        // Clear any stored token counts
        localStorage.removeItem('tokenCounts');
        
        // Notify about the reset
        const event = new CustomEvent('tokenCounterReset');
        document.dispatchEvent(event);
    }

    updateUI(totalTokens) {
        if (!this.tokenCounterCard) return;

        // Ensure totalTokens is a non-negative number
        totalTokens = Math.max(0, parseInt(totalTokens) || 0);
        this.totalTokens = totalTokens;
        
        if (this.totalTokensElement) {
            this.totalTokensElement.textContent = totalTokens.toLocaleString();
        }

        // Update each model's display
        Object.entries(this.modelLimits).forEach(([model, limit]) => {
            const validTokens = Math.min(totalTokens, limit); // Cap tokens at model limit
            const percentage = (validTokens / limit) * 100;
            const bar = this.modelBars[model];
            const count = this.modelCounts[model];

            if (bar) {
                bar.style.width = `${percentage}%`;
                // Add warning class when near or exceeding limit
                if (percentage >= 90) {
                    bar.classList.add('near-limit');
                    if (percentage >= 100) {
                        bar.classList.add('limit-exceeded');
                    }
                } else {
                    bar.classList.remove('near-limit', 'limit-exceeded');
                }
            }

            if (count) {
                const formattedLimit = (limit / 1000).toFixed(0) + 'K';
                const percentageDisplay = percentage.toFixed(1);
                const tokenDisplay = validTokens.toLocaleString();
                count.textContent = `${tokenDisplay} / ${formattedLimit} (${percentageDisplay}%)`;
                
                // Add warning class to count display when exceeding limit
                if (totalTokens > limit) {
                    count.classList.add('text-red-600');
                } else {
                    count.classList.remove('text-red-600');
                }
            }
        });
    }

    getTotalTokens() {
        return this.totalTokens;
    }
}

// Initialize token status when document is ready
document.addEventListener('DOMContentLoaded', () => {
    window.tokenStatus = new TokenStatus();
});

// Token dialog toggle function with error handling
window.toggleTokenDialog = function() {
    try {
        const dialog = document.getElementById('token-status-dialog');
        if (!dialog) {
            console.warn('Token status dialog element not found');
            return;
        }

        const isMinimized = dialog.classList.contains('minimized');
        if (isMinimized) {
            dialog.classList.remove('minimized');
        } else {
            dialog.classList.add('minimized');
        }
    } catch (error) {
        console.error('Error toggling token dialog:', error);
        // Attempt to recover by removing minimized class if present
        try {
            const dialog = document.getElementById('token-status-dialog');
            if (dialog && dialog.classList.contains('minimized')) {
                dialog.classList.remove('minimized');
            }
        } catch (e) {
            console.error('Failed to recover token dialog state:', e);
        }
    }
};
