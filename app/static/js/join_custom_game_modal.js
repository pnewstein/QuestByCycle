// Join custom game modal management functions
function closeJoinCustomGameModal(){
    const joinCustomGameModal = document.getElementById('joinCustomGameModal');
    if (!joinCustomGameModal) {
        console.error('Join Custom Game modal container not found');
        return;  // Exit if no container is found
    }
    joinCustomGameModal.style.display = 'none';
    document.body.classList.remove('body-no-scroll');
}
