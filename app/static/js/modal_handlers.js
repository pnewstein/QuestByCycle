// Combined Task Management and Modal Interaction Code
let isSubmitting = false;

const userToken = localStorage.getItem('userToken');
const currentUserId = localStorage.getItem(' current_user_id ');

// Function to open a modal by ID
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
    twitterLink.style.display = 'none';
    twitterLink.href = '#'; // Reset to default or placeholder link

    const modalTaskActions = document.getElementById('modalTaskActions');
    if (modalTaskActions) {
        modalTaskActions.innerHTML = '';
    }
    document.querySelectorAll('[id^="verifyButton-"]').forEach(button => button.remove());
    document.querySelectorAll('[id^="verifyTaskForm-"]').forEach(form => form.remove());
    document.body.classList.remove('body-no-scroll');
}

// Open Task Detail Modal
function openTaskDetailModal(taskId) {
    resetModalContent();
    fetch(`/tasks/detail/${taskId}/user_completion`)
        .then(response => response.json())
        .then(data => {
            const { task, userCompletion, canVerify, nextEligibleTime } = data;
            if (!populateTaskDetails(task, userCompletion.completions, canVerify, taskId, nextEligibleTime)) {
                console.error('Error: Required elements are missing to populate task details.');
                return;
            }
            ensureDynamicElementsExistAndPopulate(data.task, data.userCompletion.completions, data.nextEligibleTime, data.canVerify);

            fetchSubmissions(taskId);
            openModal('taskDetailModal');
        })
        .catch(error => {
            console.error('Error opening task detail modal:', error);
            alert('Failed to load task details.');
        });
}

// Populate Task Details in Modal
function populateTaskDetails(task, userCompletionCount, canVerify, taskId, nextEligibleTime) {
    const completeText = userCompletionCount >= task.completion_limit ? " - complete" : "";
    const parentElement = document.querySelector('.user-task-data'); // Assuming this is where the elements should be added
    const elementIds = [
        'modalTaskTitle', 'modalTaskDescription', 'modalTaskTips', 'modalTaskPoints',
        'modalTaskCompletionLimit', 'modalTaskCategory', 'modalTaskBadgeName',
        'modalTaskCompletions', 'modalCountdown'
    ];
    const elements = {};

    // Collect all elements now, including newly created ones if they were missing
    elementIds.forEach(id => {
        elements[id] = document.getElementById(id);
        if (!elements[id]) { // Create element if not exists
            elements[id] = document.createElement('div');
            elements[id].id = id;
            parentElement.appendChild(elements[id]); // Append new element to the parent container
        }
    });

    // Now, safely use the elements
    elements['modalTaskTitle'].innerText = `${task.title}${completeText}`;
    elements['modalTaskDescription'].innerText = task.description;
    elements['modalTaskTips'].innerText = task.tips || 'No tips available';
    elements['modalTaskPoints'].innerText = `Points: ${task.points}`;
    elements['modalTaskCategory'].innerText = `Category: ${task.category || 'No category'}`;
    elements['modalTaskBadgeName'].innerText = `Badge: ${task.badge_name || 'No badge'}`;
    elements['modalTaskCompletions'].innerText = `Total Completions: ${userCompletionCount || 0}`;

    console.log("Completion Limit:", task.completion_limit);
    console.log("Frequency:", task.frequency);
    
    if (task.completion_limit && task.frequency) {
        elements['modalTaskCompletionLimit'].innerText = `Can be completed ${task.completion_limit} times ${task.frequency}`;
    } else {
        elements['modalTaskCompletionLimit'].innerText = 'No completion limits set.';
    }

    const nextAvailableTime = nextEligibleTime && new Date(nextEligibleTime);
    elements['modalCountdown'].innerText = (!canVerify && nextAvailableTime && nextAvailableTime > new Date()) ?
        `Next eligible time: ${nextAvailableTime.toLocaleString()}` :
        (canVerify ? "You are eligible to verify!" : "You are currently eligible to verify!");

    manageVerificationSection(taskId, canVerify, task.verification_type, nextEligibleTime);
    return true; // Return true to indicate successful execution
}


