// Reference dialog functionality
import { fenceAPI } from './fence-api.js';

let currentEditor = null;
let currentDialog = null;

/**
 * Show the reference picker dialog
 * @param {CodeMirror.Editor} editor - The CodeMirror editor instance
 */
export function showReferencePicker(editor) {
    currentEditor = editor;
    
    // Get or create dialog
    currentDialog = document.getElementById('reference-dialog');
    if (!currentDialog) {
        console.error('Reference dialog not found in the DOM');
        return;
    }

    // Show dialog
    currentDialog.classList.remove('hidden');

    // Setup event listeners
    setupDialogListeners();
    
    // Initialize type dropdown
    const typeSelect = document.getElementById('reference-type');
    if (typeSelect) {
        // Clear previous selection
        typeSelect.value = '';
        
        // Hide all input containers
        hideAllInputContainers();
        
        // Update insert button state
        updateInsertButtonState();
    }
}

/**
 * Hide all input containers
 */
function hideAllInputContainers() {
    const containers = [
        'variable-input',
        'file-path-input',
        'github-title-input',
        'github-issues-container'
    ];
    
    containers.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.classList.add('hidden');
        }
    });

    // Clear and hide the selected file display
    const selectedFileDisplay = document.getElementById('selectedFileDisplay');
    const selectedFileName = document.getElementById('selectedFileName');
    if (selectedFileDisplay && selectedFileName) {
        selectedFileDisplay.classList.add('hidden');
        selectedFileName.textContent = '';
    }
}

/**
 * Handle type change event
 */
function onTypeChange(event) {
    console.log('Type change event triggered:', event.target.value);
    const type = event.target.value;
    
    // Hide all input containers first
    hideAllInputContainers();
    console.log('All input containers hidden');

    // Show the appropriate container based on type
    switch (type) {
        case 'file':
            document.getElementById('file-path-input')?.classList.remove('hidden');
            break;
        case 'github':
            document.getElementById('github-title-input')?.classList.remove('hidden');
            break;
        case 'var':
            console.log('Variable type selected, showing variable input');
            const container = document.getElementById('variable-input');
            if (container) {
                console.log('Variable input container found, removing hidden class');
                container.classList.remove('hidden');
                console.log('Loading variables...');
                loadVariables();
            } else {
                console.error('Variable input container not found in DOM');
            }
            break;
        case 'api':
            break;
        default:
            console.error('Invalid reference type');
            break;
    }
    
    // Update insert button state
    updateInsertButtonState();
}

/**
 * Load variables into the variable select dropdown
 */
async function loadVariables() {
    console.log('=== Starting loadVariables ===');
    const select = document.getElementById('variable-select');
    if (!select) {
        console.error('Variable select element not found');
        return;
    }
    console.log('Found variable select element:', select);

    // Try to get admin token from meta tag first, then from dialog data attribute
    const adminToken = document.querySelector('meta[name="admin-token"]')?.content || 
                      document.getElementById('reference-dialog')?.dataset.adminToken;
    console.log('Admin token found:', adminToken ? 'Yes (length=' + adminToken.length + ')' : 'No');
    
    if (!adminToken) {
        console.error('Admin token not found in meta tag or dialog data attribute');
        return;
    }

    try {
        console.log('Fetching variables from server...');
        console.log('Request URL:', '/admin/variables');
        console.log('Request headers:', { 'X-Admin-Token': adminToken });
        
        const response = await fetch('/admin/variables', {
            headers: {
                'X-Admin-Token': adminToken
            }
        });
        
        console.log('Server response status:', response.status);
        console.log('Server response headers:', Object.fromEntries([...response.headers]));
        
        if (!response.ok) {
            throw new Error(`Failed to load variables: ${response.status}`);
        }
        
        const variables = await response.json();
        console.log('Variables received:', JSON.stringify(variables, null, 2));
        
        // Clear existing options except the first one
        console.log('Clearing existing options...');
        console.log('Current options:', select.options.length);
        while (select.options.length > 1) {
            select.remove(1);
        }
        
        // Add variables to the dropdown
        console.log('Adding variables to dropdown...');
        variables.forEach(variable => {
            console.log('Processing variable:', JSON.stringify(variable, null, 2));
            const option = document.createElement('option');
            option.value = variable.name;
            option.textContent = variable.name;
            option.dataset.value = variable.value;
            console.log('Created option:', option.outerHTML);
            select.appendChild(option);
        });

        // Add change event listener if not already added
        console.log('Setting up variable select event listener');
        select.removeEventListener('change', onVariableSelect);
        select.addEventListener('change', onVariableSelect);
        console.log('Variable loading complete');
    } catch (error) {
        console.error('Error loading variables:', error);
        console.error('Error stack:', error.stack);
        showError('Failed to load variables');
    }
}

