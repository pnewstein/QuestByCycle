// User profile modal management functions
function showUserProfileModal(userId) {
    fetch(`/profile/${userId}`)
        .then(response => response.json())
        .then(data => {
            const userProfileDetails = document.getElementById('userProfileDetails');
            if (!userProfileDetails) {
                console.error('User profile details container not found');
                return;
            }

            userProfileDetails.innerHTML = `
                <header class="profile-header text-center py-5 mb-4 position-relative">
                    ${data.user.profile_picture ? `
                        <div class="profile-picture-container position-relative mx-auto mb-3">
                            <img src="/static/${data.user.profile_picture}" alt="Profile Picture" class="profile-picture rounded-circle shadow-lg border border-white border-4">
                            <div class="profile-picture-overlay"></div>
                        </div>` : ''}
                    <div class="header-bg position-absolute w-100 h-100 top-0 start-0"></div>
                    <div class="header-content position-relative z-index-1">
                        <h1 class="display-4 text-white font-weight-bold">${data.user.display_name || data.user.username}</h1>
                        <p class="user-interests text-white"><strong>Interests:</strong> ${data.user.interests}</p>
                    </div>
                    <div class="header-decorative-elements position-absolute w-100 h-100 top-0 start-0">
                        <div class="decorative-circle"></div>
                        <div class="decorative-triangle"></div>
                    </div>
                </header>
                <div class="row">
                    <div class="col-md-8">
                        <ul class="nav nav-tabs" id="profileTabs" role="tablist">
                            <li class="nav-item" role="presentation">
                                <a class="nav-link active" id="badges-earned-tab" data-toggle="tab" href="#badges-earned" role="tab" aria-controls="badges-earned" aria-selected="true">Badges Earned</a>
                            </li>
                            <li class="nav-item" role="presentation">
                                <a class="nav-link" id="games-participated-tab" data-toggle="tab" href="#games-participated" role="tab" aria-controls="games-participated" aria-selected="false">Games Participated</a>
                            </li>
                            <li class="nav-item" role="presentation">
                                <a class="nav-link" id="task-submissions-tab" data-toggle="tab" href="#task-submissions" role="tab" aria-controls="task-submissions" aria-selected="false">Task Submissions</a>
                            </li>
                        </ul>
                        <div class="tab-content" id="profileTabsContent">
                            <div class="tab-pane fade show active" id="badges-earned" role="tabpanel" aria-labelledby="badges-earned-tab">
                                <section class="badges-earned mb-4">
                                    <h2 class="h2">Badges Earned</h2>
                                    <div class="badges-container row">
                                        ${data.user.badges.map(badge => `
                                            <div class="badge-item col-md-4 d-flex flex-column align-items-center text-center p-3">
                                                <img src="/static/images/badge_images/${badge.image}" alt="${badge.name}" class="badge-icon mb-2">
                                                <h3 class="h5">${badge.name}</h3>
                                                <p>${badge.description}</p>
                                                <p><strong>Category:</strong> ${badge.category}</p>
                                            </div>`).join('') || '<p>No badges earned yet.</p>'}
                                    </div>
                                </section>
                            </div>
                            <div class="tab-pane fade" id="games-participated" role="tabpanel" aria-labelledby="games-participated-tab">
                                <section class="games-participated mb-4">
                                    <h2 class="h2">Games Participated</h2>
                                    <div class="games-container row">
                                        ${data.participated_games.map(game => `
                                            <div class="game-item col-md-6 p-3">
                                                <h3 class="h5">${game.title}</h3>
                                                <p>${game.description}</p>
                                                <p><strong>Start Date:</strong> ${game.start_date}</p>
                                                <p><strong>End Date:</strong> ${game.end_date}</p>
                                            </div>`).join('') || '<p>No games participated in yet.</p>'}
                                    </div>
                                </section>
                            </div>
                            <div class="tab-pane fade" id="task-submissions" role="tabpanel" aria-labelledby="task-submissions-tab">
                                <section class="task-submissions mb-4">
                                    <h2 class="h2">Task Submissions</h2>
                                    <div class="submissions-container row">
                                        ${data.task_submissions.map(submission => `
                                            <div class="submission-item col-md-6 p-3">
                                                ${submission.image_url ? `<img src="${submission.image_url}" alt="Submission Image" class="img-fluid mb-2">` : ''}
                                                <p><strong>Task:</strong> ${submission.task.title}</p>
                                                <p>${submission.comment}</p>
                                                <p><strong>Submitted At:</strong> ${submission.timestamp}</p>
                                                ${submission.twitter_url ? `<p><a href="${submission.twitter_url}" target="_blank" class="blue_button">View on Twitter</a></p>` : ''}
                                                ${submission.fb_url ? `<p><a href="${submission.fb_url}" target="_blank" class="blue_button">View on Facebook</a></p>` : ''}
                                            </div>`).join('') || '<p>No task submissions yet.</p>'}
                                    </div>
                                </section>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <section class="message-board mb-4">
                            <h2 class="h2">Message Board</h2>
                            <p>Coming soon...</p>
                        </section>
                    </div>
                </div>
            `;
            openModal('userProfileModal');
        })
        .catch(error => {
            console.error('Failed to load user profile:', error);
            alert('Could not load user profile. Please try again.');
        });
}

function toggleEditProfile() {
    var form = document.getElementById('editProfileForm');
    var view = document.getElementById('profileView');
    var button = document.getElementById('editProfileBtn');

    if (form.style.display === 'none' || form.style.display === '') {
        form.style.display = 'block';
        view.style.display = 'none';
        button.textContent = 'Cancel Edit';
    } else {
        form.style.display = 'none';
        view.style.display = 'hidden';
        button.textContent = 'Edit Profile';
    }
}

function closeUserProfileModal() {
    const userProfileModal = document.getElementById('userProfileModal');
    if (!userProfileModal) {
        console.error('User profile modal container not found');
        return;  // Exit if no container is found
    }
    userProfileModal.style.display = 'none';
    document.body.classList.remove('body-no-scroll');
}
