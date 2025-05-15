#!/bin/sh

cd /opt/app-root || exit

echo '--- Starting Alembic Upgrade 1---'
echo "PWD: $(pwd)"
echo "Available Migration Scripts:"
flask db history

echo "Current DB Revision:"
flask db current

echo "Heads:"
flask db heads

echo "--- Running upgrade ---"
flask db upgrade
