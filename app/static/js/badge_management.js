// Badge management functions
document.addEventListener('DOMContentLoaded', function() {
    loadBadges();
});

function loadBadges() {
    fetch('/badges/badges')
        .then(response => response.json())
        .then(data => {
            const badgesBody = document.getElementById('badgesBody');
            badgesBody.innerHTML = '';
            data.badges.forEach(badge => {
                const row = document.createElement('tr');
                row.setAttribute('data-badge-id', badge.id);

                const imageHTML = badge.image ? `<img src="${badge.image}" height="50" alt="Badge Image">` : 'No Image';

                row.innerHTML = `
                    <td class="badge-image-manage">${imageHTML}</td>
                    <td class="badge-name">${badge.name}</td>
                    <td class="badge-description">${badge.description}</td>
                    <td class="badge-category">${badge.category}</td>
                    <td>
                        <button class="edit-badge" onclick="editBadge(${badge.id})">Edit</button>
                        <button onclick="deleteBadge(${badge.id})">Delete</button>
                    </td>
                `;
                badgesBody.appendChild(row);
            });
        })
        .catch(error => console.error('Failed to load badges:', error));
}

function toggleForm(formId) {
    var form = document.getElementById(formId);
    if (form.style.display === "none") {
        form.style.display = "block";
    } else {
        form.style.display = "none";
    }
}

// Existing JavaScript code remains the same

function editBadge(badgeId) {
    const row = document.querySelector(`tr[data-badge-id='${badgeId}']`);
    if (!row) {
        console.error(`Badge row with ID ${badgeId} not found.`);
        return;
    }
    const nameCell = row.querySelector('.badge-name');
    const descriptionCell = row.querySelector('.badge-description');
    const categoryCell = row.querySelector('.badge-category');
    const imageCell = row.querySelector('.badge-image img');

    nameCell.innerHTML = `<input type="text" value="${nameCell.innerText.trim()}" class="form-control badge-name-input">`;
    descriptionCell.innerHTML = `<textarea class="form-control badge-description-textarea">${descriptionCell.innerText.trim()}</textarea>`;
    imageCell.parentNode.innerHTML = `<input type="file" class="form-control-file badge-image-input">`;

    setCategoryOptions(categoryCell.innerText.trim()).then(categoryHtml => {
        categoryCell.innerHTML = categoryHtml;
        const editButton = row.querySelector(`button.edit-badge`);
        editButton.innerText = 'Save';
        editButton.onclick = () => saveBadge(badgeId);
    });
}

function saveBadge(badgeId) {
    const row = document.querySelector(`tr[data-badge-id='${badgeId}']`);
    const formData = new FormData();
    formData.append('name', row.querySelector('.badge-name-input').value);
    formData.append('description', row.querySelector('.badge-description-textarea').value);
    formData.append('category', row.querySelector('.badge-category-select').value);
    const imageInput = row.querySelector('.badge-image-input');
    if (imageInput.files.length > 0) {
        formData.append('image', imageInput.files[0]);
    }

    fetch(`/badges/update/${badgeId}`, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        }
    }).then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Badge updated successfully');
            window.location.reload();
        } else {
            alert('Failed to update badge: ' + data.message);
        }
    })
    .catch(error => console.error('Error updating badge:', error));
}

function deleteBadge(badgeId) {
    if (!confirm("Are you sure you want to delete this badge?")) return;

    fetch(`/badges/delete/${badgeId}`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content'),
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.reload();
        } else {
            alert(`Failed to delete badge: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error deleting badge:', error);
        alert('Error deleting badge. Please check console for details.');
    });
}

function uploadImages() {
    const formData = new FormData(document.getElementById('uploadForm'));
    fetch('/badges/upload_images', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content'),
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Images uploaded successfully');
        } else {
            alert('Failed to upload images: ' + data.message);
        }
    })
    .catch(error => console.error('Error uploading images:', error));
}