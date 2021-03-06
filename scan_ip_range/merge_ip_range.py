#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import subprocess
import sys
import urllib2
import math


from ip_utils import *

# This code functions:
# read ip range string in code
# merge over lapped range
# filter out bad ip range

# Then reproduce good format file


# Support format:
# # Comment (#）
#
# range seperater:
# range can seperate by (,) or(|) or new line
#
# Single rang format: ：
# "xxx.xxx.xxx-xxx.xxx-xxx"
# "xxx.xxx.xxx."
# "xxx.xxx.xxx.xxx/xx"
# "xxx.xxx.xxx.xxx"


def PRINT(strlog):
    print (strlog)


def print_range_list(ip_range_list):
    for ip_range in ip_range_list:
        begin = ip_range[0]
        end = ip_range[1]
        print ip_num_to_string(begin), ip_num_to_string(end)


def merge_range(input_ip_range_list):
    output_ip_range_list = []
    range_num = len(input_ip_range_list)

    last_begin = input_ip_range_list[0][0]
    last_end = input_ip_range_list[0][1]
    for i in range(1,range_num):
        ip_range = input_ip_range_list[i]
        begin = ip_range[0]
        end = ip_range[1]

        #print "now:",ip_num_to_string(begin), ip_num_to_string(end)

        if begin > last_end + 2:
            #print "add:",ip_num_to_string(begin), ip_num_to_string(end)
            output_ip_range_list.append([last_begin, last_end])
            last_begin = begin
            last_end = end
        else:
            # print "merge:", ip_num_to_string(last_begin), ip_num_to_string(last_end), ip_num_to_string(begin), ip_num_to_string(end)
            if end > last_end:
                last_end = end

    output_ip_range_list.append([last_begin, last_end])

    return output_ip_range_list


def filter_ip_range(good_range, bad_range):
    out_good_range = []
    bad_i = 0

    bad_begin, bad_end = bad_range[bad_i]

    for good_begin, good_end in good_range:
        while True:
            if good_begin > good_end:
                PRINT("bad good ip range when filter:%s-%s" % (ip_num_to_string(good_begin), ip_num_to_string(good_end)))
                assert(good_begin < good_end)
            if good_end < bad_begin:
                # case:
                #     [  good  ]
                #                   [  bad  ]
                out_good_range.append([good_begin, good_end])
                break
            elif bad_end < good_begin:
                # case:
                #                   [  good  ]
                #     [   bad   ]
                bad_i += 1
                bad_begin, bad_end = bad_range[bad_i]
                continue
            elif good_begin <= bad_begin and good_end <= bad_end:
                # case:
                #     [   good    ]
                #           [   bad   ]
                PRINT("cut bad ip case 1:%s - %s" % (ip_num_to_string(bad_begin), ip_num_to_string(good_end)))
                if bad_begin - 1 > good_begin:
                    out_good_range.append([good_begin, bad_begin - 1])
                break
            elif good_begin >= bad_begin and good_end == bad_end:
                # case:
                #           [   good   ]
                #     [      bad       ]
                PRINT("cut bad ip case 2:%s - %s" % (ip_num_to_string(good_begin), ip_num_to_string(bad_end)))

                bad_i += 1
                bad_begin, bad_end = bad_range[bad_i]
                break
            elif good_begin >= bad_begin and good_end > bad_end:
                # case:
                #           [   good   ]
                #     [    bad  ]
                PRINT("cut bad ip case 3:%s - %s" % (ip_num_to_string(good_begin), ip_num_to_string(bad_end)))
                good_begin = bad_end + 1
                bad_i += 1
                bad_begin, bad_end = bad_range[bad_i]
                continue
            elif good_begin <= bad_begin and good_end >= bad_end:
                # case:
                #     [     good     ]
                #         [  bad  ]
                out_good_range.append([good_begin, bad_begin - 1])
                PRINT("cut bad ip case 4:%s - %s" % (ip_num_to_string(bad_begin), ip_num_to_string(bad_end)))
                good_begin = bad_end + 1
                bad_i += 1
                bad_begin, bad_end = bad_range[bad_i]
                continue
            elif good_begin >= bad_begin and good_end <= bad_end:
                # case:
                #          [good]
                #      [    bad    ]
                PRINT("cut bad ip case 5:%s - %s" % (ip_num_to_string(good_begin), ip_num_to_string(good_end)))
                break
            else:
                PRINT("any case? good:%s-%s bad:%s-%s" % (ip_num_to_string(good_begin), ip_num_to_string(good_end),
                    ip_num_to_string(bad_begin), ip_num_to_string(bad_end)))
                assert( False )

    return out_good_range


