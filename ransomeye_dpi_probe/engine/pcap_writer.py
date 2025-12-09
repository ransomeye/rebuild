# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/engine/pcap_writer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Efficient chunked PCAP writer for storing captured packets

import os
import struct
import time
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


class PCAPWriter:
    """Efficient PCAP file writer with rotation."""
    
    # PCAP global header (magic number, version, timezone, sigfigs, snaplen, network)
    PCAP_GLOBAL_HEADER = struct.pack('@ I H H i I I I',
                                      0xa1b2c3d4,  # magic number
                                      2,  # version major
                                      4,  # version minor
                                      0,  # thiszone
                                      0,  # sigfigs
                                      65535,  # snaplen
                                      1)  # network (Ethernet)
    
    # PCAP packet header format
    PACKET_HEADER_FORMAT = '@ I I I I'  # ts_sec, ts_usec, incl_len, orig_len
    
    def __init__(self, output_dir: str, max_file_size_mb: int = 100, 
                 rotate_on_time: bool = True, rotation_interval_sec: int = 3600):
        """
        Initialize PCAP writer.
        
        Args:
            output_dir: Directory for PCAP files
            max_file_size_mb: Maximum file size before rotation (MB)
            rotate_on_time: Enable time-based rotation
            rotation_interval_sec: Rotation interval in seconds
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.rotate_on_time = rotate_on_time
        self.rotation_interval = rotation_interval_sec
        
        self.current_file: Optional[file] = None
        self.current_filename: Optional[str] = None
        self.current_size = 0
        self.current_start_time = time.time()
        self.file_count = 0
        self.lock = threading.Lock()
        
        self._rotate_file()
    
    def _get_filename(self) -> str:
        """Generate filename with timestamp."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.file_count += 1
        return f"capture_{timestamp}_{self.file_count:06d}.pcap"
    
    def _rotate_file(self):
        """Rotate to new PCAP file."""
        with self.lock:
            if self.current_file:
                self.current_file.close()
                logger.info(f"Rotated PCAP file: {self.current_filename} "
                          f"({self.current_size / 1024 / 1024:.2f} MB)")
            
            self.current_filename = self._get_filename()
            filepath = self.output_dir / self.current_filename
            
            self.current_file = open(filepath, 'wb')
            self.current_file.write(self.PCAP_GLOBAL_HEADER)
            self.current_size = len(self.PCAP_GLOBAL_HEADER)
            self.current_start_time = time.time()
            
            logger.info(f"Started new PCAP file: {self.current_filename}")
    
    def _should_rotate(self) -> bool:
        """Check if rotation is needed."""
        # Size-based rotation
        if self.current_size >= self.max_file_size_bytes:
            return True
        
        # Time-based rotation
        if self.rotate_on_time:
            if time.time() - self.current_start_time >= self.rotation_interval:
                return True
        
        return False
    
    def write_packet(self, packet_data: bytes, timestamp: Optional[float] = None):
        """
        Write a packet to PCAP file.
        
        Args:
            packet_data: Raw packet bytes (Ethernet frame)
            timestamp: Optional timestamp (default: current time)
        """
        if timestamp is None:
            timestamp = time.time()
        
        ts_sec = int(timestamp)
        ts_usec = int((timestamp - ts_sec) * 1000000)
        
        incl_len = len(packet_data)
        orig_len = incl_len
        
        # Write packet header
        header = struct.pack(self.PACKET_HEADER_FORMAT,
                           ts_sec, ts_usec, incl_len, orig_len)
        
        with self.lock:
            if self._should_rotate():
                self._rotate_file()
            
            self.current_file.write(header)
            self.current_file.write(packet_data)
            self.current_file.flush()  # Ensure data is written
            
            self.current_size += len(header) + incl_len
    
    def write_packets(self, packets: List[tuple]):
        """
        Write multiple packets efficiently.
        
        Args:
            packets: List of (packet_data, timestamp) tuples
        """
        with self.lock:
            if self._should_rotate():
                self._rotate_file()
            
            for packet_data, timestamp in packets:
                if timestamp is None:
                    timestamp = time.time()
                
                ts_sec = int(timestamp)
                ts_usec = int((timestamp - ts_sec) * 1000000)
                
                incl_len = len(packet_data)
                orig_len = incl_len
                
                header = struct.pack(self.PACKET_HEADER_FORMAT,
                                   ts_sec, ts_usec, incl_len, orig_len)
                
                if self.current_size + len(header) + incl_len > self.max_file_size_bytes:
                    self._rotate_file()
                
                self.current_file.write(header)
                self.current_file.write(packet_data)
                self.current_size += len(header) + incl_len
            
            self.current_file.flush()
    
    def get_current_file(self) -> Optional[str]:
        """Get current PCAP filename."""
        with self.lock:
            return self.current_filename
    
    def get_stats(self) -> dict:
        """Get writer statistics."""
        with self.lock:
            return {
                'current_file': self.current_filename,
                'current_size_mb': self.current_size / 1024 / 1024,
                'file_count': self.file_count,
                'max_size_mb': self.max_file_size_bytes / 1024 / 1024
            }
    
    def close(self):
        """Close current file."""
        with self.lock:
            if self.current_file:
                self.current_file.close()
                self.current_file = None
                logger.info(f"Closed PCAP writer: {self.current_filename}")

