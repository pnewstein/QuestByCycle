function initializeQuill() {
    const editorElement = document.getElementById('editor');
    if (!editorElement) {
        console.error('Quill editor container not found');
        return;
    }

    const quill = new Quill('#editor', {
        theme: 'snow',
        placeholder: 'Write your message here...',
        modules: {
            toolbar: [
                [{ 'header': [1, 2, false] }],
                ['bold', 'italic', 'underline'],
                ['link', 'blockquote', 'code-block'],
                [{ 'list': 'ordered' }, { 'list': 'bullet' }]
            ]
        }
    });

    const form = document.getElementById('messageForm');
    form.onsubmit = function(event) {
        event.preventDefault();  // Prevent the default form submission
        const messageContent = document.querySelector('input[name=content]');
        messageContent.value = quill.root.innerHTML;
        postMessage(form);
    };
}

function postMessage(form) {
    const formData = new FormData(form);
    const messageContent = formData.get('content');

    fetch(`/profile/${form.dataset.userid}/messages`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        },
        body: JSON.stringify({ content: messageContent })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(`Error: ${data.error}`);
        } else {
            alert('Message posted successfully.');
            showUserProfileModal(form.dataset.userid);  // Reload profile details to reflect changes
        }
    })
    .catch(error => {
        console.error('Error posting message:', error);
        alert('Failed to post message. Please try again.');
    });
}

