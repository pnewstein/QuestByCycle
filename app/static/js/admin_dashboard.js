// Admin dashboard specific functions
document.addEventListener("DOMContentLoaded", function() {
    const userId = document.body.getAttribute('data-user-id');
    const allSubmissionsButton = document.getElementById('allSubmissionsButton');
    if (allSubmissionsButton) {
        allSubmissionsButton.addEventListener('click', function() {
            if (userId !== 'none') {
                showAllSubmissionsModal(userId);
            } else {
                console.log('No user ID found or user not logged in');
            }
        });
    }
});