// Function to manage the dynamic creation and adjustment of the verification form
function manageVerificationSection(taskId, canVerify, verificationType, nextEligibleTime, nextAvailableTime) {
    const userTaskData = document.querySelector('.user-task-data');
    userTaskData.innerHTML = '';

    if (canVerify) {
        createVerificationButton(taskId);

        const verifyForm = document.createElement('div');
        verifyForm.id = `verifyTaskForm-${taskId}`;
        verifyForm.className = 'verify-task-form';
        verifyForm.style.display = 'none'; // Hide by default

        // Ensure verificationType is correctly passed and utilized
        const formHTML = getVerificationFormHTML(verificationType.trim().toLowerCase());
        verifyForm.innerHTML = formHTML;
        userTaskData.appendChild(verifyForm);

        setupSubmissionForm(taskId);
    }

    console.log("Next Eligible Time:", nextEligibleTime);
    console.log("Can Verify:", canVerify);
    console.log("Next Available Time:", nextAvailableTime);
    console.log("Current Time:", new Date());
    console.log("Condition Result:", !canVerify && nextAvailableTime && nextAvailableTime > new Date());
    console.log("Countdown Element:", document.getElementById('modalCountdown'));

}

// Function to create and append the Verify Task button to the modal
function createVerificationButton(taskId) {
    const verifyButton = document.createElement('button');
    verifyButton.id = `verifyButton-${taskId}`;
    verifyButton.textContent = 'Verify Task';
    verifyButton.className = 'button';
    verifyButton.onclick = () => toggleVerificationForm(taskId);
    document.querySelector('.user-task-data').appendChild(verifyButton);
}

// Function to return the appropriate form HTML based on the verification type
function getVerificationFormHTML(verificationType) {
    let formHTML = '<form enctype="multipart/form-data">';

    // Explicitly handle each case
    switch (verificationType) {
        case 'photo':
            formHTML += `<input type="file" name="image" accept="image/*" required>`;
            formHTML += '<button type="submit">Submit Verification</button>';
            break;
        case 'comment':
            formHTML += `<textarea name="verificationComment" placeholder="Enter a comment..." required></textarea>`;
            formHTML += '<button type="submit">Submit Verification</button>';
            break;
        case 'photo_comment':
            formHTML += `
                <input type="file" name="image" accept="image/*" required>
                <textarea name="verificationComment" placeholder="Enter a comment..." required></textarea>
            `;
            formHTML += '<button type="submit">Submit Verification</button>';
            break;
        case 'qr_code':
            formHTML += `<p>Find and scan the QR code. No submission required here.</p>`;
            // No button is added for QR code case
            break;
        default:
            // Handle cases where no verification is needed or provide a default case
            formHTML += '<p>Verification type not set correctly.</p>';
            break;
    }

    formHTML += '</form>';
    return formHTML;
}


// Toggle the display of the verification form
function toggleVerificationForm(taskId) {
    const verifyForm = document.getElementById(`verifyTaskForm-${taskId}`);
    verifyForm.style.display = verifyForm.style.display === 'none' ? 'block' : 'none';
}

// Setup submission form with event listener
function setupSubmissionForm(taskId) {
    const submissionForm = document.getElementById(`verifyTaskForm-${taskId}`);
    if (submissionForm) {
        submissionForm.addEventListener('submit', function(event) {
            submitTaskDetails(event, taskId);
        });
    } else {
        console.error("Form not found for task ID:", taskId);
    }
}

// Define verifyTask function to handle verification form toggling
function verifyTask(taskId) {
    const verifyForm = document.getElementById(`verifyTaskForm-${taskId}`);
    if (verifyForm.style.display === 'none' || verifyForm.style.display === '') {
        verifyForm.style.display = 'block';  // Show the form
    } else {
        verifyForm.style.display = 'none';  // Hide the form
    }
}

function updateTwitterLink(tweetUrl) {
    const twitterLink = document.getElementById('twitterLink');
    if (tweetUrl) {
        twitterLink.href = tweetUrl;
        twitterLink.style.display = 'inline';  // Show the button if the URL is available
    } else {
        twitterLink.style.display = 'none';  // Hide the button if there is no URL
    }
}

