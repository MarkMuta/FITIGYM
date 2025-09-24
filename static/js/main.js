// Password visibility toggle
function togglePasswordVisibility(inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(iconId);
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}

// Payment processing
function processPayment() {
    const selectedMethod = document.querySelector('input[name="payment_method"]:checked').value;
    alert(`Processing payment via ${selectedMethod}. This feature will be implemented soon!`);
}

// Trainer dashboard functionality
document.addEventListener('DOMContentLoaded', function() {
    // Progress view buttons
    const progressButtons = document.querySelectorAll('.view-progress-btn');
    if (progressButtons) {
        progressButtons.forEach(button => {
            button.addEventListener('click', function() {
                const memberCard = this.closest('.member-card');
                const memberName = memberCard.querySelector('.member-name').textContent;
                window.location.href = `/member-progress/${memberCard.dataset.memberId}`;
            });
        });
    }

    // Message buttons
    const messageButtons = document.querySelectorAll('.message-btn');
    if (messageButtons) {
        messageButtons.forEach(button => {
            button.addEventListener('click', function() {
                const memberCard = this.closest('.member-card');
                const memberName = memberCard.querySelector('.member-name').textContent;
                window.location.href = `/chat/${memberCard.dataset.memberId}`;
            });
        });
    }

    // Schedule time slots
    const timeSlots = document.querySelectorAll('.time-slot');
    if (timeSlots) {
        timeSlots.forEach(slot => {
            slot.addEventListener('click', function() {
                this.classList.toggle('selected');
            });
        });
    }
});