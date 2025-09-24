// Trainer Dashboard JavaScript

// Notification handling
function showNotificationDetails(notificationElement) {
    const modal = document.getElementById('notificationModal');
    const message = notificationElement.querySelector('.notification-text p').textContent;
    const time = notificationElement.querySelector('.notification-time').textContent;
    const notificationId = notificationElement.dataset.notificationId;

    document.getElementById('notificationMessage').textContent = message;
    document.getElementById('notificationTime').textContent = time;
    modal.dataset.notificationId = notificationId;
    modal.style.display = 'block';
}

function markAsReadAndClose() {
    const modal = document.getElementById('notificationModal');
    const notificationId = modal.dataset.notificationId;

    fetch('/trainer/notifications/mark-read', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ notification_id: notificationId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const notification = document.querySelector(`[data-notification-id="${notificationId}"]`);
            notification.classList.remove('unread');
            
            // Update notification counter
            const counter = document.querySelector('.notification-count');
            if (counter) {
                const count = parseInt(counter.textContent) - 1;
                if (count > 0) {
                    counter.textContent = count;
                } else {
                    counter.remove();
                }
            }
            
            // Close the modal
            modal.style.display = 'none';
        }
    })
    .catch(error => console.error('Error:', error));
}

// Close modal when clicking the close button or outside the modal
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('notificationModal');
    const closeBtn = document.querySelector('.close-modal');

    closeBtn.onclick = function() {
        modal.style.display = 'none';
    }

    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    }
});

// Chat functionality
let currentMemberId = null;
let chatUpdateInterval = null;

function openChat(memberId, memberName) {
    currentMemberId = memberId;
    document.getElementById('chatMemberName').textContent = memberName;
    document.getElementById('chatModal').style.display = 'block';
    loadChatHistory();
    
    // Start periodic updates
    if (chatUpdateInterval) clearInterval(chatUpdateInterval);
    chatUpdateInterval = setInterval(loadChatHistory, 10000); // Update every 10 seconds
}

