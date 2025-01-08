document.addEventListener('DOMContentLoaded', function() {
    const outputDiv = document.getElementById('output');
    const promptId = window.location.pathname.split('/').pop();
    
    console.debug('Generate page loaded for prompt ID:', promptId);

    // Function to start the generation process
    async function startGeneration() {
        try {
            console.debug('Starting generation process...');
            outputDiv.textContent = 'Initializing generation...';
            outputDiv.classList.add('generating');

            // First, get the prompt data
            console.debug('Fetching prompt data...');
            const promptResponse = await fetch(`/prompts/${promptId}`);
            if (!promptResponse.ok) {
                throw new Error('Failed to fetch prompt data');
            }
            
            const promptData = await promptResponse.json();
            console.debug('Prompt data received:', promptData);

            if (!promptData.provider || !promptData.model) {
                throw new Error('No provider or model specified for this prompt');
            }
            
            // Start the generation
            console.debug('Sending generation request...', {
                provider: promptData.provider,
                model: promptData.model
            });

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 seconds timeout
            
            try {
                const response = await fetch(`/prompts/generate/${promptId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        provider: promptData.provider,
                        model: promptData.model
                    }),
                    signal: controller.signal
                });

                if (!response.ok) {
                    const errorData = await response.text();
                    console.error('Generation request failed:', errorData);
                    throw new Error(errorData || 'Generation failed');
                }

                console.debug('Starting to read response stream...');
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                outputDiv.textContent = '';

                let buffer = '';
                while (true) {
                    const { value, done } = await reader.read();
                    if (done) {
                        console.debug('Stream complete');
                        break;
                    }
                    
                    buffer += decoder.decode(value, { stream: true });
                    console.debug('Received chunk:', buffer);
                    
                    // Update the display
                    outputDiv.textContent = buffer;
                    outputDiv.scrollTop = outputDiv.scrollHeight;
                }

                // Handle any remaining text in the buffer
                const remaining = decoder.decode();
                if (remaining) {
                    console.debug('Final chunk:', remaining);
                    outputDiv.textContent += remaining;
                    outputDiv.scrollTop = outputDiv.scrollHeight;
                }

            } catch (error) {
                console.error('Generation error:', error);
                outputDiv.textContent = `Error: ${error.message}`;
                outputDiv.classList.add('error');
            } finally {
                clearTimeout(timeoutId);
                console.debug('Generation process complete');
                outputDiv.classList.remove('generating');
            }
        } catch (error) {
            console.error('Generation error:', error);
            outputDiv.textContent = `Error: ${error.message}`;
            outputDiv.classList.add('error');
        } finally {
            console.debug('Generation process complete');
            outputDiv.classList.remove('generating');
        }
    }

    // Start generation immediately when the page loads
    startGeneration();
});
