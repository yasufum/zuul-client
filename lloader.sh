#!/bin/bash

_dir=$1

_ctl="${_dir}/controller/logs/screen-*"
_ctl_tacker="${_dir}/controller-tacker/logs/screen-tacker*"
_job_output="${_dir}/job-output.txt"

cmd="lnav ${_ctl} ${_ctl_tacker} ${_job_output}"
cmd="lnav ${_ctl_tacker} ${_job_output}"

echo $cmd
${cmd}
