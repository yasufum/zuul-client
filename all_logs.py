#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys

def parse_args():
    parser = argparse.ArgumentParser(description="")

    parser.add_argument("-i", "--change-id", type=str,
            help="Change ID")
    parser.add_argument("-p", "--patchset", type=int,
            help="Patch set")
    return parser.parse_args()

# CHANGE_ID=$1
# 
# python3 zuul_client.py --change-ids ${CHANGE_ID} |\
#     jq -r .[].detail[].artifacts[].url |\
#     xargs bash get_logs.sh

def main():
    args = parse_args()

    cmd = ["python3", "zuul_client.py", "--change-ids", args.change_id]
    #cmd = ["python3", "zuul_client.py", "--input-json", "872690.json"]
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
