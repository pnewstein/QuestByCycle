// Contact modal management functions
function closeContactModal() {
    const contactModal = document.getElementById('contactModal');
    if (!contactModal) {
        console.error('Leaderboard modal container not found');
        return;  // Exit if no container is found
    }
    contactModal.style.display = 'none';
    document.body.classList.remove('body-no-scroll');

}