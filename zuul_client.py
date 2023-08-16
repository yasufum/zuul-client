#!/usr/bin/env python3

import argparse
import csv
import datetime
import json
import os
import re
import requests
import sys
from urllib.parse import quote

BASE_URL = "https://review.opendev.org"
ZUUL_BASE = "https://zuul.opendev.org"

# Supported output format.
FORMATS = {"json", "csv", "html"}

# Status of test result for querying.
TEST_RESULTS = {"SUCCESS", "FAILURE", "RETRY_LIMIT", "POST_FAILURE"}


HEADER_LIST = ["No.", "Gerrit URL", "PS", "Test Name", "Job", "Testr",
        "Start", "End", "Time", "All Logs", "Artifacts"]

# Included in JSON response to guard from a bot. It should be removed from by
# API consumer him/herself.
MAGIC_STR = ")]}'\n"


def _parse_args():
    parser = argparse.ArgumentParser(description="")

    parser.add_argument("-f", "--format", type=str,
            help="Output format ({}).".format(', '.join(FORMATS)))
    parser.add_argument("-i", "--change-ids", type=str, nargs="+",
            help="List of change IDs")
    parser.add_argument("-o", "--output-file", type=str,
            help="Path of output file.")
    parser.add_argument("-j", "--job-name", type=str,
            help="Job name for filtering for retrieving logs.")
    parser.add_argument("-r", "--test-results", type=str, nargs="+",
            help=("List of terms of test result ({}) for filtering. "
                  "If this option is not specified, get all logs other "
                  "than SUCCESS.").format(', '.join(TEST_RESULTS)))
    parser.add_argument("-t", "--term", type=str,
            help="Term for querying (in hours, such as '24*2' for two days).")
    parser.add_argument("--input-json", type=str,
            help="Path of JSON formatted results, for debugging.")
    return parser.parse_args()


def _change_messages(chid):

    # Use full change-id because a backport patch can have the same one as master.
    def gerrit_change_id(ch_id, proj="openstack/tacker", branch="master"):
        if ch_id.startswith("I"):
            ch_id = "{}~{}~{}".format(proj, branch, ch_id)
        else:
            ch_id = ch_id
        return quote(ch_id, safe='')

    req_gerrit = "{}/changes/{}/messages/".format(
            BASE_URL, gerrit_change_id(chid))
    r = requests.get(req_gerrit)

    contents = r.text.replace(MAGIC_STR, "")
    obj = json.loads(contents)
    return obj


def _to_csv(json_obj, ofile=None):

    hlist = HEADER_LIST.copy()
    hlist.insert(4, "Zuul Link")

    contents = []
    contents.append(hlist)
    cnt = 1
    for j in json_obj:
        jd = j["detail"][0]

        job_output = "{}{}".format(jd["log_url"], "job-output.txt")
        testr_results = "{}{}".format(jd["log_url"], "testr_results.html")
        t_start = jd["start_time"].replace("T", " ")
        t_end = jd["end_time"].replace("T", " ")
        contents.append([
            cnt, jd["ref_url"], jd["patchset"],
            j["name"], j["url"],
            job_output, testr_results,
            t_start, t_end,
            j["time"],
            jd["log_url"], jd["artifacts"][0]["url"]
            ])
        cnt += 1
    if ofile is not None:
        with open(ofile, "w") as f:
            writer = csv.writer(f)
            writer.writerows(contents)
    else:
        writer = csv.writer(sys.stdout)
        writer.writerows(contents)



def _to_html(json_obj):
    """Generate simple html from zuul_result obj"""

    def make_header(hlist):

        tmp = ""
        for h in hlist:
            tmp = tmp + "<th>" + h + "</th>"
        return "<thead><tr>{}</tr></thead>".format(tmp)

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
        line_html = line_html + "<td><a href={result}>{name}</a></td>"
        line_html = line_html + "<td><a href={job_output}>x</a></td>"
        line_html = line_html + "<td><a href={testr_results}>x</a></td>"
        line_html = line_html + "<td>{t_start}</td>"
        line_html = line_html + "<td>{t_end}</td>"
        line_html = line_html + "<td>{time}</td>"
        line_html = line_html + "<td><a href={logs}>x</td>"
        line_html = line_html + "<td><a href={art}>download</td>"
        line_html = line_html + "</tr>"

        testr_results = "{}{}".format(jd["log_url"], "testr_results.html")
        job_output = "{}{}".format(jd["log_url"], "job-output.txt")
        t_start = jd["start_time"].replace("T", " ")
        t_end = jd["end_time"].replace("T", " ")

        b = line_html.format(
                num=cnt, g_url=jd["ref_url"], ps=jd["patchset"],
                name=j["name"], result=j["url"],
                job_output=job_output, testr_results=testr_results,
                t_start=t_start, t_end=t_end,
                time=j["time"],
                logs=jd["log_url"], art=jd["artifacts"][0]["url"])

        bs = "{}{}".format(bs, b)
        cnt += 1

    styles = ["table,th,tr,td {border: 1px solid; text-align: center;}",
            ".title {font-size: 2em;}"]
    thead = make_header(HEADER_LIST)
    tbody = "<tbody>{}</tbody>".format(bs)

    page_title = "<div class='title'>{msg}</div>".format(
            msg="Zuul test results")
    table = "<div><table>{h}{b}</table></div>".format(h=thead, b=tbody)

    body = "<body>{title}{table}</body>".format(title=page_title, table=table)
    head = "<head>{style}</head>".format(
            style="<style>{}</style>".format(' '.join(styles)))
    html = "<html>{h}{b}</html>".format(h=head, b=body)
    return html


