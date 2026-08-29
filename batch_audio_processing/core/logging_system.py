"""
批次音訊處理系統 - 日誌和監控系統
Logging and Monitoring System for Batch Audio Processing

此模組實作了完整的日誌和監控系統，包括：
- 建立結構化日誌記錄
- 實作處理時間統計
- 建立錯誤統計和報告
- 性能監控和資源使用追蹤

Requirements: 6.1, 6.4, 6.5
"""

import os
import time
import logging
import logging.handlers
import json
from dataclasses import dataclass, field

# 嘗試導入 psutil，如果不可用則提供替代實現
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    # 提供簡單的替代實現
    class psutil:
        @staticmethod
        def cpu_percent(interval=1):
            return 0.0
        
        @staticmethod
        def virtual_memory():
            class Memory:
                percent = 0.0
            return Memory()
        
        @staticmethod
        def disk_usage(path):
            class Disk:
                percent = 0.0
            return Disk()
        
        @staticmethod
        def net_io_counters():
            class NetIO:
                def _asdict(self):
                    return {'bytes_sent': 0, 'bytes_recv': 0}
            return NetIO()
        
        @staticmethod
        def disk_io_counters():
            class DiskIO:
                def _asdict(self):
                    return {'read_bytes': 0, 'write_bytes': 0}
            return DiskIO()
from typing import Optional, Dict, List, Any, Callable
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import threading
from contextlib import contextmanager
import traceback
import sys

