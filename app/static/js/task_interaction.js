// task_interaction.js
let isSubmitting = false;

function openTaskDetailModal(taskId) {
    resetModalContent();
    document.body.classList.add('body-no-scroll');

    fetch(`/tasks/detail/${taskId}/user_completion`)
        .then(response => response.json())
        .then(data => {
            const task = data.task;
            const userCompletion = data.userCompletion;
            const canVerify = data.canVerify;
            const nextEligibleTime = data.nextEligibleTime;

            populateTaskDetails(task, userCompletion.completions, canVerify, taskId, nextEligibleTime);
            fetchSubmissions(taskId);

            document.getElementById('taskDetailModal').style.display = 'block';
        })
        .catch(error => {
            console.error('Error opening task detail modal:', error);
            alert('Failed to load task details.');
        });
}

function submitTaskDetails(event, taskId) {
    event.preventDefault();

    if (isSubmitting) {
        return;
    }
    isSubmitting = true;

    const form = event.target;
    const formData = new FormData(form);

    fetch(`/tasks/task/${taskId}/submit`, {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content'),
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('total-points').innerText = `Total Completed Points: ${data.total_points}`;
            alert('Submission successful!');
            // Fetch the updated task details and submissions
            openTaskDetailModal(taskId);
        } else {
            alert('Submission failed: ' + data.message);
        }
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
            const images = submissions.reverse().map(submission => {
                return {
                    url: submission.image_url,
                    alt: "Submission Image",
                    comment: submission.comment, 
                    user_id: submission.user_id
                };
            });
            distributeImages(images);
        })
        .catch(error => {
            console.error('Failed to fetch submissions:', error.message);
            alert('Could not load submissions. Please try again.');
        });
}

function distributeImages(images) {
    const board = document.getElementById('submissionBoard');
    board.innerHTML = ''; 
    const modalWidth = board.clientWidth; 
    const desiredColumnWidth = 150;
    const columnCount = Math.floor(modalWidth / desiredColumnWidth);
    const columns = [];

    // Create columns and append to the board
    for (let i = 0; i < columnCount; i++) {
        const column = document.createElement('div');
        column.className = 'photo-column';
        board.appendChild(column);
        columns.push(column);
    }

    // Add new images at the top of their respective columns
    images.forEach((image, index) => {
        const img = document.createElement('img');
        img.src = image.url;
        img.alt = "Loaded Image";
        img.onerror = () => {
            img.src = document.getElementById('taskDetailModal').getAttribute('data-placeholder-url');
        };
        img.onclick = () => showSubmissionDetail(image);
        // Prepend to column to make new images appear at the top
        columns[index % columnCount].prepend(img);
    });
}

function showSubmissionDetail(image) {
    const submissionModal = document.getElementById('submissionDetailModal');
    document.getElementById('submissionImage').src = image.url;
    document.getElementById('submissionComment').textContent = image.comment || 'No comment provided.';
    document.getElementById('submissionUserLink').onclick = function() {
        openUserProfile(image.user_id);
        return false; // Prevent default link behavior
    };
    document.getElementById('downloadLink').href = image.url;
    document.getElementById('downloadLink').download = `Image-${image.user_id}`;

    submissionModal.style.display = 'block';
    submissionModal.style.backgroundColor = 'rgba(0,0,0,0.7)';
}

function verifyTask(taskId) {
    const verifyForm = document.getElementById(`verifyTaskForm-${taskId}`);
    if (verifyForm.style.display === 'none' || verifyForm.style.display === '') {
        verifyForm.style.display = 'block';  // Show the form
    } else {
        verifyForm.style.display = 'none';  // Hide the form
    }
}

function getNextAvailableTime(lastRelevantDate, frequency) {
    const lastCompletionDate = new Date(lastRelevantDate);
    let nextAvailableDate;

    switch (frequency.toLowerCase()) {
        case 'daily':
            nextAvailableDate = new Date(lastCompletionDate.getTime() + (24 * 60 * 60 * 1000));
            break;
        case 'weekly':
            nextAvailableDate = new Date(lastCompletionDate.getTime() + (4 * 60 * 1000));
            break;
        case 'monthly':
            const month = lastCompletionDate.getMonth();
            nextAvailableDate = new Date(lastCompletionDate.setMonth(month + 1));
            break;
        default:
            nextAvailableDate = new Date(); 
    }

    return nextAvailableDate;
}

function updateCountdownFromLastRelevant(nextEligibleTime, frequency) {
    const countdownDisplay = document.getElementById('modalCountdown');
    const nextAvailableTime = new Date(nextEligibleTime);
    const now = new Date();

    if (nextAvailableTime > now) {
        const timeDiff = nextAvailableTime - now;
        countdownDisplay.innerText = `You can verify in ${formatTimeDiff(timeDiff)}`;
    } else {
        countdownDisplay.innerText = "UCLR nextAvailableTime is less than current time.";
    }
}
