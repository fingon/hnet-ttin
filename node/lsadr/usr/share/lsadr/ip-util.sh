#!/bin/sh
#-*-sh-*-
#
# $Id: ip-util.sh $
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Created:       Tue Jul 10 08:40:55 2012 mstenber
# Last modified: Thu Oct 25 22:46:07 2012 mstenber
# Edit time:     133 min
#

## Utilities that deal with ip -6

ip() 
{
    if [ "xIP_UTIL_NODEBUG" = "x" ] ; then
        echo "# ip $*" 1>&2
    fi
    for P in /sbin /usr/sbin
    do
        if [ -f $P/ip ]
        then
            $P/ip $*
            return
        fi
    done
    echo "ip not found!"
    exit 1
}

# few ip command utility aliases

delete_ip6_rules_matching()
{
    while ip -6 rule del $* 2>/dev/null
    do
        # nop
        true
    done
}

delete_routes_matching_metric()
{
    METRIC=$1

    for PREFIX in `ip -6 route | grep " metric $METRIC " | cut -d ' ' -f 1`
    do
        ip -6 route del $PREFIX
    done
}


reset_ip6_rules()
{
    # Delete ALL rules
    #delete_ip6_rules_matching
    ip -6 rule flush

    # Add back the 'default' rules
    # flush leaves this, but not default main table rule
    #ip -6 rule add table local pref 0
    ip -6 rule add
}

get_ip6_table_output_for_prefix()
{
    PREFIX=$1
    ip -6 rule | grep "from $PREFIX" 
}

get_ip6_table_output_for_prefix_pref()
{
    PREFIX=$1
    if [ $# = 2 ]
    then
        PREF=$2
        get_ip6_table_output_for_prefix $PREFIX | egrep "^$PREF:"
    else
        get_ip6_table_output_for_prefix $PREFIX
    fi
}


get_ip6_tables_for_prefix_pref() 
{
    get_ip6_table_output_for_prefix_pref $* | sed 's/^.* lookup //' | sort | uniq
}

has_ip6_table_rules() 
{
    TABLE=$1
    ip -6 rule | egrep -q " lookup $TABLE"
}

get_or_add_ip6_table_for_prefix_pref() 
{
    TABLE=`get_ip6_tables_for_prefix_pref $*`
    PREFIX=$1
    if [ -z $TABLE ]
    then
        TABLE=1000
        while has_ip6_table_rules $TABLE
        do
            #TABLE=$(($TABLE+1))

            # .. 'someone' has compiled ash without expression support
            # this works there too (but is less efficient)
            TABLE=`expr $TABLE + 1`
        done
        MYPREF=""
        if [ $# = 2 ]
        then
            MYPREF="pref $2"
        fi

        # Clear the newly found table 
        ip -6 route flush table $TABLE
        
        # And then add rule which points at the table
        ip -6 rule add from $PREFIX table $TABLE $MYPREF
    fi
    echo $TABLE
}

filter_not_ours_ipv6_linklocal()
{
    for ADDRESS in $*
    do
        #echo "Considering $ADDRESS" 1>&2

        # can't trail space - there may be /prefixlen there
        if ! ip -6 addr | grep " $ADDRESS" >/dev/null
        then
            #echo "Not local" 1>&2
            echo $ADDRESS
        fi
    done
}

get_if_default_ipv6_nexthop()
{
    DEV=$1

    # First off, if kernel has already something in default
    # routing table, we can live with that
    NH=`ip -6 route show dev $DEV default 2>/dev/null | head -1 | cut -d ' ' -f 3`
    # Sanity check
    if [ x`echo $NH | cut -d ':' -f 1` = xfe80 ]
    then
        echo $NH
    fi

    # Fallback to rdisc6 - anyone there?
    NH=`rdisc6 -1 $DEV 2>/dev/null | egrep '^ from ' | head -1 | cut -d ' ' -f 3`
    # Sanity check
    if [ x`echo $NH | cut -d ':' -f 1` = xfe80 ]
    then
        #echo "Got: '$NH'"
        NONH=`filter_not_ours_ipv6_linklocal $NH`
        if [ "x$NONH" = x ]
        then
            NHS=`rdisc6 -m $DEV 2>/dev/null | egrep '^ from ' | cut -d ' ' -f 3`
            NONH=`filter_not_ours_ipv6_linklocal $NHS | head -1`
            if [ ! "x$NONH" = x ]
            then
                echo $NONH
                return
            fi
            # fallback beyond this? who knows :p
        else
            echo $NONH
            return
        fi
    fi
}


## 6RD-related utilities

get_if_ipv4() 
{
    DEV=$1
    ip -4 addr show dev $DEV | grep " inet " | cut -d '/' -f 1 | sed 's/^.* inet //'
}

ipv6pfx_to_ipv6() 
{
    echo $* | cut -d '/' -f 1
}

ipv6pfx_to_len() 
{
    echo $* | cut -d '/' -f 2
}

my_6rd_relay_prefix_from_ip_ipmasklen() 
{
    IP=$1
    IPMASKLEN=$2
    case "${IPMASKLEN}" in
        32)
            echo $IP
            ;;
        24)
            echo `echo $IP | cut -d '.' -f 1-3`".0"
            ;;
        16)
            echo `echo $IP | cut -d '.' -f 1-2`.0.0
            ;;
        8)
            echo `echo $IP | cut -d '.' -f 1`.0.0.0
            ;;
        0)
            echo "0.0.0.0"
            ;;
    esac
}