function showUserProfileModal(userId) {
    fetch(`/profile/${userId}`)
        .then(response => response.json())
        .then(data => {
            if (!data.riding_preferences_choices) {
                console.error('Riding preferences choices data is missing.');
                return;
            }

            const userProfileDetails = document.getElementById('userProfileDetails');
            if (!userProfileDetails) {
                console.error('User profile details container not found');
                return;
            }

            const isCurrentUser = data.current_user_id === data.user.id;

            const messagesHtml = buildMessageTree(data.profile_messages, null, isCurrentUser, data.current_user_id, userId, 0);

            userProfileDetails.innerHTML = `
                <header class="profile-header text-center py-5 mb-4 position-relative">
                    ${data.user.profile_picture ? `
                        <div class="profile-picture-container position-relative mx-auto mb-3">
                            <img src="/static/${data.user.profile_picture}" alt="Profile Picture" class="profile-picture rounded-circle shadow-lg border border-white border-4">
                            ${isCurrentUser ? `<input type="file" id="profilePictureInput" name="profile_picture" accept="image/*">` : ''}
                        </div>` : ''}
                    <div class="header-bg position-absolute w-100 h-100 top-0 start-0"></div>
                    <div class="header-content position-relative z-index-1">
                        <h1 class="display-4 text-white font-weight-bold">${data.user.display_name || data.user.username}'s Profile</h1>
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
                                <a class="nav-link active" id="profile-tab" data-toggle="tab" href="#profile" role="tab" aria-controls="profile" aria-selected="true">Profile</a>
                            </li>
                            <li class="nav-item" role="presentation">
                                <a class="nav-link" id="badges-earned-tab" data-toggle="tab" href="#badges-earned" role="tab" aria-controls="badges-earned" aria-selected="false">Badges Earned</a>
                            </li>
                            <li class="nav-item" role="presentation">
                                <a class="nav-link" id="games-participated-tab" data-toggle="tab" href="#games-participated" role="tab" aria-controls="games-participated" aria-selected="false">Games Participated</a>
                            </li>
                            <li class="nav-item" role="presentation">
                                <a class="nav-link" id="task-submissions-tab" data-toggle="tab" href="#task-submissions" role="tab" aria-controls="task-submissions" aria-selected="false">Task Submissions</a>
                            </li>
                        </ul>
                        <div class="tab-content" id="profileTabsContent">
                            <div class="tab-pane fade show active" id="profile" role="tabpanel" aria-labelledby="profile-tab">
                                <section class="profile mb-4">
                                    ${isCurrentUser ? `
                                        <form id="editProfileForm">
                                            <div class="form-group">
                                                <label for="displayName">Display Name:</label>
                                                <input type="text" class="form-control" id="displayName" name="display_name" value="${data.user.display_name || ''}">
                                            </div>
                                            <div class="form-group">
                                                <label for="ageGroup">Age Group:</label>
                                                <select class="form-control" id="ageGroup" name="age_group">
                                                    <option value="teen" ${data.user.age_group === 'teen' ? 'selected' : ''}>Teen</option>
                                                    <option value="adult" ${data.user.age_group === 'adult' ? 'selected' : ''}>Adult</option>
                                                    <option value="senior" ${data.user.age_group === 'senior' ? 'selected' : ''}>Senior</option>
                                                </select>
                                            </div>
                                            <div class="form-group">
                                                <label for="interests">Interests:</label>
                                                <textarea class="form-control" id="interests" name="interests">${data.user.interests || ''}</textarea>
                                            </div>
                                            <div class="form-group-1">
                                                <label for="ridingPreferences"><b>Riding Preferences:</b></label>
                                                <div id="ridingPreferences">
                                                    ${data.riding_preferences_choices.map((choice, index) => `
                                                        <div class="form-check">
                                                            <input type="checkbox" class="form-check-input" id="ridingPref-${index}" name="riding_preferences" value="${choice[0]}" ${data.user.riding_preferences.includes(choice[0]) ? 'checked' : ''}>
                                                            <label class="form-check-label" for="ridingPref-${index}">${choice[1]}</label>
                                                        </div>
                                                    `).join('')}
                                                </div>
                                            </div>
                                            <div class="form-group">
                                                <label for="rideDescription">Describe the type of riding you like to do:</label>
                                                <textarea class="form-control" id="rideDescription" name="ride_description">${data.user.ride_description || ''}</textarea>
                                            </div>
                                            <div class="form-group">
                                                <label for="bikePicture">Upload Your Bicycle Picture:</label>
                                                <input type="file" class="form-control" id="bikePicture" name="bike_picture" accept="image/*">
                                            </div>
                                            <div class="form-group">
                                                <label for="bikePicturePreview">Current Bicycle Picture:</label>
                                                <img src="/static/${data.user.bike_picture}" id="bikePicturePreview" alt="Bicycle Picture" class="img-fluid">
                                            </div>
                                            <div class="form-group">
                                                <label for="bikeDescription">Bicycle Description:</label>
                                                <textarea class="form-control" id="bikeDescription" name="bike_description">${data.user.bike_description || ''}</textarea>
                                            </div>
                                            <div class="form-group-1 form-check">
                                                <input type="checkbox" class="form-check-input" id="uploadToSocials" name="upload_to_socials" ${data.user.upload_to_socials ? 'checked' : ''}>
                                                <label class="form-check-label" for="uploadToSocials">Upload Activities to Social Media</label>
                                            </div>
                                            <div class="form-group-1 form-check">
                                                <input type="checkbox" class="form-check-input" id="showCarbonGame" name="show_carbon_game" ${data.user.show_carbon_game ? 'checked' : ''}>
                                                <label class="form-check-label" for="showCarbonGame">Show Carbon Reduction Game</label>
                                            </div>
                                            <button type="button" class="btn btn-primary" onclick="saveProfile(${userId})">Save</button>

                                        </form>` : `
                                        <p><strong>Display Name:</strong> ${data.user.display_name || ''}</p>
                                        <p><strong>Age Group:</strong> ${data.user.age_group || ''}</p>
                                        <p><strong>Interests:</strong> ${data.user.interests || ''}</p>
                                        <p><strong>Riding Preferences:</strong> ${data.user.riding_preferences.join(', ')}</p>
                                        <p><strong>Ride Description:</strong> ${data.user.ride_description || ''}</p>
                                        ${data.user.bike_picture ? `
                                            <div class="form-group">
                                                <label for="bikePicture">Your Bicycle Picture:</label>
                                                <img src="${data.user.bike_picture}" alt="Bicycle Picture" class="img-fluid">
                                            </div>` : ''}
                                        <p><strong>Bicycle Description:</strong> ${data.user.bike_description || ''}</p>
                                        <!-- Only show these fields to the current user -->
                                        ${isCurrentUser ? `
                                        <p><strong>Uploads to Social Media:</strong> ${data.user.upload_to_socials ? 'Yes' : 'No'}</p>
                                        <p><strong>Shows Carbon Reduction Game:</strong> ${data.user.show_carbon_game ? 'Yes' : 'No'}</p>
                                        ` : ''}
                                    `}
                                </section>
                            </div>
                            <div class="tab-pane fade" id="badges-earned" role="tabpanel" aria-labelledby="badges-earned-tab">
                                <section class="badges-earned mb-4">
                                    <h2 class="h2">Badges Earned</h2>
                                    <div class="badges-container row">
                                        ${data.user.badges && data.user.badges.length > 0 ? data.user.badges.map(badge => `
                                            <div class="badge-item col-md-4 d-flex flex-column align-items-center text-center p-3">
                                                <img src="/static/images/badge_images/${badge.image}" alt="${badge.name}" class="badge-icon mb-2">
                                                <h3 class="h5">${badge.name}</h3>
                                                <p>${badge.description}</p>
                                                <p><strong>Category:</strong> ${badge.category}</p>
                                            </div>`).join('') : '<p>No badges earned yet.</p>'}
                                    </div>
                                </section>
                            </div>
                            <div class="tab-pane fade" id="games-participated" role="tabpanel" aria-labelledby="games-participated-tab">
                                <section class="games-participated mb-4">
                                    <h2 class="h2">Games Participated</h2>
                                    <div class="games-container row">
                                        ${data.participated_games && data.participated_games.length > 0 ? data.participated_games.map(game => `
                                            <div class="game-item col-md-6 p-3">
                                                <h3 class="h5">${game.title}</h3>
                                                <p>${game.description}</p>
                                                <p><strong>Start Date:</strong> ${game.start_date}</p>
                                                <p><strong>End Date:</strong> ${game.end_date}</p>
                                            </div>`).join('') : '<p>No games participated in yet.</p>'}
                                    </div>
                                </section>
                            </div>
                            <div class="tab-pane fade" id="task-submissions" role="tabpanel" aria-labelledby="task-submissions-tab">
                                <section class="task-submissions mb-4">
                                    <h2 class="h2">Task Submissions</h2>
                                    <div class="submissions-container row">
                                        ${data.task_submissions && data.task_submissions.length > 0 ? data.task_submissions.map(submission => `
                                            <div class="submission-item col-md-6 p-3">
                                                ${submission.image_url ? `<img src="${submission.image_url}" alt="Submission Image" class="img-fluid mb-2">` : ''}
                                                <p><strong>Task:</strong> ${submission.task.title}</p>
                                                <p>${submission.comment}</p>
                                                <p><strong>Submitted At:</strong> ${submission.timestamp}</p>
                                                ${submission.twitter_url ? `<p><a href="${submission.twitter_url}" target="_blank" class="blue_button">View on Twitter</a></p>` : ''}
                                                ${submission.fb_url ? `<p><a href="${submission.fb_url}" target="_blank" class="blue_button">View on Facebook</a></p>` : ''}
                                                ${submission.instagram_url ? `<p><a href="${submission.instagram_url}" target="_blank" class="blue_button">View on Instagram</a></p>` : ''}
                                                ${isCurrentUser ? `<button class="btn btn-danger" onclick="deleteSubmission(${submission.id}, 'profileSubmissions', ${data.user.id})">Delete</button>` : ''}
                                            </div>`).join('') : '<p>No task submissions yet.</p>'}
                                    </div>
                                </section>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <section class="message-board mb-4">
                            <h2 class="h2">Message Board</h2>
                            <form id="messageForm" data-userid="${userId}">
                                <div class="form-group">
                                    <div id="editor" class="form-control" style="min-height: 70px;"></div>
                                    <input type="hidden" id="messageContent" name="content">
                                </div>
                                <button type="submit" class="btn btn-primary">Post</button>
                            </form>
                            <ul class="list-group" id="messageBoard">
                                ${messagesHtml}
                            </ul>
                        </section>
                    </div>
                </div>
            `;
            initializeQuill();  // Initialize Quill for all profiles
            openModal('userProfileModal');
        })
        .catch(error => {
            console.error('Failed to load user profile:', error);
            alert('Could not load user profile. Please try again.');
        });
}

