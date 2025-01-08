// Reference handling functionality
import { createModal } from './fence-ui.js';
import { fenceAPI } from './fence-api.js';

let currentEditor = null;

export function showReferencePicker(editor) {
    currentEditor = editor;
    
    const modal = createModal({
        title: 'Insert Reference',
        content: `
            <div class="space-y-4">
                <div>
                    <label for="reference-type" class="block text-sm font-medium text-gray-700">Reference Type</label>
                    <select id="reference-type" class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md">
                        <option value="block">Block</option>
                        <option value="file">File</option>
                        <option value="prompt">Prompt</option>
                    </select>
                </div>
                <div>
                    <label for="reference-content" class="block text-sm font-medium text-gray-700">Reference Content</label>
                    <select id="reference-content" class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md">
                        <option value="">Select content...</option>
                    </select>
                </div>
                <div id="file-path-input" class="hidden">
                    <label for="file-path" class="block text-sm font-medium text-gray-700">File Path</label>
                    <div class="mt-1 flex rounded-md shadow-sm">
                        <input type="text" id="file-path" class="flex-1 min-w-0 block w-full px-3 py-2 rounded-none rounded-l-md focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm border-gray-300" placeholder="Enter file path">
                        <button type="button" class="inline-flex items-center px-3 py-2 border border-l-0 border-gray-300 rounded-r-md bg-gray-50 text-gray-500 text-sm" onclick="openFileBrowser()">
                            Browse
                        </button>
                    </div>
                </div>
            </div>
        `,
        width: 'w-96'
    });

    const typeSelect = document.getElementById('reference-type');
    if (typeSelect) {
        typeSelect.addEventListener('change', () => updateReferenceContentDropdown(typeSelect.value));
        updateReferenceContentDropdown(typeSelect.value);
    }

    modal.show();
}

async function updateReferenceContentDropdown(type) {
    const contentSelect = document.getElementById('reference-content');
    const filePathInput = document.getElementById('file-path-input');
    
    if (!contentSelect) return;

    contentSelect.innerHTML = '<option value="">Loading...</option>';
    
    if (filePathInput) {
        filePathInput.classList.toggle('hidden', type !== 'file');
    }

    try {
        const options = await fenceAPI.getReferenceOptions(type);
        contentSelect.innerHTML = `
            <option value="">Select ${type}...</option>
            ${options.map(opt => `<option value="${opt.value}">${opt.label}</option>`).join('')}
        `;
    } catch (error) {
        console.error('Error fetching reference options:', error);
        contentSelect.innerHTML = '<option value="">Error loading options</option>';
    }
}

export function insertReference(reference) {
    if (!currentEditor || !reference) return;
    
    const doc = currentEditor.getDoc();
    const cursor = doc.getCursor();
    doc.replaceRange(reference, cursor);
}

export function handleReferenceInsertion() {
    const typeSelect = document.getElementById('reference-type');
    const contentSelect = document.getElementById('reference-content');
    const filePathInput = document.getElementById('file-path');

    if (!typeSelect || !contentSelect) return;

    const type = typeSelect.value;
    const content = type === 'file' && filePathInput ? 
        filePathInput.value : 
        contentSelect.value;

    if (content) {
        insertReference(content);
        document.getElementById('fence-modal')?.classList.add('hidden');
    }
}
