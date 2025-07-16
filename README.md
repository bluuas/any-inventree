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
