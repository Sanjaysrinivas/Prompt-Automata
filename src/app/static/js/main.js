// Common UI functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('Document loaded');
    
    // Handle mobile menu toggle
    const mobileMenuButton = document.querySelector('.mobile-menu-button');
    const mobileMenu = document.querySelector('.mobile-menu');
    
    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', () => {
            mobileMenu.classList.toggle('hidden');
        });
    }

    // Handle flash messages
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        const closeButton = message.querySelector('.close-button');
        if (closeButton) {
            closeButton.addEventListener('click', () => {
                message.remove();
            });
        }
    });
});
