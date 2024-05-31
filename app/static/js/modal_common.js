// Common modal management functions
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'block';
        document.body.classList.add('body-no-scroll'); // Optional: prevent scrolling when modal is open
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.style.display = 'none';
    document.body.style.overflow = 'auto'; // Re-enable scrolling
}

// Reset all modal content and settings to initial state
function resetModalContent() {
    const twitterLink = document.getElementById('twitterLink');
    if (twitterLink) {
        twitterLink.style.display = 'none';
        twitterLink.href = '#'; // Reset to default or placeholder link
    }

    const modalTaskActions = document.getElementById('modalTaskActions');
    if (modalTaskActions) {
        modalTaskActions.innerHTML = '';
    }
    document.querySelectorAll('[id^="verifyButton-"]').forEach(button => button.remove());
    document.querySelectorAll('[id^="verifyTaskForm-"]').forEach(form => form.remove());
    document.body.classList.remove('body-no-scroll');
}

function closeAllModals(id) {
    switch(id) {
        case 'submissionDetailModal':
            closeSubmissionDetailModal();
            break;
        case 'mySubmissionsModal':
            closeMySubmissionsModal();
            break;
        case 'allSubmissionsModal':
            closeAllSubmissionsModal();
            break;
        case 'taskDetailModal':
            closeTaskDetailModal();
            break;
        case 'joinCustomGameModal':
            closeJoinCustomGameModal();
            break;
        case 'userProfileModal':
            closeUserProfileModal();
            break;
        case 'leaderboardModal':
            closeLeaderboardModal();
            break;
        case 'contactModal':
            closeContactModal();
            break;
        case 'editCarouselModal':
            closeEditCarouselModal();
            break;
    }
}

// Enhanced window click handling for modal closure
window.onclick = function(event) {
    if (event.target.className.includes('modal')) {
        closeAllModals(event.target.id);
    }
}
