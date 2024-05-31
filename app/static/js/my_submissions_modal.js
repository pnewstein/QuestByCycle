// My submissions modal management functions
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

function fetchMySubmissions() {
    fetch('/tasks/task/my_submissions')
    .then(response => response.json())
    .then(data => {
        if (data.length > 0) {
            displayMySubmissions(data);
        } else {
            document.getElementById('submissionsContainer').innerHTML = 'No submissions to display.';
        }
    })
    .catch(error => {
        console.error('Error fetching submissions:', error);
        alert('Failed to fetch submissions: ' + error.message);
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
            deleteSubmission(submission.id, 'mySubmissions');
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

function closeMySubmissionsModal() {
    const mySubmissionsModal = document.getElementById('mySubmissionsModal');
    mySubmissionsModal.style.display = 'none';
    mySubmissionsModal.style.backgroundColor = ''; // Reset background color to default
    document.body.classList.remove('body-no-scroll');
}