function setTwitterLink(url) {
    const twitterLink = document.getElementById('twitterLink');
    if (url) {
        twitterLink.href = url;  // Set the href attribute with the received Twitter URL
        twitterLink.textContent = 'Link to Twitter';  // Optional: Update button text if necessary
    } else {
        twitterLink.href = '#';  // Reset or provide a fallback URL
        twitterLink.textContent = 'Link Unavailable';  // Handle cases where the URL isn't available
    }
}

function updateFacebookLink(fbUrl) {
    const facebookLink = document.getElementById('facebookLink');
    if (fbUrl) {
        facebookLink.href = fbUrl;
        facebookLink.style.display = 'inline';  // Show the button if the URL is available
    } else {
        facebookLink.style.display = 'none';  // Hide the button if there is no URL
    }
}

function setFacebookLink(url) {
    const facebookLink = document.getElementById('facebookLink');
    if (url) {
        facebookLink.href = url;  // Set the href attribute with the received FB URL
        facebookLink.textContent = 'Link to Facebook';  // Optional: Update button text if necessary
    } else {
        facebookLink.href = '#';  // Reset or provide a fallback URL
        facebookLink.textContent = 'Link Unavailable';  // Handle cases where the URL isn't available
    }
}

// Handle Task Submissions with streamlined logic
function submitTaskDetails(event, taskId) {
    event.preventDefault();
    if (isSubmitting) return;
    isSubmitting = true;

    const form = event.target;
    const formData = new FormData(form);

    fetch(`/tasks/task/${taskId}/submit`, {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
        headers: {
            'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        }
    })
    .then(response => response.json().then(data => {
        if (!response.ok) {
            throw new Error(data.message);
        }
        return data;
    }))
    .then(data => {
        if (!data.success) {
            alert(`Submission failed: ${data.message}`);
        }
        if (data.total_points) {
            const totalPointsElement = document.getElementById('total-points');
            if (totalPointsElement) totalPointsElement.innerText = `Total Completed Points: ${data.total_points}`;
        }
        if (data.tweet_url) {
            updateTwitterLink(data.tweet_url);
        }
        if (data.fb_url) {
            updateFacebookLink(data.fb_url);
        }
        openTaskDetailModal(taskId);
        form.reset();
    })
    .catch(error => {
        console.error("Submission error:", error);
        alert('Error during submission: ' + error.message);
    })
    .finally(() => {
        isSubmitting = false;
        resetModalContent();
    });
}

// Fetch and Display Submissions
function fetchSubmissions(taskId) {
    fetch(`/tasks/task/${taskId}/submissions`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${userToken}`, // Assuming Bearer token is used
                'Content-Type': 'application/json'
            },
            credentials: 'include' // For cookies, this might be necessary
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server responded with status ${response.status}`);
            }
            return response.json();
        })
        .then(submissions => {
            const twitterLink = document.getElementById('twitterLink');

            if (submissions && submissions.length > 0) {
                const submission = submissions[0];
                const submissionImage = document.getElementById('submissionImage');
                const submissionComment = document.getElementById('submissionComment');
                const submissionUserLink = document.getElementById('submissionUserLink');
                const downloadLink = document.getElementById('downloadLink');

                submissionImage.src = submission.image_url || 'image/placeholdersubmission.png';
                submissionComment.textContent = submission.comment || 'No comment provided.';
                submissionUserLink.href = `/user/profile/${submission.user_id}`;
                downloadLink.href = submission.image_url || '#';
                downloadLink.download = `SubmissionImage-${submission.user_id}`;

                console.log("Twitter URL: ", submission.twitter_url); // Debugging

                if (submission.twitter_url && submission.twitter_url.trim() !== '') {
                    twitterLink.href = submission.twitter_url;
                    twitterLink.style.display = 'inline';
                    console.log("Displaying Twitter link."); // Debugging
                } else {
                    twitterLink.style.display = 'none';
                    console.log("Hiding Twitter link."); // Debugging
                }
            } else {
                twitterLink.style.display = 'none';
                console.log("No submissions found, hiding Twitter link."); // Debugging
            }

            const images = submissions.reverse().map(submission => ({
                url: submission.image_url,
                alt: "Submission Image",
                comment: submission.comment, 
                user_id: submission.user_id,
                twitter_url: submission.twitter_url // Ensure twitter_url is included in the object
            }));
            distributeImages(images);
        })
        .catch(error => {
            console.error('Failed to fetch submissions:', error.message);
            alert('Could not load submissions. Please try again.');
        });
}

