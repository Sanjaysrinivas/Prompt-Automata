// API service for fence editor
import { API_ENDPOINTS } from './fence-config.js';

class FenceAPI {
    async countTokens(text) {
        const response = await this.post(API_ENDPOINTS.countTokens, { text });
        return response.token_count;
    }

    async saveBlock(blockData) {
        return await this.post(API_ENDPOINTS.saveBlock, blockData);
    }

    async loadBlock(blockId) {
        return await this.get(`${API_ENDPOINTS.loadBlock}/${blockId}`);
    }

    async getReferenceOptions(type) {
        return await this.get(`${API_ENDPOINTS.getReferenceOptions}?type=${type}`);
    }

    async refreshBlock(blockId, data) {
        return await this.post(`${API_ENDPOINTS.refreshBlock}/${blockId}`, data);
    }

    async refreshAll(data) {
        return await this.post(API_ENDPOINTS.refreshAll, data);  
    }

    async post(endpoint, data = null) {
        try {
            const options = {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            };

            if (data !== null) {
                options.body = JSON.stringify(data);
            }

            const response = await fetch(endpoint, options);

            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    async get(endpoint) {
        try {
            const response = await fetch(endpoint);
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }
}

export const fenceAPI = new FenceAPI();