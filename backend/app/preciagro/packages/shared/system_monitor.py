"""System resource monitoring for infrastructure metrics."""

from __future__ import annotations

import logging
import os
import psutil
import threading
import time
from typing import Optional

from .metrics import (
    update_system_metrics,
    disk_read_bytes_total,
    disk_write_bytes_total,
    network_tx_bytes_total,
    network_rx_bytes_total,
)

logger = logging.getLogger(__name__)


class SystemMonitor:
    """Monitor system resources and update Prometheus metrics."""
    
    def __init__(self, service_name: str, interval_seconds: int = 15):
        """Initialize system monitor.
        
        Args:
            service_name: Name of the service
            interval_seconds: How often to collect metrics
        """
        self.service_name = service_name
        self.interval_seconds = interval_seconds
        self.process = psutil.Process(os.getpid())
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
        # Track previous I/O counters for delta calculations
        self._prev_disk_io = None
        self._prev_net_io = None
    
    def start(self) -> None:
        """Start monitoring in background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("System monitor already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"System monitor started for {self.service_name}")
    
    def stop(self) -> None:
        """Stop monitoring."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info(f"System monitor stopped for {self.service_name}")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while not self._stop_event.is_set():
            try:
                self._collect_metrics()
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
            
            time.sleep(self.interval_seconds)
    
    def _collect_metrics(self) -> None:
        """Collect and update all system metrics."""
        # CPU and Memory
        cpu_percent = self.process.cpu_percent(interval=None)
        memory_info = self.process.memory_info()
        memory_percent = self.process.memory_percent()
        
        update_system_metrics(
            service=self.service_name,
            cpu_percent=cpu_percent,
            memory_bytes=memory_info.rss,
            memory_percent=memory_percent
        )
        
        # Disk I/O (process-specific)
        try:
            io_counters = self.process.io_counters()
            if self._prev_disk_io:
                read_delta = io_counters.read_bytes - self._prev_disk_io.read_bytes
                write_delta = io_counters.write_bytes - self._prev_disk_io.write_bytes
                
                if read_delta > 0:
                    disk_read_bytes_total.labels(service=self.service_name).inc(read_delta)
                if write_delta > 0:
                    disk_write_bytes_total.labels(service=self.service_name).inc(write_delta)
            
            self._prev_disk_io = io_counters
        except (psutil.AccessDenied, AttributeError):
            # I/O counters not available on all platforms
            pass
        
        # Network I/O (system-wide, approximation)
        try:
            net_io = psutil.net_io_counters()
            if self._prev_net_io:
                tx_delta = net_io.bytes_sent - self._prev_net_io.bytes_sent
                rx_delta = net_io.bytes_recv - self._prev_net_io.bytes_recv
                
                if tx_delta > 0:
                    network_tx_bytes_total.labels(service=self.service_name).inc(tx_delta)
                if rx_delta > 0:
                    network_rx_bytes_total.labels(service=self.service_name).inc(rx_delta)
            
            self._prev_net_io = net_io
        except Exception:
            # Network counters not always available
            pass


# Global monitor instance
_monitor: Optional[SystemMonitor] = None


def start_system_monitoring(service_name: str, interval_seconds: int = 15) -> None:
    """Start system resource monitoring.
    
    Args:
        service_name: Name of the service
        interval_seconds: How often to collect metrics
    
    Example:
        from preciagro.packages.shared.system_monitor import start_system_monitoring
        
        # In FastAPI lifespan
        start_system_monitoring("my-service")
    """
    global _monitor
    if _monitor:
        logger.warning("System monitor already initialized")
        return
    
    _monitor = SystemMonitor(service_name, interval_seconds)
    _monitor.start()


def stop_system_monitoring() -> None:
    """Stop system resource monitoring."""
    global _monitor
    if _monitor:
        _monitor.stop()
        _monitor = None