function ensureDynamicElementsExistAndPopulate(task, userCompletionCount, nextEligibleTime, canVerify) {
    const parentElement = document.querySelector('.user-task-data'); // Target the parent element correctly.

    // Define IDs and initial values for dynamic elements.
    const dynamicElements = [
        { id: 'modalTaskCompletions', value: `Total Completions: ${userCompletionCount || 0}` },
        { id: 'modalCountdown', value: "" } // Will be updated based on conditions
    ];

    dynamicElements.forEach(elem => {
        let element = document.getElementById(elem.id);
        if (!element) {
            element = document.createElement('p');
            element.id = elem.id;
            parentElement.appendChild(element);
        }
        element.innerText = elem.value;
    });

    // Update the countdown only if necessary.
    updateCountdownElement(document.getElementById('modalCountdown'), nextEligibleTime, canVerify);
}

function updateCountdownElement(countdownElement, nextEligibleTime, canVerify) {
    if (!canVerify && nextEligibleTime) {
        const nextTime = new Date(nextEligibleTime);
        const now = new Date();
        if (nextTime > now) {
            const timeDiffMs = nextTime - now;
            countdownElement.innerText = `Next eligible time: ${formatTimeDiff(timeDiffMs)}`;
        } else {
            countdownElement.innerText = "You are currently eligible to verify!";
        }
    } else {
        countdownElement.innerText = "You are currently eligible to verify!";
    }
}

function formatTimeDiff(ms) {
    const seconds = Math.floor((ms / 1000) % 60);
    const minutes = Math.floor((ms / (1000 * 60)) % 60);
    const hours = Math.floor((ms / (1000 * 60 * 60)) % 24);
    const days = Math.floor(ms / (1000 * 60 * 60 * 24));
    return `${days}d ${hours}h ${minutes}m ${seconds}s`;
}

// Distribute images across columns in the modal
function distributeImages(images) {
    const board = document.getElementById('submissionBoard');
    board.innerHTML = ''; 
    const modalWidth = board.clientWidth; 
    const desiredColumnWidth = 150;
    const columnCount = Math.floor(modalWidth / desiredColumnWidth);
    const columns = [];

    for (let i = 0; i < columnCount; i++) {
        const column = document.createElement('div');
        column.className = 'photo-column';
        board.appendChild(column);
        columns.push(column);
    }

    images.forEach((image, index) => {
        const img = document.createElement('img');
        img.src = image.url;
        img.alt = "Loaded Image";
        img.onerror = () => img.src = document.getElementById('taskDetailModal').getAttribute('data-placeholder-url');
        img.onclick = () => showSubmissionDetail(image);
        columns[index % columnCount].prepend(img);
    });
}

// Show detailed submission view
function showSubmissionDetail(image) {
    const submissionModal = document.getElementById('submissionDetailModal');
    document.getElementById('submissionImage').src = image.url;
    document.getElementById('submissionComment').textContent = image.comment || 'No comment provided.';
    document.getElementById('submissionUserLink').onclick = function() {
        showUserProfileModal(image.user_id);
        return false;
    };
    document.getElementById('downloadLink').href = image.url;
    document.getElementById('downloadLink').download = `Image-${image.user_id}`;

    // Update the Twitter link if available
    const twitterLink = document.getElementById('twitterLink');
    if (image.verification_type !== 'comment' && image.twitter_url && isValidUrl(image.twitter_url)) {
        twitterLink.href = image.twitter_url;
        twitterLink.style.display = 'inline';  // Show the Twitter link if a URL is available and not using the placeholder image
    } else {
        twitterLink.style.display = 'none';  // Hide the Twitter link if using the placeholder image or no URL is available
    }

    submissionModal.style.display = 'block';
    submissionModal.style.backgroundColor = 'rgba(0,0,0,0.7)';
}

