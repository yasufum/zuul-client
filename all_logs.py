#!/usr/bin/env python3

import argparse
import json
from mylogging import TEST_RESULTS
from mylogging import logger
import subprocess
import sys


LOG = logger('all_logs')

ZUUL_CLIENT_SCRIPT = "zuul_client.py"


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
                  "than SUCCESS, or download all if ALL is specified."
                  ).format(', '.join(TEST_RESULTS)))
    return parser.parse_args()


def main():
    args = parse_args()

    cmd = ["python3", ZUUL_CLIENT_SCRIPT, "--change-ids", args.change_id]

    if args.test_results is not None:
        my_results = set(args.test_results)
    elif args.test_results == "ALL":
        my_results = TEST_RESULTS
    else:
        my_results = TEST_RESULTS - {"SUCCESS"}

    for x in ["--test-results"] + list(my_results):
        cmd.append(x)

    if args.job_name is not None:
        for x in ["--job-name", args.job_name]:
            cmd.append(x)

    LOG.info("Run ZUUL_CLIENT_SCRIPT '{}'".format(cmd))

    # Get the result from stdout as json.
    res = subprocess.run(cmd, encoding='utf-8', stdout=subprocess.PIPE)

    def _latest_ps(json_obj):
        """Retrieve the latest num of patchset

        If target patchset is not given with option, the latest patchset is
        used instead.
        """
        psets = []
        for j in json_obj:
            ps = j["detail"][0].get("patchset")
            if ps is not None:
                psets.append(ps)
        psets.sort()
        return int(psets[-1])

    dl_urls = []
    try:
        #j = res.stdout
        #print(j)
        #exit()
        obj = json.loads(res.stdout)
        # Matched entries with the target patchset are only picked up.
        if args.patchset is not None:
            ps = args.patchset
        else:
            ps = _latest_ps(obj)
        for j in obj:
            u = j["detail"][0]["artifacts"][0]["url"]
            if u is not None:
                if (ps == int(j["detail"][0]["ref"].get("patchset"))):
                    dl_urls.append(u)
    except Exception as e:
        raise e

    if len(dl_urls) == 0:
        sys.exit(f"No logs for change ID {args.change_id},  patchset {ps}")

    LOG.info("{} entries matched.".format(len(dl_urls)))

    for u in dl_urls:
        cmd = ["bash", "get_logs.sh", u]
        res = subprocess.run(cmd)


if __name__ == '__main__':
    main()
