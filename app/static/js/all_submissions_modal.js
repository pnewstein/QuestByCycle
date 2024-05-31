// All submissions modal management functions
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

function fetchAllSubmissions() {
    fetch('/tasks/task/all_submissions')
    .then(response => response.json())
    .then(data => {
        displayAllSubmissions(data);
    })
    .catch(error => {
        console.error('Error fetching all submissions:', error);
        alert('Failed to fetch all submissions: ' + error.message);
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
            deleteSubmission(submission.id, 'allSubmissions');
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

function deleteSubmission(submissionId, modalType) {
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
            // Refresh based on modal type
            if (modalType === 'mySubmissions') {
                fetchMySubmissions();  // Fetch and refresh my submissions
            } else if (modalType === 'allSubmissions') {
                fetchAllSubmissions();  // Fetch and refresh all submissions
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

function closeAllSubmissionsModal() {
    const allSubmissionsModal = document.getElementById('allSubmissionsModal');
    allSubmissionsModal.style.display = 'none';
    allSubmissionsModal.style.backgroundColor = ''; // Reset background color to default
    document.body.classList.remove('body-no-scroll');
}
