# Adapted from LLNL Orchestrator "KIMRun" module
# Set up a direcory structure so that the KDP utilities
# such as "kimitems" and "pipeline-run-pair" can be
# used with singularity

import os


CODE_TO_DIR = {
    'MO': 'models',
    'MD': 'model-drivers',
    'TE': 'tests',
    'TD': 'test-drivers',
    'SM': 'simulator-models',
    'VC': 'verification-checks',
}


def env_file_path(work_path):
    return os.path.join(work_path, 'kimrun-env')


work_path = os.path.abspath(input("Directory you would like to work in?\n"))
os.mkdir(work_path)
kdp_env_file_path = os.path.join(work_path, 'kimrun-kdp-env')
kim_api_config_path = os.path.join(work_path, '.kim-api/config')

with open(env_file_path(work_path), 'w') as f:
    f.write(f"PIPELINE_ENVIRONMENT_FILE={kdp_env_file_path}\n"
            + f"KIM_API_CONFIGURATION_FILE={kim_api_config_path}")

with open(kdp_env_file_path, 'w') as f:
    f.write("#!/bin/bash\n"
            + "#==============================================\n"
            + "# this file has a specific format since it is\n"
            + "# also read by python.  only FOO=bar and\n"
            + "# the use of $BAZ can be substituted. comments\n"
            + "# start in column 0\n"
            + "#==============================================\n\n"
            + "PIPELINE_LOCAL_DEV=True\n"
            + f"LOCAL_REPOSITORY_PATH={work_path}\n"
            + f"LOCAL_DATABASE_PATH={work_path}/db")


kdp_directories = list(CODE_TO_DIR.values()) + \
    ['errors', '.kim-api', 'test-results', 'verification-results']

# create KDP subdirectories
for dirname in kdp_directories:
    dirpath = os.path.join(work_path, dirname)
    os.mkdir(dirpath)

with open(kim_api_config_path, 'w') as f:
    f.write(f"model-drivers-dir = {work_path}/md\n"
            + f"portable-models-dir = {work_path}/pm\n"
            + f"simulator-models-dir = {work_path}/sm\n")

with open(kim_api_config_path) as f:
    for line in f:
        if len(line) > 255:
            raise RuntimeError(
                'Path to the work directory is too long.\n'
                'KIM API config file max line length = 255,\n'
                'your path must be less than approx. 225 chars.')

print(
    "Work directory created. Run Singularity with (at least) the following options:"
    )
print(f"--env-file {env_file_path(work_path)} -B {work_path} --writable-tmpfs")