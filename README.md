# any-inventree

## Initial Database Setup

Run in source directory:
```
docker compose run --rm inventree-server invoke update
```
Create administrator account with e.g. username=admin, password=admin
```
docker compose run inventree-server invoke superuser
```

and start the container with 
```
docker compose up -d
```

## Use the InvenTree API

### Create a Virtual Environment

To create a virtual environment for your InvenTree API project, run the following command:
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