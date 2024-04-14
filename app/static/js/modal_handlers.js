// Function to open a modal by ID
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'block';
        document.body.classList.add('body-no-scroll'); // Optional: Prevent scrolling when modal is open
    }
}

// Function to close a modal by ID
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        document.body.classList.remove('body-no-scroll'); // Optional: Re-enable scrolling when modal is closed
    }
}

// Close modals if the user clicks outside of the modal content
window.onclick = function(event) {
    let submissionModal = document.getElementById('submissionDetailModal');
    let taskModal = document.getElementById('taskDetailModal');
    
    if (event.target == modal) {
        modal.style.display = "none";
    }
    if (event.target == submissionModal) {
        closeSubmissionModal();
    }

    else if (event.target == taskModal) {
        closeTaskDetailModal(); 
    }
}

function openTaskDetailModal(taskId) {
    resetModalContent();
    document.body.classList.add('body-no-scroll');

    fetch(`/tasks/detail/${taskId}/user_completion`)
        .then(response => response.json())
        .then(data => {
            const task = data.task;
            const userCompletion = data.userCompletion;
            const canVerify = data.canVerify;
            const frequency = task.frequency;
            const lastRelevantCompletionTime = data.lastRelevantCompletionTime;
            const nextEligibleTime = task.nextEligibleTime;
            const verifyButton = document.getElementById(`verifyButton-${taskId}`);

            verifyButton.disabled = !(userCompletion.completions < task.completionLimit);
            if (verifyButton.disabled) {
                updateCountdownFromLastRelevant(lastRelevantCompletionTime, frequency);
            } else {
                document.getElementById('modalCountdown').innerText = "Verify button is not disabled.";
            }

            populateTaskDetails(task, userCompletion.completions, canVerify, taskId, nextEligibleTime);
            fetchSubmissions(taskId);

            document.getElementById('taskDetailModal').style.display = 'block';

        })
        .catch(error => {
            console.error('Error opening task detail modal:', error);
            alert('Failed to load task details.');
        });
}


// Adding new DOMContentLoaded event listener for handling auto-opening of modal on page load
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const shouldOpenModal = urlParams.get('open_modal');

    if (shouldOpenModal === 'true') {
        const taskId = urlParams.get('task_id'); // assuming task_id is passed as a parameter
        if(taskId) {
            openTaskDetailModal(taskId);
        }
    }
});


function populateTaskDetails(task, userCompletionCount, canVerify, taskId, nextEligibleTime) {
    document.getElementById('modalTaskTitle').innerText = task.title;
    document.getElementById('modalTaskDescription').innerText = task.description;
    document.getElementById('modalTaskTips').innerText = task.tips || 'No tips available';
    document.getElementById('modalTaskPoints').innerText = `Points: ${task.points}`;

    if (task.completion_limit && task.frequency) {
        let frequencyReadable = task.frequency.replace('Frequency.', ''); 
        frequencyReadable = frequencyReadable[0].toUpperCase() + frequencyReadable.slice(1);
        document.getElementById('modalTaskCompletionLimit').innerText = `Can be completed ${task.completion_limit} times ${frequencyReadable.toLowerCase()}.`;
    } else {
        document.getElementById('modalTaskCompletionLimit').innerText = 'No completion limits set.';
    }

    document.getElementById('modalTaskCategory').innerText = `Category: ${task.category || 'No category'}`;
    document.getElementById('modalTaskBadgeName').innerText = `Badge: ${task.badge_name || 'No badge'}`;
    document.getElementById('modalTaskCompletions').innerText = `Total Completions: ${userCompletionCount || 0}`;
    console.log(`Populating details for Task ID ${taskId}, canVerify: ${canVerify}`);

    const countdownDisplay = document.getElementById('modalCountdown');
    if (!canVerify && nextEligibleTime) {
        const nextAvailableTime = new Date(nextEligibleTime);
        if (nextAvailableTime > new Date()) {
            updateCountdown(countdownDisplay, nextAvailableTime);
        } else {
            countdownDisplay.innerText = "nextAvailableTime is greater than current time.";
        }
    } else {
        countdownDisplay.innerText = "You are eligible to verify!";
    }
    
    // Dynamically create verify button
    const verifyButton = document.createElement('button');
    verifyButton.id = `verifyButton-${taskId}`;
    verifyButton.textContent = 'Verify Task';
    verifyButton.className = 'verifyButton';
    verifyButton.onclick = function() { verifyTask(taskId); };
    verifyButton.style.display = canVerify ? 'block' : 'none';

    const userTaskData = document.querySelector('.user-task-data');
    userTaskData.appendChild(verifyButton);

    // Create form for submission
    const verifyForm = document.createElement('div');
    verifyForm.id = `verifyTaskForm-${taskId}`;
    verifyForm.innerHTML = `<form enctype="multipart/form-data">
                                <input type="file" name="image" accept="image/*" required>
                                <textarea name="verificationComment" placeholder="Enter a comment..." required></textarea>
                                <button type="submit">Submit Verification</button>
                            </form>`;
    verifyForm.style.display = 'none'; // Hide by default
    userTaskData.appendChild(verifyForm);

    setupSubmissionForm(taskId);
}

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

// Update countdown in the task modal
function updateCountdown(displayElement, nextEligibleTime) {
    const now = new Date();
    const nextAvailableTime = new Date(nextEligibleTime);
    if (nextAvailableTime > now) {
        const timeDiff = nextAvailableTime - now;
        displayElement.innerText = `You can verify in ${formatTimeDiff(timeDiff)}`;
    } else {
        displayElement.innerText = "UC nextAvailableTime is less than current time.";
    }
}

// Convert time difference in milliseconds to a readable format
function formatTimeDiff(timeDiff) {
    const days = Math.floor(timeDiff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((timeDiff / (1000 * 60 * 60)) % 24);
    const minutes = Math.floor((timeDiff / (1000 * 60)) % 60);
    const seconds = Math.floor((timeDiff / 1000) % 60);
    return `${days} days, ${hours} hours, ${minutes} minutes, and ${seconds} seconds`;
}

// Social media sharing functions
function shareOnFacebook(imageUrl) {
    const url = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(imageUrl)}`;
    window.open(url, '_blank');
}

function shareOnTwitter(imageUrl, text) {
    const url = `https://twitter.com/intent/tweet?url=${encodeURIComponent(imageUrl)}&text=${encodeURIComponent(text)}`;
    window.open(url, '_blank');
}

// Retrieve image URL and comments for sharing
function getImageUrl() {
    return document.getElementById('submissionImage').src;
}

function getComment() {
    return document.getElementById('submissionComment').textContent;
}
