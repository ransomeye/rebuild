# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/tools/traffic_generator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Test tool for generating synthetic network flows using Scapy

import sys
import time
import random
import logging
from scapy.all import IP, TCP, UDP, ICMP, send, RandIP, RandShort, Ether
from scapy.layers.inet import get_if_addr

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_tcp_flow(src_ip: str, dst_ip: str, duration: int = 10, packets_per_sec: int = 10):
    """
    Generate synthetic TCP flow.
    
    Args:
        src_ip: Source IP address
        dst_ip: Destination IP address
        duration: Duration in seconds
        packets_per_sec: Packets per second
    """
    src_port = random.randint(1024, 65535)
    dst_port = random.randint(1, 1024)
    
    logger.info(f"Generating TCP flow: {src_ip}:{src_port} -> {dst_ip}:{dst_port}")
    
    start_time = time.time()
    packet_count = 0
    
    while time.time() - start_time < duration:
        # SYN
        send(IP(src=src_ip, dst=dst_ip)/TCP(sport=src_port, dport=dst_port, flags='S'), verbose=0)
        packet_count += 1
        
        time.sleep(1.0 / packets_per_sec)
        
        # ACK
        send(IP(src=src_ip, dst=dst_ip)/TCP(sport=src_port, dport=dst_port, flags='A'), verbose=0)
        packet_count += 1
        
        time.sleep(1.0 / packets_per_sec)
    
    logger.info(f"Generated {packet_count} TCP packets")


def generate_udp_flow(src_ip: str, dst_ip: str, duration: int = 10, packets_per_sec: int = 20):
    """
    Generate synthetic UDP flow.
    
    Args:
        src_ip: Source IP address
        dst_ip: Destination IP address
        duration: Duration in seconds
        packets_per_sec: Packets per second
    """
    src_port = random.randint(1024, 65535)
    dst_port = random.randint(1, 1024)
    
    logger.info(f"Generating UDP flow: {src_ip}:{src_port} -> {dst_ip}:{dst_port}")
    
    start_time = time.time()
    packet_count = 0
    
    while time.time() - start_time < duration:
        send(IP(src=src_ip, dst=dst_ip)/UDP(sport=src_port, dport=dst_port), verbose=0)
        packet_count += 1
        time.sleep(1.0 / packets_per_sec)
    
    logger.info(f"Generated {packet_count} UDP packets")


def generate_port_scan(src_ip: str, dst_ip: str, port_range: tuple = (1, 100)):
    """
    Generate port scan traffic.
    
    Args:
        src_ip: Source IP address
        dst_ip: Destination IP address
        port_range: Tuple of (start_port, end_port)
    """
    logger.info(f"Generating port scan: {src_ip} -> {dst_ip} ports {port_range[0]}-{port_range[1]}")
    
    src_port = random.randint(1024, 65535)
    
    for dst_port in range(port_range[0], port_range[1] + 1):
        send(IP(src=src_ip, dst=dst_ip)/TCP(sport=src_port, dport=dst_port, flags='S'), verbose=0)
        time.sleep(0.1)
    
    logger.info(f"Generated port scan with {port_range[1] - port_range[0] + 1} packets")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate synthetic network traffic')
    parser.add_argument('--src-ip', type=str, help='Source IP address')
    parser.add_argument('--dst-ip', type=str, help='Destination IP address')
    parser.add_argument('--protocol', type=str, choices=['tcp', 'udp', 'scan'], default='tcp',
                       help='Protocol type')
    parser.add_argument('--duration', type=int, default=10, help='Duration in seconds')
    parser.add_argument('--rate', type=int, default=10, help='Packets per second')
    parser.add_argument('--port-start', type=int, default=1, help='Start port for scan')
    parser.add_argument('--port-end', type=int, default=100, help='End port for scan')
    
    args = parser.parse_args()
    
    # Get default IPs if not provided
    if not args.src_ip:
        try:
            args.src_ip = get_if_addr('eth0')
        except:
            args.src_ip = '192.168.1.100'
    
    if not args.dst_ip:
        args.dst_ip = '192.168.1.1'
    
    if args.protocol == 'tcp':
        generate_tcp_flow(args.src_ip, args.dst_ip, args.duration, args.rate)
    elif args.protocol == 'udp':
        generate_udp_flow(args.src_ip, args.dst_ip, args.duration, args.rate)
    elif args.protocol == 'scan':
        generate_port_scan(args.src_ip, args.dst_ip, (args.port_start, args.port_end))


if __name__ == '__main__':
    main()