function loadChatHistory() {
    if (!currentMemberId) return;
    
    fetch(`/trainer/chat/history/${currentMemberId}`)
        .then(response => response.json())
        .then(data => {
            const chatMessages = document.querySelector('.chat-messages');
            chatMessages.innerHTML = '';
            
            data.messages.forEach(message => {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${message.sender_id === currentMemberId ? 'received' : 'sent'}`;
                messageDiv.innerHTML = `
                    <p class="message-content">${message.message}</p>
                    <span class="message-time">${new Date(message.sent_at).toLocaleTimeString()}</span>
                `;
                chatMessages.appendChild(messageDiv);
            });
            
            chatMessages.scrollTop = chatMessages.scrollHeight;
        })
        .catch(error => console.error('Error:', error));
}

function sendMessage() {
    const messageInput = document.querySelector('.chat-input input');
    const message = messageInput.value.trim();
    
    if (!message || !currentMemberId) return;
    
    fetch('/trainer/chat/send', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            member_id: currentMemberId,
            message: message
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            messageInput.value = '';
            loadChatHistory();
        }
    })
    .catch(error => console.error('Error:', error));
}

// Member transfer functionality
function initializeTransfer(memberId, memberName) {
    document.getElementById('transferMemberName').textContent = memberName;
    document.getElementById('transferModal').style.display = 'block';
    document.querySelector('.confirm-transfer').onclick = () => transferMember(memberId);
}

function transferMember(memberId) {
    const newTrainerId = document.getElementById('trainerSelect').value;
    
    fetch('/trainer/member/transfer', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            member_id: memberId,
            new_trainer_id: newTrainerId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Remove member card from the grid
            const memberCard = document.querySelector(`[data-member-id="${memberId}"]`).closest('.member-card');
            memberCard.remove();
            
            // Close modal
            document.getElementById('transferModal').style.display = 'none';
        }
    })
    .catch(error => console.error('Error:', error));
}

// Progress tracking functionality
function initializeProgress(memberId, memberName) {
    document.getElementById('progressMemberName').textContent = memberName;
    document.getElementById('progressModal').style.display = 'block';
    document.querySelector('.save-progress').onclick = () => saveProgress(memberId);
}

function saveProgress(memberId) {
    const notes = document.querySelector('.progress-notes textarea').value;
    const metrics = {
        attendance: document.querySelector('[data-metric="attendance"]').value,
        goals_achieved: document.querySelector('[data-metric="goals"]').value
    };
    
    fetch('/trainer/member/progress', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            member_id: memberId,
            progress_notes: notes,
            metrics: metrics
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Clear form
            document.querySelector('.progress-notes textarea').value = '';
            
            // Close modal
            document.getElementById('progressModal').style.display = 'none';
        }
    })
    .catch(error => console.error('Error:', error));
}

// Search and filter functionality
function searchMembers(searchTerm) {
    const memberCards = document.querySelectorAll('.member-card');
    searchTerm = searchTerm.toLowerCase();
    
    memberCards.forEach(card => {
        const memberName = card.querySelector('h4').textContent.toLowerCase();
        const memberPlan = card.querySelector('.member-plan').textContent.toLowerCase();
        
        if (memberName.includes(searchTerm) || memberPlan.includes(searchTerm)) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

function filterMembers(status) {
    const memberCards = document.querySelectorAll('.member-card');
    
    memberCards.forEach(card => {
        if (status === 'all' || card.dataset.status === status) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

// Profile editing functionality
function openEditProfileModal() {
    document.getElementById('editProfileModal').style.display = 'block';
}

function closeEditProfileModal() {
    document.getElementById('editProfileModal').style.display = 'none';
}

function saveProfileChanges() {
    const specialization = document.getElementById('editSpecialization').value;
    const experience = document.getElementById('editExperience').value;
    const bio = document.getElementById('editBio').value;

    fetch('/trainer/profile/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            specialization: specialization,
            experience_years: experience,
            bio: bio
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update the profile section without page reload
            document.querySelector('.specialization').textContent = specialization;
            document.querySelector('.experience').textContent = experience + ' years experience';
            document.querySelector('.bio p').textContent = bio;
            closeEditProfileModal();
        }
    })
    .catch(error => console.error('Error:', error));
}

// Initialize event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Initialize notifications
    const notificationsHeader = document.querySelector('.notifications-header');
    const notificationsList = document.querySelector('.notifications-list');

    if (notificationsHeader && notificationsList) {
        notificationsHeader.addEventListener('click', function() {
            notificationsList.classList.toggle('active');
            
            if (notificationsList.classList.contains('active')) {
                notificationsList.style.maxHeight = notificationsList.scrollHeight + 'px';
            } else {
                notificationsList.style.maxHeight = '0';
            }
        });
    }

    // Initialize edit profile modal
    const editProfileModal = document.getElementById('editProfileModal');
    const closeEditProfileButtons = editProfileModal.querySelectorAll('.close-modal, .cancel-edit');

    closeEditProfileButtons.forEach(button => {
        button.addEventListener('click', closeEditProfileModal);
    });

    // Close edit profile modal when clicking outside
    editProfileModal.addEventListener('click', function(e) {
        if (e.target === this) {
            closeEditProfileModal();
        }
    });
    }

    // Initialize modals
    const modals = document.querySelectorAll('.modal'),
    const closeButtons = document.querySelectorAll('.close-modal');
    const chatButtons = document.querySelectorAll('.chat-btn');
    const chatModal = document.getElementById('chatModal');
    const chatMemberName = document.getElementById('chatMemberName');
    const transferButtons = document.querySelectorAll('.transfer-btn');
    const transferModal = document.getElementById('transferModal');
    const transferMemberName = document.getElementById('transferMemberName');
    const progressButtons = document.querySelectorAll('.progress-btn');
    const progressModal = document.getElementById('progressModal');
    const progressMemberName = document.getElementById('progressMemberName');

    // Add event listeners for modal closing
    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            button.closest('.modal').style.display = 'none';
            if (chatUpdateInterval) {
                clearInterval(chatUpdateInterval);
                chatUpdateInterval = null;
            }
        });
    });

    // Add event listeners for notifications
    const notificationsToggle = document.getElementById('notificationsToggle');
    const notificationsList = document.getElementById('notificationsList');

    notificationsToggle.addEventListener('click', () => {
        notificationsToggle.classList.toggle('active');
        notificationsList.style.display = notificationsList.style.display === 'none' ? 'block' : 'none';
    });

    // Initially hide the notifications list
    notificationsList.style.display = 'none';

    document.querySelectorAll('.mark-read-btn').forEach(button => {
        button.addEventListener('click', () => {
            const notificationId = button.dataset.notificationId;
            markNotificationAsRead(notificationId);
        });
    });

    // Add event listeners for chat buttons
    chatButtons.forEach(button => {
        button.addEventListener('click', () => {
            const memberId = button.closest('.member-card').querySelector('.member-actions').dataset.memberId;
            const memberName = button.closest('.member-card').querySelector('h4').textContent;
            chatModal.style.display = 'block';
            openChat(memberId, memberName);
        });
    });

    // Add event listener for chat send button
    document.querySelector('.send-message').addEventListener('click', sendMessage);
    document.querySelector('.chat-input input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // Add event listeners for transfer buttons
    transferButtons.forEach(button => {
        button.addEventListener('click', () => {
            const memberId = button.closest('.member-card').querySelector('.member-actions').dataset.memberId;
            const memberName = button.closest('.member-card').querySelector('h4').textContent;
            transferModal.style.display = 'block';
            initializeTransfer(memberId, memberName);
        });
    });

    // Add event listeners for progress buttons
    progressButtons.forEach(button => {
        button.addEventListener('click', () => {
            const memberId = button.closest('.member-card').querySelector('.member-actions').dataset.memberId;
            const memberName = button.closest('.member-card').querySelector('h4').textContent;
            progressModal.style.display = 'block';
            initializeProgress(memberId, memberName);
        });
    });

    // Add event listeners for search and filter
    document.querySelector('.search-input').addEventListener('input', (e) => {
        searchMembers(e.target.value);
    });

    document.querySelector('.filter-select').addEventListener('change', (e) => {
        filterMembers(e.target.value);
    });

    // Member Card Click Handler
    const memberCards = document.querySelectorAll('.member-card');
    const memberDetailsModal = document.getElementById('memberDetailsModal');

    memberCards.forEach(card => {
        card.addEventListener('click', function(e) {
            // Prevent triggering when clicking action buttons
            if (e.target.closest('.member-actions')) {
                e.stopPropagation();
                return;
            }
        });
    });

    function showMemberDetails(memberId) {
        // TODO: Replace with actual API call to get member details
        const mockMemberData = {
            image: document.querySelector(`[data-member-id="${memberId}"] img`).src,
            name: document.querySelector(`[data-member-id="${memberId}"] h4`).textContent,
            plan: document.querySelector(`[data-member-id="${memberId}"] .member-plan`).textContent,
            status: document.querySelector(`[data-member-id="${memberId}"]`).dataset.status,
            height: '5\'10"',
            weight: '75 kg',
            bmi: '23.5',
            age: '28',
            health: 'No known health conditions',
            goals: [
                'Lose 5kg in 3 months',
                'Improve cardiovascular endurance', 
                'Build core strength'
            ],
            workout: 'Full body workout 3 times per week'
        };

        // Update modal content
        document.getElementById('memberDetailImage').src = mockMemberData.image;
        document.getElementById('memberDetailName').textContent = mockMemberData.name;
        document.getElementById('memberDetailPlan').textContent = mockMemberData.plan;
        document.getElementById('memberDetailStatus').textContent = mockMemberData.status;
        document.getElementById('memberDetailHeight').textContent = mockMemberData.height;
        document.getElementById('memberDetailWeight').textContent = mockMemberData.weight;
        document.getElementById('memberDetailBMI').textContent = mockMemberData.bmi;
        document.getElementById('memberDetailAge').textContent = mockMemberData.age;
        document.getElementById('memberDetailHealth').textContent = mockMemberData.health;

        // Update goals list
        const goalsList = document.getElementById('memberDetailGoals');
        goalsList.innerHTML = mockMemberData.goals.map(goal => `<li>${goal}</li>`).join('');

        // Update workout plan
        document.getElementById('memberDetailWorkout').textContent = mockMemberData.workout;

        // Show modal
        memberDetailsModal.style.display = 'block';
    }

    // Close modal when clicking outside
    memberDetailsModal.addEventListener('click', function(e) {
        if (e.target === this) {
            this.style.display = 'none';
        }
    });

    // Close modal when clicking close button
    memberDetailsModal.querySelector('.close-modal').addEventListener('click', function() {
        memberDetailsModal.style.display = 'none';
    });

    // Close modals when clicking outside
    window.addEventListener('click', (e) => {
        modals.forEach(modal => {
            if (e.target === modal) {
                modal.style.display = 'none';
                if (chatUpdateInterval) {
                    clearInterval(chatUpdateInterval);
                    chatUpdateInterval = null;
                }
                // Remove active class from buttons
                document.querySelectorAll('.chat-btn.active, .progress-btn.active, .transfer-btn.active')
                    .forEach(btn => btn.classList.remove('active'));
            }
        });
    });
            const modal = button.closest('.modal');
            modal.style.display = 'none';
            if (chatUpdateInterval) {
                clearInterval(chatUpdateInterval);
                chatUpdateInterval = null;
            }
            document.querySelector('.chat-btn.active, .progress-btn.active, .transfer-btn.active')?.classList.remove('active');
        ;
    ;

    // Close modal when clicking outside
    window.addEventListener('click', (event) => {
        modals.forEach(modal => {
            if (event.target === modal) {
                modal.style.display = 'none';
                if (chatUpdateInterval) {
                    clearInterval(chatUpdateInterval);
                    chatUpdateInterval = null;
                }
                document.querySelector('.chat-btn.active, .progress-btn.active, .transfer-btn.active')?.classList.remove('active');
            }
        });
    });

    // Initialize search and filter
    const searchInput = document.querySelector('.search-input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => searchMembers(e.target.value));
    }

    const filterSelect = document.querySelector('.filter-select');
    if (filterSelect) {
        filterSelect.addEventListener('change', (e) => filterMembers(e.target.value));
    }

    // Initialize chat message sending
    const sendButton = document.querySelector('.send-message');
    if (sendButton) {
        sendButton.addEventListener('click', sendMessage);
    }

    const chatInput = document.querySelector('.chat-input input');
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
;