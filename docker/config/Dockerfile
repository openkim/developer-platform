#
# Copyright (c) 2018-2022, Regents of the University of Minnesota. All rights
# reserved.
#
# This software may be distributed as-is, without modification.
#
ARG IMAGE_INSTALL

FROM ${IMAGE_INSTALL} AS install

# Import all sys-level libs/utils
FROM ubuntu:20.04

# Grab only system directories from 'install' image
COPY --from=install /usr /usr
COPY --from=install /etc /etc
COPY --from=install /var /var
COPY --from=install /etc/sudoers /etc/sudoers

# Set default encoding to UTF-8
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

ARG PACKAGE_DIR=/pipeline/packages/
RUN mkdir -p ${PACKAGE_DIR}
COPY --from=install ${PACKAGE_DIR}/kim_api_install_manifest.txt ${PACKAGE_DIR}

# Add user 'openkim' to group 'sudo' with password 'openkim'
ARG USER=openkim
RUN useradd -ms /bin/bash ${USER} && \
    usermod -aG sudo ${USER} && \
    echo "${USER}:${USER}" | chpasswd

# Copy vim config file
COPY external_files/vimrc /home/openkim/.vimrc

# Copy instructions for pipeline utils into home directory
COPY instructions/README.txt /home/openkim/
RUN chmod 644 /home/openkim/README.txt

COPY excerpts /pipeline/excerpts
COPY tools /pipeline/tools
COPY utils/bashcompletion /pipeline/bashcompletion
COPY utils/kimitems /usr/local/bin/
COPY utils/pipeline-database /usr/local/bin/
COPY utils/pipeline-find-matches /usr/local/bin/
COPY utils/pipeline-run-matches /usr/local/bin/
COPY utils/pipeline-run-pair /usr/local/bin/
COPY utils/pipeline-run-tests /usr/local/bin/
COPY utils/pipeline-run-verification-checks /usr/local/bin/
COPY utils/kimgenie /usr/local/bin/

# Create local repository directory structure
ENV LOCAL_REPOSITORY_ROOT=/home/openkim/
RUN mkdir -p ${LOCAL_REPOSITORY_ROOT}/tests \
    && mkdir ${LOCAL_REPOSITORY_ROOT}/test-drivers \
    && mkdir ${LOCAL_REPOSITORY_ROOT}/verification-checks \
    && mkdir ${LOCAL_REPOSITORY_ROOT}/models \
    && mkdir ${LOCAL_REPOSITORY_ROOT}/model-drivers \
    && mkdir ${LOCAL_REPOSITORY_ROOT}/simulator-models \
    && mkdir ${LOCAL_REPOSITORY_ROOT}/test-results \
    && mkdir ${LOCAL_REPOSITORY_ROOT}/verification-results \
    && mkdir ${LOCAL_REPOSITORY_ROOT}/errors

# Create vim directories
RUN mkdir -p /home/openkim/.vim/tmp.undo/ \
    && mkdir -p /home/openkim/.vim/tmp.backup/ \
    && mkdir -p /home/openkim/.vim/tmp.swp/

