/**
 * GitHub reference handling for fence blocks
 */

class GitHubReferenceHandler {
    constructor() {
        this.initializeElements();
        this.bindEvents();
    }

    initializeElements() {
        // Cache element references
        this.section = document.getElementById('github-reference-section');
        this.repoInput = document.getElementById('repo-url');
        this.fetchButton = document.getElementById('fetch-issues');
        this.issueSelect = document.getElementById('issue-select');
        this.preview = document.getElementById('issue-preview');
        this.errorContainer = document.getElementById('error-container');
    }

    bindEvents() {
        // Show GitHub section when GitHub reference type is selected
        document.getElementById('reference-type')
            .addEventListener('change', (e) => {
                if (e.target.value === 'github') {
                    this.section.classList.remove('hidden');
                } else {
                    this.section.classList.add('hidden');
                }
            });

        // Fetch issues when button is clicked
        this.fetchButton.addEventListener('click', () => this.fetchIssues());
        
        // Handle Enter key in repo URL input
        this.repoInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.fetchIssues();
            }
        });
        
        // Update preview when issue is selected
        this.issueSelect.addEventListener('change', () => this.updatePreview());
    }

    async fetchIssues() {
        const repoUrl = this.repoInput.value.trim();
        const githubUrlPattern = /^https?:\/\/github\.com\/[\w-]+\/[\w.-]+\/?(?:\.git)?$/;
        
        if (!repoUrl) {
            this.showError('Please enter a GitHub repository URL.');
            return;
        }
        
        if (!githubUrlPattern.test(repoUrl)) {
            this.showError('Invalid GitHub repository URL format. Expected format: https://github.com/owner/repo');
            return;
        }

        try {
            this.setLoading(true);
            
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
            
            try {
                // Get admin token from session
                const tokenResponse = await fetch('/admin/token');
                if (!tokenResponse.ok) {
                    throw new Error('Failed to get admin token');
                }
                const { token } = await tokenResponse.json();
                
                const response = await fetch(
                    `/api/github/issues?repo_url=${encodeURIComponent(repoUrl)}`,
                    { 
                        signal: controller.signal,
                        headers: {
                            'X-Admin-Token': token
                        }
                    }
                );
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || 'Failed to fetch issues');
                }
                
                const issues = await response.json();
                console.log('Raw response:', issues);
                
                if (!issues || !issues.issues || !Array.isArray(issues.issues)) {
                    throw new Error('Invalid response format from server');
                }
                
                console.log('Issues array:', issues.issues);
                this.populateIssues(issues.issues);
            } finally {
                clearTimeout(timeoutId);
            }
            
        } catch (error) {
            console.error('Error fetching issues:', error);
            if (error.name === 'AbortError') {
                this.showError('Request timed out. Please try again.');
            } else {
                this.showError(error.message);
            }
        } finally {
            this.setLoading(false);
        }
    }

    populateIssues(issues) {
        console.log('Populating issues:', issues);
        this.issueSelect.innerHTML = `
            <option value="">Select an issue...</option>
            ${issues.map(issue => {
                console.log('Processing issue:', issue);
                return `
                    <option value="${issue.value}" 
                            data-state="${issue.state}"
                            data-created="${issue.created_at}"
                            data-updated="${issue.updated_at}"
                            data-description="${issue.body || ''}">
                        ${issue.label}
                    </option>
                `;
            }).join('')}
        `;
        console.log('Final select HTML:', this.issueSelect.innerHTML);
        this.issueSelect.disabled = false;
    }

    async updatePreview() {
        const selectedOption = this.issueSelect.selectedOptions[0];
        if (!selectedOption) {
            this.preview.innerHTML = '';
            return;
        }

        const issueNumber = selectedOption.value;
        const [owner, repo] = this.getRepoInfo();
        if (!owner || !repo) {
            console.error('Could not extract owner/repo from URL');
            return;
        }

        try {
            // Get admin token
            const tokenResponse = await fetch('/admin/token');
            if (!tokenResponse.ok) {
                throw new Error('Failed to get admin token');
            }
            const { token } = await tokenResponse.json();
            if (!token) {
                throw new Error('Admin token not found');
            }

            const response = await fetch(`/api/github/issues/${owner}/${repo}/${issueNumber}/content`, {
                headers: {
                    'X-Admin-Token': token
                }
            });
            if (!response.ok) {
                throw new Error('Failed to fetch issue content');
            }

            const issue = await response.json();
            this.renderPreview(issue);
        } catch (error) {
            console.error('Error fetching issue content:', error);
            this.preview.innerHTML = '<p class="text-red-500">Error loading issue content</p>';
        }
    }

    getRepoInfo() {
        const repoUrl = this.repoInput.value.trim();
        const match = repoUrl.match(/^https?:\/\/github\.com\/([\w-]+)\/([\w.-]+)\/?$/);
        return match ? [match[1], match[2]] : [null, null];
    }

    renderPreview(issue) {
        const state = issue.state;
        const created = new Date(issue.created_at).toLocaleDateString();
        const updated = new Date(issue.updated_at).toLocaleDateString();
        const description = issue.body || 'No description available';

        // Escape HTML to prevent XSS
        const escapeHtml = (unsafe) => {
            return unsafe
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        };

        this.preview.innerHTML = `
            <h4 class="issue-title">${escapeHtml(issue.title)}</h4>
            <p class="issue-state ${state === 'open' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}">
                ${escapeHtml(state)}
            </p>
            <p class="issue-dates">
                Created: ${created}<br>Last Updated: ${updated}
            </p>
            <p class="issue-description">${escapeHtml(description)}</p>
        `;
    }

    setLoading(loading) {
        this.fetchButton.disabled = loading;
        this.fetchButton.innerHTML = loading ? 
            '<i class="fas fa-spinner fa-spin mr-2"></i>Loading...' : 
            'Fetch Issues';
        this.issueSelect.disabled = loading;
    }

    showError(message) {
        this.errorContainer.innerHTML = `
            <div class="alert alert-danger">
                ${message}
            </div>
        `;
    }

    createReference() {
        const selected = this.issueSelect.value;
        if (!selected) {
            console.error('No issue selected');
            return null;
        }
        const [owner, repo] = this.getRepoInfo();
        if (!owner || !repo) {
            console.error('Could not extract owner/repo from URL');
            return null;
        }

        return `@[github:issue:${owner}/${repo}#${selected}]`;
    }
    getSelectedReference() {
        return this.createReference();
    }
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => {
    window.githubReferenceHandler = new GitHubReferenceHandler();
});
