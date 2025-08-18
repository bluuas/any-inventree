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
pip install -r requirements.txt
```

### Create an InvenTree API Token

To create an InvenTree API Token, navigate to the following URL in your web browser:

[http://inventree.localhost/admin/users/apitoken/add/](http://inventree.localhost/admin/users/apitoken/add/)

Follow the instructions to generate your API token.

### Insert the API Token in the .env File

After generating your API token, insert it into the `.env` file located in the `./scripts/` directory. The file should look like this:

```env
# InvenTree
INVENTREE_API_TOKEN=inv-123456789
```

Make sure to replace `inv-123456789` with your actual API token.


### Deactivate the Virtual Environment

You can deactivate the virtual environment by running:

```bash
deactivate
```