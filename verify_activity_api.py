
import os
import sys
import json
from app.database.models.user import User
from app.database.models.activity_model import ActivityLog
from app.database.db_manager import DBManager
from app import create_app

def verify_activity_logging():
    print("Verifying Activity API & Logging...")
    app = create_app()

    with app.app_context():
        try:
            # 1. Setup Test User
            print("1. Setting up test user...")
            user_data = {
                'username': 'activity_tester',
                'email': 'activity@test.com',
                'password': 'password',
                'name': 'Activity Tester',
                'role': 'admin'
            }
            # Cleanup first
            existing = User.find_by_username('activity_tester')
            if existing:
                DBManager.execute_write_query("DELETE FROM users WHERE id=%s", (existing.id,))

            user_id = User.create(user_data)
            print(f"   User created: {user_id}")

            # 2. Test Direct Log Creation
            print("\n2. Testing direct log creation...")
            log_id = ActivityLog.create_log(
                user_id=user_id,
                action='TEST_ACTION',
                entity_type='test_entity',
                entity_id='12345',
                details={'foo': 'bar'},
                ip_address='127.0.0.1'
            )
            print(f"   Log created: {log_id}")

            # 3. Verify Log Retrieval
            print("\n3. Verifying log retrieval...")
            logs, total = ActivityLog.list_logs(user_id=user_id)
            assert total >= 1
            found = False
            for log in logs:
                if log.id == log_id:
                    found = True
                    assert log.action == 'TEST_ACTION'
                    assert log.details['foo'] == 'bar'
                    break

            if found:
                print("   ✅ Log retrieved successfully!")
            else:
                print("   ❌ Log not found in list!")

            # 4. Verify Entity Filtering
            print("\n4. Verifying entity filtering...")
            logs, total = ActivityLog.list_logs(entity_type='test_entity', entity_id='12345')
            assert total >= 1
            assert logs[0].entity_type == 'test_entity'
            print("   ✅ Entity filtering working!")

            print("\n✅ Verification Passed!")

        except Exception as e:
            print(f"\n❌ Verification Failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Cleanup
            print("\nCleaning up...")
            if 'user_id' in locals():
                DBManager.execute_write_query("DELETE FROM activity_logs WHERE user_id=%s", (user_id,))
                DBManager.execute_write_query("DELETE FROM users WHERE id=%s", (user_id,))

if __name__ == "__main__":
    verify_activity_logging()
