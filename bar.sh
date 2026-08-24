#!/bin/bash

# Build the docker containers.
if [[ $1 = "build" ]]; then

	# Build the containers.
	echo -e "\033[01;36mBuilding container for Streamline...\033[0;0m\n"

	if [[ $2 = "-nc" ]]; then
		docker compose build --no-cache
	else
		docker compose build
	fi

	if [ $? -eq 0 ]; then
		echo -e "\n\033[01;102m BUILD COMPLETED \033[0;0m\n"
	else
		echo -e "\n\033[01;91m BUILD FAILED \033[0;0m\n"
		exit
	fi

fi

# Run the docker containers in detached mode.
docker compose up Streamline -d