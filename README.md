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

### Server Setup


1. Login with SSH key:

```ssh-keygen -t rsa -b 4096 -C "YOUR_EMAIL"```
```cat ~/.ssh/id_rsa.pub``` <- Copy this key from local computer
```mkdir -p ~/.ssh && nano ~/.ssh/authorized_keys``` Paste the key in here on remote server 
Now login with ```ssh USER@HOST```

2. Allocate Swap on low ram systems:

```sudo fallocate -l 4G /swapfile```
```sudo chmod 600 /swapfile```
```sudo mkswap /swapfile```
```sudo swapon /swapfile```
```echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab```

3. Install NGINX:
```sudo apt install nginx```
```sudo ufw allow 'Nginx Full'```
```sudo ufw allow 'OpenSSH'```
```sudo ufw enable```
Set directory permissions to 775:
```sudo find /var/www/html/ -type d -exec chmod 775 {} \;```

Set file permissions to 664:
```sudo find /var/www/html/ -type f -exec chmod 664 {} \;```

4. Edit NGINX config:
```sudo nano /etc/nginx/sites-available/default```
    [Example default](/docs/default.NGINX)
```sudo systemctl restart nginx.service```
```sudo certbot --nginx -d DOMAINNAME```

### Installation and Deployment

1. Clone and open the repository:

``` cd /opt```
```git clone https://github.com/denuoweb/QuestByCycle.git```
```cd QuestByCycle```

2. Install python3.11:

```sudo add-apt-repository ppa:deadsnakes/ppa```
```sudo apt install python3.11 python3.11-venv python3-pip python3-gevent python3-certbot-nginx```

3. Create new user:

```sudo adduser --system --group --disabled-login APPUSER```
```sudo chown -R APPUSER:APPUSER /opt/QuestByCycle```

4. Prepare the Deployment:

```sudo nano /etc/systemd/system/questbycycleApp.service```

```markdown
[Unit]
Description=gunicorn daemon for QuestByCycle application
After=network.target

[Service]
User=APPUSER
Group=APPUSER
WorkingDirectory=/opt/QuestByCycle
ExecStart=/opt/QuestByCycle/venv/bin/gunicorn --config /opt/QuestByCycle/gunicorn.conf.py wsgi:app

[Install]
WantedBy=multi-user.target
```

5. Start the virtual environment
```sudo -u APPUSER -H bash -c "python3.11 -m venv /opt/QuestByCycle/venv"```

6. Install the requirements:

```sudo -u APPUSER /bin/bash -c "source /opt/QuestByCycle/venv/bin/activate && pip install -r /opt/QuestByCycle/requirements.txt"```

7. Set up the environment variables:
    
    - Copy `config.toml.example` to `config.toml` and adjust the variables accordingly.

8. PostgresDB Setup:
```sudo apt install postgresql postgresql-contrib```

```sudo systemctl start postgresql```

```sudo systemctl enable postgresql```

```sudo su - postgres```

```psql -U postgres```

```CREATE DATABASE databasename;```

```\c databasename```

```CREATE USER username WITH PASSWORD 'password';```

```GRANT ALL PRIVILEGES ON DATABASE databasename TO username;```

```GRANT USAGE, CREATE ON SCHEMA public TO username;```

```GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO username;```

```ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO username;```

```\q```

```exit```

9. Initialize the database:

```flask db init```

```flask db migrate```

```flask db upgrade```

10. Deploy

```sudo systemctl start questbycycleApp.service```
```sudo systemctl enable questbycycleApp.service```

## Connect Game to X
https://developer.x.com/en/portal/dashboard

## Connect Game to Facebook and Instagram
Create 'app' here to get app id and app secret: https://developers.facebook.com/
Use this to generate the access token: https://developers.facebook.com/tools/explorer/

Permissions required:
pages_show_list
pages_read_engagement
pages_read_user_content
pages_manage_posts
pages_manage_engagement
instagram_basic
instagram_branded_content_ads_brand
instagram_branded_content_brand
instagram_branded_content_creator

## Connect OpenAI API for Task and Badge Generation
https://platform.openai.com/api-keys

## msmtp
```
sudo apt-get update
sudo apt-get install msmtp msmtp-mta
nano ~/.msmtprc

# Set default values for all accounts
defaults
auth           on
tls            on
tls_trust_file /etc/ssl/certs/ca-certificates.crt
logfile        ~/.msmtp.log

# Set a default account
account        default
host           smtp.gmail.com
port           587
from           no-reply@questbycycle.org
user           your-email@gmail.com
password       your-gmail-password

# Alternatively, if you are using another SMTP server
# host           smtp.your-email-provider.com
# port           587
# from           no-reply@questbycycle.org
# user           your-smtp-username
# password       your-smtp-password

# Map local user to this account
account default : default

chmod 600 ~/.msmtprc

echo "Subject: Test Email" | msmtp -a default your-email@gmail.com

pip install Flask-Mail


```
## Contributing

We welcome contributions from the community! Whether you're interested in adding new features, fixing bugs, or improving documentation, your help is appreciated. Please refer to CONTRIBUTING.md for guidelines on how to contribute to QuestByCycle.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The bicycling community for their endless passion and dedication to making the world a greener place.
- All contributors who spend their time and effort to improve QuestByCycle.