/**
 * Handle variable selection change
 */
async function onVariableSelect(event) {
    const selectedValue = event.target.value;
    if (!selectedValue) return;

    const tokenCountEl = document.getElementById('variable-token-count');
    if (tokenCountEl) {
        tokenCountEl.classList.add('hidden');
    }

    try {
        // Fetch token count for the variable reference
        const response = await fetch('/api/tokens/reference-count', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                reference: `@[var:${selectedValue}]`
            })
        });

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Failed to fetch variable token count');
        }
        
        // Update token count display
        if (tokenCountEl) {
            tokenCountEl.textContent = `${data.token_count} tokens`;
            tokenCountEl.classList.remove('hidden', 'error');
        }

        // Enable insert button if we have a valid selection
        updateInsertButtonState(true);

    } catch (error) {
        console.error('Error fetching variable token count:', error);
        if (tokenCountEl) {
            tokenCountEl.textContent = error.message || 'Error fetching token count';
            tokenCountEl.classList.remove('hidden');
            tokenCountEl.classList.add('error');
        }
        updateInsertButtonState(false);
    }
}

/**
 * Update insert button state based on current selections and validation
 * @param {boolean} [isValid] - Optional validation state for file paths
 */
function updateInsertButtonState(isValid = true) {
    const insertButton = document.getElementById('insert-reference');
    if (!insertButton) {
        console.error('Insert button not found');
        return;
    }

    const type = document.getElementById('reference-type')?.value;
    if (!type) {
        insertButton.disabled = true;
        return;
    }

    let shouldEnable = false;

    switch (type) {
        case 'file':
            // Check both the selected file input and file path input
            const selectedFile = document.getElementById('selectedFileInput')?.value || 
                               document.getElementById('file-path-input')?.value;
            shouldEnable = Boolean(selectedFile) && isValid;
            console.log('File selection state:', { selectedFile, isValid, shouldEnable });
            break;
        case 'github':
            const githubIssues = document.getElementById('github-issues')?.value;
            const githubTitle = document.getElementById('github-title')?.value;
            shouldEnable = Boolean(githubIssues && githubTitle);
            break;
        case 'var':
            const variableSelect = document.getElementById('variable-select')?.value;
            shouldEnable = Boolean(variableSelect);
            break;
        case 'api':
            shouldEnable = true;
            break;
        default:
            shouldEnable = false;
            break;
    }

    insertButton.disabled = !shouldEnable;
    console.log('Insert button state updated:', { type, shouldEnable });
}

// Debounce helper function
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

// Validate file path
async function validateFilePath(path) {
    if (!path) {
        updateInsertButtonState(false);
        return;
    }
    
    const validationDiv = document.getElementById('file-path-validation');
    const validationIcon = document.getElementById('validation-icon');
    const validationMessage = document.getElementById('validation-message');
    const fileValidationDiv = document.getElementById('file-validation');
    const previewDiv = document.getElementById('fileTreePreview');

    // Hide validation elements if path is empty
    if (!path.trim()) {
        if (validationDiv) validationDiv.classList.add('hidden');
        if (fileValidationDiv) fileValidationDiv.classList.add('hidden');
        if (previewDiv) previewDiv.style.display = 'none';
        updateInsertButtonState(false);
        return;
    }
    
    console.log("Sending validation request for path:", path);
    
    try {
        const response = await fetch('/api/files/validate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ path: path.replace(/\\/g, '/') })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log("Received validation response:", data);
        
        // Update validation UI
        if (validationDiv) validationDiv.classList.remove('hidden');
        if (fileValidationDiv) fileValidationDiv.classList.remove('hidden');
        
        if (data.valid) {
            if (validationIcon) {
                validationIcon.innerHTML = '✓';
                validationIcon.className = 'mr-2 text-green-500';
            }
            if (validationMessage) {
                validationMessage.textContent = 'Valid file path';
                validationMessage.className = 'text-green-500';
            }
            
            // Determine if path is recursive from the file validation message
            const isRecursive = data.fileValidation !== "Allowed directory is not recursive";
            
            // Update file tree preview
            await updateFileTreePreview(path.replace(/\\/g, '/'), isRecursive);
        } else {
            if (validationIcon) {
                validationIcon.innerHTML = '!';
                validationIcon.className = 'mr-2 text-red-500';
            }
            if (validationMessage) {
                validationMessage.textContent = data.error || 'Invalid file path';
                validationMessage.className = 'text-red-500';
            }
            if (previewDiv) previewDiv.style.display = 'none';
        }
        
        // Update file validation message
        const fileValidationMessage = document.getElementById('file-validation-message');
        if (fileValidationMessage && data.fileValidation) {
            fileValidationMessage.textContent = data.fileValidation;
            fileValidationMessage.className = data.valid ? 'text-green-500' : 'text-red-500';
            if (fileValidationDiv) fileValidationDiv.classList.remove('hidden');
        } else if (fileValidationDiv) {
            fileValidationDiv.classList.add('hidden');
        }
        
        // Update button state based on validation result
        updateInsertButtonState(Boolean(data.valid));
        
        return data.valid;
    } catch (error) {
        console.error("Validation error:", error);
        if (validationDiv) validationDiv.classList.remove('hidden');
        if (fileValidationDiv) fileValidationDiv.classList.add('hidden');
        if (validationIcon) {
            validationIcon.innerHTML = '!';
            validationIcon.className = 'mr-2 text-red-500';
        }
        if (validationMessage) {
            validationMessage.textContent = 'Error validating path';
            validationMessage.className = 'text-red-500';
        }
        if (previewDiv) previewDiv.style.display = 'none';
        
        updateInsertButtonState(false);
        return false;
    }
}

// Format file tree for display
function formatFileTree(tree, basePath = '', isRecursive = true) {
    if (!tree) {
        console.warn('Empty tree data');
        return '';
    }

    // Handle error messages
    if (typeof tree === 'string' && tree.includes('<')) {
        return `<li class="file-item error" title="${tree}">
            <span class="tree-icon">⚠️</span>
            <span class="tree-label">${tree}</span>
        </li>`;
    }

    // Handle file nodes (simple strings)
    if (typeof tree === 'string') {
        const fullPath = basePath ? `${basePath}/${tree}` : tree;
        const isSelectable = isRecursive; // Files are only selectable in recursive mode
        return `<li class="file-item ${isSelectable ? 'selectable' : 'non-selectable'}" data-path="${fullPath}">
            <span class="tree-icon">📄</span>
            <span class="tree-label" data-path="${fullPath}" data-selectable="${isSelectable}" data-type="file">${tree}</span>
        </li>`;
    }

    // Handle directory nodes (objects with children)
    if (typeof tree === 'object') {
        let html = '';
        for (const [name, subtree] of Object.entries(tree)) {
            const fullPath = basePath ? `${basePath}/${name}` : name;
            const isDir = typeof subtree === 'object';
            const isSelectable = !isRecursive && isDir; // Directories are only selectable in non-recursive mode
            
            if (isDir) {
                html += `<li class="directory-item ${isSelectable ? 'selectable' : 'non-selectable'}">
                    <span class="tree-icon">📁</span>
                    <span class="tree-label" data-path="${fullPath}" data-selectable="${isSelectable}" data-type="directory">${name}</span>
                    <ul class="file-tree">${formatFileTree(subtree, fullPath, isRecursive)}</ul>
                </li>`;
            } else {
                html += formatFileTree(subtree, fullPath, isRecursive);
            }
        }
        return html;
    }

    return '';
}

// Update file tree preview
async function updateFileTreePreview(path, isRecursive) {
    const previewDiv = document.getElementById('fileTreePreview');
    if (!previewDiv) return;

    try {
        const response = await fetch(`/api/files/tree?path=${encodeURIComponent(path)}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        if (!data || !data.tree) {
            previewDiv.style.display = 'none';
            return;
        }
        
        previewDiv.innerHTML = `
            <div class="file-tree-container">
                <ul class="file-tree root">
                    ${formatFileTree(data.tree, '', isRecursive)}
                </ul>
            </div>`;
        previewDiv.style.display = 'block';
        
        // Add CSS class to indicate recursive mode
        previewDiv.classList.toggle('recursive-mode', isRecursive);
        previewDiv.classList.toggle('non-recursive-mode', !isRecursive);
        
        // Add click handlers to all tree items
        previewDiv.querySelectorAll('.tree-label').forEach(label => {
            label.onclick = (e) => {
                const isSelectable = label.dataset.selectable === 'true';
                handleTreeItemClick(e, label.dataset.path, isSelectable);
            };
        });

        // Add CSS if not already present
        if (!document.getElementById('file-tree-styles')) {
            const styles = document.createElement('style');
            styles.id = 'file-tree-styles';
            styles.textContent = `
                .file-tree-container {
                    border: 1px solid #e5e7eb;
                    border-radius: 6px;
                    margin-top: 8px;
                    background: white;
                }
                .file-tree {
                    list-style: none;
                    padding-left: 20px;
                    margin: 0;
                    font-family: system-ui, -apple-system, sans-serif;
                }
                .file-tree.root {
                    padding: 8px;
                    max-height: 300px;
                    overflow-y: auto;
                }
                .file-item, .directory-item {
                    padding: 4px 8px;
                    border-radius: 4px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin: 2px 0;
                }
                .file-item.selected, .directory-item.selected {
                    background-color: #e5e7eb;
                }
                .tree-icon {
                    flex-shrink: 0;
                }
                .tree-label {
                    flex-grow: 1;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                .selectable {
                    cursor: pointer;
                }
                .selectable:hover {
                    background-color: #f3f4f6;
                }
                .non-selectable {
                    cursor: not-allowed;
                    opacity: 0.6;
                }
                .error {
                    color: #ef4444;
                    font-style: italic;
                }
            `;
            document.head.appendChild(styles);
        }
    } catch (error) {
        console.error('Error updating file tree:', error);
        previewDiv.style.display = 'none';
    }
}

// Handle tree item click
function handleTreeItemClick(event, path, isSelectable) {
    event.preventDefault();
    event.stopPropagation();

    if (!isSelectable) {
        return;
    }

    // Remove selection from all items
    document.querySelectorAll('.file-item.selected, .directory-item.selected').forEach(item => {
        item.classList.remove('selected');
    });

    // Add selection to clicked item
    const listItem = event.target.closest('li');
    if (listItem) {
        listItem.classList.add('selected');
    }

    const normalizedPath = path.replace(/\\/g, '/');
    
    // Update both input fields with the normalized path
    const filePathInput = document.getElementById('filePathInput');  
    const selectedFileInput = document.getElementById('selectedFileInput');
    
    if (filePathInput) {
        filePathInput.value = normalizedPath;
        // Don't trigger validation since we're selecting from pre-validated tree
    }
    
    if (selectedFileInput) {
        selectedFileInput.value = normalizedPath;
    }
    
    // Update button state directly since we know tree items are pre-validated
    updateInsertButtonState(true);
}

// Initialize file picker when dialog is shown
document.addEventListener('DOMContentLoaded', () => {
    initializeFilePicker();
    
    // Add click handler for tree items
    document.addEventListener('click', (event) => {
        const treeLabel = event.target.closest('.tree-label');
        if (!treeLabel) return;
        
        event.preventDefault();
        event.stopPropagation();
        
        const path = treeLabel.dataset.path;
        const isSelectable = treeLabel.dataset.selectable === 'true';
        
        if (!isSelectable) return;

        // Remove selection from all items
        document.querySelectorAll('.file-item.selected, .directory-item.selected').forEach(item => {
            item.classList.remove('selected');
        });

        // Add selection to clicked item
        const listItem = treeLabel.closest('li');
        if (listItem) {
            listItem.classList.add('selected');
        }

        const normalizedPath = path.replace(/\\/g, '/');
        
        // Update both input fields with the normalized path
        const filePathInput = document.getElementById('filePathInput');  
        const selectedFileInput = document.getElementById('selectedFileInput');
        
        if (filePathInput) filePathInput.value = normalizedPath;
        if (selectedFileInput) selectedFileInput.value = normalizedPath;
        
        // Validate the selected path
        validateFilePath(normalizedPath);
    });
});

// Setup event listeners for the dialog
function setupDialogListeners() {
    // Clean up any existing file input
    const existingFileInput = currentDialog.querySelector('input[type="file"]');
    if (existingFileInput) {
        existingFileInput.remove();
    }

    // Get dialog elements
    const closeButton = currentDialog.querySelector('.close-dialog');
    const typeSelect = document.getElementById('reference-type');
    const filePathInput = document.getElementById('file-path-input');
    const browseButton = currentDialog.querySelector('.browse-files');
    const insertButton = document.getElementById('insert-reference');
    const githubTitleInput = document.getElementById('github-title');
    const githubIssuesSelect = document.getElementById('github-issues');
    const githubGoButton = document.getElementById('github-go-button');
    const variableSelect = document.getElementById('variable-select');

    // Create hidden file input for native file picker
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.style.display = 'none';
    currentDialog.appendChild(fileInput);

    // Insert button handler
    if (insertButton) {
        // Remove any existing click listeners
        insertButton.replaceWith(insertButton.cloneNode(true));
        const newInsertButton = document.getElementById('insert-reference');
        
        newInsertButton.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('Insert button clicked');
            
            try {
                await handleReferenceInsertion();
            } catch (error) {
                console.error('Error handling reference insertion:', error);
                showError(error.message);
            }
        });
        
        // Initialize button state
        updateInsertButtonState();
    } else {
        console.error('Insert button not found in dialog');
    }

    // Close button handler
    if (closeButton) {
        closeButton.addEventListener('click', (e) => {
            e.preventDefault();
            currentDialog.classList.add('hidden');
            // Reset the dialog state
            if (typeSelect) typeSelect.value = '';
            if (filePathInput) filePathInput.value = '';
            if (githubTitleInput) githubTitleInput.value = '';
            if (githubIssuesSelect) {
                githubIssuesSelect.innerHTML = '<option value="">Select an issue...</option>';
                document.getElementById('github-issues-container')?.classList.add('hidden');
            }
            if (variableSelect) {
                variableSelect.value = '';
                document.getElementById('variable-input')?.classList.add('hidden');
            }
            currentEditor = null;
        });
    }

    // Type select handler
    if (typeSelect) {
        typeSelect.addEventListener('change', onTypeChange);
    }

    // Variable select handler
    if (variableSelect) {
        variableSelect.addEventListener('change', () => {
            updateInsertButtonState();
        });
    }

    // File path input handler
    if (filePathInput) {
        const debouncedValidation = debounce((e) => validateFilePath(e.target.value), 300);
        filePathInput.addEventListener('input', debouncedValidation);
    }

    // GitHub title input handler
    if (githubTitleInput) {
        githubTitleInput.addEventListener('input', () => {
            updateInsertButtonState();
        });

        // Add enter key handler for GitHub title input
        githubTitleInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleReferenceInsertion();
            }
        });
    }

    // GitHub Go button handler
    if (githubGoButton) {
        githubGoButton.addEventListener('click', async (e) => {
            e.preventDefault();
            const repoUrl = document.getElementById('github-title')?.value;
            if (repoUrl) {
                await updateGitHubIssuesDropdown(repoUrl);
            }
        });
    }

    // GitHub issues select handler
    if (githubIssuesSelect) {
        githubIssuesSelect.addEventListener('change', () => {
            updateInsertButtonState();
        });
    }

    // Browse button handler
    if (browseButton) {
        browseButton.addEventListener('click', (e) => {
            e.preventDefault();
            fileInput.click();
        });
    }

    // File input change handler
    fileInput.addEventListener('change', (event) => {
        const files = event.target.files;
        if (files.length > 0) {
            const file = files[0];
            const selectedPath = file.name; // Use just the filename for simplicity
            
            // Update the selected file display
            const selectedFileDisplay = document.getElementById('selectedFileDisplay');
            const selectedFileName = document.getElementById('selectedFileName');
            if (selectedFileName && selectedFileDisplay) {
                selectedFileName.textContent = file.name;
                selectedFileDisplay.classList.remove('hidden');
            }
            
            // Update both inputs
            if (filePathInput) {
                filePathInput.value = selectedPath;
                const selectedFileInput = document.getElementById('selectedFileInput');
                if (selectedFileInput) {
                    selectedFileInput.value = selectedPath;
                }
                validateFilePath(selectedPath);
            }
            fileInput.remove();
        }
    });
}

async function validateAndSetFilePicker(path) {
    if (!path) return false;

    try {
        const response = await fetch(`/api/files/validate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ path: path })
        });
        
        const data = await response.json();
        const browseFolderBtn = document.getElementById('browseFolderBtn');
        
        if (data.valid) {
            // Path is valid
            const stats = await fetch(`/api/files/stats?path=${encodeURIComponent(path)}`).then(r => r.json());
            
            if (browseFolderBtn) {
                browseFolderBtn.classList.remove('btn-outline-danger');
                browseFolderBtn.classList.add('btn-outline-success');
            }
            
            // Set the selectedFileInput value and update button state
            const selectedFileInput = document.getElementById('selectedFileInput');
            if (selectedFileInput) {
                selectedFileInput.value = path;
                updateInsertButtonState(true);
            }
            
            return true;
        } else {
            // Path is invalid
            if (browseFolderBtn) {
                browseFolderBtn.classList.remove('btn-outline-success');
                browseFolderBtn.classList.add('btn-outline-danger');
            }
            
            // Clear the selectedFileInput value and update button state
            const selectedFileInput = document.getElementById('selectedFileInput');
            if (selectedFileInput) {
                selectedFileInput.value = '';
                updateInsertButtonState(false);
            }
            
            return false;
        }
    } catch (error) {
        console.error('Error validating path:', error);
        // Clear the selectedFileInput value and update button state on error
        const selectedFileInput = document.getElementById('selectedFileInput');
        if (selectedFileInput) {
            selectedFileInput.value = '';
            updateInsertButtonState(false);
        }
        return false;
    }
}

function initializeFilePicker() {
    const filePathInput = document.getElementById('filePathInput');
    const selectedFileInput = document.getElementById('selectedFileInput'); // New input for selected file
    const browseFolderBtn = document.getElementById('browseFolderBtn');
    let validationTimeout;

    if (!filePathInput || !browseFolderBtn) {
        console.error('Required file picker elements not found');
        return;
    }

    // Create a custom file input that remembers the last directory
    const createFileInput = () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.id = 'tempFilePicker';
        input.style.display = 'none';
        document.body.appendChild(input);
        return input;
    };

    // Handle browse button click
    browseFolderBtn.addEventListener('click', async () => {
        // Remove any existing temporary file input
        const oldInput = document.getElementById('tempFilePicker');
        if (oldInput) {
            oldInput.remove();
        }

        // Create new file input
        const tempInput = createFileInput();

        // Handle file selection
        tempInput.addEventListener('change', (event) => {
            const files = event.target.files;
            if (files.length > 0) {
                const file = files[0];
                const selectedPath = file.name; // Use just the filename for simplicity
                
                // Update the selected file input if it exists
                if (selectedFileInput) {
                    selectedFileInput.value = selectedPath;
                }
                
                // Update the selected file display if elements exist
                const selectedFileDisplay = document.getElementById('selectedFileDisplay');
                const selectedFileName = document.getElementById('selectedFileName');
                selectedFileName.textContent = file.name;
                selectedFileDisplay.classList.remove('hidden');
                
                tempInput.remove();
            }
        });

        // Open the file picker
        tempInput.click();
    });

    // Handle manual path input with debouncing
    filePathInput.addEventListener('input', (event) => {
        const path = event.target.value.trim();
        
        // Clear existing timeout
        if (validationTimeout) {
            clearTimeout(validationTimeout);
        }
        
        // Set new timeout for validation
        validationTimeout = setTimeout(async () => {
            validateFilePath(path);
            await validateAndSetFilePicker(path);
        }, 500);
    });
}

