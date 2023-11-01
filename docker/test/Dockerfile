ARG IMAGE_MINIMAL

FROM ${IMAGE_MINIMAL}

COPY test_scripts_and_data test_scripts_and_data

ENV LD_LIBRARY_PATH :/usr/local/lib

# for now filenames are hardcoded, including a string literal in compare_dbs.py
RUN /bin/bash -c 'cd test_scripts_and_data && bash set_up_and_run_equilibriumcrystalstructure_sample.sh && python compare_dbs.py'
