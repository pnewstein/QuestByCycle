# QuestByCycle

## Overview

QuestByCycle is a Flask-based web application designed to engage and motivate the bicycling community through a gamified approach, promoting environmental sustainability and climate activism. Participants complete tasks or missions related to bicycling and environmental stewardship, earning badges and recognition among the community. The platform features a competitive yet collaborative environment where users can view their standings on a leaderboard, track their progress through profile pages, and contribute to a greener planet.

## Features

- **User Authentication:** Secure sign-up and login functionality to manage user access and personalize user experiences.
- **Leaderboard/Homepage:** A dynamic display of participants, their rankings, and badges earned, fostering a sense of competition and achievement.
- **Task Submission:** An interface for users to submit completed tasks or missions, facilitating the review and award of badges.
- **User Profiles:** Dedicated pages for users to view their badges, completed tasks, and ranking within the community.
- **Responsive Design:** Ensuring a seamless and engaging user experience across various devices and screen sizes.

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL

### Installation

1. Clone the repository:

```git clone https://github.com/yourusername/QuestByCycle.git```

2. Navigate into the project directory:

```cd QuestByCycle```

3. Create and activate a virtual environment (optional):

```python3 -m venv venv```
```source venv/bin/activate```

4. Install the requirements:

```pip install -r requirements.txt```

5. Set up the environment variables:
- Edit `config.toml` to adjust the variables accordingly.

6. Database Setup:

```sudo su - postgres```

```psql -U postgres```

```CREATE DATABASE databasename;```

```\c databasename```

```CREATE USER username WITH PASSWORD 'password';```

```GRANT ALL PRIVILEGES ON DATABASE databasename TO username;```

```GRANT USAGE, CREATE ON SCHEMA public TO username;```

```GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO username;```

```ALTER TABLE badge ALTER COLUMN name TYPE VARCHAR(255);```

```ALTER TABLE badge ALTER COLUMN description TYPE VARCHAR(500);```

```ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO username;```

```\q```

```exit```

6. Initialize the database:

```flask db init```

```flask db migrate```

```flask db upgrade```

7. Run the application:

```gunicorn --bind 0.0.0.0:8000 wsgi:app```

8. Update instructions:

```ssh questbycycle.org```
```cd QuestByCycle/```
```git pull```
```cd QuestByCycle/```
```screen -r```

```Ctrl-c```

```sudo rm -rf *```
```cp -r ~/QuestByCycle/* /var/www/html```
```flask db migrate -m "pulled updates"```
```sudo su - postgres```
```psql```
```\c DATABASENAME```

```\q```
```exit```
```flask db upgrade```

## Facebook API
https://developers.facebook.com/tools/explorer/
Permissions 
Reset

Clear
pages_show_list
pages_read_engagement
pages_read_user_content
pages_manage_posts
pages_manage_engagement

get code put here to get page access:
https://graph.facebook.com/v12.0/oauth/access_token?grant_type=fb_exchange_token&client_id=CLIENTID&client_secret=CLIENTSECRET&fb_exchange_token=EXPLORERGENERATEDTOKEN

Put page access token in edit game
## Contributing

We welcome contributions from the community! Whether you're interested in adding new features, fixing bugs, or improving documentation, your help is appreciated. Please refer to CONTRIBUTING.md for guidelines on how to contribute to QuestByCycle.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The bicycling community for their endless passion and dedication to making the world a greener place.
- All contributors who spend their time and effort to improve QuestByCycle.

