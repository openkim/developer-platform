DOCKER_COMMAND="whoami"
docker run --rm --mount type=bind,src=$PWD/test/test_scripts_and_data,target=/home/openkim/test_scripts_and_data $1 /bin/bash -c "$DOCKER_COMMAND"