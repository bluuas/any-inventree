#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "docker-compose could not be found. Please install Docker Compose."
    exit 1
fi

# Define the Docker Compose file location
COMPOSE_FILE="docker-compose.yml"

# Function to reset the InvenTree database
reset_inventree_database() {
    echo "Resetting the InvenTree database..."

    # Echo 'y' to confirm deletion and run the command to delete all database records
    echo "y" | docker-compose -f $COMPOSE_FILE run --rm inventree-server invoke dev.delete-data

    echo "InvenTree database has been reset."
    echo "(Note: InvenTree API key has also been deleted)"
}

# Main script execution
reset_inventree_database