function isValidUrl(string) {
    try {
        new URL(string);
        return true;
    } catch (_) {
        return false;  // Fails to construct a URL, it's likely not a valid URL
    }
}

// User profile modal display
function showUserProfileModal(userId) {
    fetch(`/profile/${userId}`)
        .then(response => response.text())
        .then(html => {
            const userProfileDetails = document.getElementById('userProfileDetails');
            if (!userProfileDetails) {
                console.error('User profile details container not found');
                return;  // Exit if no container is found
            }
            userProfileDetails.innerHTML = html;
            openModal('userProfileModal');
        })
        .catch(error => {
            console.error('Failed to load user profile:', error);
            alert('Could not load user profile. Please try again.');
        });
}


function showLeaderboardModal(selectedGameId) {
    console.log("Attempting to show leaderboard modal for game ID:", selectedGameId);

    const leaderboardContent = document.getElementById('leaderboardModalContent');
    if (!leaderboardContent) {
        console.error('Leaderboard modal content element not found. Cannot proceed with displaying leaderboard.');
        alert('Leaderboard modal content element not found. Please ensure the page has loaded completely and the correct ID is used.');
        return;
    }

    fetch('/leaderboard_partial?game_id=' + selectedGameId)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch leaderboard data');
            }
            return response.json();
        })
        .then(data => {
            leaderboardContent.innerHTML = '';
            appendGameSelector(leaderboardContent, data, selectedGameId);
            appendCompletionMeter(leaderboardContent, data);
            appendLeaderboardTable(leaderboardContent, data);
            openModal('leaderboardModal');
        })
        .catch(error => {
            console.error('Failed to load leaderboard:', error);
            alert('Failed to load leaderboard data. Please try again.');
        });
}


function showMySubmissionsModal() {
    fetch('/tasks/task/my_submissions')  // Adjusted to the new endpoint
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch data: ' + response.statusText);
            }
            return response.json();
        })
        .then(data => {
            if (Array.isArray(data)) {
                displayMySubmissions(data);
            } else {
                console.error('Expected an array of submissions, but got:', data);
                alert('Error: ' + data.error);
            }
            openModal('mySubmissionsModal');
        })
        .catch(error => {
            console.error('Error fetching submissions:', error);
            alert('Error fetching submissions: ' + error.message);
        });
}

function appendGameSelector(parentElement, data, selectedGameId) {
    if (data.games && data.games.length > 1) {
        const form = document.createElement('form');
        form.method = 'get';
        form.action = '#';  // Update with correct endpoint if needed

        const selectLabel = document.createElement('label');
        selectLabel.for = 'game_Select';
        selectLabel.textContent = 'Select Game:';
        form.appendChild(selectLabel);

        const select = document.createElement('select');
        select.name = 'game_id';
        select.id = 'game_Select';
        select.className = 'form-control';
        select.onchange = () => form.submit();  // Adjust as needed for actual use
        data.games.forEach(game => {
            const option = document.createElement('option');
            option.value = game.id;
            option.textContent = game.title;
            option.selected = (game.id === selectedGameId);
            select.appendChild(option);
        });
        form.appendChild(select);
        parentElement.appendChild(form);
    }
}

