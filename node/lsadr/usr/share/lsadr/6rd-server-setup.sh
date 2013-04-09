#!/bin/sh
#-*-sh-*-
#
# $Id: 6rd-server-setup.sh $
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Created:       Tue Jul 10 14:57:51 2012 mstenber
# Last modified: Fri Sep 14 11:17:55 2012 mstenber
# Edit time:     19 min
#

# Setup the server-side 6rd tunnel
if [ -f ip-util.sh ]
then
    . ./ip-util.sh
else
    . /usr/share/lsadr/ip-util.sh
fi

if [ $# != 3 ]
then
    echo "Usage: $0 <ipv6-6rd-prefix>::/<ipv6-6rd-prefix-len> <interface> <6rd-bits>"
    exit 1
fi

PREFIX=$1
INTERFACE=$2
# IP mask length
IPMASKLEN=$3

# XXX - should we care about MTU? or let PMTU take care of it?

MYIF=6rd
PREFIXLEN=$(ipv6pfx_to_len $PREFIX)
MYIP=$(get_if_ipv4 $INTERFACE)
MYIP6=$(my_6rd_ipv6_from_prefix_ipv4 $PREFIX $MYIP $IPMASKLEN)
RELAYPREFIX=$(my_6rd_relay_prefix_from_ip_ipmasklen $MYIP $IPMASKLEN)/$IPMASKLEN

# configure 6rd topology while we're at it (as per http://www.litech.org/6rd/)
ip tunnel add $MYIF mode sit local ${MYIP} ttl 64
ip tunnel $MYIF dev $MYIF 6rd-prefix ${PREFIX} 6rd-relay_prefix ${RELAYPREFIX}
ip link set $MYIF up
ip -6 addr add ${MYIP6}/${PREFIXLEN} dev 6rd
#ip -6 addr add ${MYIP6}/64 dev ${INTERFACE}
