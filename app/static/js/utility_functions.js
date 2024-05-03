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