def download_apic(filename):
    url = 'http://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest'
    try:
        data = subprocess.check_output(['wget', url, '-O-'])
    except (OSError, AttributeError):
        print >> sys.stderr, "Fetching data from apnic.net, "\
                             "it might take a few minutes, please wait..."
        data = urllib2.urlopen(url).read()

    with open(filename, "w") as f:
        f.write(data)
    return data


def generate_range_from_apnic(input):

    cnregex = re.compile(r'^apnic\|(?:cn)\|ipv4\|[\d\.]+\|\d+\|\d+\|a\w*$',
                         re.I | re.M )
    cndata = cnregex.findall(input)

    results = []

    for item in cndata:
        unit_items = item.split('|')
        starting_ip = unit_items[3]
        num_ip = int(unit_items[4])

        cidr = 32 - int(math.log(num_ip, 2))

        results.append("%s/%s" % (starting_ip, cidr))

    return "\n".join(results)


def load_bad_ip_range():
    file_name = "delegated-apnic-latest.txt"
    apnic_file = file_name
    if not os.path.isfile(apnic_file):
        download_apic(apnic_file)

    with open(apnic_file, "r") as inf:
        apnic_lines = inf.read()

    bad_ip_range_lines = generate_range_from_apnic(apnic_lines)

    special_bad_ip_range_lines = """
    0.0.0.0/8               # localhost
    10.0.0.0/8              # private 
    100.64.0.0/10           # ISP share ip
    127.0.0.0/8             # loop back network
    130.211.0.0/16          # Empty ip range, no route to it.
    169.254.0.0/16          # link local
    172.16.0.0/12           # private network
    192.0.0.0/24            # private network
    192.0.2.0/24            # TEST-NET-1
    192.88.99.0/24          # 6-to-4 relay
    192.168.0.0/16          # private network
    198.18.0.0/15           # network base test
    198.51.100.0/24         # TEST-NET-2
    203.0.113.0/24          # TEST-NET-3
    224.0.0.0/4             # group broadcast address(group D)
    240.0.0.0/4             # preserve ip    
    255.255.255.255/32      # for algorithm
    """
    return bad_ip_range_lines + special_bad_ip_range_lines


def generate_ip_range(input_file, output_file):
    # load input good ip range

    ip_range_list = load_ip_range(input_file)
    ip_range_list = merge_range(ip_range_list)
    # PRINT("Good ip range:\n")
    # print_range_list(ip_range_list)

    if True:
        input_bad_ip_range_lines = load_bad_ip_range()
        bad_range_list = parse_range_string(input_bad_ip_range_lines)
        bad_range_list = merge_range(bad_range_list)
        # PRINT("Bad ip range:\n")
        # print_range_list(ip_range_list)

        ip_range_list = filter_ip_range(ip_range_list, bad_range_list)
        # PRINT("Output ip range:\n")
        # print_range_list(ip_range_list)

    # write out
    fd = open(output_file, "w")
    for ip_range in ip_range_list:
        begin = ip_range[0]
        end = ip_range[1]
        #print ip_num_to_string(begin), ip_num_to_string(end)
        fd.write(ip_num_to_string(begin)+ "-" + ip_num_to_string(end)+"\n")

    fd.close()


def test_load(file_name):
    print("Begin test load %s\n" % file_name)
    fd = open(file_name, "r")
    if not fd:
        print("open %s fail." % file_name)
        exit()

    amount = 0
    for line in fd.readlines():
        if len(line) == 0 or line[0] == '#':
            continue
        begin, end = split_ip(line)

        nbegin = ip_string_to_num(begin)
        nend = ip_string_to_num(end)

        num = nend - nbegin
        amount += num
        # print ip_num_to_string(nbegin), ip_num_to_string(nend), num

    fd.close()
    print "amount ip:", amount


def main():

    file_name = "ip_range_in.txt"
    input_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_name)

    output_file = "ip_range_out.txt"

    generate_ip_range(input_file, output_file)
    test_load(output_file)


if __name__ == "__main__":
    main()
