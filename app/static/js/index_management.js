function refreshCSRFToken() {
    fetch('/refresh-csrf')
        .then(response => response.json())
        .then(data => {
            document.querySelector('meta[name="csrf-token"]').setAttribute('content', data.csrf_token);
        })
        .catch(error => console.error('Error refreshing CSRF token:', error));
}

// Refresh the CSRF token every 15 minutes (900000 milliseconds)
setInterval(refreshCSRFToken, 900000);

function updateMeter(gameId) {
    fetch(`games/get_game_points/${gameId}`)
        .then(response => response.json())
        .then(data => {
            const totalPoints = data.total_game_points;
            const gameGoal = data.game_goal;
            const remainingPoints = gameGoal - totalPoints;
            const heightPercentage = Math.min((totalPoints / gameGoal) * 100, 100);
            document.getElementById('meterBar').style.height = heightPercentage + '%';
            document.documentElement.style.setProperty('--meter-fill-height', heightPercentage + '%');

            document.querySelector('.meter-label').innerText = `Remaining Reduction: ${remainingPoints} / ${gameGoal}`;
        })
        .catch(err => console.error('Failed to update meter:', err));
}

function previewFile() {
    var preview = document.getElementById('profileImageDisplay');
    var file = document.querySelector('input[type=file]').files[0];
    var reader = new FileReader();

    reader.addEventListener("load", function () {
        preview.src = reader.result;
    }, false);

    if (file) {
        reader.readAsDataURL(file);
    }
}

function likeMessage(messageId) {
    const likeButton = document.getElementById(`like-button-${messageId}`);
    const likeCount = document.getElementById(`like-count-${messageId}`);
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    // Immediately disable the button to prevent multiple clicks
    likeButton.disabled = true;

    fetch(`/like-message/${messageId}`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update like count
            likeCount.innerText = data.new_like_count;
            
            // Update button text and style as needed
            likeButton.innerText = 'Liked';
            
            // Keep the button disabled to reflect that the like action is complete
            likeButton.disabled = true;
        } else {
            // Optional: Handle cases where the like wasn't successful or was a duplicate
            // For duplicate likes, the button can remain disabled or provide feedback
        }
    })
    .catch(error => {
        console.error('Error:', error);
        // Re-enable the button in case of error to allow retrying
        likeButton.disabled = false;
    });
}

function likeQuest(questId) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    const likeButton = document.getElementById(`like-button-${questId}`);
    const likeCountSpan = document.getElementById(`like-count-${questId}`);

    // Check if the button is already disabled to prevent multiple submissions
    if (likeButton.disabled) {
        return;
    }

    // Immediately disable the button to prevent multiple clicks
    likeButton.disabled = true;

    fetch(`/like_quest/${questId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken,
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            likeButton.textContent = 'Liked';
            let likeCount = parseInt(likeCountSpan.textContent) || 0;
            likeCountSpan.textContent = likeCount + 1;
            likeButton.classList.add('liked-button-style');
        } else {
            // Handle already liked status
            likeButton.textContent = 'Liked';
            alert('Already liked');
        }
    })
    .catch(error => {
        console.error('Error liking the quest:', error);
        likeButton.disabled = false;  // Re-enable the button in case of error to allow retrying
    });
}

// New function to update the game name in the header using the game ID from the hidden element
function updateGameName() {
    const gameHolder = document.getElementById("game_IdHolder");
    if (!gameHolder) return;

    const gameId = gameHolder.getAttribute("data-game-id");
    const gameNameHeader = document.getElementById("gameNameHeader");

    if (gameId && gameNameHeader) {
        fetch(`/games/get_game/${gameId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error("Network response was not ok");
                }
                return response.json();
            })
            .then(data => {
                if (data.name) {
                    gameNameHeader.textContent = data.name;
                } else {
                    gameNameHeader.textContent = "Game Not Found";
                }
            })
            .catch(error => {
                console.error("Error retrieving game name:", error);
                gameNameHeader.textContent = "Error Loading Game";
            });
    }
}

document.addEventListener("DOMContentLoaded", function() {
    const leaderboardButton = document.getElementById('leaderboardButton');
    if (leaderboardButton) {
        leaderboardButton.addEventListener('click', function() {
            const gameId = this.getAttribute('data-game-id');
            showLeaderboardModal(gameId);
            updateMeter(gameId);
        });
    }

    const submissionsButton = document.getElementById('submissionsButton');
    if (submissionsButton) {
        submissionsButton.addEventListener('click', function() {
            if (currentUserId !== 'none') {
                showMySubmissionsModal(currentUserId);
            }
        });
    }

    const contactForm = document.getElementById('contactForm');
    if (contactForm) {
        contactForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const formData = new FormData(contactForm);
            const request = new XMLHttpRequest();
            request.open('POST', contactForm.action, true);
            request.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            request.onload = function() {
                if (request.status >= 200 && request.status < 400) {
                    const response = JSON.parse(request.responseText);
                    if (response.success) {
                        alert('Your message has been sent successfully.');
                        closeContactModal();
                    } else {
                        alert('Failed to send your message. Please try again.');
                    }
                } else {
                    alert('Failed to send your message. Please try again.');
                }
            };
            request.onerror = function() {
                alert('Failed to send your message. Please try again.');
            };
            request.send(formData);
        });
    }

    // Call the new function to update the game name in the header
    updateGameName();
});
