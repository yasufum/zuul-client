#!/usr/bin/env python3

import argparse
import json
import re
import requests
from urllib.parse import quote

BASE_URL = "https://review.opendev.org"
ZUUL_BASE = "https://zuul.opendev.org"

# Supported output format.
# TODO: impl output for each formats
FORMATS = ["json", "html"]

# Status of test result for querying.
TARGET_STATUS = "FAILURE"

# Included in JSON response to guard from a bot. It should be removed from by
# API consumer him/herself.
MAGIC_STR = ")]}'\n"


# Use full change-id because a backport patch can have the same one as master.
def gerrit_change_id(ch_id, proj="openstack/tacker", branch="master"):
    if ch_id.startswith("I"):
        ch_id = "{}~{}~{}".format(proj, branch, ch_id)
    else:
        ch_id = ch_id
    return quote(ch_id, safe='')


def parse_args():
    parser = argparse.ArgumentParser(description="")

    parser.add_argument("-f", "--format", type=str,
            default="json",
            help="Output format")
    parser.add_argument("--change-ids", type=str, nargs="+",
            help="List of change IDs")
    parser.add_argument("-i", "--change-ids-file", type=str,
            help="Input file include a list of change IDs")
    return parser.parse_args()


def change_messages(chid):
    req_gerrit = "{}/changes/{}/messages/".format(
            BASE_URL, gerrit_change_id(chid))
    r = requests.get(req_gerrit)

    contents = r.text.replace(MAGIC_STR, "")
    obj = json.loads(contents)
    return obj


def main():
    args = parse_args()

    ch_ids = []

    if args.change_ids is not None:
        ch_ids = args.change_ids

    if args.change_ids_file is not None:
        with open(args.change_ids_file) as f:
            for l in f.readlines():
                if not l.startswith("#"):
                    ch_ids.append(l.rstrip())

    ch_ids = list(set(ch_ids))

    ptn = re.compile(r'^- (.*) (.*) : {} in (.*)$'.format(TARGET_STATUS))

    zuul_results = []
    for chid in ch_ids:
        msg_objs = change_messages(chid)
        for obj in msg_objs:
            for m in obj["message"].split("\n"):
                matched = ptn.match(m)
                if matched is not None:
                    zr = {"name": matched.group(1), "url": matched.group(2),
                            "time": matched.group(3)}
                    zuul_results.append(zr)

    for zr in zuul_results:
        uuid = zr["url"].split("/")[-1]
        req_zuul = "{}/api/tenant/openstack/builds?uuid={}".format(
            ZUUL_BASE, uuid)

        r = requests.get(req_zuul)
        zr["detail"] = json.loads(r.text)

    print(json.dumps(zuul_results))

if __name__ == '__main__':
    main()
