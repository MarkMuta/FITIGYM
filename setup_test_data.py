from db_config import get_connection
from werkzeug.security import generate_password_hash
from datetime import datetime

def setup_test_data():
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            # Create a trainer user
            cursor.execute(
                "INSERT INTO users (first_name, last_name, email, phone, password, user_type) VALUES (%s, %s, %s, %s, %s, %s)",
                ('John', 'Smith', 'john.trainer@example.com', '1234567890', generate_password_hash('password123'), 'trainer')
            )
            trainer_user_id = cursor.lastrowid
            
            # Add trainer details
            cursor.execute(
                "INSERT INTO trainers (user_id, specialization, experience_years, certifications) VALUES (%s, %s, %s, %s)",
                (trainer_user_id, 'Strength Training', 5, 'NASM-CPT, ACE')
            )
            trainer_id = cursor.lastrowid
            
            # Create a member user
            cursor.execute(
                "INSERT INTO users (first_name, last_name, email, phone, password, user_type) VALUES (%s, %s, %s, %s, %s, %s)",
                ('Alice', 'Johnson', 'alice.member@example.com', '0987654321', generate_password_hash('password456'), 'member')
            )
            member_user_id = cursor.lastrowid
            
            # Assign member to trainer
            cursor.execute(
                "INSERT INTO members (user_id, trainer_id, plan_type, join_date, status) VALUES (%s, %s, %s, %s, %s)",
                (member_user_id, trainer_id, 'premium', datetime.now().date(), 'active')
            )
            
            conn.commit()
            
            print("Test data setup completed successfully!")
            print(f"Trainer login: john.trainer@example.com / password123")
            print(f"Member login: alice.member@example.com / password456")

if __name__ == '__main__':
    setup_test_data()