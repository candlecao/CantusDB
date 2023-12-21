#!/bin.bash

# This script creates a compressed SQL dump of the database in the /home/ubuntu/backups/postgres/yearly directory.
# It then deletes any yearly backups so that only 10 yearly backups are retained.

# Note: This script is set up to run on the production server. If you want to run it on your local machine, you will need to change the paths.

DOCKER_COMPOSE_FILE=/home/ubuntu/code/CantusDB/docker-compose.yml   # This is the path to the docker-compose file.
BACKUP_DIR=/home/ubuntu/backups/postgres/yearly                     # This is the directory where the yearly backups will be stored.
RETENTION_COUNT=10                                                  # This is the number of yearly backups to keep.

mkdir -p $BACKUP_DIR
FILENAME=$(date "+%Y-%m-%dT%H:%M:%S").sql.gz
/usr/bin/docker exec cantusdb_postgres_1 /usr/local/bin/postgres_backup.sh $FILENAME
/usr/bin/docker cp cantusdb_postgres_1:/var/lib/postgresql/backups/$FILENAME $BACKUP_DIR
/usr/bin/docker exec cantusdb_postgres_1 rm /var/lib/postgresql/backups/$FILENAME
FILES_TO_REMOVE=$(ls -td $BACKUP_DIR/* | tail -n +$(($RETENTION_COUNT + 1)))
[[ ! -z "$FILES_TO_REMOVE" ]] && rm $FILES_TO_REMOVE