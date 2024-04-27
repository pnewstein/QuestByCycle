// utility_functions.js

function shareOnFacebook() {
    const url = encodeURIComponent(document.getElementById('submissionImage').src); // Shares the URL of the page
    const facebookUrl = `https://www.facebook.com/sharer/sharer.php?u=${url}`;
    window.open(facebookUrl, '_blank', 'height=600,width=600,scrollbars=yes,status=yes');
}

function shareOnTwitter() {
    const imageUrl = encodeURIComponent(document.getElementById('submissionImage').src);
    const text = encodeURIComponent("Check out my achievement!"); // Text to accompany the image in the tweet
    const hashtags = encodeURIComponent("questbycycle"); // Relevant hashtags
    const twitterUrl = `https://twitter.com/intent/tweet?text=${text}&url=${imageUrl}&hashtags=${hashtags}`;

    window.open(twitterUrl, '_blank', 'location=yes,height=570,width=520,scrollbars=yes,status=yes');
}

function formatTimeDiff(timeDiff) {
    const days = Math.floor(timeDiff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((timeDiff / (1000 * 60 * 60)) % 24);
    const minutes = Math.floor((timeDiff / (1000 * 60)) % 60);
    const seconds = Math.floor((timeDiff / 1000) % 60);
    return `${days} days, ${hours} hours, ${minutes} minutes, and ${seconds} seconds`;
}