my_6rd_ipv6_from_prefix_ipv4() 
{
    # Base IPv6 prefix (foo:: or foo::/64)
    PREFIX=$(ipv6pfx_to_ipv6 $1)
    # IP (ipv4)
    IP=$2
    # 6RD prefix portion length 
    IPMASKLEN=$3
    
    base=$(echo $PREFIX | sed 's/::/:/')
    case "${IPMASKLEN}" in
        24)
            ipvalues=`echo $IP | cut -d '.' -f 4`" 0"
            ipvalues=$(echo $ipvalues | sed 's/\./ /g')
            echo ${base}$(printf "%x%02x::1" `echo $ipvalues`)
            ;;
        16)
            ipvalues=`echo $IP | cut -d '.' -f 3-4`
            ipvalues=$(echo $ipvalues | sed 's/\./ /g')
            echo ${base}$(printf "%x%02x::1" `echo $ipvalues`)
            ;;
        8)
            ipvalues=`echo $IP | cut -d '.' -f 2-4`" 0"
            ipvalues=$(echo $ipvalues | sed 's/\./ /g')
            echo ${base}$(printf "%x%02x:%x%02x::1" `echo $ipvalues`)
            ;;
        0)
            ipvalues=$IP
            ipvalues=$(echo $ipvalues | sed 's/\./ /g')
            echo ${base}$(printf "%x%02x:%x%02x::1" `echo $ipvalues`)
            ;;
        *)
            echo "Unsupported 6rd mask length $IPMASKLEN"
            exit 1
            ;;
    esac
}

## radvd.conf utilities

echo_radvd_conf()
{
    IF=$1
    echo "interface $IF {"
    cat <<EOF
  AdvSendAdvert on;
  AdvManagedFlag off;
  AdvOtherConfigFlag off;
  AdvDefaultLifetime 600;
EOF
    for ADDR in `ip -6 addr show dev $IF scope global | grep inet6 | cut -d ' ' -f 6`
    do
        echo "  prefix $ADDR {"
        cat <<EOF
    AdvOnLink on;
    AdvAutonomous on;
  };
EOF
    done
    echo "};"
}

reconfigure_radvd()
{
    IF=$1

    # Wait for old radvd to die (if any)
    while ps | grep radvd | grep -v grep >/dev/null
    do
        sleep 1
        # send kill, if relevant - this is to prevent
        # someone else starting radvd in the interim and us getting stuck
        killall -q -9 radvd
    done

    # Write new configuration
    echo_radvd_conf $IF > /tmp/radvd.conf

    # And start fresh radvd
    radvd -C /tmp/radvd.conf
}
