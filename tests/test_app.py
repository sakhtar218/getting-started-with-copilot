import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Fixture to provide a test client with reset activities state"""
    import sys
    if "src.app" in sys.modules:
        del sys.modules["src.app"]
    import src.app as app_module
    test_client = TestClient(app_module.app)
    # Reset activities state before each test
    test_client.post("/test/reset-activities")
    return test_client


class TestActivitiesEndpoint:
    """Tests for the /activities endpoint"""
    
    def test_get_activities_returns_dict(self, client):
        """Test that GET /activities returns a dictionary of activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
    
    def test_get_activities_contains_expected_activities(self, client):
        """Test that activities contain expected fields"""
        response = client.get("/activities")
        data = response.json()
        assert "Baseball Team" in data
        
        activity = data["Baseball Team"]
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
        assert isinstance(activity["participants"], list)


class TestSignupEndpoint:
    """Tests for the /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        test_email = "newstudent@mergington.edu"
        activity = "Baseball Team"
        
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": test_email}
        )
        assert response.status_code == 200
        assert f"Signed up {test_email}" in response.json()["message"]
        
        # Verify participant was added
        activities = client.get("/activities").json()
        assert test_email in activities[activity]["participants"]
    
    def test_signup_duplicate_fails(self, client):
        """Test that signing up twice fails"""
        activity = "Tennis Club"
        email = "sarah@mergington.edu"
        
        # Try to sign up again (sarah is already signed up)
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]
    
    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signing up for non-existent activity fails"""
        response = client.post(
            "/activities/NonexistentClub/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]


class TestUnregisterEndpoint:
    """Tests for the /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client):
        """Test successful unregister from an activity"""
        test_email = "pytestuser@mergington.edu"
        activity = "Baseball Team"
        
        # First sign up
        client.post(f"/activities/{activity}/signup", params={"email": test_email})
        
        # Then unregister
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": test_email}
        )
        assert response.status_code == 200
        assert f"Unregistered {test_email}" in response.json()["message"]
        
        # Verify participant was removed
        activities = client.get("/activities").json()
        assert test_email not in activities[activity]["participants"]
    
    def test_unregister_not_registered_fails(self, client):
        """Test that unregistering someone not signed up fails"""
        activity = "Drama Club"
        email = "notregistered@mergington.edu"
        
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert response.status_code == 400
        assert "not signed up for this activity" in response.json()["detail"]
    
    def test_unregister_nonexistent_activity_fails(self, client):
        """Test that unregistering from non-existent activity fails"""
        response = client.delete(
            "/activities/NonexistentClub/unregister",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]


class TestSignupAndUnregisterFlow:
    """Tests for complete signup and unregister workflows"""
    
    def test_signup_and_unregister_flow(self, client):
        """Test a complete flow of signing up and unregistering"""
        test_email = "flowtest@mergington.edu"
        activity = "Chess Club"
        
        # Get initial participant count
        initial_activities = client.get("/activities").json()
        initial_count = len(initial_activities[activity]["participants"])
        
        # Sign up
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": test_email}
        )
        assert response.status_code == 200
        
        # Check participant count increased
        activities = client.get("/activities").json()
        assert len(activities[activity]["participants"]) == initial_count + 1
        
        # Unregister
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": test_email}
        )
        assert response.status_code == 200
        
        # Check participant count is back to initial
        activities = client.get("/activities").json()
        assert len(activities[activity]["participants"]) == initial_count
    
    def test_multiple_signups_and_unregisters(self, client):
        """Test multiple students signing up and unregistering"""
        activity = "Science Club"
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        # Sign all up
        for email in emails:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Check all are registered
        activities = client.get("/activities").json()
        for email in emails:
            assert email in activities[activity]["participants"]
        
        # Unregister middle student
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": emails[1]}
        )
        assert response.status_code == 200
        
        # Check only middle student is gone
        activities = client.get("/activities").json()
        assert emails[0] in activities[activity]["participants"]
        assert emails[1] not in activities[activity]["participants"]
        assert emails[2] in activities[activity]["participants"]
