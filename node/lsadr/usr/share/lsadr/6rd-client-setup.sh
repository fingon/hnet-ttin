#!/bin/sh
#-*-sh-*-
#
# $Id: 6rd-client-setup.sh $
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Created:       Tue Jul 10 15:38:19 2012 mstenber
# Last modified: Thu Sep  6 13:25:46 2012 mstenber
# Edit time:     47 min
#

# Setup the server-side 6rd tunnel
DEFAULT_METRIC=2000
BLACKHOLE_METRIC=1234567
MYIF=6rd

if [ -f ip-util.sh ]
then
    . ./ip-util.sh
else
    . /usr/share/lsadr/ip-util.sh
fi

if [ $# != 5 ]
then
    echo "Usage: $0 <ipv6-6rd-prefix>::/<ipv6-6rd-prefix-len> <wan-interface> <lan-interface> <6rd-bits> <gw>"
    exit 1
fi

PREFIX=$1
INTERFACE=$2
LAN_INTERFACE=$3
# IP mask length
IP_MASK_LEN=$4
GW=$5

# XXX - should we care about MTU? or let PMTU take care of it?

PREFIX_LEN=$(ipv6pfx_to_len $PREFIX)

if [ -n $new_ip_address  ]
then
    MYIP=$new_ip_address
else
    MYIP=$(get_if_ipv4 $INTERFACE)
fi
MYIP6=$(my_6rd_ipv6_from_prefix_ipv4 $PREFIX $MYIP $IP_MASK_LEN)
MYIP6PREFIX=$(echo $MYIP6 | sed 's/::1$/::/')
MYIP6PREFIX_LEN=$((${PREFIX_LEN}+(32-${IP_MASK_LEN})))
PREFERENCE=$((1128-${MYIP6PREFIX_LEN}))
TABLE=$(get_or_add_ip6_table_for_prefix_pref ${MYIP6PREFIX}/${MYIP6PREFIX_LEN} $PREFERENCE)
RELAYPREFIX=$(my_6rd_relay_prefix_from_ip_ipmasklen $MYIP $IP_MASK_LEN)/$IP_MASK_LEN

# configure 6rd topology while we're at it (as per http://www.litech.org/6rd/)
ip tunnel add $MYIF mode sit local ${MYIP} ttl 64
ip tunnel $MYIF dev $MYIF 6rd-prefix ${PREFIX} 6rd-relay_prefix ${RELAYPREFIX}
# Route the v4 traffic through the 6rd tunnel, this may be redundant
#ip -6 route add ::/96 dev 6rd || true

ip link set $MYIF up

# Note: Linux kernel has a bug, which requires dev to be
# specified for ip -6 routes with e.g. throw and blackhole
# target. If yours is too old, yours does too. Oh well. 

# primarily, we try to handle default route via the source address
# specific table - but only that, the rest goes to main table
if [ ! "x$MYIP6PREFIX_LEN" = 64 ]
then
    ip -6 route add throw $PREFIX table ${TABLE}
fi
ip -6 route add default via ::$GW dev 6rd table ${TABLE} metric ${DEFAULT_METRIC}

# Also add to default routing table
ip -6 route add $PREFIX dev 6rd 
if [ ! "x$MYIP6PREFIX_LEN" = 64 ]
then
    ip -6 route add blackhole $MYIP6PREFIX metric ${BLACKHOLE_METRIC}
fi
ip -6 route add default via ::$GW dev 6rd metric ${DEFAULT_METRIC}

# Finally, configure the $LAN_INTERFACE to have appropriate address
ip -6 addr add ${MYIP6}/64 dev ${LAN_INTERFACE}
