# Linux Server Configuration(Item Catalog Apache2 Deploy)
> Denis Ceban

## About ##
This project involves taking a baseline installation of Linux on a virtual machine and preparing it to host web applications. This includes installing updates, securing the server from attacks, and installing / configuring web and database servers.

## Server Info ##
- **Public IP:** 34.214.202.168
- **Port:** 2200
- [www.itemcatalog.gq](http://www.itemcatalog.gq)

## Getting Started ##
This project uses [Amazon Lightsail](https://amazonlightsail.com/) to create a Linux server instance.

### 1. Get your server. ###
- Start a new Ubuntu Linux server instance on Amazon Lightsail. 
    - Log in!
    - Create an instance
    - Choose an instance image: Ubuntu (OS only)
    - Choose your instance plan (lowest tier is fine)
    - Give your instance a hostname
    - Wait for startup
    - Once the instance has started up, follow the instructions provided to SSH into your server.

### 2. Secure your server. ###
- Update all currently installed packages.
    - `sudo apt-get update`
        - [https://help.ubuntu.com/lts/serverguide/automatic-updates.html](https://help.ubuntu.com/lts/serverguide/automatic-updates.html)
    - `sudo apt-get upgrade`
        - [https://serverfault.com/questions/262751/update-ubuntu-10-04/262773#262773](https://serverfault.com/questions/262751/update-ubuntu-10-04/262773#262773)

- Auto upgrades run
    - `sudo dpkg-reconfigure --priority=low unattended-upgrades`

- Change the SSH port from 22 to 2200. Make sure to configure the Lightsail firewall to allow it.
    - `sudo vim /etc/ssh/sshd_config`
    - change port form 22 to 2200
    - [http://www.cheat-sheets.org/saved-copy/OpenSSH_quickref.pdf](http://www.cheat-sheets.org/saved-copy/OpenSSH_quickref.pdf)
        
- Configure the Uncomplicated Firewall (UFW) to only allow incoming connections for SSH (port 2200), HTTP (port 80), and NTP (port 123).
    - `sudo ufw allow 2200/tcp`
    - `sudo ufw allow 80/tcp`
    - `sudo ufw allow 123/tcp`
    - `sudo ufw enable`
    - Warning: When changing the SSH port, make sure that the firewall is open for port 2200 first, so that you don't lock yourself out of the server. Review this video for details! When you change the SSH port, the Lightsail instance will no longer be accessible through the web app 'Connect using SSH' button. The button assumes the default port is being used. There are instructions on the same page for connecting from your terminal to the instance. Connect using those instructions and then follow the rest of the steps.

- [https://www.udacity.com/course/linux-command-line-basics--ud595](https://www.udacity.com/course/linux-command-line-basics--ud595)
- [https://www.udacity.com/course/configuring-linux-web-servers--ud299](https://www.udacity.com/course/configuring-linux-web-servers--ud299)
- [https://www.digitalocean.com/community/tutorials/initial-server-setup-with-ubuntu-16-04](https://www.digitalocean.com/community/tutorials/initial-server-setup-with-ubuntu-16-04)

### 3. Give grader access. ###
In order for your project to be reviewed, the grader needs to be able to log in to your server. 
- Create a new user account named grader.
    - `sudo adduser grader`
- Give grader the permission to sudo.
    - `sudo vim /etc/sudoers.d/grader`
    - add text `grader ALL=(ALL) NOPASSWD:ALL`
- Create an SSH key pair for grader using the ssh-keygen tool.
    - `ssh-keygen -t rsa`
    - To login
        - `ssh  grader@34.214.202.168 -p 2200`

### 4. Prepare to deploy your project. ###
- Configure the local timezone to UTC.
    - `sudo dpkg-reconfigure tzdata`
        - select none of the above, then UTC
            
- Install and configure Apache to serve a Python mod_wsgi application.
    - [https://classroom.udacity.com/courses/ud299/lessons/4340119836/concepts/48065785530923](https://classroom.udacity.com/courses/ud299/lessons/4340119836/concepts/48065785530923)
    - [https://www.digitalocean.com/community/tutorials/how-to-install-the-apache-web-server-on-ubuntu-16-04](https://www.digitalocean.com/community/tutorials/how-to-install-the-apache-web-server-on-ubuntu-16-04)

- Install and configure PostgreSQL:
    - [https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-on-ubuntu-16-04](https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-on-ubuntu-16-04)
    - [https://docs.sqlalchemy.org/en/latest/core/engines.html](https://docs.sqlalchemy.org/en/latest/core/engines.html)
    - [https://www.digitalocean.com/community/tutorials/how-to-use-roles-and-manage-grant-permissions-in-postgresql-on-a-vps--2](https://www.digitalocean.com/community/tutorials/how-to-use-roles-and-manage-grant-permissions-in-postgresql-on-a-vps--2)
    ```python
        def connect():
            return psycopg.connect(user='itemcatalog', host='localhost')
        db = create_engine('postgresql://', creator=connect)
    ```
### 5. Do not allow remote connections ###
- Create a new database user named catalog that has limited permissions to your catalog application database.
    - [https://help.ubuntu.com/community/PostgreSQL](https://help.ubuntu.com/community/PostgreSQL)

### 6. Deploy the Item Catalog project. ###
- [http://34.214.202.168/](http://34.214.202.168/)
- [https://www.digitalocean.com/community/tutorials/how-to-deploy-a-flask-application-on-an-ubuntu-vps](https://www.digitalocean.com/community/tutorials/how-to-deploy-a-flask-application-on-an-ubuntu-vps)
    
#### In This Repo ####
This project has the `view` Python module *project.py* which runs the Flask application. A SQL database is created using the `model` file *database_setup.py* module and you can populate the database with test data using *categories_loader.py*. The Flask application uses stored HTML templates in the tempaltes folder to build the front-end of the application.


#### To Install ####
1. `sudo apt-get install python-pip`
2. `sudo apt-get install git-core`
    - [https://www.liquidweb.com/kb/install-git-ubuntu-16-04-lts/](https://www.liquidweb.com/kb/install-git-ubuntu-16-04-lts/)
3. `cd /var/www/Flaskapp/Flaskapp`
4. `git clone https://github.com/airdenis/item_catalog_apache2_deploy.git`
5. `sudo pip install virtualenv` and `sudo virtualenv venv`(if not performed after previous instructions)
6. `source venv/bin/activate`
7. `sudo apt-get update`
8. `sudo pip install --upgrade oauth2client`
9. `sudo pip install Flask`
10. `sudo pip install passlib`
11. `sudo pip install flask-httpauth`
12. `sudo pip install request`
13. `sudo pip install pillow`
14. `sudo pip install python-resize-image`
15. `sudo apt-get install python-psycopg2`
16. `deactivate`
17. `python database_setup.py` init the database.
18. Insert fake data python `python categories_loader.py` (inser your email address used for google or facebook account to be able to do CRUD manipulation with given data.)

##### *More links to write a good README* #####
- [http://stackoverflow.com/questions/2304863/how-to-write-a-good-readme](http://stackoverflow.com/questions/2304863/how-to-write-a-good-readme)
- [https://robots.thoughtbot.com/how-to-write-a-great-readme](https://robots.thoughtbot.com/how-to-write-a-great-readme)
- [http://www.wikihow.com/Write-a-Read-Me](http://www.wikihow.com/Write-a-Read-Me)
- [http://docs.writethedocs.org/writing/beginners-guide-to-docs/](http://docs.writethedocs.org/writing/beginners-guide-to-docs/)
- [https://guides.github.com/features/mastering-markdown/](https://guides.github.com/features/mastering-markdown/)
- [https://classroom.udacity.com/courses/ud777](https://classroom.udacity.com/courses/ud777)
