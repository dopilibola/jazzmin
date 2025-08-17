// Global state
let currentTab = 'login';

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Add event listeners
    document.addEventListener('click', handleRippleEffect);
    
    // Initialize form validation
    initializeFormValidation();
    
    // Set initial tab indicator position
    updateTabIndicator();
}

// Handle user button click
function handleUserClick() {
    showMessage('User functionality coming soon!', 'success');
}

// Show cemetery modal
function showCemeteryModal() {
    const modal = document.getElementById('cemeteryModal');
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

// Close cemetery modal
function closeCemeteryModal() {
    const modal = document.getElementById('cemeteryModal');
    modal.classList.remove('active');
    document.body.style.overflow = 'auto';
}

// Switch tabs
function switchTab(tab) {
    currentTab = tab;
    
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tab}Tab`).classList.add('active');
    
    // Update tab indicator
    updateTabIndicator();
}

// Update tab indicator position
function updateTabIndicator() {
    const indicator = document.querySelector('.tab-indicator');
    if (currentTab === 'register') {
        indicator.classList.add('register');
    } else {
        indicator.classList.remove('register');
    }
}

// Toggle password visibility
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const toggleBtn = input.nextElementSibling.nextElementSibling;
    const icon = toggleBtn.querySelector('i');
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('bi-eye-fill');
        icon.classList.add('bi-eye-slash-fill');
    } else {
        input.type = 'password';
        icon.classList.remove('bi-eye-slash-fill');
        icon.classList.add('bi-eye-fill');
    }
}

// Handle ripple effect
function handleRippleEffect(e) {
    const button = e.target.closest('.btn-primary-custom, .btn-secondary-custom');
    if (!button) return;
    
    const ripple = button.querySelector('.btn-ripple');
    if (!ripple) return;
    
    const rect = button.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = e.clientX - rect.left - size / 2;
    const y = e.clientY - rect.top - size / 2;
    
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';
    
    ripple.classList.remove('ripple');
    void ripple.offsetWidth; // Trigger reflow
    ripple.classList.add('ripple');
}

// Initialize form validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('.auth-form');
    
    forms.forEach(form => {
        form.addEventListener('submit', handleFormSubmit);
        
        // Add input event listeners for real-time validation
        const inputs = form.querySelectorAll('input');
        inputs.forEach(input => {
            input.addEventListener('input', handleInputChange);
            input.addEventListener('blur', handleInputBlur);
        });
    });
}

// Handle form submission
function handleFormSubmit(e) {
    e.preventDefault();
    
    const form = e.target;
    const formData = new FormData(form);
    const formType = form.id.includes('login') ? 'login' : 'register';
    
    // Validate form
    if (!validateForm(form)) {
        return;
    }
    
    // Show loading state
    const submitBtn = form.querySelector('.submit-btn');
    const originalText = submitBtn.querySelector('span').textContent;
    submitBtn.querySelector('span').textContent = 'Processing...';
    submitBtn.disabled = true;
    
    // Simulate API call
    setTimeout(() => {
        // Reset button state
        submitBtn.querySelector('span').textContent = originalText;
        submitBtn.disabled = false;
        
        // Show success message
        const message = formType === 'login' ? 'Login successful!' : 'Registration successful!';
        showMessage(message, 'success');
        
        // Close modal after success
        setTimeout(() => {
            closeCemeteryModal();
        }, 1500);
    }, 2000);
}

// Handle input changes
function handleInputChange(e) {
    const input = e.target;
    const container = input.closest('.input-container');
    
    // Remove error state if input is being corrected
    if (input.classList.contains('error')) {
        input.classList.remove('error');
        removeErrorMessage(container);
    }
}

// Handle input blur
function handleInputBlur(e) {
    const input = e.target;
    validateInput(input);
}

// Validate individual input
function validateInput(input) {
    const container = input.closest('.input-container');
    const value = input.value.trim();
    let isValid = true;
    let errorMessage = '';
    
    // Remove existing error
    input.classList.remove('error');
    removeErrorMessage(container);
    
    // Check if required field is empty
    if (input.required && !value) {
        isValid = false;
        errorMessage = 'This field is required';
    }
    
    // Specific validations
    if (value) {
        switch (input.type) {
            case 'tel':
                if (!/^\+?[\d\s-()]{10,}$/.test(value)) {
                    isValid = false;
                    errorMessage = 'Please enter a valid phone number';
                }
                break;
            case 'password':
                if (value.length < 6) {
                    isValid = false;
                    errorMessage = 'Password must be at least 6 characters';
                }
                break;
        }
        
        // Check password confirmation
        if (input.id === 'confirmPassword') {
            const passwordInput = document.getElementById('registerPassword');
            if (value !== passwordInput.value) {
                isValid = false;
                errorMessage = 'Passwords do not match';
            }
        }
    }
    
    // Show error if validation failed
    if (!isValid) {
        input.classList.add('error');
        showErrorMessage(container, errorMessage);
    }
    
    return isValid;
}

// Validate entire form
function validateForm(form) {
    const inputs = form.querySelectorAll('input[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!validateInput(input)) {
            isValid = false;
        }
    });
    
    return isValid;
}

// Show error message
function showErrorMessage(container, message) {
    removeErrorMessage(container);
    
    const errorElement = document.createElement('div');
    errorElement.className = 'error-message';
    errorElement.textContent = message;
    container.appendChild(errorElement);
}

// Remove error message
function removeErrorMessage(container) {
    const existingError = container.querySelector('.error-message');
    if (existingError) {
        existingError.remove();
    }
}

// Show success/error messages
function showMessage(message, type = 'success') {
    const messageContainer = document.getElementById('messageContainer');
    const messageElement = document.getElementById('message');
    const messageText = document.getElementById('messageText');
    const messageIcon = messageElement.querySelector('i');
    
    // Set message content
    messageText.textContent = message;
    
    // Set message type
    messageElement.className = `message ${type}`;
    
    // Set appropriate icon
    if (type === 'success') {
        messageIcon.className = 'bi bi-check-circle-fill';
    } else if (type === 'error') {
        messageIcon.className = 'bi bi-exclamation-circle-fill';
    }
    
    // Show message
    messageContainer.classList.add('active');
    
    // Hide message after 3 seconds
    setTimeout(() => {
        messageContainer.classList.remove('active');
    }, 3000);
}

// Close modal when clicking outside
document.addEventListener('click', function(e) {
    const modal = document.getElementById('cemeteryModal');
    if (e.target === modal) {
        closeCemeteryModal();
    }
});

// Close modal with Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeCemeteryModal();
    }
});

// Add CSS for error states
const errorStyles = `
    .input-container input.error {
        border-color: #dc3545;
        box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.1);
    }
    
    .error-message {
        position: absolute;
        top: 100%;
        left: 0;
        color: #dc3545;
        font-size: 0.875rem;
        margin-top: 0.25rem;
        animation: fadeIn 0.2s ease-in-out;
    }
    
    .form-group {
        margin-bottom: 2rem;
    }
`;

// Inject error styles
const styleSheet = document.createElement('style');
styleSheet.textContent = errorStyles;
document.head.appendChild(styleSheet);