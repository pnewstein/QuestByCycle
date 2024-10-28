// User management functions
document.getElementById('userDropdown').addEventListener('change', function() {
    var userId = this.value;
    if (userId) {
        fetch('/admin/user_details/' + userId)
            .then(response => response.json())
            .then(data => {
                document.getElementById('userForm').action = '/admin/update_user/' + data.id;
                document.getElementById('deleteUserForm').action = '/admin/delete_user/' + data.id;
                document.getElementById('username').value = data.username;
                document.getElementById('email').value = data.email;
                document.getElementById('is_admin').checked = data.is_admin;
                document.getElementById('is_super_admin').checked = data.is_super_admin;
                document.getElementById('license_agreed').checked = data.license_agreed;
                document.getElementById('score').value = data.score;
                document.getElementById('display_name').value = data.display_name;
                document.getElementById('profile_picture').value = data.profile_picture;
                document.getElementById('age_group').value = data.age_group;
                document.getElementById('interests').value = data.interests;
                document.getElementById('email_verified').checked = data.email_verified;

                var participatedGamesList = document.getElementById('participatedGamesList');
                participatedGamesList.innerHTML = '';
                data.participated_games.forEach(function(game) {
                    var listItem = document.createElement('li');
                    listItem.textContent = game.title;
                    participatedGamesList.appendChild(listItem);
                });

                document.getElementById('userDetails').style.display = 'block';
            })
            .catch(error => console.error('Error:', error));
    } else {
        document.getElementById('userDetails').style.display = 'none';
    }
});

function confirmUpdate() {
    return confirm("Are you sure you want to update this user?");
}

function confirmDelete() {
    return confirm("Are you sure you want to delete this user?");
}

document.getElementById('gameFilter').addEventListener('change', function() {
    var gameId = this.value;
    if (gameId) {
        window.location.href = '/admin/user_management/game/' + gameId;
    } else {
        window.location.href = '/admin/user_management';
    }
});