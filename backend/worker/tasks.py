from app.core.celery_app import celery_app
import time

@celery_app.task(bind=True, name="test_dummy_task")
def test_dummy_task(self, iterations: int):
    for i in range(iterations):
        time.sleep(1)
        # Update internal state for frontend polling
        self.update_state(state='PROGRESS', meta={'current': i, 'total': iterations})
    return {"status": "Complete", "result": f"Processed {iterations} items."}
