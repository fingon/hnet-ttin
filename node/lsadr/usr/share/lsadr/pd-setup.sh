#!/bin/sh
#-*-sh-*-
#
# $Id: pd-setup.sh $
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Created:       Tue Jul 24 16:06:53 2012 mstenber
# Last modified: Thu Oct 25 22:30:10 2012 mstenber
# Edit time:     30 min
#

BLACKHOLE_METRIC=1234567

if [ -f ip-util.sh ]
then
    . ./ip-util.sh
else
    . /usr/share/lsadr/ip-util.sh
fi

usage() 
{
    echo "Usage: $0 <start/stop> <ip6-prefix/ip6-prefix-length> <wan-if> <lan-if>"
    exit 1
}

perform_ip_cmds()
{
    MODE=$1

    # Add default route to the source-specific table
    ip -6 route $MODE default via $NH dev $WAN_IF table $TABLE

    # And also to the global one (to have a default)
    ip -6 route $MODE default via $NH dev $WAN_IF 

    # If we don't have LAN_IF set, we're in 
    if [ "x$LAN_IF" = "x" ]
    then
        return
    fi

    if [ ! $PREFIX_LEN = 64 ]
    then
        # Note: Linux kernel has a bug, which requires dev to be
        # specified for ip -6 routes with e.g. throw and blackhole
        # target. If yours is too old, yours does too. Oh well. 
        
        # Add throw rule for those not matching the specific routes
        ip -6 route $MODE throw $PREFIX table $TABLE

        # And blackhole them in main table to prevent routing loops
        # (with high enough metric)
        ip -6 route $MODE blackhole $PREFIX metric $BLACKHOLE_METRIC
    fi

    # Finally, add the address to the $LAN_IF
    # (PREFIX_IPV6 ends with :: => 1/64 is fine way to add our address)
    ip -6 addr $MODE ${PREFIX_IPV6}1/64 dev $LAN_IF
}

shared_init() {
    PREFIX_IPV6=`ipv6pfx_to_ipv6 $PREFIX`
    PREFIX_LEN=`ipv6pfx_to_len $PREFIX`

    PREFERENCE=$((1128-${PREFIX_LEN}))
    TABLE=`get_or_add_ip6_table_for_prefix_pref $PREFIX $PREFERENCE`

    NH=`get_if_default_ipv6_nexthop $WAN_IF`
    if [ "x$NH" = x ]
    then
        echo "No default next-hop found on $WAN_IF"
        exit 1
    fi
}

if [ $# -ne 4 -a $# -ne 3 ]
then
    usage
fi

OP=$1
PREFIX=$2
WAN_IF=$3
LAN_IF=$4

case $OP in
    start)
        shared_init
        perform_ip_cmds add
        ;;
    stop)
        shared_init
        perform_ip_cmds del
        ;;
    *)
        usage
        ;;
esac

