# aiogram-base
a basic telegram bot with basic options with aiogram. for base of new projects.

- all necessary packages are in requirements.txt
- migrations in migrations
- Application in app

# Installation guide

### 1. Postgresql
#### step 1 - install postgres

`sudo apt update`

`sudo apt install postgresql postgresql-contrib`

#### step 2 - create a postgres user

`sudo -u postgres createuser -P -s -e <user>`

now enter the user name. make sure to be the same as current server user!

enter yes after _'Shall the new role be a superuser? (y/n)'_

`sudo apt install build-essential python3-dev`

`python3 -m virtualenv .venv`

`source .venv/bin/activate`

`pip install -r requirements.txt`


place your database and bot configurations in app/config.py

`sudo -u postgres createdb subbot2 -h localhost -p 5432 -U <user> -W`

use app/config.py.sample for example.
## running:
`make migration`

`make migrate`

running in polling mode (app/\_\_main__.py):

`python -m app polling`

or for skipping updates:

`python -m app polling --skip-updates`


# Activate the autobackup functionality

`sudo systemctl edit redis-server.service`

In the editor, type:

`[Service]`   
`UMask=0002`

`systemctl reenable redis-server.service`   
`systemctl restart redis-server`

create a new bot and put token in backup.py.

`chmod +x backup.sh`
 
for manual backup just run `backup.sh` and for auto set a cronjob.

example: `0 00 * * * ~/antispam/backup.sh > /dev/null 2>&1`  
to run everyday at midnight _(recommended)_