def _output_to_file(json_obj, ofile=None, format="json"):
    """Output results.

    The results is given as JSON object of a list contains each entry.
    """

    if format == "html":
        if ofile is not None:
            with open(ofile, "w") as f:
                f.write(_to_html(json_obj))
        else:
            print(_to_html(json_obj))

    elif format == "csv":
        _to_csv(json_obj, ofile)
    else:
        if ofile is not None:
            with open(ofile, "w") as f:
                f.write(json.dumps(json_obj))
        else:
            print(json.dumps(json_obj))


def _get_zuul_results(ch_ids, test_results, job_name):
    """Get a list of job results matched with given conditions.
    
    The given conditions are evaluated from job_name first, then test_results.
    If job_name is not None, the next check for test_results will be skipped.
    For example, if no job_name and a test_results ['SUCCESS'] are given, it
    returns all results matched with SUCCESS.
    """

    zuul_results = []
    ptns = []
    if job_name is not None:
        ptns.append(re.compile(r'^- ({}) (.*) : .* in (.*)$'.format(job_name)))
    else:
        if test_results is not None:
            test_results = set(test_results)
        else:
            test_results = TEST_RESULTS - {"SUCCESS"}
        for ts in test_results:
            ptns.append(
                re.compile(r'^- (.*) (.*) : {} in (.*)$'.format(ts)))

    for ptn in ptns:
        for chid in ch_ids:
            msg_objs = _change_messages(chid)
            for obj in msg_objs:
                for m in obj["message"].split("\n"):
                    matched = ptn.match(m)
                    if matched is not None:
                        name = matched.group(1)
                        url = matched.group(2)
                        time = matched.group(3).replace(" (non-voting)", "")
                        zr = {"name": name, "url": url, "time": time}
                        zuul_results.append(zr)

    return zuul_results


def _setup_ch_ids(ch_ids):

    def _parse_change_ids_file(fname):
        ch_ids = []
        with open(fname) as f:
            for l in f.readlines():
                if not l.startswith("#"):
                    ch_ids.append(l.rstrip())
        return list(set(ch_ids))

    ch_files = []
    ids = []
    for i in ch_ids:
        if os.path.isfile(i):
            ch_files.append(i)
            ids = ids + _parse_change_ids_file(i)
    return list(set(ids + ch_ids) - set(ch_files))


def main():
    args = _parse_args()

    ch_ids = []
    if args.change_ids is not None:
        ch_ids = list(set(args.change_ids))
    ch_ids = _setup_ch_ids(ch_ids)

    # Find format from output file.
    ofile_ext = None
    if args.output_file is not None:
        ofile_ext = os.path.splitext(args.output_file)[-1]
        ofile_ext = ofile_ext.replace(".", "")

    # Overwrite output format if it's not specified explicitly, or do not
    # anything on the other hand.
    if (args.format is None) and (ofile_ext is not None):
        args.format = ofile_ext

    if args.input_json is not None:
        zuul_results = json.load(open(args.input_json))
    else:
        zuul_results = _get_zuul_results(ch_ids, args.test_results, args.job_name)

        for zr in zuul_results:
            uuid = zr["url"].split("/")[-1]
            req_zuul = "{}/api/tenant/openstack/builds?uuid={}".format(
                ZUUL_BASE, uuid)

            r = requests.get(req_zuul)
            zr["detail"] = json.loads(r.text)

    filtered_results = []  # filter with term
    if args.term is not None:
        dterm = int(eval(args.term))
        for zr in zuul_results:
            dt = datetime.datetime.strptime(
                    zr["detail"][0]["event_timestamp"], '%Y-%m-%dT%H:%M:%S')
            ddelta = datetime.datetime.now() - datetime.timedelta(hours=dterm)
            if dt > ddelta:
                filtered_results.append(zr)
    else:
        filtered_results = zuul_results

    _output_to_file(filtered_results, args.output_file, args.format)

if __name__ == '__main__':
    main()
