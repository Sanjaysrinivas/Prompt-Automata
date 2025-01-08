// Token counting functionality
import { fenceAPI } from './fence-api.js';

export async function countTokens(text) {
    try {
        return await fenceAPI.countTokens(text);
    } catch (error) {
        console.error('Error counting tokens:', error);
        throw error;
    }
}

export function formatTokenCount(count) {
    return new Intl.NumberFormat().format(count);
}

// Debounce helper
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Token refresh functionality
export function initializeRefreshButtons() {
    console.log('Initializing refresh buttons...');
    
    // Initialize block level refresh buttons
    const initializeBlockButtons = () => {
        const blockButtons = document.querySelectorAll('.block-refresh-btn');
        console.log('Found block refresh buttons:', blockButtons.length);
        
        blockButtons.forEach(btn => {
            // Skip if already initialized
            if (btn.dataset.initialized) return;
            
            btn.dataset.initialized = 'true';
            btn.addEventListener('click', async (e) => {
                e.stopPropagation(); // Prevent token panel from opening
                const block = e.target.closest('.fence-block');
                if (block) {
                    const blockId = block.dataset.blockId || block.id;  
                    console.log('Refreshing block:', blockId);
                    if (!blockId) {
                        console.error('Block ID not found for block:', block);
                        return;
                    }
                    await refreshBlock(blockId);
                }
            });
        });
    };

    // Initialize global refresh button with debouncing
    const globalRefreshBtn = document.getElementById('global-refresh-btn');
    console.log('Found global refresh button:', globalRefreshBtn);
    
    if (globalRefreshBtn) {
        const debouncedRefresh = debounce(async () => {
            await refreshAll();
        }, 300); // 300ms debounce
        globalRefreshBtn.addEventListener('click', debouncedRefresh);
    }

    // Initial initialization
    initializeBlockButtons();

    // Set up mutation observer to handle dynamically added blocks
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.addedNodes.length) {
                // Check if any added nodes contain refresh buttons
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1 && (
                        node.classList?.contains('block-refresh-btn') ||
                        node.querySelector?.('.block-refresh-btn')
                    )) {
                        console.log('New block refresh button detected, initializing...');
                        initializeBlockButtons();
                    }
                });
            }
        });
    });

    // Start observing the document for added nodes
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
}

async function refreshBlock(blockId) {
    try {
        const block = document.querySelector(`.fence-block[data-block-id="${blockId}"]`);
        const btn = block?.querySelector('.block-refresh-btn');
        if (!block || !btn) {
            console.error('Block or refresh button not found:', blockId);
            return;
        }

        setLoading(btn, true);

        // Get the current content from the block
        const editor = block.querySelector('.CodeMirror')?.CodeMirror;
        const content = editor ? editor.getValue() : block.querySelector('textarea')?.value || '';

        // If content is empty, reset token counts to 0
        if (!content || content.trim() === '') {
            // Update block display
            const tokenCount = block.querySelector('.total-token-count');
            if (tokenCount) {
                tokenCount.textContent = '0';
            }
            
            // Dispatch event to reset global count for this block
            document.dispatchEvent(new CustomEvent('globalTokenUpdate', {
                detail: {
                    totalTokens: 0,
                    blockTokens: { [blockId]: 0 }
                }
            }));
            return;
        }

        // Get the actual content after reference processing
        const response = await fenceAPI.refreshBlock(blockId, { content });
        if (response && response.status === 'success') {
            // First update the global token counter
            document.dispatchEvent(new CustomEvent('globalTokenUpdate', {
                detail: {
                    totalTokens: response.total_tokens,
                    blockTokens: response.block_tokens
                }
            }));
            
            // Then update the block display
            const tokenCount = block.querySelector('.total-token-count');
            if (tokenCount && response.block_tokens[blockId] !== undefined) {
                tokenCount.textContent = formatTokenCount(response.block_tokens[blockId]);
            }
        } else {
            console.error('Invalid refresh response:', response);
        }
    } catch (error) {
        console.error('Block refresh failed:', error);
    } finally {
        const btn = document.querySelector(`.fence-block[data-block-id="${blockId}"] .block-refresh-btn`);
        if (btn) setLoading(btn, false);
    }
}

async function refreshAll() {
    const btn = document.getElementById('global-refresh-btn');
    if (!btn) {
        console.error('Global refresh button not found');
        return;
    }

    // Prevent concurrent refreshes with debouncing
    if (refreshTimeout) {
        clearTimeout(refreshTimeout);
    }

    refreshTimeout = setTimeout(async () => {
        if (isRefreshing) {
            console.log('Refresh already in progress, will retry in 500ms');
            setTimeout(refreshAll, 500);
            return;
        }

        try {
            isRefreshing = true;
            setLoading(btn, true);

            // Get all blocks and their content
            const blocks = Array.from(document.querySelectorAll('.fence-block'))
                .filter(block => block.id && block.id.startsWith('fence-'));

            if (blocks.length === 0) {
                console.log('No blocks found to refresh');
                return;
            }

            // Create blocks array and contents map
            const blockIds = blocks.map(block => block.id);
            const contents = {};
            
            // Extract content from each block
            for (const block of blocks) {
                const editor = block.querySelector('.CodeMirror')?.CodeMirror;
                const content = editor ? editor.getValue() : block.querySelector('textarea')?.value || '';
                
                // Store the content
                contents[block.id] = content;
            }

            console.log('Found blocks for refresh:', blockIds);

            const response = await fenceAPI.refreshAll({
                blocks: blockIds,
                contents: contents
            });
            
            if (response && response.status === 'success') {
                // Update block tokens from response
                const blockTokens = response.block_tokens || {};
                
                // Update each block's tokens and content
                Object.entries(blockTokens).forEach(([blockId, tokenCount]) => {
                    const block = document.querySelector(`.fence-block[data-block-id="${blockId}"]`);
                    if (block) {
                        updateBlockTokens(blockId, { token_count: tokenCount });
                        
                        // Update editor content if needed
                        const editor = block.querySelector('.CodeMirror')?.CodeMirror;
                        const content = response.contents?.[blockId];
                        if (content && editor) {
                            editor.setValue(content);
                        }
                    }
                });

                // Dispatch global token update event with response data
                document.dispatchEvent(new CustomEvent('globalTokenUpdate', {
                    detail: {
                        totalTokens: response.total_tokens,
                        blockTokens: blockTokens
                    }
                }));
            } else {
                console.error('Invalid refresh response:', response);
            }
        } catch (error) {
            console.error('Global refresh failed:', error);
        } finally {
            isRefreshing = false;
            setLoading(btn, false);
            refreshTimeout = null;
        }
    }, 100); // Debounce for 100ms
}

function updateBlockTokens(blockId, data) {
    const block = document.querySelector(`.fence-block[data-block-id="${blockId}"]`);
    if (!block) return;

    // Update token count display
    const tokenCount = block.querySelector('.total-token-count');
    if (tokenCount && data.token_count !== undefined) {
        tokenCount.textContent = formatTokenCount(data.token_count);
    }
}

function setLoading(btn, isLoading) {
    if (!btn) return;
    
    const icon = btn.querySelector('i');
    if (!icon) return;

    if (isLoading) {
        btn.disabled = true;
        icon.classList.add('fa-spin');
    } else {
        btn.disabled = false;
        icon.classList.remove('fa-spin');
    }
}

// Track ongoing refresh
let isRefreshing = false;
let refreshTimeout = null;

// Initialize refresh buttons when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeRefreshButtons);