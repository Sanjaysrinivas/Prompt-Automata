import { COLORS, ICONS, PREVIEW_TYPES } from './constants.js';

class ReferencePreview {
    constructor() {
        this.previewElement = document.getElementById('referencePreview');
        this.typeElement = document.getElementById('referenceType');
        this.validationIcon = document.getElementById('validationIcon');
        this.validationStatus = document.getElementById('validationStatus');
        this.errorElement = document.getElementById('previewError');
        this.loadingElement = document.getElementById('previewLoading');

        this.fileSection = document.getElementById('filePreviewSection');
        this.fileContent = document.getElementById('fileContent');
        this.syntaxSelector = document.getElementById('syntaxSelector');
        this.copyButton = document.getElementById('copyContent');

        this.apiSection = document.getElementById('apiPreviewSection');
        this.apiContent = document.getElementById('apiContent');
        this.endpointUrl = document.getElementById('endpointUrl');
        this.apiMetadata = document.getElementById('apiMetadata');
        this.refreshButton = document.getElementById('refreshApi');

        this.variableSection = document.getElementById('variablePreviewSection');
        this.variableContent = document.getElementById('variableContent');
        this.variableSelect = document.getElementById('variableSelect');
        this.lastUpdated = document.getElementById('variableLastUpdated');

        this.githubIssueSection = document.getElementById('githubIssuePreviewSection');
        this.githubIssueUrl = document.getElementById('githubIssueUrl');
        this.githubIssueContent = document.getElementById('githubIssueContent');
        this.refreshGithubIssue = document.getElementById('refreshGithubIssue');

        this.initializeEventListeners();
        this.loadVariables();
    }

    initializeEventListeners() {
        this.copyButton.addEventListener('click', () => this.copyContent());
        this.refreshButton.addEventListener('click', () => this.refreshApiContent());
        this.syntaxSelector.addEventListener('change', (e) => this.updateSyntaxHighlighting(e.target.value));
        this.githubIssueUrl.addEventListener('input', (e) => this.validateGitHubIssueUrl(e.target.value));
        this.refreshGithubIssue.addEventListener('click', () => this.loadGitHubIssue(this.githubIssueUrl.value));
        document.getElementById('referenceTypeSelect').addEventListener('change', (e) => this.handleReferenceTypeSelect(e.target.value));
        this.variableSelect.addEventListener('change', (e) => this.handleVariableSelect(e.target.value));
    }

    async loadVariables() {
        try {
            const response = await fetch('/admin/variables', {
                headers: {
                    'X-Admin-Token': document.querySelector('meta[name="admin-token"]').content
                }
            });
            if (!response.ok) {
                throw new Error('Failed to load variables');
            }
            const variables = await response.json();
            
            // Clear existing options except the first one
            while (this.variableSelect.options.length > 1) {
                this.variableSelect.remove(1);
            }
            
            // Add variables to the dropdown
            variables.forEach(variable => {
                const option = document.createElement('option');
                option.value = variable.name;
                option.textContent = variable.name;
                this.variableSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading variables:', error);
            this.showError('Failed to load variables');
        }
    }

    async handleVariableSelect(variableName) {
        if (!variableName) return;
        
        try {
            const response = await fetch(`/admin/variables?name=${encodeURIComponent(variableName)}`, {
                headers: {
                    'X-Admin-Token': document.querySelector('meta[name="admin-token"]').content
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to load variable value');
            }
            
            const variables = await response.json();
            const variable = variables.find(v => v.name === variableName);
            
            if (variable) {
                this.variableContent.textContent = variable.value;
                this.lastUpdated.textContent = `Last updated: ${new Date(variable.updated_at).toLocaleString()}`;
            }
        } catch (error) {
            console.error('Error loading variable value:', error);
            this.showError('Failed to load variable value');
        }
    }

    async previewReference(reference) {
        this.showLoading();
        this.clearError();

        try {
            const referenceType = this.detectReferenceType(reference);
            this.updateReferenceType(referenceType);

            this.hideAllSections();

            switch (referenceType) {
                case 'file':
                    await this.previewFile(reference);
                    break;
                case 'api':
                    await this.previewApi(reference);
                    break;
                case 'variable':
                    const varName = this.extractValue(reference);
                    this.variableSelect.value = varName;
                    await this.handleVariableSelect(varName);
                    this.variableSection.classList.add('active');
                    break;
                case 'github-issue':
                    await this.loadGitHubIssue(reference);
                    break;
                default:
                    throw new Error('Unknown reference type');
            }

            this.updateValidationStatus(true, 'Reference validated successfully');
        } catch (error) {
            this.showError(error.message);
            this.updateValidationStatus(false, error.message);
        } finally {
            this.hideLoading();
        }
    }

    handleReferenceTypeSelect(type) {
        this.hideAllSections();
        this.clearError();
        
        switch (type) {
            case 'file':
                this.fileSection.classList.add('active');
                break;
            case 'api':
                this.apiSection.classList.add('active');
                break;
            case 'variable':
                this.variableSection.classList.add('active');
                this.loadVariables(); // Reload variables when switching to variable type
                break;
            case 'github':
                this.githubIssueSection.classList.add('active');
                break;
        }
    }

    detectReferenceType(reference) {
        if (reference.startsWith('@[file:')) return 'file';
        if (reference.startsWith('@[api:')) return 'api';
        if (reference.startsWith('@[var:')) return 'variable';
        if (reference.startsWith('https://github.com/')) return 'github-issue';
        throw new Error('Invalid reference format');
    }

    async previewFile(reference, isNativePicker = false) {
        try {
            // Handle both raw file paths and reference format
            const filePath = reference.startsWith('@[') ? this.extractValue(reference) : reference;

            // First try /prompts/preview for file references
            const previewResponse = await fetch('/prompts/preview', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    content: `@[file:${filePath}]`,
                    isNativePicker: isNativePicker
                })
            });

            if (!previewResponse.ok) {
                // Try to get error from JSON response
                let error;
                try {
                    const errorData = await previewResponse.json();
                    error = errorData.error || 'Failed to load file preview';
                } catch {
                    error = 'Failed to load file preview';
                }
                
                // If that fails, fall back to /api/preview/file
                const fileResponse = await fetch(`/api/preview/file?path=${encodeURIComponent(filePath)}&isNativePicker=${isNativePicker}`);
                if (!fileResponse.ok) {
                    const fileData = await fileResponse.json();
                    throw new Error(fileData.error || error || 'Failed to load file preview');
                }
                const content = await fileResponse.text();
                this.fileContent.innerHTML = content;
            } else {
                // Handle successful response as raw text
                const content = await previewResponse.text();
                this.fileContent.innerHTML = content;
                this.fileSection.classList.add('active');
                
                // Update syntax highlighting based on file extension
                const extension = filePath.split('.').pop();
                const syntax = this.getSyntaxFromExtension(extension);
                if (syntax) {
                    this.syntaxSelector.value = syntax;
                    this.updateSyntaxHighlighting(syntax);
                }
            }
        } catch (error) {
            console.error('Error previewing file:', error);
            throw error;
        }
    }

    async previewApi(reference) {
        const endpoint = this.extractValue(reference);
        const response = await fetch(`/api/preview/endpoint?endpoint=${encodeURIComponent(endpoint)}`);

        if (!response.ok) {
            throw new Error('Failed to load API preview');
        }

        const data = await response.json();
        this.endpointUrl.textContent = endpoint;
        this.apiContent.textContent = JSON.stringify(data.content, null, 2);
        this.apiMetadata.textContent = `Last fetched: ${new Date().toLocaleString()}`;
        this.apiSection.classList.add('active');
    }

    async previewVariable(reference) {
        const varName = this.extractValue(reference);
        const response = await fetch(`/api/preview/variable?name=${encodeURIComponent(varName)}`);

        if (!response.ok) {
            throw new Error('Failed to load variable preview');
        }

        const data = await response.json();
        this.variableName.textContent = varName;
        this.variableContent.textContent = data.value;
        this.lastUpdated.textContent = `Last updated: ${new Date(data.lastUpdated).toLocaleString()}`;
        this.variableSection.classList.add('active');
    }

    async loadGitHubIssue(url) {
        try {
            const [owner, repo, issueNumber] = this.parseGitHubUrl(url);
            this.showLoading();

            const response = await fetch('/admin/github/issue', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    owner,
                    repo,
                    issue_number: issueNumber
                })
            });

            if (!response.ok) {
                throw new Error('Failed to load GitHub issue');
            }

            const data = await response.json();
            this.displayGitHubIssue(data);
            this.setValidationStatus(true, 'GitHub issue loaded successfully');
        } catch (error) {
            console.error('Error loading GitHub issue:', error);
            this.setValidationStatus(false, error.message);
        } finally {
            this.hideLoading();
        }
    }

    parseGitHubUrl(url) {
        const match = url.match(/github\.com\/([\w-]+)\/([\w-]+)\/issues\/(\d+)/);
        if (!match) {
            throw new Error('Invalid GitHub issue URL');
        }
        return [match[1], match[2], match[3]];
    }

    displayGitHubIssue(issue) {
        const content = this.githubIssueContent;
        content.innerHTML = `
            <h3>${issue.title}</h3>
            <div class="issue-metadata">
                <span class="issue-number">#${issue.number}</span>
                <span class="issue-state ${issue.state}">${issue.state}</span>
            </div>
            <div class="issue-body">${marked(issue.body)}</div>
        `;
        this.githubIssueSection.classList.add('active');
    }

    extractValue(reference) {
        const match = reference.match(/@\[(file|api|var):(.+)\]/);
        if (!match) throw new Error('Invalid reference format');
        return match[2];
    }

    getSyntaxFromExtension(extension) {
        const syntaxMap = {
            'py': 'python',
            'md': 'markdown',
            'json': 'json',
            'js': 'javascript',
            'html': 'html',
            'css': 'css'
        };
        return syntaxMap[extension] || 'plain';
    }

    updateSyntaxHighlighting(syntax) {
        if (window.Prism) {
            const code = this.fileContent.textContent;
            this.fileContent.innerHTML = Prism.highlight(code, Prism.languages[syntax], syntax);
        }
    }

    async refreshApiContent() {
        const endpoint = this.endpointUrl.textContent;
        if (endpoint) {
            await this.previewApi(`@[api:${endpoint}]`);
        }
    }

    copyContent() {
        const activeSection = this.previewElement.querySelector('.preview-section.active');
        if (activeSection) {
            const content = activeSection.querySelector('.preview-window').textContent;
            navigator.clipboard.writeText(content);
            this.showTemporaryMessage('Content copied to clipboard!');
        }
    }

    updateReferenceType(type) {
        this.typeElement.textContent = type.charAt(0).toUpperCase() + type.slice(1);
    }

    updateValidationStatus(isValid, message) {
        this.validationIcon.innerHTML = isValid ? ICONS.SUCCESS : ICONS.ERROR;
        this.validationIcon.style.color = isValid ? COLORS.SUCCESS : COLORS.ERROR;
        this.validationStatus.textContent = message;
    }

    hideAllSections() {
        this.fileSection.classList.remove('active');
        this.apiSection.classList.remove('active');
        this.variableSection.classList.remove('active');
        this.githubIssueSection.classList.remove('active');
    }

    showError(message) {
        this.errorElement.textContent = message;
        this.errorElement.style.display = 'block';
    }

    clearError() {
        this.errorElement.textContent = '';
        this.errorElement.style.display = 'none';
    }

    showLoading() {
        this.loadingElement.style.display = 'flex';
    }

    hideLoading() {
        this.loadingElement.style.display = 'none';
    }

    showTemporaryMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'temporary-message';
        messageDiv.textContent = message;
        this.previewElement.appendChild(messageDiv);
        setTimeout(() => messageDiv.remove(), 2000);
    }

    setValidationStatus(isValid, message) {
        const status = document.getElementById('validationStatus');
        const icon = document.getElementById('validationIcon');

        status.textContent = message;
        icon.className = 'status-icon ' + (isValid ? 'valid' : 'invalid');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.referencePreview = new ReferencePreview();
});
