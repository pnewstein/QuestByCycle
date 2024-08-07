import Shepherd from 'https://cdn.jsdelivr.net/npm/shepherd.js@13.0.0/dist/esm/shepherd.mjs';

document.addEventListener('DOMContentLoaded', () => {
  console.log('Initializing Shepherd Tour...');
  
  const onboardingStatusElement = document.getElementById('onboardingStatus');
  const startOnboarding = onboardingStatusElement.getAttribute('data-start-onboarding') === 'true';
  
  // Check if onboarding is needed
  console.log('Start onboarding status:', startOnboarding);
  if (!startOnboarding) {
    console.log('Onboarding already completed for this user.');
    return; // Exit if onboarding is not needed
  }

  const tour = new Shepherd.Tour({
    useModalOverlay: true,
    defaultStepOptions: {
      classes: 'shepherd-theme-custom', // Apply custom theme
      scrollTo: false, // Disable auto-scrolling for all steps by default
      canClickTarget: false, // Allow clicking on target elements
      buttons: [
        {
          text: 'Next',
          action: () => {
            console.log('Next button clicked');
            tour.next();
          }
        }
      ]
    }
  });

  console.log('Shepherd Tour initialized:', tour);

  // Step 1: Introduction
  tour.addStep({
    id: 'introduction',
    text: 'Welcome to Quest by Cycle! Ready to explore?',
    attachTo: {
      on: 'bottom'
    },
    modalOverlayOpeningPadding: 10,
    modalOverlayOpeningRadius: 8,
    buttons: [
      {
        text: 'Next',
        action: () => {
          console.log('Next button clicked');
          tour.next();
        }
      }
    ]
  });

  console.log('Added introduction step.');

  // Step 2: Let's Get Started Button
  tour.addStep({
    id: 'lets-get-started',
    text: 'Click "Let\'s Get Started!" to learn the game rules.',
    attachTo: {
      element: '#lets-get-started-button',
      on: 'bottom'
    },
    buttons: [
      {
        text: 'Next',
        action: () => {
          console.log('Next button clicked');
          tour.next();
        }
      }
    ]
  });

  console.log('Added Let\'s Get Started button step.');

  // Step 3: Contact Us Button
  tour.addStep({
    id: 'contact-us',
    text: 'Need help or want to reach out? Click here to contact us.',
    attachTo: {
      element: '#contact-us-button',
      on: 'bottom'
    },
    buttons: [
      {
        text: 'Next',
        action: () => {
          console.log('Next button clicked');
          tour.next();
        }
      }
    ]
  });

  console.log('Added Contact Us button step.');

  // Step 4: Select Active Game Dropdown
  tour.addStep({
    id: 'select-active-game',
    text: 'Use this dropdown to select your active game.',
    attachTo: {
      element: '#gameSelectDropdown',
      on: 'bottom'
    },
    buttons: [
      {
        text: 'Next',
        action: () => {
          console.log('Next button clicked');
          tour.next();
        }
      }
    ]
  });

  console.log('Added Select Active Game dropdown step.');

  // Step 5: What's Happening Section
  tour.addStep({
    id: 'whats-happening',
    text: 'Check out what\'s happening in your current game right now!',
    attachTo: {
      element: '#whats-happening-step',
      on: 'top'
    },
    scrollTo: true, // Enable scrolling for this step
    buttons: [
      {
        text: 'Next',
        action: () => {
          console.log('Next button clicked');
          tour.next();
        }
      }
    ]
  });

  console.log('Added What\'s Happening section step.');

  // Step 6: Available Tasks Section
  tour.addStep({
    id: 'available-tasks',
    text: 'These are your available tasks. Complete them to earn points and rewards!',
    attachTo: {
      element: '#available-tasks-step',
      on: 'top'
    },
    scrollTo: true, // Enable scrolling for this step
    buttons: [
      {
        text: 'Next',
        action: () => {
          console.log('Next button clicked');
          tour.next();
        }
      }
    ]
  });

  console.log('Added Available Tasks section step.');

  // Step 7: View Profile Button
  tour.addStep({
    id: 'view-profile',
    text: 'Access your profile here to check your progress and update your information.',
    attachTo: {
      element: '#view-profile-button',
      on: 'bottom'
    },
    scrollTo: true, // Enable scrolling for this step
    buttons: [
      {
        text: 'Next',
        action: () => {
          console.log('View Profile button clicked');
          document.getElementById('view-profile-button').click(); // Open the modal
          setTimeout(() => tour.next(), 500); // Proceed to the next step after a short delay
        }
      }
    ]
  });

  console.log('Added View Profile button step.');

  // Step 8: Profile Modal - Display Name
  tour.addStep({
    id: 'profile-display-name',
    text: 'Here you can update your display name.',
    attachTo: {
      element: '#displayName',
      on: 'bottom'
    },
    canClickTarget: true, // Allow clicking on target elements
    buttons: [
      {
        text: 'Next',
        action: () => {
          console.log('Next button clicked');
          tour.next();
        }
      }
    ]
  });

  console.log('Added Display Name step.');

  // Step 9: Profile Modal - Age Group
  tour.addStep({
    id: 'profile-age-group',
    text: 'Select your age group from this dropdown.',
    attachTo: {
      element: '#ageGroup',
      on: 'bottom'
    },
    canClickTarget: true, // Allow clicking on target elements
    buttons: [
      {
        text: 'Next',
        action: () => {
          console.log('Next button clicked');
          tour.next();
        }
      }
    ]
  });

  console.log('Added Age Group step.');

  // Step 10: Profile Modal - Interests
  tour.addStep({
    id: 'profile-interests',
    text: 'Describe your interests here.',
    attachTo: {
      element: '#interests',
      on: 'bottom'
    },
    canClickTarget: true, // Allow clicking on target elements
    scrollTo: true, // Enable scrolling for this step
    buttons: [
      {
        text: 'Next',
        action: () => {
          console.log('Next button clicked');
          tour.next();
        }
      }
    ]
  });

  console.log('Added Interests step.');

  // Step 11: Profile Modal - Riding Preferences
  tour.addStep({
    id: 'profile-riding-preferences',
    text: 'Check your riding preferences.',
    attachTo: {
      element: '#ridingPreferences',
      on: 'bottom'
    },
    canClickTarget: true, // Allow clicking on target elements
    scrollTo: true, // Enable scrolling for this step
    buttons: [
      {
        text: 'Next',
        action: () => {
          console.log('Next button clicked');
          tour.next();
        }
      }
    ]
  });

  console.log('Added Riding Preferences step.');

  // Step 12: Profile Modal - Ride Description
  tour.addStep({
    id: 'profile-ride-description',
    text: 'Describe the type of riding you like to do.',
    attachTo: {
      element: '#rideDescription',
      on: 'bottom'
    },
    canClickTarget: true, // Allow clicking on target elements
    scrollTo: true, // Enable scrolling for this step
    buttons: [
      {
        text: 'Next',
        action: () => {
          console.log('Next button clicked');
          tour.next();
        }
      }
    ]
  });

  console.log('Added Ride Description step.');

  // Step 13: Profile Modal - Upload to Social Media
  tour.addStep({
    id: 'profile-upload-to-socials',
    text: 'Enable this option to upload your activities to social media.',
    attachTo: {
      element: '#uploadToSocials',
      on: 'bottom'
    },
    canClickTarget: true, // Allow clicking on target elements
    scrollTo: true, // Enable scrolling for this step
    buttons: [
      {
        text: 'Next',
        action: () => {
          console.log('Next button clicked');
          tour.next();
        }
      }
    ]
  });

  console.log('Added Upload to Social Media step.');

  // Step 14: Profile Modal - Save Profile
  tour.addStep({
    id: 'profile-save',
    text: 'Finally, save your profile with this button.',
    attachTo: {
      element: '#editProfileForm .btn-primary',
      on: 'bottom'
    },
    canClickTarget: true, // Allow the user to click the target element
    advanceOn: {
      selector: '#editProfileForm .btn-primary', // Selector for the Save Profile button
      event: 'click' // The event that will trigger advancing to the next step
    },
    modalOverlayOpeningPadding: 10,
    modalOverlayOpeningRadius: 8,
    // No buttons, as we want the user to click the element
  });

  console.log('Added Save Profile step.');

  // Step 15: Final Completion Step
  tour.addStep({
    id: 'completion-step',
    text: 'Congratulations, you have completed the onboarding!',
    buttons: [
      {
        text: 'Finish',
        action: () => {
          console.log('Onboarding completed');
          markOnboardingComplete(); // Trigger the onboarding complete function
          tour.complete();
        }
      }
    ]
  });

  console.log('Added completion step.');

  // Start the tour automatically on page load
  tour.start();
  console.log('Shepherd Tour started.');

  // Function to send a request to mark onboarding as complete
  function markOnboardingComplete() {
    const userId = document.querySelector('meta[name="current-user-id"]').getAttribute('content'); // Fetch user ID
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content'); // Fetch CSRF token

    fetch('/mark-onboarding-complete', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken // Set CSRF token header
      },
      body: JSON.stringify(userId) // Include user ID in the request body
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        console.log('Onboarding marked as complete.');
        // Optionally, redirect or refresh the page
        location.reload();
      } else {
        console.error('Failed to mark onboarding as complete.');
      }
    })
    .catch(error => {
      console.error('Error:', error);
    });
  }
});
