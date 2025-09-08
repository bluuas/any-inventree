# inventree-project

This repository contains the InvenTree Docker deployment configuration and related files.

## Initial Setup

### Environment Variables

Configure the environment variables as needed.
For this basic setup, we will configure
- `INVENTREE_ADMIN_USER`
- `INVENTREE_ADMIN_PASSWORD`
- `INVENTREE_ADMIN_EMAIL`

### Install Docker
<details>

Follow the [installation guide from InvenTree](https://docs.inventree.org/en/latest/start/docker_install/).

```bash
sudo apt update
```

If you're not using GNOME, install `gnome-terminal` to enable terminal access from Docker Desktop:

```bash
sudo apt install gnome-terminal
```

[Install Docker Desktop](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository)

```bash
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
```

Install the latest version:

```bash
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

[Linux post-installation steps for Docker Engine](https://docs.docker.com/engine/install/linux-postinstall/)

```bash
# Create the docker group
sudo groupadd docker
# add user to docker group
sudo usermod -aG docker $USER
# run the following command to log in to a new group:
newgrp docker
# check if your user has docker group membership by running:
groups
# once done, try running one of the docker commands:
docker ps
```
</details>

After installing all the required dependencies, run the following command in the source directory to initialize the database:

```bash
docker compose run --rm inventree-server invoke update
```

and start the container with 

```bash
docker compose up
# or -d if you want to run it in detached mode
```

You should now be able to access the InvenTree web interface at http://short-circuits.sandbox.anybotics.com or http://inventree.localhost, depending on your configuration

## Migrating Data to a Different Database

[InvenTree Data Migration](https://docs.inventree.org/en/stable/start/migrate/)

### Export Data

```bash
docker compose run inventree-server invoke export-records -f data/data-export.json
```

### Import Data

**NOTE:** did not work for me so far

**UPDATE:** only works if the database is empty

<details>

```bash
docker compose run inventree-server invoke import-records -c -f data/data-export.json
```
```bash
(.venv) lu@tplb:~/any/github/any-inventree$ docker compose run --rm inventree-server invoke import-records -c -f 'data/data-export.json'
[+] Creating 2/2
 ✔ Container inventree-cache  Running                                      0.0s 
 ✔ Container inventree-db     Running                                      0.0s 
Loading config file : /home/inventree/data/config.yaml
Deleting all data from InvenTree database...
Python version 3.11.9 - /usr/local/bin/python3
/root/.local/lib/python3.11/site-packages/allauth/exceptions.py:9: UserWarning: allauth.exceptions is deprecated, use allauth.core.exceptions
  warnings.warn("allauth.exceptions is deprecated, use allauth.core.exceptions")
CommandError: Database inventree couldn't be flushed. Possible reasons:
  * The database isn't running or isn't configured correctly.
  * At least one of the expected database tables doesn't exist.
  * The SQL was invalid.
Hint: Look at the output of 'django-admin sqlflush'. That's the SQL this command wasn't able to run.
ERROR: InvenTree command failed: 'python3 manage.py flush --noinput'
- Refer to the error messages in the log above for more information
```

[InvenTree command failed: 'python3 manage.py](https://github.com/inventree/InvenTree/issues/9592)
```bash
sudo apt-get install libpq-dev
pip install psycopg2 pgcli
```
</details>

## Backups

Note that a [backup](https://docs.inventree.org/en/stable/start/backup/) operation is not the same as [migrating data](https://docs.inventree.org/en/stable/start/migrate/). While data migration exports data into a database-agnostic JSON file, backup exports a native database file and media file archive.

### Perform Manual Backup

```bash
docker compose run --rm inventree-server invoke backup
```

### Restore Backup

```bash
docker compose run --rm inventree-server invoke restore
```

## Using a VPN

To access the short-circuits.sandbox.anybotics.com domain via VPN, you have to add some configuration to your Anybotics VPN:

1. Open the settings of the Anybotics VPN client
2. Switch to the IPv4 Tab
3. Add a new route for the InvenTree domain:
  - Address: `18.153.69.123`
  - Netmask: `255.255.255.255`
  - Gateway: `10.0.0.254`

*Note: if this does not work, you may have to update the IP address. This you can find out by running `ping short-circuits.sandbox.anybotics.com`*

## DBeaver

To access the PostgreSQL database, you can use DBeaver:

1. Install DBeaver from [here](https://dbeaver.io/download/).
2. Find the IP address of the `inventree-db` container by running the following command in the terminal:

    ```bash
    docker ps -q | xargs -I{} sh -c "docker inspect -f '{{.Name}}: {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' {}"
    ```

    typically it would be something like `172.19.0.2`
3. Create a new connection in DBeaver using the following details:
  - Host: use the IP address you found in step 2
  - Port: 5432 *(or the port specified in the .env file)*
  - Database: inventree
  - User: user (find the username in the .env file)
  - Password: user (find the password in the .env file)
4. If the database is hosted on a remote server, connect via ssh tunnel first

<details>

![Postgres Configuration Main](assets/postgres-configuration-main.jpg)

![Postgres Configuration SSH](assets/postgres-configuration-ssh.jpg)

</details>

## start from scratch...

```bash
sudo docker stop $(sudo docker ps -aq)
sudo docker rm $(sudo docker ps -aq)
sudo docker rmi $(sudo docker images -q)
sudo docker volume rm $(sudo docker volume ls -q)
sudo rm -rf inventree-data
```

Then re-run

```bash
docker compose run --rm inventree-server invoke update
docker compose up -d
```

```bash
source .venv/bin/activate
python3 scripts/inventree_initial_setup.py --config-file "scripts/gsheet-database/AM0304_Component_DB - Configuration.csv"
python3 scripts/inventree_create_units.py
python3 scripts/inventree_process_csv.py --directory "gsheet-database/" --method CSV --log-level INFO
```

```bash
docker compose run --rm inventree-server invoke backup
scp data/backup/*.gz ubuntu@short-circuits.sandbox.anybotics.com:/home/ubuntu/inventree-project/
```

On the server

```bash
docker compose down
sudo mv default-data.psql.bin.gz data.tar.gz ./inventree-data/backup/
docker compose run --rm inventree-server invoke restore
docker compose up -d
```
