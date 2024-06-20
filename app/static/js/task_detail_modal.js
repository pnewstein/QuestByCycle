// Task detail modal management functions
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
            alert('Sign in to view task details.');
        });
}

function closeTaskDetailModal() {
    document.getElementById('taskDetailModal').style.display = 'none';
    resetModalContent();  // Ensure clean state on next open
}

function populateTaskDetails(task, userCompletionCount, canVerify, taskId, nextEligibleTime) {
    const completeText = userCompletionCount >= task.completion_limit ? " - complete" : "";
    const elements = {
        'modalTaskTitle': document.getElementById('modalTaskTitle'),
        'modalTaskDescription': document.getElementById('modalTaskDescription'),
        'modalTaskTips': document.getElementById('modalTaskTips'),
        'modalTaskPoints': document.getElementById('modalTaskPoints'),
        'modalTaskCompletionLimit': document.getElementById('modalTaskCompletionLimit'),
        'modalTaskCategory': document.getElementById('modalTaskCategory'),
        'modalTaskVerificationType': document.getElementById('modalTaskVerificationType'),
        'modalTaskBadgeImage': document.getElementById('modalTaskBadgeImage'),
        'modalTaskCompletions': document.getElementById('modalTaskCompletions'),
        'modalCountdown': document.getElementById('modalCountdown')
    };

    // Ensure all required elements exist
    for (let key in elements) {
        if (!elements[key]) {
            console.error(`Error: Missing element ${key}`);
            return false;
        }
    }

    // Update text content for elements
    elements['modalTaskTitle'].innerText = `${task.title}${completeText}`;
    elements['modalTaskDescription'].innerHTML = task.description;
    elements['modalTaskTips'].innerHTML = task.tips || 'No tips available';
    elements['modalTaskPoints'].innerText = `${task.points}`;
    const completionText = task.completion_limit > 1 ? `${task.completion_limit} times` : `${task.completion_limit} time`;
    elements['modalTaskCompletionLimit'].innerText = `${completionText} ${task.frequency}`;
    elements['modalTaskCategory'].innerText = task.category || 'No category set';

    switch (task.verification_type) {
        case 'photo_comment':
            elements['modalTaskVerificationType'].innerText = "Must upload a photo and a comment to earn points!";
            break;
        case 'photo':
            elements['modalTaskVerificationType'].innerText = "Must upload a photo to earn points!";
            break;
        case 'comment':
            elements['modalTaskVerificationType'].innerText = "Must upload a comment to earn points!";
            break;
        case 'qr_code':
            elements['modalTaskVerificationType'].innerText = "Find the QR code and post a photo to earn points!";
            break;
        default:
            elements['modalTaskVerificationType'].innerText = 'Not specified';
            break;
    }

    const badgeImagePath = task.badge && task.badge.image ? `/static/images/badge_images/${task.badge.image}` : '/static/images/badge_images/default_badge.png';
    elements['modalTaskBadgeImage'].src = badgeImagePath;
    elements['modalTaskBadgeImage'].alt = task.badge && task.badge.name ? `Badge: ${task.badge.name}` : 'Default Badge';

    elements['modalTaskCompletions'].innerText = `Total Completions: ${userCompletionCount}`;

    const nextAvailableTime = nextEligibleTime && new Date(nextEligibleTime);
    if (!canVerify && nextAvailableTime && nextAvailableTime > new Date()) {
        elements['modalCountdown'].innerText = `Next eligible time: ${nextAvailableTime.toLocaleString()}`;
        elements['modalCountdown'].style.color = 'red';
    } else {
        elements['modalCountdown'].innerText = "You are currently eligible to verify!";
        elements['modalCountdown'].style.color = 'green';
    }

    manageVerificationSection(taskId, canVerify, task.verification_type, nextEligibleTime);
    return true;
}

