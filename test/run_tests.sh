DOCKER_COMMAND="cd /home/openkim/test_scripts_and_data && bash set_up_and_run_$2.sh && python compare_dbs.py $2"
docker run --rm --mount type=bind,src=$PWD/test/test_scripts_and_data,target=/home/openkim/test_scripts_and_data --env LD_LIBRARY_PATH=:/usr/local/lib $1 /bin/bash -c "$DOCKER_COMMAND"

