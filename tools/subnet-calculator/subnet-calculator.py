#!/usr/bin/env python3
"""Calculate subnet details for an IPv4 network.

Shows network address, broadcast, netmask, wildcard, first and last usable
host, host count, and the CIDR split into two halves.

Usage:
    subnet-calculator.py 192.168.1.0/24
    subnet-calculator.py 10.0.5.23/20
"""

import argparse
import ipaddress
import sys


def describe(net):
    lines = []
    lines.append("Network:       %s" % net.network_address)
    lines.append("Broadcast:     %s" % net.broadcast_address)
    lines.append("Netmask:       %s" % net.netmask)
    lines.append("Wildcard:      %s" % net.hostmask)
    lines.append("Prefix length: /%d" % net.prefixlen)
    lines.append("Total IPs:     %d" % net.num_addresses)
    if net.num_addresses <= 2:
        lines.append("Usable hosts:  %d (point-to-point or single host)" % max(net.num_addresses - 2, 0))
    else:
        hosts = list(net.hosts())
        lines.append("First host:    %s" % hosts[0])
        lines.append("Last host:     %s" % hosts[-1])
        lines.append("Usable hosts:  %d" % (net.num_addresses - 2))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Show subnet details for an IPv4 address in CIDR notation.",
        epilog="Examples:\n"
               "  subnet-calculator.py 192.168.1.0/24\n"
               "  subnet-calculator.py 10.0.5.23/20\n"
               "  subnet-calculator.py 172.16.0.0/12 --binary",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("network", help="IPv4 network in CIDR notation, e.g. 192.168.1.0/24")
    parser.add_argument("--binary", action="store_true",
                        help="also show the netmask in binary")
    args = parser.parse_args(argv)

    try:
        net = ipaddress.ip_network(args.network, strict=False)
    except ValueError as exc:
        parser.error("invalid network %r: %s" % (args.network, exc))

    print(describe(net))
    if args.binary:
        bits = "".join("%08b" % b for b in net.netmask.packed)
        dotted = ".".join(str(int(bits[i:i + 8], 2)) for i in range(0, 32, 8))
        print("Netmask binary: %s.%s.%s.%s" % (bits[0:8], bits[8:16], bits[16:24], bits[24:32]))
        print("Netmask dotted: %s" % dotted)
    return 0


if __name__ == "__main__":
    sys.exit(main())
