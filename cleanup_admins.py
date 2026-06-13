from app import app
from extensions import db
from models import User

def cleanup_database():
    with app.app_context():
        print("--- Fetching all current ADMIN accounts ---")
        # 1. Get all accounts that currently have the admin role
        admin_accounts = User.query.filter_by(role='admin').all()
        
        if not admin_accounts:
            print("No admin accounts found.")
            return

        # Define the exact email address of the ONE master account you want to keep
        MASTER_EMAIL = "admin@agrosphere.com" 
        
        master_found = False
        removed_count = 0

        for account in admin_accounts:
            if account.email == MASTER_EMAIL:
                print(f"✅ KEEPING MASTER ACCOUNT: {account.fullname} ({account.email})")
                master_found = True
            else:
                print(f"❌ REMOVING EXTRA ADMIN: {account.fullname} ({account.email})")
                # Option A: Completely delete the account from the database
                db.session.delete(account)
                
                # Option B: Alternatively, if you just want to demote them to a farmer instead of deleting:
                # account.role = 'farmer'
                
                removed_count += 1

        # 2. Save the changes to your database file
        db.session.commit()
        print("---------------------------------------")
        print(f"Cleanup finished! Removed {removed_count} extra admin accounts.")
        if not master_found:
            print(f"⚠️ Warning: Your master email '{MASTER_EMAIL}' was not found in the database. You may need to register it fresh.")

if __name__ == '__main__':
    cleanup_database()