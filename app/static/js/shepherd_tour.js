import Shepherd from 'https://cdn.jsdelivr.net/npm/shepherd.js@13.0.0/dist/esm/shepherd.mjs';

document.addEventListener('DOMContentLoaded', () => {
  console.log('Initializing Shepherd Tour...');
  
  const onboardingStatusElement = document.getElementById('onboardingStatus');
  const startOnboarding = onboardingStatusElement ? onboardingStatusElement.getAttribute('data-start-onboarding') === 'true' : false;

  // Initialize Shepherd tour
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
            updateStepCounter();
          }
        }
      ]
    }
  });

  console.log('Shepherd Tour initialized:', tour);

  // Define steps
  const steps = [
    {
      id: 'introduction',
      text: 'Welcome to Quest by Cycle! Ready to start your journey? Please fill out your profile!',
      attachTo: { on: 'top' },
      modalOverlayOpeningPadding: 10,
      modalOverlayOpeningRadius: 8,
    },
    {
      id: 'view-profile',
      text: 'Access your profile here.',
      attachTo: { element: '#view-profile-button', on: 'top' },
      scrollTo: true,
      buttons: [
        {
          text: 'Next',
          action: () => {
            console.log('View Profile button clicked');
            document.getElementById('view-profile-button').click(); // Open the modal
            setTimeout(() => {
              tour.next();
              updateStepCounter();
              console.log('Onboarding completed');
              markOnboardingComplete(); // Trigger the onboarding complete function
              tour.complete();
            }, 200); // Proceed to the next step after a short delay
          }
        }
      ]
    }
  ];

  // Add steps to the tour
  steps.forEach((step, index) => {
    step.buttons = step.buttons || [
      {
        text: `Next (${index + 1}/${steps.length})`,
        action: () => {
          tour.next();
          updateStepCounter();
        }
      }
    ];
    tour.addStep(step);
  });

  // Function to update step counter
  function updateStepCounter() {
    const currentStep = tour.getCurrentStep();
    if (currentStep && currentStep.buttons && currentStep.buttons.length > 0) {
      const currentIndex = steps.findIndex(step => step.id === currentStep.id) + 1;
      const totalSteps = steps.length;
      const nextButton = currentStep.buttons[0].text;
      if (nextButton.includes('Next')) {
        currentStep.updateButton(0, { text: `Next (${currentIndex}/${totalSteps})` });
      }
    }
  }

  console.log('Steps added to the tour.');

  // Start the tour automatically if needed
  if (startOnboarding) {
    tour.start();
    console.log('Shepherd Tour started automatically.');
  }

  // Function to send a request to mark onboarding as complete
  function markOnboardingComplete() {
    const userIdMeta = document.querySelector('meta[name="current-user-id"]');
    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    
    if (!userIdMeta || !csrfTokenMeta) {
      console.error('Meta tags for user ID or CSRF token not found.');
      return;
    }

    const userId = userIdMeta.getAttribute('content');
    const csrfToken = csrfTokenMeta.getAttribute('content');

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
      } else {
        console.error('Failed to mark onboarding as complete.');
      }
    })
    .catch(error => {
      console.error('Error:', error);
    });
  }

  // Add the event listener for the "Show me a tour" link
  const restartTourLink = document.getElementById('restart-tour-link');
  if (restartTourLink) {
    restartTourLink.addEventListener('click', () => {
      console.log('Restarting Shepherd Tour...');
      tour.start(); // Start the tour when the link is clicked
      updateStepCounter(); // Ensure step counter is updated
    });
  }
});