function saveProfile(userId) {
    const form = document.getElementById('editProfileForm');
    const formData = new FormData(form);

    // Append bicycle picture to FormData if it exists
    const bikePictureInput = document.getElementById('bikePicture');
    if (bikePictureInput.files.length > 0) {
        formData.append('bike_picture', bikePictureInput.files[0]);
    }

    // Collect riding preferences from checkboxes
    const ridingPreferences = [];
    form.querySelectorAll('input[name="riding_preferences"]:checked').forEach((checkbox) => {
        ridingPreferences.push(checkbox.value);
    });

    formData.delete('riding_preferences');
    ridingPreferences.forEach((preference) => {
        formData.append('riding_preferences', preference);
    });

    // Debug: Print form data to the console
    console.log('Form data before submission:');
    formData.forEach((value, key) => {
        console.log(`${key}: ${value}`);
    });

    fetch(`/profile/${userId}/edit`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            console.error('Server error:', data.error);
            alert(`Error: ${data.error}`);
        } else {
            console.log('Profile updated successfully:', data);
            alert('Profile updated successfully.');
            showUserProfileModal(userId);  // Reload profile details to reflect changes
        }
    })
    .catch(error => {
        console.error('Error updating profile:', error);
        alert('Failed to update profile. Please try again.');
    });
}


