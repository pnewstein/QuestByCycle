// badge_modal.js

// Cache all badges in a global variable once loaded
window.allBadges = window.allBadges || [];

/**
 * Load all badges from the server endpoint (/badges/badges) if not already cached.
 * Calls the provided callback with the badge array.
 */
function loadAllBadges(callback) {
  if (window.allBadges.length > 0) {
    callback(window.allBadges);
  } else {
    fetch('/badges/badges')
      .then(response => {
        if (!response.ok) {
          throw new Error("Error fetching badges");
        }
        return response.json();
      })
      .then(data => {
        window.allBadges = data.badges; // Assume data.badges is the array of badge objects
        callback(window.allBadges);
      })
      .catch(error => {
        console.error("Error loading badges:", error);
        callback([]);  // Return an empty array on error
      });
  }
}

/**
 * Open the badge modal and populate it with data.
 * @param {HTMLElement} element - The badge element that was clicked.
 */
function openBadgeModal(element) {
  const badgeId = element.getAttribute('data-badge-id');
  const earned = element.getAttribute('data-earned') === 'true';
  
  // Load all badges and then find the badge details
  loadAllBadges(function(badges) {
    const badge = badges.find(b => b.id == badgeId);
    if (!badge) {
      alert("Badge not found.");
      return;
    }
  
    // Get modal elements
    const modalTitle = document.getElementById('badgeModalTitle');
    const modalImage = document.getElementById('badgeModalImage');
    const modalText = document.getElementById('badgeModalText');
    
    // Set the modal title and image source
    modalTitle.textContent = badge.name;
    modalImage.src = (badge.image || 'default_badge.png');
  
    // Update the image style and text based on whether the badge is earned
    if (earned) {
      modalImage.style.filter = "none";
      modalText.innerHTML = `<p><strong>Awarded!</strong></p><p>${badge.description}</p>`;
    } else {
      modalImage.style.filter = "grayscale(100%) opacity(0.5)";
      modalText.innerHTML = `<p><strong>Not Awarded Yet</strong></p><p>To earn this badge, ${badge.description}</p>`;
    }
  
    // Open the modal (assumes you have an openModal function)
    openModal('badgeModal');
  });
}

/**
 * Close the badge modal.
 */
function closeBadgeModal() {
  document.getElementById('badgeModal').style.display = 'none';
}
