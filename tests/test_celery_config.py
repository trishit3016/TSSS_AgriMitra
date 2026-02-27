"""Tests for Celery configuration and task infrastructure"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from app.celery_app import celery_app
from app.tasks.base import BaseTask, SatelliteTask, CacheTask, get_task_status, get_task_result
from app.tasks.satellite_tasks import (
    fetch_satellite_data,
    process_ndvi,
    process_soil_moisture,
    process_rainfall,
    update_cache
)


class TestCeleryConfiguration:
    """Test Celery app configuration"""
    
    def test_celery_app_exists(self):
        """Test that Celery app is properly initialized"""
        assert celery_app is not None
        assert celery_app.main == "agrichain"
    
    def test_broker_configured(self):
        """Test that Redis broker is configured"""
        assert celery_app.conf.broker_url is not None
        assert "redis://" in celery_app.conf.broker_url
    
    def test_result_backend_configured(self):
        """Test that result backend is configured"""
        assert celery_app.conf.result_backend is not None
        assert "redis://" in celery_app.conf.result_backend
    
    def test_task_serializer_json(self):
        """Test that JSON serialization is configured"""
        assert celery_app.conf.task_serializer == "json"
        assert "json" in celery_app.conf.accept_content
        assert celery_app.conf.result_serializer == "json"
    
    def test_timezone_configured(self):
        """Test that timezone is set to Asia/Kolkata"""
        assert celery_app.conf.timezone == "Asia/Kolkata"
        assert celery_app.conf.enable_utc is True
    
    def test_priority_queues_configured(self):
        """Test that high, normal, and low priority queues are configured"""
        queues = celery_app.conf.task_queues
        queue_names = [q.name for q in queues]
        
        assert "high" in queue_names
        assert "normal" in queue_names
        assert "low" in queue_names
        assert len(queue_names) == 3
    
    def test_queue_priorities(self):
        """Test that queues have correct priority levels"""
        queues = {q.name: q for q in celery_app.conf.task_queues}
        
        # Queues use x-max-priority argument for priority configuration
        assert queues["high"].queue_arguments["x-max-priority"] == 10
        assert queues["normal"].queue_arguments["x-max-priority"] == 10
        assert queues["low"].queue_arguments["x-max-priority"] == 10
    
    def test_queue_max_priority_argument(self):
        """Test that queues have x-max-priority argument set"""
        for queue in celery_app.conf.task_queues:
            assert "x-max-priority" in queue.queue_arguments
            assert queue.queue_arguments["x-max-priority"] == 10
    
    def test_task_time_limits(self):
        """Test that task time limits are configured"""
        assert celery_app.conf.task_time_limit == 300  # 5 minutes
        assert celery_app.conf.task_soft_time_limit == 240  # 4 minutes
    
    def test_task_acks_late_enabled(self):
        """Test that late acknowledgment is enabled for reliability"""
        assert celery_app.conf.task_acks_late is True
        assert celery_app.conf.task_reject_on_worker_lost is True
    
    def test_task_routes_configured(self):
        """Test that task routes map tasks to correct queues"""
        routes = celery_app.conf.task_routes
        
        assert routes["app.tasks.satellite_tasks.fetch_satellite_data"]["queue"] == "high"
        assert routes["app.tasks.satellite_tasks.process_ndvi"]["queue"] == "normal"
        assert routes["app.tasks.satellite_tasks.process_soil_moisture"]["queue"] == "normal"
        assert routes["app.tasks.satellite_tasks.process_rainfall"]["queue"] == "normal"
        assert routes["app.tasks.satellite_tasks.update_cache"]["queue"] == "low"


class TestBaseTask:
    """Test BaseTask class with error handling"""
    
    @patch('app.tasks.base.get_supabase_client')
    def test_before_start_creates_task_record(self, mock_supabase):
        """Test that before_start creates task record in Supabase"""
        mock_client = Mock()
        mock_table = Mock()
        mock_client.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value = None
        mock_supabase.return_value = mock_client
        
        task = BaseTask()
        task.name = "test_task"
        task.before_start("task-123", (1, 2), {"key": "value"})
        
        mock_client.table.assert_called_once_with("celery_tasks")
        mock_table.insert.assert_called_once()
        
        # Verify inserted data structure
        call_args = mock_table.insert.call_args[0][0]
        assert call_args["task_id"] == "task-123"
        assert call_args["task_type"] == "test_task"
        assert call_args["status"] == "processing"
        assert call_args["params"]["args"] == [1, 2]
        assert call_args["params"]["kwargs"] == {"key": "value"}
    
    @patch('app.tasks.base.get_supabase_client')
    def test_on_success_updates_task_record(self, mock_supabase):
        """Test that on_success updates task record with result"""
        mock_client = Mock()
        mock_table = Mock()
        mock_update = Mock()
        mock_client.table.return_value = mock_table
        mock_table.update.return_value = mock_update
        mock_update.eq.return_value.execute.return_value = None
        mock_supabase.return_value = mock_client
        
        task = BaseTask()
        result = {"data": "test_result"}
        task.on_success(result, "task-123", (), {})
        
        mock_client.table.assert_called_once_with("celery_tasks")
        mock_table.update.assert_called_once()
        
        # Verify update data
        call_args = mock_table.update.call_args[0][0]
        assert call_args["status"] == "completed"
        assert call_args["result"] == result
        mock_update.eq.assert_called_once_with("task_id", "task-123")
    
    @patch('app.tasks.base.get_supabase_client')
    def test_on_failure_updates_task_record(self, mock_supabase):
        """Test that on_failure updates task record with error"""
        mock_client = Mock()
        mock_table = Mock()
        mock_update = Mock()
        mock_client.table.return_value = mock_table
        mock_table.update.return_value = mock_update
        mock_update.eq.return_value.execute.return_value = None
        mock_supabase.return_value = mock_client
        
        task = BaseTask()
        exc = ValueError("Test error")
        task.on_failure(exc, "task-123", (), {}, None)
        
        mock_client.table.assert_called_once_with("celery_tasks")
        mock_table.update.assert_called_once()
        
        # Verify update data
        call_args = mock_table.update.call_args[0][0]
        assert call_args["status"] == "failed"
        assert call_args["error"] == "Test error"
        mock_update.eq.assert_called_once_with("task_id", "task-123")
    
    def test_base_task_retry_configuration(self):
        """Test that BaseTask has correct retry configuration"""
        task = BaseTask()
        assert task.autoretry_for == (Exception,)
        assert task.retry_kwargs == {"max_retries": 3}
        assert task.retry_backoff is True
        assert task.retry_backoff_max == 600
        assert task.retry_jitter is True


class TestSatelliteTask:
    """Test SatelliteTask specialized class"""
    
    def test_satellite_task_time_limits(self):
        """Test that SatelliteTask has longer time limits"""
        task = SatelliteTask()
        assert task.time_limit == 300  # 5 minutes
        assert task.soft_time_limit == 240  # 4 minutes
    
    def test_satellite_task_inherits_base_task(self):
        """Test that SatelliteTask inherits from BaseTask"""
        assert issubclass(SatelliteTask, BaseTask)
    
    def test_satellite_task_run_not_implemented(self):
        """Test that run method must be implemented by subclasses"""
        task = SatelliteTask()
        with pytest.raises(NotImplementedError):
            task.run()


class TestCacheTask:
    """Test CacheTask specialized class"""
    
    def test_cache_task_time_limits(self):
        """Test that CacheTask has shorter time limits"""
        task = CacheTask()
        assert task.time_limit == 60  # 1 minute
        assert task.soft_time_limit == 45  # 45 seconds
    
    def test_cache_task_retry_configuration(self):
        """Test that CacheTask has less aggressive retry"""
        task = CacheTask()
        assert task.retry_kwargs == {"max_retries": 1}
    
    def test_cache_task_inherits_base_task(self):
        """Test that CacheTask inherits from BaseTask"""
        assert issubclass(CacheTask, BaseTask)
    
    def test_cache_task_run_not_implemented(self):
        """Test that run method must be implemented by subclasses"""
        task = CacheTask()
        with pytest.raises(NotImplementedError):
            task.run()


class TestTaskStatusHelpers:
    """Test helper functions for task status retrieval"""
    
    @patch('app.tasks.base.get_supabase_client')
    def test_get_task_status_success(self, mock_supabase):
        """Test retrieving task status from Supabase"""
        mock_client = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_eq = Mock()
        
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = [{
            "task_id": "task-123",
            "status": "completed",
            "result": {"data": "test"}
        }]
        mock_supabase.return_value = mock_client
        
        result = get_task_status("task-123")
        
        assert result is not None
        assert result["task_id"] == "task-123"
        assert result["status"] == "completed"
    
    @patch('app.tasks.base.get_supabase_client')
    def test_get_task_status_not_found(self, mock_supabase):
        """Test retrieving non-existent task status"""
        mock_client = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_eq = Mock()
        
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = []
        mock_supabase.return_value = mock_client
        
        result = get_task_status("nonexistent")
        
        assert result is None
    
    @patch('app.tasks.base.get_task_status')
    def test_get_task_result_completed(self, mock_get_status):
        """Test retrieving result from completed task"""
        mock_get_status.return_value = {
            "task_id": "task-123",
            "status": "completed",
            "result": {"data": "test_result"}
        }
        
        result = get_task_result("task-123")
        
        assert result == {"data": "test_result"}
    
    @patch('app.tasks.base.get_task_status')
    def test_get_task_result_not_completed(self, mock_get_status):
        """Test retrieving result from non-completed task"""
        mock_get_status.return_value = {
            "task_id": "task-123",
            "status": "processing",
            "result": None
        }
        
        result = get_task_result("task-123")
        
        assert result is None


class TestSatelliteTasks:
    """Test satellite task definitions"""
    
    def test_fetch_satellite_data_task_registered(self):
        """Test that fetch_satellite_data task is registered"""
        assert "app.tasks.satellite_tasks.fetch_satellite_data" in celery_app.tasks
    
    def test_process_ndvi_task_registered(self):
        """Test that process_ndvi task is registered"""
        assert "app.tasks.satellite_tasks.process_ndvi" in celery_app.tasks
    
    def test_process_soil_moisture_task_registered(self):
        """Test that process_soil_moisture task is registered"""
        assert "app.tasks.satellite_tasks.process_soil_moisture" in celery_app.tasks
    
    def test_process_rainfall_task_registered(self):
        """Test that process_rainfall task is registered"""
        assert "app.tasks.satellite_tasks.process_rainfall" in celery_app.tasks
    
    def test_update_cache_task_registered(self):
        """Test that update_cache task is registered"""
        assert "app.tasks.satellite_tasks.update_cache" in celery_app.tasks
    
    def test_fetch_satellite_data_uses_satellite_task_base(self):
        """Test that fetch_satellite_data uses SatelliteTask base"""
        task = celery_app.tasks["app.tasks.satellite_tasks.fetch_satellite_data"]
        assert isinstance(task, SatelliteTask)
    
    def test_update_cache_uses_cache_task_base(self):
        """Test that update_cache uses CacheTask base"""
        task = celery_app.tasks["app.tasks.satellite_tasks.update_cache"]
        assert isinstance(task, CacheTask)


class TestTaskResultStorage:
    """Test task result storage in Supabase"""
    
    @patch('app.tasks.base.get_supabase_client')
    def test_task_result_stored_on_completion(self, mock_supabase):
        """Test that task results are stored in Supabase on completion"""
        mock_client = Mock()
        mock_table = Mock()
        mock_update = Mock()
        mock_client.table.return_value = mock_table
        mock_table.update.return_value = mock_update
        mock_update.eq.return_value.execute.return_value = None
        mock_supabase.return_value = mock_client
        
        task = BaseTask()
        result = {
            "latitude": 21.1458,
            "longitude": 79.0882,
            "ndvi": 0.75,
            "status": "success"
        }
        
        task.on_success(result, "task-456", (), {})
        
        # Verify result was stored
        call_args = mock_table.update.call_args[0][0]
        assert call_args["result"] == result
        assert call_args["status"] == "completed"
    
    @patch('app.tasks.base.get_supabase_client')
    def test_task_error_stored_on_failure(self, mock_supabase):
        """Test that task errors are stored in Supabase on failure"""
        mock_client = Mock()
        mock_table = Mock()
        mock_update = Mock()
        mock_client.table.return_value = mock_table
        mock_table.update.return_value = mock_update
        mock_update.eq.return_value.execute.return_value = None
        mock_supabase.return_value = mock_client
        
        task = BaseTask()
        error = Exception("Satellite data fetch timeout")
        
        task.on_failure(error, "task-789", (), {}, None)
        
        # Verify error was stored
        call_args = mock_table.update.call_args[0][0]
        assert call_args["error"] == "Satellite data fetch timeout"
        assert call_args["status"] == "failed"