# 設定日誌
logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """日誌級別"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class MetricType(Enum):
    """指標類型"""
    COUNTER = "counter"        # 計數器
    GAUGE = "gauge"           # 儀表
    HISTOGRAM = "histogram"   # 直方圖
    TIMER = "timer"          # 計時器


@dataclass
class LogEntry:
    """日誌條目"""
    timestamp: datetime
    level: LogLevel
    message: str
    module: str
    function: str = ""
    line_number: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    exception_info: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'message': self.message,
            'module': self.module,
            'function': self.function,
            'line_number': self.line_number,
            'context': self.context,
            'exception_info': self.exception_info
        }


@dataclass
class ProcessingMetrics:
    """處理指標"""
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    total_processing_time: float = 0.0
    average_processing_time: float = 0.0
    transcription_time: float = 0.0
    summary_time: float = 0.0
    document_generation_time: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100
    
    @property
    def completion_rate(self) -> float:
        """完成率"""
        if self.total_files == 0:
            return 0.0
        return ((self.processed_files + self.failed_files + self.skipped_files) / self.total_files) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'total_files': self.total_files,
            'processed_files': self.processed_files,
            'failed_files': self.failed_files,
            'skipped_files': self.skipped_files,
            'total_processing_time': self.total_processing_time,
            'average_processing_time': self.average_processing_time,
            'transcription_time': self.transcription_time,
            'summary_time': self.summary_time,
            'document_generation_time': self.document_generation_time,
            'success_rate': self.success_rate,
            'completion_rate': self.completion_rate
        }


@dataclass
class SystemMetrics:
    """系統指標"""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    network_io: Dict[str, int] = field(default_factory=dict)
    disk_io: Dict[str, int] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'disk_usage': self.disk_usage,
            'network_io': self.network_io,
            'disk_io': self.disk_io,
            'timestamp': self.timestamp.isoformat()
        }


class StructuredLogger:
    """
    結構化日誌記錄器
    
    提供結構化的日誌記錄功能，支援：
    - 多種輸出格式（JSON、文字）
    - 日誌輪轉
    - 上下文資訊記錄
    """
    
    def __init__(self, name: str, log_dir: str = "logs", max_file_size: int = 10*1024*1024, backup_count: int = 5):
        """
        初始化結構化日誌記錄器
        
        Args:
            name: 日誌記錄器名稱
            log_dir: 日誌目錄
            max_file_size: 最大檔案大小（位元組）
            backup_count: 備份檔案數量
        """
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 創建日誌記錄器
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 清除現有處理器
        self.logger.handlers.clear()
        
        # 設定檔案處理器（JSON 格式）
        json_log_file = self.log_dir / f"{name}_structured.log"
        json_handler = logging.handlers.RotatingFileHandler(
            json_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        json_handler.setFormatter(self._create_json_formatter())
        self.logger.addHandler(json_handler)
        
        # 設定檔案處理器（文字格式）
        text_log_file = self.log_dir / f"{name}.log"
        text_handler = logging.handlers.RotatingFileHandler(
            text_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        text_handler.setFormatter(self._create_text_formatter())
        self.logger.addHandler(text_handler)
        
        # 設定控制台處理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self._create_console_formatter())
        self.logger.addHandler(console_handler)
        
        # 日誌條目緩存
        self.log_entries: List[LogEntry] = []
        self._lock = threading.Lock()
        
        logger.info(f"StructuredLogger 初始化完成: {name}")
    
    def _create_json_formatter(self):
        """創建 JSON 格式化器"""
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                    'level': record.levelname,
                    'message': record.getMessage(),
                    'module': record.module,
                    'function': record.funcName,
                    'line_number': record.lineno,
                    'thread': record.thread,
                    'process': record.process
                }
                
                # 添加上下文資訊
                if hasattr(record, 'context'):
                    log_entry['context'] = record.context
                
                # 添加異常資訊
                if record.exc_info:
                    log_entry['exception_info'] = self.formatException(record.exc_info)
                
                return json.dumps(log_entry, ensure_ascii=False)
        
        return JsonFormatter()
    
    def _create_text_formatter(self):
        """創建文字格式化器"""
        return logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def _create_console_formatter(self):
        """創建控制台格式化器"""
        return logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
    
    def log(self, level: LogLevel, message: str, context: Dict[str, Any] = None, exc_info: bool = False):
        """
        記錄日誌
        
        Args:
            level: 日誌級別
            message: 日誌訊息
            context: 上下文資訊
            exc_info: 是否包含異常資訊
        """
        # 創建日誌記錄
        log_record = self.logger.makeRecord(
            name=self.name,
            level=getattr(logging, level.value),
            fn="",
            lno=0,
            msg=message,
            args=(),
            exc_info=sys.exc_info() if exc_info else None
        )
        
        # 添加上下文資訊
        if context:
            log_record.context = context
        
        # 處理日誌記錄
        self.logger.handle(log_record)
        
        # 添加到內部緩存
        with self._lock:
            log_entry = LogEntry(
                timestamp=datetime.now(),
                level=level,
                message=message,
                module=log_record.module,
                function=log_record.funcName,
                line_number=log_record.lineno,
                context=context or {},
                exception_info=self.logger.handlers[0].formatter.formatException(log_record.exc_info) if log_record.exc_info else None
            )
            self.log_entries.append(log_entry)
    
    def debug(self, message: str, context: Dict[str, Any] = None):
        """記錄 DEBUG 級別日誌"""
        self.log(LogLevel.DEBUG, message, context)
    
    def info(self, message: str, context: Dict[str, Any] = None):
        """記錄 INFO 級別日誌"""
        self.log(LogLevel.INFO, message, context)
    
    def warning(self, message: str, context: Dict[str, Any] = None):
        """記錄 WARNING 級別日誌"""
        self.log(LogLevel.WARNING, message, context)
    
    def error(self, message: str, context: Dict[str, Any] = None, exc_info: bool = True):
        """記錄 ERROR 級別日誌"""
        self.log(LogLevel.ERROR, message, context, exc_info)
    
    def critical(self, message: str, context: Dict[str, Any] = None, exc_info: bool = True):
        """記錄 CRITICAL 級別日誌"""
        self.log(LogLevel.CRITICAL, message, context, exc_info)
    
    def get_recent_logs(self, count: int = 100) -> List[LogEntry]:
        """取得最近的日誌條目"""
        with self._lock:
            return self.log_entries[-count:]


class PerformanceMonitor:
    """
    性能監控器
    
    監控系統資源使用情況和處理性能
    """
    
    def __init__(self, monitoring_interval: float = 5.0):
        """
        初始化性能監控器
        
        Args:
            monitoring_interval: 監控間隔（秒）
        """
        self.monitoring_interval = monitoring_interval
        self.is_monitoring = False
        self.monitoring_thread: Optional[threading.Thread] = None
        
        # 指標資料
        self.system_metrics: List[SystemMetrics] = []
        self.processing_metrics = ProcessingMetrics()
        
        # 計時器
        self.timers: Dict[str, float] = {}
        
        # 回調函數
        self.metric_callbacks: List[Callable[[SystemMetrics], None]] = []
        
        self._lock = threading.Lock()
        
        logger.info("PerformanceMonitor 初始化完成")
    
    def start_monitoring(self):
        """開始監控"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("性能監控已開始")
    
    def stop_monitoring(self):
        """停止監控"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=1.0)
        
        logger.info("性能監控已停止")
    
    def _monitoring_loop(self):
        """監控循環"""
        while self.is_monitoring:
            try:
                metrics = self._collect_system_metrics()
                
                with self._lock:
                    self.system_metrics.append(metrics)
                    
                    # 保持最近 1000 個指標
                    if len(self.system_metrics) > 1000:
                        self.system_metrics = self.system_metrics[-1000:]
                
                # 觸發回調
                for callback in self.metric_callbacks:
                    try:
                        callback(metrics)
                    except Exception as e:
                        logger.error(f"指標回調執行失敗: {e}")
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"監控循環錯誤: {e}")
                time.sleep(self.monitoring_interval)
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """收集系統指標"""
        try:
            # CPU 使用率
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # 記憶體使用率
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # 磁碟使用率
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            
            # 網路 I/O
            network_io = psutil.net_io_counters()._asdict()
            
            # 磁碟 I/O
            disk_io = psutil.disk_io_counters()._asdict()
            
            return SystemMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                network_io=network_io,
                disk_io=disk_io
            )
            
        except Exception as e:
            logger.error(f"收集系統指標失敗: {e}")
            return SystemMetrics()
    
    @contextmanager
    def timer(self, name: str):
        """計時器上下文管理器"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            with self._lock:
                self.timers[name] = self.timers.get(name, 0) + duration
    
    def record_processing_start(self, total_files: int):
        """記錄處理開始"""
        with self._lock:
            self.processing_metrics.total_files = total_files
            self.processing_metrics.processed_files = 0
            self.processing_metrics.failed_files = 0
            self.processing_metrics.skipped_files = 0
    
    def record_file_processed(self, success: bool, processing_time: float, stage: str = ""):
        """記錄檔案處理完成"""
        with self._lock:
            if success:
                self.processing_metrics.processed_files += 1
            else:
                self.processing_metrics.failed_files += 1
            
            self.processing_metrics.total_processing_time += processing_time
            
            # 更新平均處理時間
            total_processed = self.processing_metrics.processed_files + self.processing_metrics.failed_files
            if total_processed > 0:
                self.processing_metrics.average_processing_time = self.processing_metrics.total_processing_time / total_processed
            
            # 記錄各階段時間
            if stage == "transcription":
                self.processing_metrics.transcription_time += processing_time
            elif stage == "summary":
                self.processing_metrics.summary_time += processing_time
            elif stage == "document_generation":
                self.processing_metrics.document_generation_time += processing_time
    
    def record_file_skipped(self):
        """記錄檔案跳過"""
        with self._lock:
            self.processing_metrics.skipped_files += 1
    
    def add_metric_callback(self, callback: Callable[[SystemMetrics], None]):
        """添加指標回調函數"""
        self.metric_callbacks.append(callback)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """取得當前指標"""
        with self._lock:
            latest_system_metrics = self.system_metrics[-1] if self.system_metrics else SystemMetrics()
            
            return {
                'system_metrics': latest_system_metrics.to_dict(),
                'processing_metrics': self.processing_metrics.to_dict(),
                'timers': self.timers.copy()
            }
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """取得指標摘要"""
        with self._lock:
            if not self.system_metrics:
                return {'error': '無可用指標資料'}
            
            # 計算系統指標統計
            cpu_values = [m.cpu_usage for m in self.system_metrics]
            memory_values = [m.memory_usage for m in self.system_metrics]
            disk_values = [m.disk_usage for m in self.system_metrics]
            
            return {
                'monitoring_period': {
                    'start_time': self.system_metrics[0].timestamp.isoformat(),
                    'end_time': self.system_metrics[-1].timestamp.isoformat(),
                    'duration_minutes': (self.system_metrics[-1].timestamp - self.system_metrics[0].timestamp).total_seconds() / 60
                },
                'system_metrics_summary': {
                    'cpu_usage': {
                        'avg': sum(cpu_values) / len(cpu_values),
                        'max': max(cpu_values),
                        'min': min(cpu_values)
                    },
                    'memory_usage': {
                        'avg': sum(memory_values) / len(memory_values),
                        'max': max(memory_values),
                        'min': min(memory_values)
                    },
                    'disk_usage': {
                        'avg': sum(disk_values) / len(disk_values),
                        'max': max(disk_values),
                        'min': min(disk_values)
                    }
                },
                'processing_metrics': self.processing_metrics.to_dict(),
                'timers': self.timers.copy()
            }


