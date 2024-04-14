// utility_functions.js

function shareOnFacebook(imageUrl) {
    const url = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(imageUrl)}`;
    window.open(url, '_blank');
}

function shareOnTwitter(imageUrl, text) {
    const url = `https://twitter.com/intent/tweet?url=${encodeURIComponent(imageUrl)}&text=${encodeURIComponent(text)}`;
    window.open(url, '_blank');
}

function formatTimeDiff(timeDiff) {
    const days = Math.floor(timeDiff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((timeDiff / (1000 * 60 * 60)) % 24);
    const minutes = Math.floor((timeDiff / (1000 * 60)) % 60);
    const seconds = Math.floor((timeDiff / 1000) % 60);
    return `${days} days, ${hours} hours, ${minutes} minutes, and ${seconds} seconds`;
}

function incrementCompletion(taskId) {
    fetch(`/tasks/adjust_completion/${taskId}/increment`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content'),
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({}) 
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            document.getElementById('modalTaskCompletions').innerText = `Total Completions: ${data.new_completions_count}`;

            document.getElementById('total-points').innerText = `Total Completed Points: ${data.total_points}`;
        } else {
            console.error('Increment failed:', data.error);
        }
    })
    .catch(error => console.error('Error incrementing task completions:', error));
}