function appendLeaderboardTable(parentElement, data) {
    if (data.top_users && data.top_users.length > 0) {
        const table = document.createElement('table');
        table.className = 'table table-striped';

        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        ['Rank', 'Player', 'Carbon “Reduction” Points'].forEach(text => {
            const th = document.createElement('th');
            th.textContent = text;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        const tbody = document.createElement('tbody');
        data.top_users.forEach((user, index) => {
            const row = document.createElement('tr');
            appendTableCell(row, index + 1);
            appendTableCell(row, user.username, true, user.user_id);
            appendTableCell(row, user.total_points);
            tbody.appendChild(row);
        });
        table.appendChild(tbody);
        parentElement.appendChild(table);
    } else {
        const p = document.createElement('p');
        p.textContent = 'Join a game to see the leaderboard!';
        parentElement.appendChild(p);
    }
}

function appendTableCell(row, content, isLink = false, userId = null) {
    const cell = document.createElement('td');
    if (isLink) {
        const link = document.createElement('a');
        link.href = "javascript:void(0)";
        link.onclick = () => showUserProfileModal(userId);
        link.textContent = content;
        cell.appendChild(link);
    } else {
        cell.textContent = content;
    }
    row.appendChild(cell);
}

function appendCompletionMeter(parentElement, data) {
    if (data.total_game_points && data.game_goal) {
        const meterContainer = document.createElement('div');
        meterContainer.className = 'completion-meter-container';

        const meterLabel = document.createElement('div');
        meterLabel.className = 'meter-label';
        meterLabel.textContent = `Group Completion: ${data.total_game_points} / ${data.game_goal}`;
        meterContainer.appendChild(meterLabel);

        const completionMeter = document.createElement('div');
        completionMeter.className = 'completion-meter';

        const meterBar = document.createElement('div');
        meterBar.className = 'meter-bar';
        meterBar.id = 'meterBar';  // Ensure the id is correctly set
        let percent = Math.min(data.total_game_points / data.game_goal * 100, 100);
        meterBar.style.width = '100%';
        meterBar.style.height = `${percent}%`;
        meterBar.dataset.label = `${percent.toFixed(1)}% Complete`;
        completionMeter.appendChild(meterBar);

        meterContainer.appendChild(completionMeter);
        parentElement.appendChild(meterContainer);

        setTimeout(() => {
            meterBar.style.transition = 'height 2s ease-in-out, background-color 2s';
            meterBar.style.height = `${percent}%`;
        }, 100);
    }
}


// Close modal helpers enhanced with specific targeting and cleanup
function closeTaskDetailModal() {
    document.getElementById('taskDetailModal').style.display = 'none';
    resetModalContent();  // Ensure clean state on next open
}

function closeTipsModal() {
    document.getElementById('tipsModal').style.display = 'none';
}

function closeSubmissionDetailModal() {
    const submissionModal = document.getElementById('submissionDetailModal');
    submissionModal.style.display = 'none';
    submissionModal.style.backgroundColor = ''; // Reset background color to default
    document.body.classList.remove('body-no-scroll');
}

function closeAllSubmissionsModal() {
    const allSubmissionsModal = document.getElementById('allSubmissionsModal');
    allSubmissionsModal.style.display = 'none';
    allSubmissionsModal.style.backgroundColor = ''; // Reset background color to default
    document.body.classList.remove('body-no-scroll');
}

function closeMySubmissionsModal() {
    const mySubmissionsModal = document.getElementById('mySubmissionsModal');
    mySubmissionsModal.style.display = 'none';
    mySubmissionsModal.style.backgroundColor = ''; // Reset background color to default
    document.body.classList.remove('body-no-scroll');
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

function closeLeaderboardModal() {
    const leaderboardModal = document.getElementById('leaderboardModal');
    if (!leaderboardModal) {
        console.error('Leaderboard modal container not found');
        return;  // Exit if no container is found
    }
    leaderboardModal.style.display = 'none';
    document.body.classList.remove('body-no-scroll');

}

// Enhanced window click handling for modal closure
window.onclick = function(event) {
    if (event.target.className.includes('modal')) {
        switch(event.target.id) {
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
            case 'userProfileModal':
                closeUserProfileModal();
                break;
            case 'leaderboardModal':
                closeLeaderboardModal();
                break;
            case 'tipsModal':
                closeTipsModal();
                break;
        }
    }
}

function showAllSubmissionsModal() {
    fetch('/tasks/task/all_submissions')  // Adjusted to the new endpoint for fetching all submissions
        .then(response => response.json())
        .then(data => {
            displayAllSubmissions(data);
            openModal('allSubmissionsModal');
        })
        .catch(error => {
            console.error('Error fetching all submissions:', error);
            alert('Error fetching all submissions: ' + error.message);
        });
}

function displayAllSubmissions(submissions) {
    const container = document.getElementById('allSubmissionsContainer');
    container.innerHTML = ''; // Clear previous submissions
    submissions.forEach(submission => {
        const card = document.createElement('div');
        card.className = 'submission-card';

        const img = document.createElement('img');
        img.src = submission.image_url || 'path/to/default/image.png';
        img.alt = 'Task Submission';
        img.className = 'submission-image';

        const info = document.createElement('div');
        info.className = 'submission-info';

        const userDetails = document.createElement('p');
        userDetails.textContent = `User ID: ${submission.user_id}`;
        userDetails.className = 'submission-user-details';

        const taskDetails = document.createElement('p');
        taskDetails.textContent = `Task ID: ${submission.task_id}`;
        taskDetails.className = 'submission-task-details';

        const timestamp = document.createElement('p');
        timestamp.textContent = `Submitted on: ${submission.timestamp}`;
        timestamp.className = 'submission-timestamp';

        const comment = document.createElement('p');
        comment.textContent = `Comment: ${submission.comment}`;
        comment.className = 'submission-comment';
    
        const twitterLink = document.createElement('p');
        twitterLink.textContent = `Twitter: ${submission.tweet_url}`;
        twitterLink.className = 'submission-comment';

        const deleteButton = document.createElement('button');
        deleteButton.textContent = 'Delete';
        deleteButton.className = 'button delete-button';
        deleteButton.addEventListener('click', function() {
            deleteSubmission(submission.id);
        });

        info.appendChild(userDetails);
        info.appendChild(taskDetails);
        info.appendChild(timestamp);
        info.appendChild(comment);    
        info.appendChild(twitterLink);
        card.appendChild(img);
        card.appendChild(info);
        card.appendChild(deleteButton);

        container.appendChild(card);
    });
}


// Function to display submissions in a grid
function displayMySubmissions(submissions) {
    const container = document.getElementById('submissionsContainer');
    container.innerHTML = ''; // Clear previous submissions

    submissions.forEach(submission => {
        const card = document.createElement('div');
        card.className = 'submission-card';

        const img = document.createElement('img');
        img.src = submission.image_url || 'path/to/default/image.png';
        img.alt = 'Task Submission';
        img.className = 'submission-image';

        const info = document.createElement('div');
        info.className = 'submission-info';

        const timestamp = document.createElement('p');
        timestamp.textContent = `Submitted on: ${submission.timestamp}`;
        timestamp.className = 'submission-timestamp';

        const comment = document.createElement('p');
        comment.textContent = `Comment: ${submission.comment}`;
        comment.className = 'submission-comment';

        const twitterLink = document.createElement('p');
        twitterLink.textContent = `Twitter: ${submission.tweet_url}`;
        twitterLink.className = 'submission-comment';

        const deleteButton = document.createElement('button');
        deleteButton.textContent = 'Delete';
        deleteButton.className = 'button delete-button';
        deleteButton.addEventListener('click', function() {
            deleteSubmission(submission.id);
        });

        info.appendChild(timestamp);
        info.appendChild(comment);
        info.appendChild(twitterLink);
        card.appendChild(img);
        card.appendChild(info);
        card.appendChild(deleteButton);

        container.appendChild(card);
    });
}

// Function to delete a submission
function deleteSubmission(submissionId) {
    fetch(`/tasks/task/delete_submission/${submissionId}`, {
        method: 'DELETE',
        headers: {
            'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        }
    })
    .then(response => response.json().then(data => ({ data, ok: response.ok }))) // Create an object that includes both data and the ok status
    .then(result => {
        if (result.ok) {
            alert('Submission deleted successfully');
            // Optionally, remove the submission's element from the DOM to update the UI instantly
            // Make sure you have an element with the id formatted as `submission-${submissionId}`
            const element = document.getElementById(`submission-${submissionId}`);
            if (element) {
                element.remove();
            } else {
                console.log('Element not found:', `submission-${submissionId}`);
            }
        } else {
            alert(`Failed to delete submission: ${result.data.error}`);
        }
    })
    .catch(error => console.error('Error deleting submission:', error));
}
