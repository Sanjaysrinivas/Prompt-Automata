// UI components for fence editor

// Modal component
export function createModal({ title, content, width = 'w-1/2', maxHeight = 'max-h-[90vh]', headerButtons = '' }) {
    let modal = document.getElementById('fence-modal');
    
    const modalHTML = `
        <div class="bg-white rounded-lg shadow-xl ${width} ${maxHeight} flex flex-col">
            <div class="flex justify-between items-center p-4 border-b">
                <h3 class="text-lg font-semibold text-gray-900">${title}</h3>
                <div class="flex items-center space-x-2">
                    ${headerButtons}
                    <button class="modal-close p-2 text-gray-400 hover:text-gray-500">×</button>
                </div>
            </div>
            <div class="p-4 overflow-auto flex-1">
                ${content}
            </div>
            <div class="border-t p-4 flex justify-end">
                <button class="modal-close px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md">
                    Close
                </button>
            </div>
        </div>
    `;

    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'fence-modal';
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center hidden';
        document.body.appendChild(modal);
    }

    // Update modal content
    modal.innerHTML = modalHTML;

    // Add close handlers
    modal.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', () => modal.classList.add('hidden'));
    });

    return {
        element: modal,
        show: () => modal.classList.remove('hidden'),
        hide: () => modal.classList.add('hidden'),
        setContent: (newContent) => {
            const contentDiv = modal.querySelector('.p-4.overflow-auto');
            if (contentDiv) {
                contentDiv.innerHTML = newContent;
            }
        },
        setTitle: (newTitle) => {
            const titleEl = modal.querySelector('h3');
            if (titleEl) {
                titleEl.textContent = newTitle;
            }
        }
    };
}

// Success/Error message display
export function showMessage(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 transition-all transform translate-y-0 ${
        type === 'success' ? 'bg-green-500' : 'bg-red-500'
    } text-white`;
    toast.textContent = message;

    document.body.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('translate-y-full', 'opacity-0');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

export function showSuccess(message) {
    showMessage(message, 'success');
}

export function showError(message) {
    showMessage(message, 'error');
}