ENV BASHRC /home/openkim/.bashrc
RUN echo "" >> ${BASHRC} \
    && echo "" >> ${BASHRC} \
    && echo "if [[ \":\$PYTHONPATH:\" != *\":/usr/local/lib:\"* ]]; then" >> ${BASHRC} \
    && echo "    export PYTHONPATH=\$PYTHONPATH:/usr/local/lib/python3/dist-packages/" >> ${BASHRC} \
    && echo "fi" >> ${BASHRC} \
    && echo "" >> ${BASHRC} \
    && echo "# Disable CMA for inter-rank communication in any MPI processes." >> ${BASHRC} \
    && echo "# Although this offers performance benefits, it requires access" >> ${BASHRC} \
    && echo "# to the `ptrace` utility, which docker generally doesn't provide." >> ${BASHRC} \
    && echo "export OMPI_MCA_btl_vader_single_copy_mechanism=none" >> ${BASHRC} \
    && echo "" >> ${BASHRC} \
    && echo "# Set LAMMPS binary path for ASE in case someone wants to use the lammpsrun" >> ${BASHRC} \
    && echo "# calculator outside of a Test" >> ${BASHRC} \
    && echo "ASE_LAMMPSRUN_COMMAND=/usr/local/bin/lmp" >> ${BASHRC} \
    && echo "" >> ${BASHRC} \
    && echo "# Enable bashcompletion for local item repository" >> ${BASHRC} \
    && echo ". /pipeline/bashcompletion" >> ${BASHRC} \
    && echo "" >> ${BASHRC} \
    && echo "disable_globbing_for_next_command_and_restore() { " >> ${BASHRC} \
    && echo "    # Use a nested trap to disable globbing only for the next command" >> ${BASHRC} \
    && echo "    current_shell_settings=\"${-}\"" >> ${BASHRC} \
    && echo "    if [[ \"${current_shell_settings}\" != *\"f\"* ]]; then" >> ${BASHRC} \
    && echo "        # Globbing is enabled; disable it and reset the depth counter" >> ${BASHRC} \
    && echo "        set -f;" >> ${BASHRC} \
    && echo "        num_noglob_commands_executed=0" >> ${BASHRC} \
    && echo "" >> ${BASHRC} \
    && echo "        # Set the trap function. This will be executed after every command" >> ${BASHRC} \
    && echo "        # until the trap is reset. In this case, we use the shell variable" >> ${BASHRC} \
    && echo "        # corresponding to the depth counter as a persistent means of checking" >> ${BASHRC} \
    && echo "        # how many commands have been executed since the trap was set. Before" >> ${BASHRC} \
    && echo "        # executing the next command, the trap will activate and increment the" >> ${BASHRC} \
    && echo "        # depth counter to 1. Then, just before the *next* command after that" >> ${BASHRC} \
    && echo "        # one, the trap function will trigger again, incrementing the depth" >> ${BASHRC} \
    && echo "        # counter to 2 just before the if statement, which will then execute," >> ${BASHRC} \
    && echo "        # reenabling globbing." >> ${BASHRC} \
    && echo "        trapfcn='" >> ${BASHRC} \
    && echo "            # Increment depth counter" >> ${BASHRC} \
    && echo "            let \"++num_noglob_commands_executed\"" >> ${BASHRC} \
    && echo "            # Check if we have finished executing the next command" >> ${BASHRC} \
    && echo "            if (( $num_noglob_commands_executed == 2 )); then" >> ${BASHRC} \
    && echo "                # Reenable globbing and reset trap" >> ${BASHRC} \
    && echo "                set +f" >> ${BASHRC} \
    && echo "                trap - DEBUG" >> ${BASHRC} \
    && echo "            fi'" >> ${BASHRC} \
    && echo "" >> ${BASHRC} \
    && echo "        # Set trap" >> ${BASHRC} \
    && echo "        trap \"${trapfcn}\" DEBUG" >> ${BASHRC} \
    && echo "    fi" >> ${BASHRC} \
    && echo "};" >> ${BASHRC} \
    && echo "" >> ${BASHRC} \
    && echo "alias kimitems='disable_globbing_for_next_command_and_restore;kimitems';kimitems(){ command kimitems \"\$@\";set +f;};" >> ${BASHRC} \
    && echo "alias pipeline-database='disable_globbing_for_next_command_and_restore;pipeline-database';pipeline-database(){ command pipeline-database \"\$@\";set +f;};" >> ${BASHRC} \
    && echo "alias pipeline-find-matches='disable_globbing_for_next_command_and_restore;pipeline-find-matches';pipeline-find-matches(){ command pipeline-find-matches \"\$@\";set +f;};" >> ${BASHRC} \
    && echo "alias pipeline-run-matches='disable_globbing_for_next_command_and_restore;pipeline-run-matches';pipeline-run-matches(){ command pipeline-run-matches \"\$@\";set +f;};" >> ${BASHRC} \
    && echo "alias pipeline-run-pair='disable_globbing_for_next_command_and_restore;pipeline-run-pair';pipeline-run-pair(){ command pipeline-run-pair \"\$@\";set +f;};" >> ${BASHRC} \
    && echo "alias pipeline-run-tests='disable_globbing_for_next_command_and_restore;pipeline-run-tests';pipeline-run-tests(){ command pipeline-run-tests \"\$@\";set +f;};" >> ${BASHRC} \
    && echo "alias pipeline-run-verification-checks='disable_globbing_for_next_command_and_restore;pipeline-run-verification-checks';pipeline-run-verification-checks(){ command pipeline-run-verification-checks \"\$@\";set +f;};" >> ${BASHRC} \
    && echo "" >> ${BASHRC}

RUN chmod 4755 /usr/bin/sudo

# Assign ownership
RUN chown -R openkim:openkim /home/openkim/
RUN chown -R openkim:openkim /pipeline/

# parses /etc/ld.so.conf.d/libc.conf to permanently look for libraries in /usr/local/bin
RUN ldconfig

USER openkim

WORKDIR /home/openkim/
