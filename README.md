# any-inventree

## Initial InvenTree Database Setup

### Environment Configuration

Copy the `.env-example` file and rename it to `.env`. Configure the environment variables as needed.
For this basic setup, we will configure `INVENTREE_ADMIN_USER`, `INVENTREE_ADMIN_PASSWORD` and `INVENTREE_ADMIN_EMAIL`

### Install Docker

Follow the [installation guide from InvenTree](https://docs.inventree.org/en/latest/start/docker_install/).

<details>
<summary>Ubuntu</summary>

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
sudo groupadd docker
sudo usermod -aG docker $USER
```
Log out and log back in to apply the group changes.

</details>

### Database Migration

Run in source directory:
```
docker compose run --rm inventree-server invoke update
```

and start the container with `docker compose up` (`-d` if you want to run it in detached mode)

## Use the InvenTree API Scripts

### Virtual Environment

Create a virtual environment for your InvenTree API project by running the following command in the project directory:

```bash
python -m venv .venv
```

### Activate the Virtual Environment

#### On Windows

```bash
.venv\Scripts\activate
```

#### On macOS and Linux

```bash
source .venv/bin/activate
```

### Install Required Packages

Once the virtual environment is activated, install the required packages listed in `requirements.txt`
```bash
pip install -r scripts/requirements.txt
```

## Usage

### Create Parts from CSV

Process CSV files to create parts, categories, parameters, and suppliers:

```bash
cd scripts
python inventree_create_parts.py --directory ../data --log-level INFO --verbose
```

### Delete All Data

To clean up the database (use with caution):

```bash
cd scripts
python inventree_create_parts.py --delete-all --log-level INFO
```

### Resolve BOM Substitutes

Process a BOM file to resolve part relations and substitutes:

```bash
cd scripts
python resolve_bom.py -f /path/to/bom.csv
```

### Create Assembly from BOM

Create an assembly part with BOM items from a CSV file:

```bash
cd scripts
python create_assembly_from_bom.py -f /path/to/bom.csv
```

### Command Line Options

- `--log-level`: Set logging level (DEBUG, INFO, WARNING, ERROR)
- `--verbose`: Print configuration details
- `--directory`: Directory containing CSV files to process
- `--delete-all`: Delete all parts and entities (use with caution)

### Deactivate the Virtual Environment

You can deactivate the virtual environment by running:

```bash
deactivate
```

# DBeaver

To edit the database locally, you can use DBeaver:

1. Install DBeaver from [here](https://dbeaver.io/download/).
2. Find the IP address of the `inventree-db` container by running the following command in the terminal:

    ```bash
    docker ps -q | xargs -I{} sh -c "docker inspect -f '{{.Name}}: {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' {}"
    ```

    typically it would be something like `172.18.0.4`
3. Create a new connection in DBeaver using the following details:
   - Host: use the IP address you found in step 2
   - Port: 5432
   - Database: inventree
   - User: pguser (find the username in the .env file)
   - Password: pgpassword (find the password in the .env file)
4. If the database is hosted on a remote server, connect via ssh tunnel first