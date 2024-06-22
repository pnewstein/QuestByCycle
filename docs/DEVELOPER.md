# DEVELOPER.md

Welcome to the Developer Guide for our Ultimate Challenge and Reward Platform! This document will provide you with an in-depth understanding of the architecture, codebase, and development practices. Whether you're adding new features, fixing bugs, or maintaining the system, this guide will help you navigate the code and understand its intricacies.

## Table of Contents

1. [Project Structure](#project-structure)
    - [Directory Overview](#directory-overview)
    - [Important Files](#important-files)
2. [Setting Up the Development Environment](#setting-up-the-development-environment)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
    - [Configuration](#configuration)
3. [Key Components](#key-components)
    - [Flask Blueprints](#flask-blueprints)
    - [Database Models](#database-models)
    - [Forms](#forms)
    - [Utilities](#utilities)
4. [Admin Functionality](#admin-functionality)
    - [Admin Dashboard](#admin-dashboard)
    - [Badge Management](#badge-management)
    - [Task Management](#task-management)
    - [Shout Board](#shout-board)
5. [User Functionality](#user-functionality)
    - [Task Submission](#task-submission)
    - [Profile Management](#profile-management)
    - [Social Media Integration](#social-media-integration)
6. [AI Task Generation](#ai-task-generation)
7. [Static Assets](#static-assets)
    - [CSS](#css)
    - [JavaScript](#javascript)
    - [Images and Videos](#images-and-videos)
8. [Testing and Debugging](#testing-and-debugging)
    - [Running Tests](#running-tests)
    - [Debugging](#debugging)
9. [Deployment](#deployment)
    - [Production Configuration](#production-configuration)
    - [Deployment Steps](#deployment-steps)

## Project Structure

### Directory Overview

The project is organized as follows:

- `app/`: The main application directory.
  - `static/`: Contains static assets like CSS, JavaScript, images, and fonts.
    - `carousel_images/`: Images used in the homepage carousel.
    - `css/`: Stylesheets.
    - `js/`: JavaScript files.
    - `qr_codes/`: QR code images.
    - `videos/`: Video files.
    - `webfonts/`: Font files.
  - `templates/`: Contains HTML templates for rendering views.
    - `modals/`: Templates for modal dialogs.
  - `__init__.py`: Initializes the Flask application.
  - `admin.py`: Admin-specific routes and logic.
  - `ai.py`: AI task generation logic.
  - `auth.py`: Authentication routes and logic.
  - `badges.py`: Badge management logic.
  - `config.py`: Configuration settings.
  - `forms.py`: WTForms definitions.
  - `games.py`: Game management logic.
  - `main.py`: Main routes and views.
  - `models.py`: SQLAlchemy models.
  - `profile.py`: User profile management logic.
  - `social.py`: Social media integration logic.
  - `tasks.py`: Task management and submission logic.
  - `utils.py`: Utility functions.
- `csv/`: Contains CSV files for bulk data import.
- `docs/`: Documentation files.
- `migrations/`: Database migration scripts.
- `venv/`: Virtual environment directory.
- `.gitignore`: Git ignore file.
- `config.toml`: Configuration file.
- `LICENSE.md`: License information.
- `README.md`: Project overview and setup instructions.
- `requirements.txt`: Python dependencies.
- `wsgi.py`: WSGI entry point for deploying the application.

### Important Files

- **`app/__init__.py`**: Initializes the Flask application and registers blueprints.
- **`app/models.py`**: Defines the database models.
- **`app/forms.py`**: Defines the forms used in the application.
- **`app/utils.py`**: Contains utility functions used across the application.
- **`app/templates/`**: Contains HTML templates for rendering views.
- **`requirements.txt`**: Lists the dependencies required for the project.

## Setting Up the Development Environment

### Prerequisites

Ensure you have the following installed:

- Python 3.x
- PostgreSQL
- Virtualenv

### Installation

1. **Clone the repository**:
   \`\`\`bash
   git clone https://github.com/your-repo/your-project.git
   cd your-project
   \`\`\`

2. **Create a virtual environment**:
   \`\`\`bash
   python3 -m venv venv
   source venv/bin/activate
   \`\`\`

3. **Install dependencies**:
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

4. **Set up the database**:
   Create a PostgreSQL database and update the `config.toml` file with your database credentials.

5. **Run database migrations**:
   \`\`\`bash
   flask db upgrade
   \`\`\`

### Configuration

Update the `config.toml` file with the appropriate configuration settings for your development environment.

## Key Components

### Flask Blueprints

The application is modularized using Flask Blueprints:

- **`main_bp`**: Main routes and views (defined in `main.py`).
- **`admin_bp`**: Admin-specific routes and views (defined in `admin.py`).
- **`auth_bp`**: Authentication routes and views (defined in `auth.py`).
- **`badges_bp`**: Badge management routes and views (defined in `badges.py`).
- **`ai_bp`**: AI task generation routes and views (defined in `ai.py`).
- **`profile_bp`**: User profile management routes and views (defined in `profile.py`).
- **`tasks_bp`**: Task management and submission routes and views (defined in `tasks.py`).

### Database Models

The database models are defined in `app/models.py` and include:

- **`User`**: Represents a user in the system.
- **`Game`**: Represents a game that users can participate in.
- **`Task`**: Represents a task that users can complete.
- **`Badge`**: Represents a badge that users can earn.
- **`UserTask`**: Represents a user's completion of a task.
- **`TaskSubmission`**: Represents a user's submission for a task.
- **`ShoutBoardMessage`**: Represents a message posted on the Shout Board.

### Forms

Forms are defined using WTForms in `app/forms.py` and include:

- **`ProfileForm`**: Form for updating user profiles.
- **`ShoutBoardForm`**: Form for posting messages on the Shout Board.
- **`TaskForm`**: Form for creating and updating tasks.
- **`PhotoForm`**: Form for submitting photos for task verification.
- **`ContactForm`**: Form for contacting support.

### Utilities

Utility functions are defined in `app/utils.py` and include:

- **`save_profile_picture`**: Saves profile pictures.
- **`save_badge_image`**: Saves badge images.
- **`update_user_score`**: Updates a user's score.
- **`award_badges`**: Awards badges to users.
- **`can_complete_task`**: Checks if a user can complete a task.
- **`send_email`**: Sends emails.

## Admin Functionality

### Admin Dashboard

The admin dashboard provides an overview of the platform's activity and allows admins to manage various aspects of the system. It includes:

- **User Management**: View and manage user accounts.
- **Game Management**: Create, update, and delete games.
- **Task Management**: Create, update, and delete tasks.
- **Badge Management**: Create, update, and delete badges.
- **Shout Board Management**: View and delete Shout Board messages.

### Badge Management

Admins can manage badges using the following routes:

- **Create Badge**: `/badges/create`
- **Manage Badges**: `/badges/manage_badges`
- **Update Badge**: `/badges/update/<int:badge_id>`
- **Delete Badge**: `/badges/delete/<int:badge_id>`

### Task Management

Admins can manage tasks using the following routes:

- **Create Task**: `/tasks/<int:game_id>/add_task`
- **Manage Tasks**: `/tasks/<int:game_id>/manage_tasks`
- **Update Task**: `/tasks/task/<int:task_id>/update`
- **Delete Task**: `/tasks/task/<int:task_id>/delete`

### Shout Board

The Shout Board allows admins to post and pin messages that are viewable by all users. Admins can manage Shout Board messages using the following routes:

- **Post Message**: `/shout-board`
- **Pin Message**: `/pin_message/<int:message_id>`
- **Delete Message**: Managed via the admin dashboard.

## User Functionality

### Task Submission

Users can complete tasks and submit verification using the following routes:

- **Submit Task**: `/tasks/task/<int:task_id>/submit`
- **View Task Submissions**: `/tasks/task/<int:task_id>/submissions`
- **Delete Submission**: `/tasks/task/delete_submission/<int:submission_id>`

### View User Submissions

Users can view their submissions using the following routes:

- **View My Submissions**: `/tasks/task/my_submissions`
- **Delete My Submission**: `/tasks/task/delete_submission/<int:submission_id>`

### Profile Management

Users can manage their profiles using the following routes:

- **View Profile**: `/profile/<int:user_id>`
- **Edit Profile**: `/profile/<int:user_id>/edit`
- **Post Message on Profile Wall**: `/profile/<int:user_id>/messages`
- **Delete Profile Wall Message**: `/profile/<int:user_id>/messages/<int:message_id>/delete`
- **Reply to Profile Wall Message**: `/profile/<int:user_id>/messages/<int:message_id>/reply`
- **Edit Profile Wall Message**: `/profile/<int:user_id>/messages/<int:message_id>/edit`

### Social Media Integration

Users can integrate their social media accounts to share their achievements:

- **Twitter Integration**: Post task completions on Twitter.
- **Facebook Integration**: Share task completions and photos on Facebook.
- **Instagram Integration**: Post photos related to task completions on Instagram.

## AI Task Generation

Our platform leverages AI to generate new tasks for users. This functionality is powered by OpenAI and involves the following steps:

1. **Generate Task**: `/ai/generate_task`
   - This route accepts a task description and uses OpenAI to generate task details such as title, description, tips, points, completion limit, frequency, verification type, badge name, and badge description.
   
2. **Create Task**: `/ai/create_task`
   - After generating task details, this route creates the task in the database.

3. **Generate Badge Image**: `/ai/generate_badge_image`
   - This route uses OpenAI to generate a badge image based on the badge description.

## Static Assets

### CSS

Stylesheets are located in `app/static/css` and include:

- `all.min.css`
- `atom-one-dark.min.css`
- `bootstrap.min.css`
- `highlight.min.js`
- `katex.min.css`
- `main1.css`
- `quill.snow.css`

### JavaScript

JavaScript files are located in `app/static/js` and include:

- `admin_dashboard.js`
- `all_submissions_modal.js`
- `badge_management.js`
- `bootstrap.min.js`
- `contact_modal.js`
- `edit_carousel_modal.js`
- `generated_task.js`
- `highlight.min.js`
- `index_management.js`
- `join_custom_game_modal.js`
- `jquery-3.6.0.min.js`
- `katex.min.js`
- `leaderboard_modal.js`
- `modal_common.js`
- `popper.min.js`
- `quill.min.js`
- `submission_detail_modal.js`
- `task_detail_modal.js`
- `user_management.js`
- `user_profile_modal.js`

### Images and Videos

Images and videos are located in `app/static/images`, `app/static/qr_codes`, and `app/static/videos`. The `carousel_images` directory contains images used in the homepage carousel.

## Testing and Debugging

### Running Tests

Tests are crucial for maintaining the integrity of the codebase. To run tests:

1. **Navigate to the project directory**:
   \`\`\`bash
   cd your-project
   \`\`\`

2. **Run tests**:
   \`\`\`bash
   pytest
   \`\`\`

### Debugging

To enable debugging, update the `config.toml` file to set `DEBUG = true`. This will enable Flask's debugger, providing detailed error messages and an interactive debugger in the browser.

## Deployment

### Production Configuration

Before deploying to production, ensure the following settings in `config.toml`:

- `DEBUG = false`
- `SESSION_COOKIE_SECURE = true`
- `SQLALCHEMY_DATABASE_URI` is set to the production database URL.
- `SECRET_KEY` is set to a secure value.

### Deployment Steps

1. **Set up the server**:
   - Install required packages: `Python`, `PostgreSQL`, `Nginx`, `Gunicorn`.

   - NGINX Config:
\`\`\`
    # Serve robots.txt
    location = /robots.txt {
        alias /var/www/html/app/robots.txt;
    }
    a
    # Security Headers
    add_header Strict-Transport-Security "max-age=3600; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";

    # Content Security Policy
    add_header Content-Security-Policy "
        default-src 'self';
        script-src 'self' 'unsafe-inline' https://code.jquery.com https://cdnjs.cloudflare.com https://stackpath.bootstrapcdn.com https://cdn.jsdelivr.net https://code.jquery.com https://cdnjs.cloudflare.com https://www.googletagmanager.com;
        style-src 'self' 'unsafe-inline' https://stackpath.bootstrapcdn.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com;
        img-src 'self' data:;
        font-src 'self' data: https://cdn.jsdelivr.net;
        connect-src 'self' https://www.google-analytics.com https://questbycycle.org wss://questbycycle.org;
        frame-src 'self';
        object-src 'none';
        base-uri 'self';
        form-action 'self';
    ";

    # Gzip Compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;


    # Serve Static Files - CSS
    location /static/css/ {
        alias /var/www/html/app/static/css/;
        expires 1h; # Cache CSS files for 1 hour
        add_header Cache-Control "public, max-age=3600, must-revalidate";
        try_files $uri $uri/ =404;
    }

   # Serve Static Files - Video
    location /static/videos/ {
        alias /var/www/html/app/static/videos/;
        expires 30d;
        add_header Cache-Control "public, max-age=, max-age=2592000, must-revalidate";
        try_files $uri $uri/ =404;
    }


    # Serve Static Files - Photos
    location /static/photos/ {
        alias /var/www/html/app/static/photos/;
        expires 30d; # Cache photos for 30 days
        add_header Cache-Control "public, max-age=2592000, must-revalidate";
        try_files $uri $uri/ =404;
    }

    # Serve Other Static Files
    location /static/ {
        alias /var/www/html/app/static/;
        expires 1h; # Cache other static files for 1 hour
        add_header Cache-Control "public, max-age=3600, must-revalidate";
        try_files $uri $uri/ =404;
    }

    # Proxy Pass for Application
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # Allow WebSocket origin
        proxy_set_header Origin "https://questbycycle.org";
    }

    client_max_body_size 10M;

    # First attempt to serve request as file, then as directory, then fall back to displaying a 404.
    try_files $uri $uri/ =404;
}
\`\`\`
2. **Clone the repository**:
   \`\`\`bash
   git clone https://github.com/your-repo/your-project.git
   cd your-project
   \`\`\`

3. **Set up the virtual environment**:
   \`\`\`bash
   python3 -m venv venv
   source venv/bin/activate
   \`\`\`

4. **Install dependencies**:
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

5. **Configure the database**:
   - Update `config.toml` with the production database credentials.

6. **Run database migrations**:
   \`\`\`bash
   flask db upgrade
   \`\`\`

7. **Set up Gunicorn**:
   \`\`\`bash
   gunicorn --bind 0.0.0.0:8000 wsgi:app
   \`\`\`

8. **Configure Nginx**:
   - Set up an Nginx server block to proxy requests to Gunicorn.

9. **Start the application**:
   - Ensure Gunicorn and Nginx are running.

By following this guide, you should have a comprehensive understanding of the project's architecture, codebase, and development practices. Happy coding!
