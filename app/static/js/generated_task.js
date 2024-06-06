function openTaskCreationModal() {
    openModal('taskCreationModal');
}

$(document).ready(function() {
    $('#generateAITaskModal').modal({
        show: false
    });
});

document.addEventListener("DOMContentLoaded", function() {
    const buttons = document.querySelectorAll('button[data-game-id]');
    
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            openTaskCreationModal(this);
        });
    });

    function openTaskCreationModal(button) {
        const form = document.getElementById('taskCreationForm');
        const gameId = button.getAttribute('data-game-id');

        if (form) {
            form.addEventListener('submit', function(event) {
                event.preventDefault();

                const taskDescription = document.getElementById('taskDescription').value;
                const csrfToken = document.querySelector('[name=csrf_token]').value;

                fetch('/ai/generate_task', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ description: taskDescription, game_id: gameId })
                })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(data => Promise.reject({
                            status: response.status,
                            statusText: response.statusText,
                            errorMessage: data.error
                        }));
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.generated_task_html) {
                        document.getElementById('generatedTaskContent').innerHTML = data.generated_task_html;

                        $('#generateAITaskModal').modal('show');
                
                        const modalForm = document.getElementById('generateAITaskModalForm');
                        if (modalForm) {
                            modalForm.setAttribute('data-game-id', gameId);
                        }
                        if (modalForm) {
                            modalForm.addEventListener('submit', function(e) {
                                e.preventDefault();
                                const formData = new FormData(modalForm);
                                const csrfToken = document.querySelector('[name=csrf_token]').value;
                
                                fetch(`/ai/create_task`, {
                                    method: 'POST',
                                    headers: {
                                        'X-CSRFToken': csrfToken
                                    },
                                    body: formData
                                }).then(response => response.json())
                                .then(result => {
                                    // Handle the response here
                                    console.log(result);
                                }).catch(error => {
                                    console.error('Error:', error);
                                });
                            });
                        }
                    }
                })
                .catch(error => {
                    alert('Error generating task: ' + (error.errorMessage || error.statusText));
                });
            });
        } else {
            console.error("Form '#taskCreationForm' not found.");
        }
    }
});
