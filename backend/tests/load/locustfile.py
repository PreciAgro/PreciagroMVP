"""Locust load testing scenarios for PreciagroMVP."""

from locust import HttpUser, task, between
import random


class APIGatewayUser(HttpUser):
    """Simulate users hitting the API Gateway."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    @task(3)
    def health_check(self):
        """Test health endpoint (most common)."""
        self.client.get("/health")
    
    @task(1)
    def metrics(self):
        """Test metrics endpoint."""
        self.client.get("/metrics")


class ConversationalUser(HttpUser):
    """Simulate conversational NLP users."""
    
    wait_time = between(2, 5)
    host = "http://localhost:8101"
    
    def on_start(self):
        """Setup test data."""
        self.tenant_id = f"tenant-{random.randint(1, 100)}"
        self.user_id = f"user-{random.randint(1, 1000)}"
    
    @task
    def send_message(self):
        """Send a conversational message."""
        payload = {
            "message": "What crops should I plant?",
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
        }
        self.client.post(
            "/api/v1/chat",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )


class TemporalLogicUser(HttpUser):
    """Simulate temporal logic event creation."""
    
    wait_time = between(3, 7)
    host = "http://localhost:8100"
    
    def on_start(self):
        """Setup test data."""
        self.user_id = f"user-{random.randint(1, 1000)}"
    
    @task
    def create_event(self):
        """Create a temporal event."""
        payload = {
            "user_id": self.user_id,
            "event_type": "weather_alert",
            "source": "load_test",
            "payload": {
                "temperature": random.randint(15, 35),
                "condition": random.choice(["sunny", "rainy", "cloudy"])
            }
        }
        self.client.post("/api/v1/events", json=payload)
    
    @task(2)
    def health_check(self):
        """Check service health."""
        self.client.get("/health")
