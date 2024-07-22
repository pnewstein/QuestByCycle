// Submission detail modal management functions
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

    // Update the Twitter link if available
    const twitterLink = document.getElementById('twitterLink');
    if (image.verification_type !== 'comment' && image.twitter_url && isValidUrl(image.twitter_url)) {
        twitterLink.href = image.twitter_url;
        twitterLink.style.display = 'inline';  // Show the Twitter link if a URL is available and not using the placeholder image
    } else {
        twitterLink.style.display = 'none';  // Hide the Twitter link if using the placeholder image or no URL is available
    }

    // Update the Facebook link if available
    const facebookLink = document.getElementById('facebookLink');
    if (image.fb_url && isValidUrl(image.fb_url)) {
        facebookLink.href = image.fb_url;
        facebookLink.style.display = 'inline';  // Show the Facebook link if a URL is available
    } else {
        facebookLink.style.display = 'none';  // Hide the Facebook link if no URL is available
    }

    // Update the Instagram link if available
    const instagramLink = document.getElementById('instagramLink');
    if (image.instagram_url && isValidUrl(image.instagram_url)) {
        instagramLink.href = image.instagram_url;
        instagramLink.style.display = 'inline';  // Show the Instagram link if a URL is available
    } else {
        instagramLink.style.display = 'none';  // Hide the Instagram link if no URL is available
    }

    submissionModal.style.display = 'block';
    submissionModal.style.backgroundColor = 'rgba(0,0,0,0.7)';
}

function closeSubmissionDetailModal() {
    const submissionModal = document.getElementById('submissionDetailModal');
    submissionModal.style.display = 'none';
    submissionModal.style.backgroundColor = ''; // Reset background color to default
    document.body.classList.remove('body-no-scroll');
}

function closeSponsorsModal() {
    const sponsorsModal = document.getElementById('sponsorsModal');
    sponsorsModal.style.display = 'none';
    sponsorsModal.style.backgroundColor = ''; // Reset background color to default
    document.body.classList.remove('body-no-scroll');
}


function isValidUrl(string) {
    try {
        new URL(string);
        return true;
    } catch (_) {
        return false;  // Fails to construct a URL, it's likely not a valid URL
    }
}
