#!/bin/bash -ue
#-*-sh-*-
#
# $Id: test-ip-util.sh $
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Created:       Tue Jul 10 10:24:42 2012 mstenber
# Last modified: Wed Sep  5 16:28:25 2012 mstenber
# Edit time:     8 min
#

. ./ip-util.sh

echo 0
my_6rd_relay_prefix_from_ip_ipmasklen 1.2.3.4 0
my_6rd_ipv6_from_prefix_ipv4 2000:: 1.2.3.4 0

echo 8
my_6rd_relay_prefix_from_ip_ipmasklen 1.2.3.4 8
my_6rd_ipv6_from_prefix_ipv4 2000:: 1.2.3.4 8

echo 16
my_6rd_relay_prefix_from_ip_ipmasklen 1.2.3.4 16
my_6rd_ipv6_from_prefix_ipv4 2000:: 1.2.3.4 16

echo 24
my_6rd_relay_prefix_from_ip_ipmasklen 1.2.3.4 24
my_6rd_ipv6_from_prefix_ipv4 2000:: 1.2.3.4 24

get_if_ipv4 eth2

reset_ip6_rules
echo "z" `get_ip6_tables_for_prefix_pref all`
echo "x" `get_or_add_ip6_table_for_prefix_pref dead::/16`
echo "y" `get_or_add_ip6_table_for_prefix_pref feed::/16`
echo "y-2" `get_or_add_ip6_table_for_prefix_pref feed::/16`
echo "y-2-123" `get_or_add_ip6_table_for_prefix_pref feed::/16 123`
echo "y-2-123-2" `get_or_add_ip6_table_for_prefix_pref feed::/16 123`
delete_ip6_rules_matching feed::/16 pref 123

echo "nh-ok" `get_if_default_ipv6_nexthop eth1`
echo "nh-!ok" `get_if_default_ipv6_nexthop asdf`

echo_radvd_conf eth2

# then, add fake blackhole route to test the delete-by-metric
BLACKHOLE_METRIC=1234567
ip -6 route add blackhole ::1.2.3.4/96 dev eth2 metric $BLACKHOLE_METRIC
delete_routes_matching_metric $BLACKHOLE_METRIC
delete_routes_matching_metric $BLACKHOLE_METRIC

