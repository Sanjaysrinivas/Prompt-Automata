// Token Counter UI Logic
document.addEventListener('DOMContentLoaded', function() {
    const referenceForm = document.getElementById('reference-form');
    const referenceList = document.getElementById('reference-list');
    const submitBtn = document.getElementById('submit-btn');
    const results = document.getElementById('results');
    const taskStatus = document.getElementById('task-status');
    const tokenCounts = document.getElementById('token-counts');

    let references = [];
    let currentTaskId = null;
    let statusCheckInterval = null;

    // Handle adding references
    referenceForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const type = document.getElementById('reference-type').value;
        const content = document.getElementById('reference-content').value;

        if (!content) return;

        references.push({ type, content });
        updateReferenceList();
        referenceForm.reset();
    });

    // Update reference list UI
    function updateReferenceList() {
        referenceList.innerHTML = references.map((ref, index) => `
            <div class="reference-item">
                <button class="remove-btn" onclick="removeReference(${index})">×</button>
                <div class="font-bold">${ref.type}</div>
                <div class="text-gray-600">${ref.content}</div>
            </div>
        `).join('');

        // Enable/disable submit button based on references
        submitBtn.disabled = references.length === 0;
        submitBtn.classList.toggle('opacity-50', references.length === 0);
    }

    // Remove reference
    window.removeReference = function(index) {
        references.splice(index, 1);
        updateReferenceList();
    };

    // Submit token counting task
    submitBtn.addEventListener('click', async function() {
        if (references.length === 0) return;

        const priority = document.getElementById('priority').value;
        
        try {
            submitBtn.disabled = true;
            const response = await fetch('/tokens/count', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    references,
                    priority
                })
            });

            const data = await response.json();
            currentTaskId = data.task_id;
            
            // Show results section and start status checking
            results.classList.remove('hidden');
            updateTaskStatus('PENDING');
            startStatusChecking();

        } catch (error) {
            console.error('Error submitting task:', error);
            alert('Error submitting task. Please try again.');
            submitBtn.disabled = false;
        }
    });

    // Start checking task status
    function startStatusChecking() {
        if (statusCheckInterval) {
            clearInterval(statusCheckInterval);
        }

        statusCheckInterval = setInterval(checkTaskStatus, 1000);
    }

    // Check task status
    async function checkTaskStatus() {
        if (!currentTaskId) return;

        try {
            const response = await fetch(`/tokens/status/${currentTaskId}`);
            const data = await response.json();

            updateTaskStatus(data.status);

            if (data.status === 'completed') {
                displayResults(data.result);
                clearInterval(statusCheckInterval);
                submitBtn.disabled = false;
            } else if (data.status === 'failed') {
                displayError(data.error);
                clearInterval(statusCheckInterval);
                submitBtn.disabled = false;
            }

        } catch (error) {
            console.error('Error checking task status:', error);
        }
    }

    // Update task status UI
    function updateTaskStatus(status) {
        const statusText = status.charAt(0).toUpperCase() + status.slice(1);
        taskStatus.innerHTML = `
            <div class="status-${status.toLowerCase()}">
                Status: ${statusText}
            </div>
        `;
    }

    // Display token count results
    function displayResults(results) {
        console.log('Received results:', results);  // Debug log
        const { content_tokens, reference_tokens, total_tokens, references } = results;
        console.log('Content Tokens:', content_tokens);  // Debug log
        console.log('Reference Tokens:', reference_tokens);  // Debug log
        console.log('Total Tokens:', total_tokens);  // Debug log
        console.log('References:', references);  // Debug log

        tokenCounts.innerHTML = `
            <div class="bg-green-50 p-3 rounded">
                <div class="font-bold">Content Tokens</div>
                <div>Tokens: ${content_tokens}</div>
            </div>
            <div class="bg-blue-50 p-3 rounded mt-2">
                <div class="font-bold">Reference Tokens</div>
                <div>Tokens: ${reference_tokens}</div>
            </div>
            <div class="bg-yellow-50 p-3 rounded mt-2">
                <div class="font-bold">Total Tokens</div>
                <div>Tokens: ${total_tokens}</div>
            </div>
            <div class="bg-gray-50 p-3 rounded mt-2">
                <div class="font-bold">References</div>
                <ul class="list-disc pl-5">
                    ${Object.entries(references).map(([ref, count]) => `
                        <li>${ref}: ${count} tokens</li>
                    `).join('')}
                </ul>
            </div>
        `;
    }

    // Display error message
    function displayError(error) {
        tokenCounts.innerHTML = `
            <div class="bg-red-50 p-3 rounded text-red-600">
                Error: ${error}
            </div>
        `;
    }

    // Function to update token count for a fence block
    async function updateTokenCount(fenceBlock) {
        console.log('Starting token count update for fence block:', fenceBlock);
        const content = fenceBlock.querySelector('.fence-content');
        const countDisplay = fenceBlock.querySelector('.token-count');
        const text = content.value;
        console.log('Content text:', text);

        try {
            // First get all references in the text
            const references = extractReferences(text);
            console.log('Extracted references:', references);

            // Get the base content token count
            console.log('Fetching base token count...');
            const baseResponse = await fetch('/api/tokens/count_text', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: text })
            });
            console.log('Base token count response:', baseResponse.status);
            const baseData = await baseResponse.json();
            console.log('Base token count data:', baseData);
            
            if (baseData.status !== 'success') {
                throw new Error(baseData.message || 'Failed to count base tokens');
            }

            // Get token counts for each reference
            const referenceCounts = {};
            let totalReferenceTokens = 0;

            for (const ref of references) {
                console.log('Processing reference:', ref);
                const response = await fetch('/api/tokens/reference-count', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ reference: ref })
                });
                console.log('Reference count response status:', response.status);
                const data = await response.json();
                console.log('Reference count response data:', data);
                
                if (data.status === 'success') {
                    referenceCounts[ref] = data.token_count;
                    totalReferenceTokens += data.token_count;
                    console.log('Updated token counts:', { 
                        reference: ref, 
                        count: data.token_count, 
                        total: totalReferenceTokens 
                    });
                } else {
                    console.error('Error counting tokens for reference:', ref, data.message);
                    referenceCounts[ref] = 0;
                }
            }

            console.log('Final counts:', {
                baseTokens: baseData.token_count,
                referenceTokens: totalReferenceTokens,
                total: baseData.token_count + totalReferenceTokens,
                referenceCounts
            });

            // Create or get the token count container
            let tokenCountContainer = fenceBlock.querySelector('.token-count-container');
            if (!tokenCountContainer) {
                tokenCountContainer = document.createElement('div');
                tokenCountContainer.className = 'token-count-container mt-2';
                countDisplay.parentNode.insertBefore(tokenCountContainer, countDisplay.nextSibling);
            }

            // Create token info HTML
            let html = `<div class="token-info">
                <div class="content-count">${baseData.token_count} content tokens</div>`;

            // Add reference tokens if any exist
            if (totalReferenceTokens > 0) {
                html += `<div class="reference-count">${totalReferenceTokens} reference tokens</div>`;
            }

            // Add total tokens
            const totalTokens = baseData.token_count + totalReferenceTokens;
            html += `<div class="total-count">${totalTokens} total tokens</div>`;

            // Add reference counts if any exist
            if (Object.keys(referenceCounts).length > 0) {
                html += `
                    <div class="references-list mt-1">
                        <small class="text-muted">References (${Object.keys(referenceCounts).length}):</small>
                        <ul class="list-unstyled mb-0 ps-3">`;
                
                // Sort references by type to group them together
                const sortedRefs = Object.entries(referenceCounts).sort(([a], [b]) => {
                    const typeA = a.split(':')[0].replace('@[', '');
                    const typeB = b.split(':')[0].replace('@[', '');
                    return typeA.localeCompare(typeB);
                });
                
                for (const [ref, count] of sortedRefs) {
                    // Extract reference type and value
                    const [fullType, value] = ref.split(':');
                    const type = fullType.replace('@[', '');
                    const displayType = type === 'api' ? 'API' : 
                                      type === 'var' ? 'Variable' : 
                                      type === 'file' ? 'File' : type;
                    const displayValue = value.replace(']', '');
                    
                    html += `
                        <li class="reference-item">
                            <small>
                                <span class="reference-type text-gray-500">${displayType}:</span>
                                <span class="reference-name text-primary">${displayValue}</span>
                                <span class="reference-tokens">(${count} tokens)</span>
                            </small>
                        </li>`;
                }
                
                html += `
                        </ul>
                    </div>`;
            }
            
            html += '</div>';
            tokenCountContainer.innerHTML = html;

        } catch (error) {
            console.error('Error:', error);
            countDisplay.textContent = 'Error counting tokens';
        }
    }

    // Add event listeners to all fence blocks
    document.querySelectorAll('.fence-block').forEach(block => {
        const content = block.querySelector('.fence-content');
        if (content) {
            content.addEventListener('input', () => updateTokenCount(block));
            // Initial count
            updateTokenCount(block);
        }
    });

    function extractReferences(text) {
        console.log('Extracting references from text:', text);
        const referenceRegex = /@\[(api|var|file):[^\]]+\]/g;
        const matches = text.match(referenceRegex) || [];
        console.log('Found references:', matches);
        return matches;
    }

    async function fetchReferenceTokenCount(reference) {
        console.log('Fetching token count for reference:', reference);  // Debug log
        try {
            const response = await fetch('/api/tokens/reference-count', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ reference: reference })
            });
            console.log('Response status:', response.status);  // Debug log
            const data = await response.json();
            console.log('Response data:', data);  // Debug log
            
            if (response.ok) {
                return { token_count: data.token_count };
            } else {
                console.error('Error response:', data.error);  // Debug log
                return { error: data.error || 'Failed to count tokens' };
            }
        } catch (error) {
            console.error('Network error:', error);  // Debug log
            return { error: 'Network error' };
        }
    }
});
