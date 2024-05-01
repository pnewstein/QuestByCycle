// Combined Task Management and Modal Interaction Code
let isSubmitting = false;

// Function to open a modal by ID
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'block';
        document.body.classList.add('body-no-scroll'); // Optional: prevent scrolling when modal is open
    }
}

// Reset all modal content and settings to initial state
function resetModalContent() {
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
        'modalTaskCompletionLimit', 'modalTaskCategory', 'modalTaskBadgeName'
    ];

    // Dynamically create 'modalTaskCompletions' and 'modalCountdown' if not present
    const dynamicIds = ['modalTaskCompletions', 'modalCountdown'];
    dynamicIds.forEach(id => {
        if (!document.getElementById(id)) {
            const newElement = document.createElement('p');
            newElement.id = id;
            parentElement.appendChild(newElement);
        }
    });

    elementIds.push(...dynamicIds); // Add dynamic element IDs to the array for processing
    const elements = {};

    // Collect all elements now, including newly created ones if they were missing
    elementIds.forEach(id => {
        elements[id] = document.getElementById(id);
    });

    // Now, safely use the elements
    elements['modalTaskTitle'].innerText = `${task.title}${completeText}`;
    elements['modalTaskDescription'].innerText = task.description;
    elements['modalTaskTips'].innerText = task.tips || 'No tips available';
    elements['modalTaskPoints'].innerText = `Points: ${task.points}`;
    elements['modalTaskCategory'].innerText = `Category: ${task.category || 'No category'}`;
    elements['modalTaskBadgeName'].innerText = `Badge: ${task.badge_name || 'No badge'}`;
    elements['modalTaskCompletions'].innerText = `Total Completions: ${userCompletionCount || 0}`;

    if (task.completion_limit && task.frequency) {
        const frequencyReadable = `${task.frequency[0].toUpperCase()}${task.frequency.slice(1).toLowerCase()}`;
        elements['modalTaskCompletionLimit'].innerText = `Can be completed ${task.completion_limit} times ${frequencyReadable}`;
    } else {
        elements['modalTaskCompletionLimit'].innerText = 'No completion limits set.';
    }

    const nextAvailableTime = nextEligibleTime && new Date(nextEligibleTime);
    elements['modalCountdown'].innerText = (!canVerify && nextAvailableTime && nextAvailableTime > new Date()) ?
        `Next eligible time: ${nextAvailableTime.toLocaleString()}` :
        (canVerify ? "You are eligible to verify!" : "You are currently eligible to verify!");

    manageVerificationSection(taskId, canVerify, nextEligibleTime, nextAvailableTime);
    return true; // Return true to indicate successful execution
}

// Manage Verification Section dynamically
function manageVerificationSection(taskId, canVerify, nextEligibleTime, nextAvailableTime) {
    const userTaskData = document.querySelector('.user-task-data');
    userTaskData.innerHTML = '';

    if (canVerify) {
        const verifyButton = document.createElement('button');
        verifyButton.id = `verifyButton-${taskId}`;
        verifyButton.textContent = 'Verify Task';
        verifyButton.className = 'verifyButton';
        verifyButton.onclick = () => toggleVerificationForm(taskId);
        userTaskData.appendChild(verifyButton);

        const verifyForm = document.createElement('div');
        verifyForm.id = `verifyTaskForm-${taskId}`;
        verifyForm.innerHTML = `<form enctype="multipart/form-data">
                                    <input type="file" name="image" accept="image/*" required>
                                    <textarea name="verificationComment" placeholder="Enter a comment..." required></textarea>
                                    <button type="submit">Submit Verification</button>
                                </form>`;
        verifyForm.style.display = 'none';
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
    .then(response => {
        if (!response.ok) throw new Error('Failed to submit task details.');
        return response.json();
    })
    .then(data => {
        alert(data.success ? 'Submission successful!' : `Submission failed: ${data.message}`);
        if (data.total_points) {
            const totalPointsElement = document.getElementById('total-points');
            if (totalPointsElement) totalPointsElement.innerText = `Total Completed Points: ${data.total_points}`;
        }
        openTaskDetailModal(taskId);
        form.reset();
    })
    .catch(error => {
        console.error("Submission error:", error);
        alert('Error during submission: Check console for more information.');
    })
    .finally(() => {
        isSubmitting = false;
        resetModalContent();
    });
}

// Fetch and Display Submissions
function fetchSubmissions(taskId) {
    fetch(`/tasks/task/${taskId}/submissions`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server responded with status ${response.status}`);
            }
            return response.json();
        })
        .then(submissions => {
            // Reverse the array to display newest submissions first
            const images = submissions.reverse().map(submission => ({
                url: submission.image_url,
                alt: "Submission Image",
                comment: submission.comment, 
                user_id: submission.user_id
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

    submissionModal.style.display = 'block';
    submissionModal.style.backgroundColor = 'rgba(0,0,0,0.7)';
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

// Close modal helpers enhanced with specific targeting and cleanup
function closeTaskDetailModal() {
    document.getElementById('taskDetailModal').style.display = 'none';
    resetModalContent();  // Ensure clean state on next open
}

function closeTipsModal() {
    document.getElementById('tipsModal').style.display = 'none';
}

function closeSubmissionModal() {
    const submissionModal = document.getElementById('submissionDetailModal');
    submissionModal.style.display = 'none';
    submissionModal.style.backgroundColor = ''; // Reset background color to default
}

function closeUserProfileModal() {
    const userProfileModal = document.getElementById('userProfileModal');
    if (!userProfileModal) {
        console.error('User profile modal container not found');
        return;  // Exit if no container is found
    }
    userProfileModal.style.display = 'none';
}

// Enhanced window click handling for modal closure
window.onclick = function(event) {
    if (event.target.className.includes('modal')) {
        switch(event.target.id) {
            case 'submissionDetailModal':
                closeSubmissionModal();
                break;
            case 'taskDetailModal':
                closeTaskDetailModal();
                break;
            case 'userProfileModal':
                closeUserProfileModal();
                break;
            case 'tipsModal':
                closeTipsModal();
                break;
        }
    }
}
