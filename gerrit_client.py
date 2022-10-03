#!/usr/bin/env python3

import argparse
import datetime
import json
import re
import requests
from urllib.parse import quote

BASE_URL = "https://review.opendev.org"
ZUUL_BASE = "https://zuul.opendev.org"

# Supported output format.
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
    parser.add_argument("--input-json", type=str,
            help="Path of JSON formatted results, for debugging.")
    parser.add_argument("-t", "--term", type=str,
            help="Term for querying (in hours, such as '24*2' for two days).")
    return parser.parse_args()


def change_messages(chid):
    req_gerrit = "{}/changes/{}/messages/".format(
            BASE_URL, gerrit_change_id(chid))
    r = requests.get(req_gerrit)

    contents = r.text.replace(MAGIC_STR, "")
    obj = json.loads(contents)
    return obj


def to_html(json_obj):
    def make_header(hlist):
        tmp = ""
        for h in hlist:
            tmp = tmp + "<th>" + h + "</th>"
        return "<thead><tr>{}</tr></thead>".format(tmp)

    hlist = ["No.", "Gerrit URL", "Patchset", "Test Name", "Test Result",
            "Start", "End", "Time", "All logs", "Artifacts"]

    html = ""

    js = json_obj

    bs = ""
    cnt = 1
    for j in js:
        jd = j["detail"][0]

        line_html = "<tr>"
        line_html = line_html + "<td>{num}</td>"
        line_html = line_html + "<td><a href={g_url}>{g_url}</td>"
        line_html = line_html + "<td>{ps}</td>"
        line_html = line_html + "<td>{name}</td>"
        line_html = line_html + "<td><a href={result}>result</td>"
        line_html = line_html + "<td>{t_start}</td>"
        line_html = line_html + "<td>{t_end}</td>"
        line_html = line_html + "<td>{time}</td>"
        line_html = line_html + "<td><a href={logs}>logs</td>"
        line_html = line_html + "<td><a href={art}>download</td>"
        line_html = line_html + "</tr>"

        b = line_html.format(
                num=cnt, g_url=jd["ref_url"], ps=jd["patchset"], name=j["name"],
                result=j["url"],
                t_start=jd["start_time"], t_end=jd["end_time"],
                time=j["time"],
                logs=jd["log_url"], art=jd["artifacts"][0]["url"])

        bs = "{}{}".format(bs, b)
        cnt += 1


    thead = make_header(hlist)

    tbody = "<tbody>{}</tbody>".format(bs)
    html = "<html><table border=1>{}{}</table></html>".format(thead, tbody)
    print(html)


def output(json_obj, format="html"):
    if format == "html":
        to_html(json_obj)
    else:
        print(json.dumps(json_obj))


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

    zuul_results = []
    if args.input_json is not None:
        zuul_results = json.load(open(args.input_json))
    else:
        ptn = re.compile(r'^- (.*) (.*) : {} in (.*)$'.format(TARGET_STATUS))

        for chid in ch_ids:
            msg_objs = change_messages(chid)
            for obj in msg_objs:
                for m in obj["message"].split("\n"):
                    matched = ptn.match(m)
                    if matched is not None:
                        name = matched.group(1)
                        url = matched.group(2)
                        time = matched.group(3).replace(" (non-voting)", "")
                        zr = {"name": name, "url": url, "time": time}
                        zuul_results.append(zr)

        for zr in zuul_results:
            uuid = zr["url"].split("/")[-1]
            req_zuul = "{}/api/tenant/openstack/builds?uuid={}".format(
                ZUUL_BASE, uuid)

            r = requests.get(req_zuul)
            zr["detail"] = json.loads(r.text)

    results = []
    if args.term is not None:
        dterm = int(eval(args.term))
        for zr in zuul_results:
            dt = datetime.datetime.strptime(
                    zr["detail"][0]["event_timestamp"], '%Y-%m-%dT%H:%M:%S')
            ddelta = datetime.datetime.now() - datetime.timedelta(hours=dterm)
            if dt > ddelta:
                results.append(zr)
    else:
        results = zuul_results

    output(results, args.format)

if __name__ == '__main__':
    main()