// Parse GitHub URL to get owner and repo
function parseGitHubUrl(url) {
    if (!url) return null;
    try {
        url= url.replace(/\.git\/?$/, '').replace(/\/$/, '');
        const match = url.match(/github\.com\/([^/]+)\/([^/]+)/);
        if (match) {
            const [, owner, repo] = match;
            console.log('Parsed GitHub URL - owner:', owner, 'repo:', repo);
            return [owner, repo];
        }
        console.error('URL does not match expected GitHub format:', url);
    } catch (error) {
        console.error('Error parsing GitHub URL:', error);
    }
    return null;
}

// Fetch GitHub issues using admin token
async function fetchGitHubIssues(owner, repo) {
    try {
        const repoUrl = `https://github.com/${owner}/${repo}`;
        const adminToken = currentDialog.dataset.adminToken;
        
        const response = await fetch(
            `/api/github/issues?repo_url=${encodeURIComponent(repoUrl)}`,
            {
                headers: {
                    'X-Admin-Token': adminToken
                }
            }
        );
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to fetch GitHub issues');
        }

        const data = await response.json();
        return data.issues || [];
    } catch (error) {
        console.error('Error fetching GitHub issues:', error);
        throw error;
    }
}

// Update GitHub issues dropdown
async function updateGitHubIssuesDropdown(url) {
    const issuesContainer = document.getElementById('github-issues-container');
    const issuesSelect = document.getElementById('github-issues');
    const goButton = document.getElementById('github-go-button');
    const goText = document.getElementById('github-go-text');
    const goLoading = document.getElementById('github-go-loading');
    
    if (!issuesContainer || !issuesSelect || !goButton || !goText || !goLoading) return;

    try {
        // Show loading state
        goButton.disabled = true;
        goText.classList.add('hidden');
        goLoading.classList.remove('hidden');
        issuesContainer.classList.add('hidden');

        // Parse GitHub URL
        const urlParts = parseGitHubUrl(url);
        if (!urlParts) {
            throw new Error('Invalid GitHub repository URL');
        }
        const [owner, repo] = urlParts;
        console.log('Fetching issues for GitHub repository:', owner, repo);

        // Fetch issues
        const issues = await fetchGitHubIssues(owner, repo);

        // Hide loading state
        goButton.disabled = false;
        goText.classList.remove('hidden');
        goLoading.classList.add('hidden');

        // Update dropdown
        issuesSelect.innerHTML = '<option value="">Select an issue...</option>';
        issues.forEach(issue => {
            const option = document.createElement('option');
            option.value = issue.value;
            option.dataset.state = issue.state;
            option.dataset.created = issue.created_at;
            option.dataset.updated = issue.updated_at;
            option.textContent = issue.label;
            issuesSelect.appendChild(option);
        });

        // Show the container and enable select only if we have issues
        if (issues.length > 0) {
            issuesContainer.classList.remove('hidden');
            issuesSelect.disabled = false;
        } else {
            showError('No issues found in this repository');
        }
    } catch (error) {
        // Reset loading state
        goButton.disabled = false;
        goText.classList.remove('hidden');
        goLoading.classList.add('hidden');
        
        // Hide the issues container
        issuesContainer.classList.add('hidden');
        
        console.error('Error updating issues dropdown:', error);
        showError(error.message);
    }
}

