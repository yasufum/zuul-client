#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys


TEST_RESULTS = {"SUCCESS", "FAILURE", "RETRY_LIMIT", "POST_FAILURE"}


def parse_args():
    parser = argparse.ArgumentParser(description="")

    parser.add_argument("-i", "--change-id", type=str,
            help="Change ID")
    parser.add_argument("-p", "--patchset", type=int,
            help="Patch set")
    parser.add_argument("-j", "--job-name", type=str,
            help="Job name for filtering for retrieving logs.")
    parser.add_argument("-r", "--test-results", type=str, nargs="+",
            help=("List of terms of test result ({}) for filtering. "
                  "If this option is not specified, get all logs other "
                  "than SUCCESS.").format(', '.join(TEST_RESULTS)))
    return parser.parse_args()

# CHANGE_ID=$1
#
# python3 zuul_client.py --change-ids ${CHANGE_ID} |\
#     jq -r .[].detail[].artifacts[].url |\
#     xargs bash get_logs.sh


def _zuul_client_script():
    return "zuul_client.py"


def main():
    args = parse_args()

    cmd = ["python3", _zuul_client_script(), "--change-ids", args.change_id]

    if args.test_results is not None:
        my_results = set(args.test_results)
    else:
        my_results = TEST_RESULTS - {"SUCCESS"}

    for x in ["--test-results", " ".join(my_results)]:
        cmd.append(x)

    if args.job_name is not None:
        for x in ["--job-name", args.job_name]:
            cmd.append(x)

    print(cmd)
    res = subprocess.run(cmd, encoding='utf-8', stdout=subprocess.PIPE)

    dl_urls = []
    try:
        obj = json.loads(res.stdout)
        for j in obj:
            u = j["detail"][0]["artifacts"][0]["url"]
            if u is not None:
                if (args.patchset == int(j["detail"][0].get("patchset")) or
                    args.patchset is None):
                    dl_urls.append(u)
    except Exception as e:
        raise e

    if len(dl_urls) == 0:
        sys.exit(f"No logs for change ID {args.change_id} ps {args.patchset}")

    for u in dl_urls:
        cmd = ["bash", "get_logs.sh", u]
        res = subprocess.run(cmd)


if __name__ == '__main__':
    main()