function ensureDynamicElementsExistAndPopulate(task, userCompletionCount, nextEligibleTime, canVerify) {
    const parentElement = document.querySelector('.user-task-data'); // Target the parent element correctly.

    // Define IDs and initial values for dynamic elements.
    const dynamicElements = [
        { id: 'modalTaskCompletions', value: `${userCompletionCount || 0}` },
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

// Task detail modal verification functions
const userToken = localStorage.getItem('userToken');
const currentUserId = localStorage.getItem('current_user_id');

// Function to manage the dynamic creation and adjustment of the verification form
function manageVerificationSection(taskId, canVerify, verificationType, nextEligibleTime, nextAvailableTime) {
    const userTaskData = document.querySelector('.user-task-data');
    userTaskData.innerHTML = '';

    if (canVerify) {
        const verifyForm = document.createElement('div');
        verifyForm.id = `verifyTaskForm-${taskId}`;
        verifyForm.className = 'verify-task-form';
        verifyForm.style.display = 'show'; // Hide by default

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

function getVerificationFormHTML(verificationType) {
    let formHTML = '<form enctype="multipart/form-data" class="epic-form">';

    // Explicitly handle each case
    switch (verificationType) {
        case 'photo':
            formHTML += `
                <div class="form-group">
                    <label for="image" class="epic-label">Upload a Photo</label>
                    <input type="file" id="image" name="image" class="epic-input" accept="image/*" required>
                </div>
                <div class="form-group">
                    <button type="submit" class="epic-button">Submit Verification</button>
                </div>`;
            break;
        case 'comment':
            formHTML += `
                <div class="form-group">
                    <label for="verificationComment" class="epic-label">Enter a Comment</label>
                    <textarea id="verificationComment" name="verificationComment" class="epic-textarea" placeholder="Enter a comment..." required></textarea>
                </div>
                <div class="form-group">
                    <button type="submit" class="epic-button">Submit Verification</button>
                </div>`;
            break;
        case 'photo_comment':
            formHTML += `
                <div class="form-group">
                    <label for="image" class="epic-label">Upload a Photo</label>
                    <input type="file" id="image" name="image" class="epic-input" accept="image/*" required>
                </div>
                <div class="form-group">
                    <label for="verificationComment" class="epic-label">Enter a Comment</label>
                    <textarea id="verificationComment" name="verificationComment" class="epic-textarea" placeholder="Enter a comment..." required></textarea>
                </div>
                <div class="form-group">
                    <button type="submit" class="epic-button">Submit Verification</button>
                </div>`;
            break;
        case 'qr_code':
            formHTML += `<p class="epic-message">Find and scan the QR code. No submission required here.</p>`;
            // No button is added for QR code case
            break;
        case 'pause':
            formHTML += `<p class="epic-message">Task is currently paused.</p>`;
            // No button is added for pause case
            break;
        default:
            // Handle cases where no verification is needed or provide a default case
            formHTML += '<p class="epic-message">Submission Requirements not set correctly.</p>';
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

function updateTwitterLink(url) {
    const twitterLink = document.getElementById('twitter-link');
    if (twitterLink) {
        console.debug('Twitter link element found, setting href:', url);
        twitterLink.href = url;
        twitterLink.style.display = 'block';
    } else {
        console.debug('Twitter link element not found');
    }
}


function setTwitterLink(url) {
    const twitterLink = document.getElementById('twitterLink');
    if (twitterLink) {
        if (url) {
            twitterLink.href = url;  // Set the href attribute with the received Twitter URL
            twitterLink.textContent = 'Link to Twitter';  // Optional: Update button text if necessary
        } else {
            twitterLink.href = '#';  // Reset or provide a fallback URL
            twitterLink.textContent = 'Link Unavailable';  // Handle cases where the URL isn't available
        }
    }
}

function updateFacebookLink(url) {
    const facebookLink = document.getElementById('facebook-link');
    if (facebookLink) {
        console.debug('Facebook link element found, setting href:', url);
        facebookLink.href = url;
        facebookLink.style.display = 'block';
    } else {
        console.debug('Facebook link element not found');
    }
}

function setFacebookLink(url) {
    const facebookLink = document.getElementById('facebookLink');
    if (facebookLink) {
        if (url) {
            facebookLink.href = url;  // Set the href attribute with the received FB URL
            facebookLink.textContent = 'Link to Facebook';  // Optional: Update button text if necessary
        } else {
            facebookLink.href = '#';  // Reset or provide a fallback URL
            facebookLink.textContent = 'Link Unavailable';  // Handle cases where the URL isn't available
        }
    }
}


// Handle Task Submissions with streamlined logic
let isSubmitting = false;

function submitTaskDetails(event, taskId) {
    event.preventDefault();
    if (isSubmitting) return;
    isSubmitting = true;

    const form = event.target;
    const formData = new FormData(form);
    formData.append('user_id', currentUserId); // Add user_id to form data

    console.debug('Submitting form with data:', formData);

    fetch(`/tasks/task/${taskId}/submit`, {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
        headers: {
            'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        }
    })
    .then(response => response.json())
    .then(data => {
        console.debug('Response data:', data);

        if (!data.success) {
            throw new Error(data.message);
        }
        if (data.total_points) {
            const totalPointsElement = document.getElementById('total-points');
            if (totalPointsElement) {
                console.debug('Updating total points:', data.total_points);
                totalPointsElement.innerText = `Total Completed Points: ${data.total_points}`;
            }
        }
        if (data.tweet_url) {
            console.debug('Updating Twitter link:', data.tweet_url);
            updateTwitterLink(data.tweet_url);
        }
        if (data.fb_url) {
            console.debug('Updating Facebook link:', data.fb_url);
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
            console.debug('Fetched submissions:', submissions);

            const twitterLink = document.getElementById('twitterLink');
            const facebookLink = document.getElementById('facebookLink');

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

                if (submission.twitter_url && submission.twitter_url.trim() !== '') {
                    twitterLink.href = submission.twitter_url;
                    twitterLink.style.display = 'inline';
                } else {
                    twitterLink.style.display = 'none';
                }

                if (submission.fb_url && submission.fb_url.trim() !== '') {
                    facebookLink.href = submission.fb_url;
                    facebookLink.style.display = 'inline';
                } else {
                    facebookLink.style.display = 'none';
                }
            } else {
                twitterLink.style.display = 'none';
                facebookLink.style.display = 'none';
            }

            const images = submissions.reverse().map(submission => ({
                url: submission.image_url,
                alt: "Submission Image",
                comment: submission.comment,
                user_id: submission.user_id,
                twitter_url: submission.twitter_url, // Ensure twitter_url is included in the object
                fb_url: submission.fb_url // Ensure fb_url is included in the object
            }));
            distributeImages(images);
        })
        .catch(error => {
            console.error('Failed to fetch submissions:', error.message);
            alert('Could not load submissions. Please try again.');
        });
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