/**
 * Handle reference insertion
 */
async function handleReferenceInsertion() {
    console.log('Handling reference insertion');
    
    if (!currentEditor) {
        throw new Error('No active editor');
    }

    const type = document.getElementById('reference-type')?.value;
    if (!type) {
        throw new Error('No reference type selected');
    }

    let reference = '';
    
    try {
        switch (type) {
            case 'file':
                // Get the file path from either input
                const filePath = document.getElementById('selectedFileInput')?.value || 
                               document.getElementById('file-path-input')?.value;
                               
                console.log('File path for insertion:', filePath);
                
                if (!filePath) {
                    throw new Error('No file selected');
                }
                reference = `@[file:${filePath}]`;
                break;
                
                case 'github':
                    {
                    if (!document.getElementById('github-issues') || !document.getElementById('github-issues').value) {
                        throw new Error('No GitHub issue selected');
                    }
                    console.log('GitHub issue value:', document.getElementById('github-issues').value);
                    const issueNumber = document.getElementById('github-issues').value;
                    const repoUrl = document.getElementById('github-title')?.value;
                    console.log('Repository URL:', repoUrl);
                    const urlParts = parseGitHubUrl(repoUrl);
                    if (!urlParts) {
                        throw new Error('Invalid GitHub repository URL');
                    }
                    const [owner, repo] = urlParts;
    
                    // Format the reference to match Python's expected format with 'issue:' prefix
                    reference = `@[github:issue:${owner}/${repo}#${issueNumber}]`;
                    console.log('created reference:', reference);
                    break;
                }
            case 'var':
                const variableSelect = document.getElementById('variable-select')?.value;
                if (!variableSelect) {
                    throw new Error('No variable selected');
                }
                reference = `@[var:${variableSelect}]`;
                break;
                
            case 'api':
                reference = '@[api:]';
                break;
                
            default:
                throw new Error('Invalid reference type');
        }

        console.log('Inserting reference:', reference);

        // Insert the reference at the cursor position
        const cursor = currentEditor.getCursor();
        currentEditor.replaceRange(reference, cursor);
        
        // Close the dialog
        const dialog = document.getElementById('reference-dialog');
        if (dialog) {
            dialog.classList.add('hidden');
        }

    } catch (error) {
        console.error('Error inserting reference:', error);
        throw error;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const dialog = document.getElementById('reference-dialog');
    if (!dialog) {
        console.error('Reference dialog not found');
        return;
    }
    currentDialog = dialog;

    // Initial setup of insert button
    const insertButton = document.getElementById('insert-reference');
    if (insertButton) {
        insertButton.disabled = true;
    }
});

// Helper function to show error messages
function showError(message) {
    const errorElement = document.getElementById('error-message');
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.remove('hidden');
    }
}

// Make handleTreeItemClick globally accessible
window.handleTreeItemClick = handleTreeItemClick;