class LoggingSystem:
    """
    日誌和監控系統
    
    整合結構化日誌記錄和性能監控功能
    Requirements: 6.1, 6.4, 6.5
    """
    
    def __init__(self, name: str = "batch_audio_processing", log_dir: str = "logs"):
        """
        初始化日誌和監控系統
        
        Args:
            name: 系統名稱
            log_dir: 日誌目錄
        """
        self.name = name
        self.log_dir = Path(log_dir)
        
        # 創建日誌記錄器
        self.logger = StructuredLogger(name, str(self.log_dir))
        
        # 創建性能監控器
        self.monitor = PerformanceMonitor()
        
        # 開始監控
        self.monitor.start_monitoring()
        
        self.logger.info("LoggingSystem 初始化完成", {'name': name, 'log_dir': str(self.log_dir)})
    
    def log_processing_start(self, total_files: int, context: Dict[str, Any] = None):
        """記錄處理開始"""
        self.monitor.record_processing_start(total_files)
        self.logger.info(f"開始批次處理，總檔案數: {total_files}", context)
    
    def log_file_processing_start(self, file_path: str, context: Dict[str, Any] = None):
        """記錄檔案處理開始"""
        ctx = {'file_path': file_path}
        if context:
            ctx.update(context)
        self.logger.info(f"開始處理檔案: {file_path}", ctx)
    
    def log_file_processing_complete(self, file_path: str, success: bool, processing_time: float, 
                                   stage: str = "", error_message: str = None, context: Dict[str, Any] = None):
        """記錄檔案處理完成"""
        self.monitor.record_file_processed(success, processing_time, stage)
        
        ctx = {
            'file_path': file_path,
            'success': success,
            'processing_time': processing_time,
            'stage': stage
        }
        if context:
            ctx.update(context)
        
        if success:
            self.logger.info(f"檔案處理成功: {file_path} ({processing_time:.2f}秒)", ctx)
        else:
            ctx['error_message'] = error_message
            self.logger.error(f"檔案處理失敗: {file_path} - {error_message}", ctx)
    
    def log_file_skipped(self, file_path: str, reason: str, context: Dict[str, Any] = None):
        """記錄檔案跳過"""
        self.monitor.record_file_skipped()
        
        ctx = {'file_path': file_path, 'skip_reason': reason}
        if context:
            ctx.update(context)
        
        self.logger.warning(f"檔案跳過: {file_path} - {reason}", ctx)
    
    def log_stage_start(self, stage: str, context: Dict[str, Any] = None):
        """記錄階段開始"""
        ctx = {'stage': stage}
        if context:
            ctx.update(context)
        self.logger.info(f"開始階段: {stage}", ctx)
    
    def log_stage_complete(self, stage: str, duration: float, context: Dict[str, Any] = None):
        """記錄階段完成"""
        ctx = {'stage': stage, 'duration': duration}
        if context:
            ctx.update(context)
        self.logger.info(f"階段完成: {stage} ({duration:.2f}秒)", ctx)
    
    def log_error(self, message: str, context: Dict[str, Any] = None, exc_info: bool = True):
        """記錄錯誤"""
        self.logger.error(message, context, exc_info)
    
    def log_warning(self, message: str, context: Dict[str, Any] = None):
        """記錄警告"""
        self.logger.warning(message, context)
    
    def log_info(self, message: str, context: Dict[str, Any] = None):
        """記錄資訊"""
        self.logger.info(message, context)
    
    def log_debug(self, message: str, context: Dict[str, Any] = None):
        """記錄除錯資訊"""
        self.logger.debug(message, context)
    
    @contextmanager
    def timer(self, name: str):
        """計時器上下文管理器"""
        with self.monitor.timer(name):
            yield
    
    def get_processing_report(self) -> Dict[str, Any]:
        """取得處理報告"""
        metrics = self.monitor.get_metrics_summary()
        recent_logs = self.logger.get_recent_logs(50)
        
        return {
            'report_time': datetime.now().isoformat(),
            'system_name': self.name,
            'metrics': metrics,
            'recent_logs': [log.to_dict() for log in recent_logs],
            'log_summary': {
                'total_logs': len(self.logger.log_entries),
                'error_count': len([log for log in recent_logs if log.level == LogLevel.ERROR]),
                'warning_count': len([log for log in recent_logs if log.level == LogLevel.WARNING])
            }
        }
    
    def export_report(self, file_path: str):
        """匯出處理報告"""
        try:
            report = self.get_processing_report()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"處理報告已匯出: {file_path}")
            
        except Exception as e:
            self.logger.error(f"匯出處理報告失敗: {e}")
    
    def cleanup(self):
        """清理資源"""
        self.monitor.stop_monitoring()
        self.logger.info("LoggingSystem 清理完成")


