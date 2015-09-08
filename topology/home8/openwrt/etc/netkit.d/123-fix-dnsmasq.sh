#! /bin/sh

uci set dhcp.@dnsmasq[0].rebind_protection=0
uci set dhcp.@dnsmasq[0].boguspriv=0
uci commit dhcp

reload_config