function buildMessageTree(messages, parentId, isCurrentUser, currentUserId, profileUserId, depth) {
    if (depth > 3) return '';  // Limit replies to a depth of 3

    const nestedMessages = messages.filter(message => message.parent_id === parentId)
                                   .map(message => {
        const replies = buildMessageTree(messages, message.id, isCurrentUser, currentUserId, profileUserId, depth + 1);
        const canReply = (depth < 2) && (currentUserId === profileUserId ||
                         currentUserId === message.author_id ||
                         currentUserId === message.user_id ||
                         (message.parent_id && currentUserId === messages.find(m => m.id === message.parent_id).author_id));
        const canDelete = currentUserId === message.author_id || currentUserId === profileUserId;

        const displayName = message.author.display_name || message.author.username;

        return `
            <li class="list-group-item ${message.parent_id ? 'reply-message' : ''}" data-messageid="${message.id}">
                <div class="message-content">
                    ${message.content}
                </div>
                <small>Posted by ${displayName} on ${message.timestamp}</small>
                ${message.author_id === currentUserId ? `
                    <div class="mt-2">
                        <button class="btn btn-secondary btn-sm" onclick="editMessage(${message.id}, ${currentUserId})">Edit</button>
                    </div>` : ''}
                ${canDelete ? `
                    <button class="btn btn-danger btn-sm mt-2" onclick="deleteMessage(${message.id}, ${profileUserId})">Delete</button>` : ''}
                ${canReply ? `
                    <button class="btn btn-sm btn-primary mt-2" onclick="showReplyForm(${message.id}, ${profileUserId})">Reply</button>
                    <form id="replyForm-${message.id}" class="reply-form mt-2 d-none" data-messageid="${message.id}">
                        <div class="form-group">
                            <textarea class="form-control" name="replyContent" rows="3"></textarea>
                        </div>
                        <button type="button" class="btn btn-primary" onclick="postReply(${profileUserId}, ${message.id})">Submit Reply</button>
                    </form>` : ''}
                <ul class="list-group mt-2">
                    ${replies}
                </ul>
            </li>
        `;
    }).join('');

    return nestedMessages;
}

function showReplyForm(messageId, profileUserId) {
    document.getElementById(`replyForm-${messageId}`).classList.toggle('d-none');
    document.getElementById(`replyForm-${messageId}`).dataset.profileUserId = profileUserId;
}

function postReply(profileUserId, messageId) {
    const replyForm = document.querySelector(`#replyForm-${messageId}`);
    const replyContent = replyForm.querySelector('textarea[name=replyContent]').value;

    fetch(`/profile/${profileUserId}/messages/${messageId}/reply`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        },
        body: JSON.stringify({ content: replyContent })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(`Error: ${data.error}`);
        } else {
            alert('Reply posted successfully.');
            showUserProfileModal(profileUserId);  // Reload profile details to reflect changes
        }
    })
    .catch(error => {
        console.error('Error posting reply:', error);
        alert('Failed to post reply. Please try again.');
    });
}

function deleteSubmission(submissionId, context, userId) {
    fetch(`/tasks/task/delete_submission/${submissionId}`, {
        method: 'DELETE',
        headers: {
            'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Submission deleted successfully.');
            if (context === 'profileSubmissions') {
                showUserProfileModal(userId);  // Reload profile submissions
            }
        } else {
            throw new Error(data.message);
        }
    })
    .catch(error => {
        console.error('Error deleting submission:', error);
        alert('Error during deletion: ' + error.message);
    });
}

function editMessage(messageId, userId) {
    const messageElement = document.querySelector(`li[data-messageid="${messageId}"]`);
    const messageContentElement = messageElement.querySelector('.message-content');
    const currentContent = messageContentElement.innerHTML;

    messageContentElement.innerHTML = `
        <textarea class="form-control">${currentContent}</textarea>
        <button class="btn btn-primary mt-2" onclick="saveMessage(${messageId}, ${userId})">Save</button>
        <button class="btn btn-secondary mt-2" onclick="cancelEditMessage(${messageId}, '${currentContent}')">Cancel</button>
    `;
}

function saveMessage(messageId, userId) {
    const messageElement = document.querySelector(`li[data-messageid="${messageId}"]`);
    const messageContentElement = messageElement.querySelector('.message-content textarea');
    const newContent = messageContentElement.value;

    fetch(`/profile/${userId}/messages/${messageId}/edit`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        },
        body: JSON.stringify({ content: newContent })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(`Error: ${data.error}`);
        } else {
            alert('Message updated successfully.');
            showUserProfileModal(userId);  // Reload profile details to reflect changes
        }
    })
    .catch(error => {
        console.error('Error updating message:', error);
        alert('Failed to update message. Please try again.');
    });
}

function cancelEditMessage(messageId, originalContent) {
    const messageElement = document.querySelector(`li[data-messageid="${messageId}"]`);
    const messageContentElement = messageElement.querySelector('.message-content');
    messageContentElement.innerHTML = originalContent;
}

function deleteMessage(messageId, userId) {
    fetch(`/profile/${userId}/messages/${messageId}/delete`, {
        method: 'POST',
        headers: {
            'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Message deleted successfully.');
            showUserProfileModal(userId);  // Reload profile messages to reflect changes
        } else {
            throw new Error(data.error);
        }
    })
    .catch(error => {
        console.error('Error deleting message:', error);
        alert('Error during deletion: ' + error.message);
    });
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
