from db_config import get_connection

def setup_membership_plans():
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            # Clear existing plans (optional)
            cursor.execute("DELETE FROM membership_plans")
            
            # Add membership plans
            plans = [
                {
                    'name': 'Daily Pass',
                    'price': 500,
                    'description': 'Full gym access, Basic equipment orientation, Locker access, No commitment required',
                    'duration_days': 1
                },
                {
                    'name': 'Basic Plan',
                    'price': 1500,
                    'description': 'All Daily Pass features, 2 group classes/month, Basic fitness assessment, Monthly progress tracking',
                    'duration_days': 30
                },
                {
                    'name': 'Standard Plan',
                    'price': 2500,
                    'description': 'All Basic features, Unlimited group classes, Personalized workout plan, Nutrition consultation',
                    'duration_days': 30
                },
                {
                    'name': 'Premium Plan',
                    'price': 4000,
                    'description': 'All Standard features, Personal trainer (2x/week), Custom meal plans, Recovery sessions, Premium app features',
                    'duration_days': 30
                },
                {
                    'name': 'Annual Premium',
                    'price': 40000,
                    'description': 'All Premium features, 2 months free, Priority booking, Exclusive events access, Free guest passes',
                    'duration_days': 365
                }
            ]
            
            for plan in plans:
                cursor.execute(
                    "INSERT INTO membership_plans (name, price, description, duration_days) VALUES (%s, %s, %s, %s)",
                    (plan['name'], plan['price'], plan['description'], plan['duration_days'])
                )
            
            conn.commit()
            
            print("Membership plans setup completed successfully!")
            cursor.execute("SELECT id, name, price, duration_days FROM membership_plans")
            for plan in cursor.fetchall():
                print(f"- {plan['name']}: KES {plan['price']} for {plan['duration_days']} days")

if __name__ == '__main__':
    setup_membership_plans()