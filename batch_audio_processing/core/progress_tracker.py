"""
批次音訊處理系統 - 進度追蹤器
Progress Tracker for Batch Audio Processing

此模組實作了完整的進度追蹤系統，包括：
- ProgressTracker 類別：進度追蹤和狀態管理
- 整合 tqdm 進度條顯示
- 處理狀態更新機制
- 多層級進度追蹤

Requirements: 6.2, 6.3
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Callable
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import threading
from contextlib import contextmanager

try:
    from tqdm import tqdm
except ImportError:
    # 如果 tqdm 不可用，提供一個簡單的替代實現
    class tqdm:
        def __init__(self, total=None, desc=None, **kwargs):
            self.total = total
            self.desc = desc
            self.n = 0
            
        def update(self, n=1):
            self.n += n
            if self.total:
                print(f"\r{self.desc}: {self.n}/{self.total} ({self.n/self.total*100:.1f}%)", end="")
            else:
                print(f"\r{self.desc}: {self.n}", end="")
        
        def set_description(self, desc):
            self.desc = desc
        
        def close(self):
            print()
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            self.close()

# 設定日誌
logger = logging.getLogger(__name__)


class ProcessingStage(Enum):
    """處理階段"""
    DISCOVERY = "discovery"          # 檔案發現
    TRANSCRIPTION = "transcription"  # 語音轉錄
    SUMMARY = "summary"             # 智能摘要
    DOCUMENT_GENERATION = "document_generation"  # 文件生成
    COMPLETED = "completed"         # 完成
    FAILED = "failed"              # 失敗


class TaskStatus(Enum):
    """任務狀態"""
    PENDING = "pending"       # 等待中
    RUNNING = "running"       # 執行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"        # 失敗
    SKIPPED = "skipped"      # 跳過


@dataclass
class TaskProgress:
    """任務進度資訊"""
    task_id: str
    task_name: str
    status: TaskStatus = TaskStatus.PENDING
    stage: ProcessingStage = ProcessingStage.DISCOVERY
    progress: float = 0.0  # 0.0 到 1.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    
    @property
    def duration(self) -> Optional[timedelta]:
        """計算任務持續時間"""
        if self.start_time:
            end_time = self.end_time or datetime.now()
            return end_time - self.start_time
        return None
    
    @property
    def is_active(self) -> bool:
        """檢查任務是否正在執行"""
        return self.status == TaskStatus.RUNNING
    
    @property
    def is_completed(self) -> bool:
        """檢查任務是否已完成"""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED]
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'task_id': self.task_id,
            'task_name': self.task_name,
            'status': self.status.value,
            'stage': self.stage.value,
            'progress': self.progress,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration.total_seconds() if self.duration else None,
            'error_message': self.error_message,
            'file_path': self.file_path
        }


@dataclass
class BatchProgress:
    """批次處理進度資訊"""
    batch_id: str
    total_tasks: int
    completed_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def pending_tasks(self) -> int:
        """等待中的任務數量"""
        return self.total_tasks - self.completed_tasks - self.failed_tasks - self.skipped_tasks
    
    @property
    def progress_percentage(self) -> float:
        """進度百分比"""
        if self.total_tasks == 0:
            return 100.0
        return (self.completed_tasks + self.failed_tasks + self.skipped_tasks) / self.total_tasks * 100
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        processed = self.completed_tasks + self.failed_tasks
        if processed == 0:
            return 0.0
        return self.completed_tasks / processed * 100
    
    @property
    def duration(self) -> Optional[timedelta]:
        """批次處理持續時間"""
        if self.start_time:
            end_time = self.end_time or datetime.now()
            return end_time - self.start_time
        return None
    
    @property
    def estimated_remaining_time(self) -> Optional[timedelta]:
        """估計剩餘時間"""
        if not self.duration or self.completed_tasks == 0:
            return None
        
        avg_time_per_task = self.duration.total_seconds() / (self.completed_tasks + self.failed_tasks)
        remaining_seconds = avg_time_per_task * self.pending_tasks
        return timedelta(seconds=remaining_seconds)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'batch_id': self.batch_id,
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'skipped_tasks': self.skipped_tasks,
            'pending_tasks': self.pending_tasks,
            'progress_percentage': self.progress_percentage,
            'completion_rate': self.progress_percentage,  # 添加 completion_rate
            'success_rate': self.success_rate,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration.total_seconds() if self.duration else None,
            'estimated_remaining_seconds': self.estimated_remaining_time.total_seconds() if self.estimated_remaining_time else None
        }


class ProgressTracker:
    """
    進度追蹤器類別
    
    提供完整的進度追蹤和狀態管理功能，包括：
    - 建立 ProgressTracker 類別
    - 整合 tqdm 進度條顯示
    - 實作處理狀態更新機制
    
    Requirements: 6.2, 6.3
    """
    
    def __init__(self, batch_id: str = None, enable_tqdm: bool = True):
        """
        初始化進度追蹤器
        
        Args:
            batch_id: 批次處理 ID
            enable_tqdm: 是否啟用 tqdm 進度條
        """
        self.batch_id = batch_id or f"batch_{int(time.time())}"
        self.enable_tqdm = enable_tqdm
        
        # 進度資料
        self.tasks: Dict[str, TaskProgress] = {}
        self.batch_progress: Optional[BatchProgress] = None
        
        # 進度條
        self.progress_bars: Dict[str, tqdm] = {}
        self.main_progress_bar: Optional[tqdm] = None
        
        # 回調函數
        self.progress_callbacks: List[Callable[[TaskProgress], None]] = []
        self.batch_callbacks: List[Callable[[BatchProgress], None]] = []
        
        # 線程安全
        self._lock = threading.Lock()
        
        logger.info(f"ProgressTracker 初始化完成，批次 ID: {self.batch_id}")
    
    def initialize_batch(self, total_tasks: int, task_names: List[str] = None):
        """
        初始化批次處理
        
        Args:
            total_tasks: 總任務數量
            task_names: 任務名稱列表（可選）
        """
        with self._lock:
            self.batch_progress = BatchProgress(
                batch_id=self.batch_id,
                total_tasks=total_tasks,
                start_time=datetime.now()
            )
            
            # 創建主進度條
            if self.enable_tqdm:
                self.main_progress_bar = tqdm(
                    total=total_tasks,
                    desc=f"批次處理 {self.batch_id}",
                    unit="檔案",
                    position=0
                )
            
            # 初始化任務
            if task_names:
                for i, name in enumerate(task_names):
                    task_id = f"task_{i}"
                    self.tasks[task_id] = TaskProgress(
                        task_id=task_id,
                        task_name=name
                    )
            
            logger.info(f"批次處理初始化完成，總任務數: {total_tasks}")
    
    def create_task(self, task_id: str, task_name: str, file_path: str = None) -> TaskProgress:
        """
        創建新任務
        
        Args:
            task_id: 任務 ID
            task_name: 任務名稱
            file_path: 檔案路徑（可選）
            
        Returns:
            創建的任務進度物件
        """
        with self._lock:
            task_progress = TaskProgress(
                task_id=task_id,
                task_name=task_name,
                file_path=file_path
            )
            
            self.tasks[task_id] = task_progress
            
            logger.debug(f"創建任務: {task_id} - {task_name}")
            return task_progress
    
    def start_task(self, task_id: str, stage: ProcessingStage = ProcessingStage.DISCOVERY):
        """
        開始任務
        
        Args:
            task_id: 任務 ID
            stage: 處理階段
        """
        with self._lock:
            if task_id not in self.tasks:
                logger.warning(f"任務不存在: {task_id}")
                return
            
            task = self.tasks[task_id]
            task.status = TaskStatus.RUNNING
            task.stage = stage
            task.start_time = datetime.now()
            task.progress = 0.0
            
            # 創建任務專用進度條
            if self.enable_tqdm and task_id not in self.progress_bars:
                self.progress_bars[task_id] = tqdm(
                    total=100,
                    desc=f"{task.task_name}",
                    unit="%",
                    position=len(self.progress_bars) + 1,
                    leave=False
                )
            
            # 觸發回調
            self._trigger_progress_callbacks(task)
            
            logger.debug(f"開始任務: {task_id} - {stage.value}")
    
    def update_task_progress(self, task_id: str, progress: float, stage: ProcessingStage = None):
        """
        更新任務進度
        
        Args:
            task_id: 任務 ID
            progress: 進度 (0.0 到 1.0)
            stage: 處理階段（可選）
        """
        with self._lock:
            if task_id not in self.tasks:
                logger.warning(f"任務不存在: {task_id}")
                return
            
            task = self.tasks[task_id]
            old_progress = task.progress
            task.progress = max(0.0, min(1.0, progress))
            
            if stage:
                task.stage = stage
            
            # 更新進度條
            if task_id in self.progress_bars:
                progress_bar = self.progress_bars[task_id]
                progress_diff = (task.progress - old_progress) * 100
                if progress_diff > 0:
                    progress_bar.update(progress_diff)
            
            # 觸發回調
            self._trigger_progress_callbacks(task)
            
            logger.debug(f"更新任務進度: {task_id} - {task.progress:.1%}")
    
    def complete_task(self, task_id: str, success: bool = True, error_message: str = None):
        """
        完成任務
        
        Args:
            task_id: 任務 ID
            success: 是否成功
            error_message: 錯誤訊息（如果失敗）
        """
        with self._lock:
            if task_id not in self.tasks:
                logger.warning(f"任務不存在: {task_id}")
                return
            
            task = self.tasks[task_id]
            task.end_time = datetime.now()
            task.progress = 1.0
            
            if success:
                task.status = TaskStatus.COMPLETED
                task.stage = ProcessingStage.COMPLETED
                if self.batch_progress:
                    self.batch_progress.completed_tasks += 1
            else:
                task.status = TaskStatus.FAILED
                task.stage = ProcessingStage.FAILED
                task.error_message = error_message
                if self.batch_progress:
                    self.batch_progress.failed_tasks += 1
            
            # 關閉任務進度條
            if task_id in self.progress_bars:
                progress_bar = self.progress_bars[task_id]
                if not success:
                    progress_bar.set_description(f"{task.task_name} (失敗)")
                progress_bar.update(100 - progress_bar.n)  # 確保到達 100%
                progress_bar.close()
                del self.progress_bars[task_id]
            
            # 更新主進度條
            if self.main_progress_bar:
                self.main_progress_bar.update(1)
                
                # 更新描述顯示統計資訊
                if self.batch_progress:
                    desc = f"批次處理 {self.batch_id} (成功: {self.batch_progress.completed_tasks}, 失敗: {self.batch_progress.failed_tasks})"
                    self.main_progress_bar.set_description(desc)
            
            # 觸發回調
            self._trigger_progress_callbacks(task)
            self._trigger_batch_callbacks()
            
            logger.info(f"任務完成: {task_id} - {'成功' if success else '失敗'}")
    
    def skip_task(self, task_id: str, reason: str = None):
        """
        跳過任務
        
        Args:
            task_id: 任務 ID
            reason: 跳過原因
        """
        with self._lock:
            if task_id not in self.tasks:
                logger.warning(f"任務不存在: {task_id}")
                return
            
            task = self.tasks[task_id]
            task.status = TaskStatus.SKIPPED
            task.end_time = datetime.now()
            task.error_message = reason
            
            if self.batch_progress:
                self.batch_progress.skipped_tasks += 1
            
            # 關閉任務進度條
            if task_id in self.progress_bars:
                progress_bar = self.progress_bars[task_id]
                progress_bar.set_description(f"{task.task_name} (跳過)")
                progress_bar.close()
                del self.progress_bars[task_id]
            
            # 更新主進度條
            if self.main_progress_bar:
                self.main_progress_bar.update(1)
            
            # 觸發回調
            self._trigger_progress_callbacks(task)
            self._trigger_batch_callbacks()
            
            logger.info(f"任務跳過: {task_id} - {reason}")
    
    def finish_batch(self):
        """完成批次處理"""
        with self._lock:
            if self.batch_progress:
                self.batch_progress.end_time = datetime.now()
            
            # 關閉主進度條
            if self.main_progress_bar:
                self.main_progress_bar.close()
                self.main_progress_bar = None
            
            # 關閉所有剩餘的進度條
            for progress_bar in self.progress_bars.values():
                progress_bar.close()
            self.progress_bars.clear()
            
            # 觸發最終回調
            self._trigger_batch_callbacks()
            
            logger.info(f"批次處理完成: {self.batch_id}")
    
    @contextmanager
    def task_context(self, task_id: str, task_name: str, file_path: str = None):
        """
        任務上下文管理器
        
        Args:
            task_id: 任務 ID
            task_name: 任務名稱
            file_path: 檔案路徑（可選）
        """
        task = self.create_task(task_id, task_name, file_path)
        self.start_task(task_id)
        
        try:
            yield task
            self.complete_task(task_id, success=True)
        except Exception as e:
            self.complete_task(task_id, success=False, error_message=str(e))
            raise
    
    def add_progress_callback(self, callback: Callable[[TaskProgress], None]):
        """
        添加進度回調函數
        
        Args:
            callback: 回調函數
        """
        self.progress_callbacks.append(callback)
    
    def add_batch_callback(self, callback: Callable[[BatchProgress], None]):
        """
        添加批次回調函數
        
        Args:
            callback: 回調函數
        """
        self.batch_callbacks.append(callback)
    
    def _trigger_progress_callbacks(self, task: TaskProgress):
        """觸發進度回調函數"""
        for callback in self.progress_callbacks:
            try:
                callback(task)
            except Exception as e:
                logger.error(f"進度回調函數執行失敗: {e}")
    
    def _trigger_batch_callbacks(self):
        """觸發批次回調函數"""
        if self.batch_progress:
            for callback in self.batch_callbacks:
                try:
                    callback(self.batch_progress)
                except Exception as e:
                    logger.error(f"批次回調函數執行失敗: {e}")
    
    def get_task_status(self, task_id: str) -> Optional[TaskProgress]:
        """
        取得任務狀態
        
        Args:
            task_id: 任務 ID
            
        Returns:
            任務進度物件或 None
        """
        return self.tasks.get(task_id)
    
    def get_batch_status(self) -> Optional[BatchProgress]:
        """
        取得批次狀態
        
        Returns:
            批次進度物件或 None
        """
        return self.batch_progress
    
    def get_summary(self) -> Dict[str, Any]:
        """
        取得進度摘要
        
        Returns:
            進度摘要字典
        """
        summary = {
            'batch_id': self.batch_id,
            'batch_progress': self.batch_progress.to_dict() if self.batch_progress else None,
            'total_tasks': len(self.tasks),
            'tasks_by_status': {},
            'tasks_by_stage': {},
            'active_tasks': []
        }
        
        # 統計任務狀態
        for task in self.tasks.values():
            status = task.status.value
            stage = task.stage.value
            
            summary['tasks_by_status'][status] = summary['tasks_by_status'].get(status, 0) + 1
            summary['tasks_by_stage'][stage] = summary['tasks_by_stage'].get(stage, 0) + 1
            
            if task.is_active:
                summary['active_tasks'].append(task.to_dict())
        
        return summary
    
    def export_progress_report(self, file_path: str):
        """
        匯出進度報告
        
        Args:
            file_path: 匯出檔案路徑
        """
        try:
            import json
            
            report_data = {
                'export_time': datetime.now().isoformat(),
                'batch_id': self.batch_id,
                'summary': self.get_summary(),
                'tasks': [task.to_dict() for task in self.tasks.values()]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"進度報告已匯出到: {file_path}")
            
        except Exception as e:
            logger.error(f"匯出進度報告失敗: {e}")


def create_progress_tracker(batch_id: str = None, enable_tqdm: bool = True) -> ProgressTracker:
    """
    創建進度追蹤器
    
    Args:
        batch_id: 批次 ID
        enable_tqdm: 是否啟用 tqdm
        
    Returns:
        ProgressTracker 實例
    """
    return ProgressTracker(batch_id=batch_id, enable_tqdm=enable_tqdm)


if __name__ == "__main__":
    """測試進度追蹤器功能"""
    import time
    import random
    
    # 設定日誌
    logging.basicConfig(level=logging.INFO)
    
    print("=== 進度追蹤器測試 ===\n")
    
    # 創建進度追蹤器
    tracker = create_progress_tracker("test_batch")
    
    # 初始化批次處理
    task_names = ["檔案1.mp3", "檔案2.wav", "檔案3.m4a"]
    tracker.initialize_batch(len(task_names), task_names)
    
    # 模擬處理任務
    for i, name in enumerate(task_names):
        task_id = f"task_{i}"
        
        try:
            with tracker.task_context(task_id, name) as task:
                # 模擬不同階段的處理
                stages = [
                    ProcessingStage.DISCOVERY,
                    ProcessingStage.TRANSCRIPTION,
                    ProcessingStage.SUMMARY,
                    ProcessingStage.DOCUMENT_GENERATION
                ]
                
                for j, stage in enumerate(stages):
                    tracker.update_task_progress(task_id, j / len(stages), stage)
                    time.sleep(0.5)  # 模擬處理時間
                
                # 隨機決定是否成功
                if random.random() > 0.2:  # 80% 成功率
                    tracker.update_task_progress(task_id, 1.0, ProcessingStage.COMPLETED)
                else:
                    raise Exception("模擬處理失敗")
                    
        except Exception as e:
            print(f"任務 {task_id} 失敗: {e}")
    
    # 完成批次處理
    tracker.finish_batch()
    
    # 顯示摘要
    summary = tracker.get_summary()
    print(f"\n批次處理摘要:")
    print(f"  總任務數: {summary['total_tasks']}")
    print(f"  狀態統計: {summary['tasks_by_status']}")
    print(f"  階段統計: {summary['tasks_by_stage']}")
    
    if summary['batch_progress']:
        batch = summary['batch_progress']
        print(f"  成功率: {batch['success_rate']:.1f}%")
        print(f"  處理時間: {batch['duration_seconds']:.1f} 秒")
    
    print("\n=== 測試完成 ===")