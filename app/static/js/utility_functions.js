// utility_functions.js

function shareOnFacebook(taskId) {
    const url = `tasks/task/${taskId}/share`;
    const shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`;
    window.open(shareUrl, '_blank');
}

function shareOnTwitter(taskId, text) {
    const url = `tasks/task/${taskId}/share`;
    const shareUrl = `https://twitter.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`;
    window.open(shareUrl, '_blank');
}

function formatTimeDiff(timeDiff) {
    const days = Math.floor(timeDiff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((timeDiff / (1000 * 60 * 60)) % 24);
    const minutes = Math.floor((timeDiff / (1000 * 60)) % 60);
    const seconds = Math.floor((timeDiff / 1000) % 60);
    return `${days} days, ${hours} hours, ${minutes} minutes, and ${seconds} seconds`;
}