def create_logging_system(name: str = "batch_audio_processing", log_dir: str = "logs") -> LoggingSystem:
    """
    創建日誌和監控系統
    
    Args:
        name: 系統名稱
        log_dir: 日誌目錄
        
    Returns:
        LoggingSystem 實例
    """
    return LoggingSystem(name, log_dir)


if __name__ == "__main__":
    """測試日誌和監控系統"""
    import time
    import random
    
    print("=== 日誌和監控系統測試 ===\n")
    
    # 創建日誌系統
    logging_system = create_logging_system("test_system")
    
    # 模擬批次處理
    total_files = 5
    logging_system.log_processing_start(total_files)
    
    for i in range(total_files):
        file_path = f"test_file_{i}.mp3"
        
        # 記錄檔案處理開始
        logging_system.log_file_processing_start(file_path)
        
        # 模擬處理時間
        processing_time = random.uniform(1.0, 3.0)
        
        with logging_system.timer(f"file_{i}_processing"):
            time.sleep(processing_time)
        
        # 隨機決定成功或失敗
        success = random.random() > 0.2
        
        if success:
            logging_system.log_file_processing_complete(
                file_path, True, processing_time, "transcription"
            )
        else:
            logging_system.log_file_processing_complete(
                file_path, False, processing_time, "transcription", "模擬錯誤"
            )
    
    # 等待一些監控資料
    time.sleep(6)
    
    # 取得報告
    report = logging_system.get_processing_report()
    print(f"處理報告:")
    print(f"  處理指標: {report['metrics']['processing_metrics']}")
    print(f"  日誌摘要: {report['log_summary']}")
    
    # 匯出報告
    logging_system.export_report("test_report.json")
    
    # 清理
    logging_system.cleanup()
    
    print("\n=== 測試完成 ===")