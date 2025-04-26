# create_users.py
from firebase.auth_helpers import create_user, list_users

def main():
    # Example: create a Front Office user
    users_to_create = [
        ("office1@wisdom.com", "OfficePass123", "Front Office"),
        ("principal@wisdom.com", "PrincipalPass123", "Principal"),
        ("teacher@wisdom.com", "TeacherPass123", "Teacher"),
        ("student@wisdom.com", "StudentPass123", "Student"),
        ("parent@wisdom.com", "ParentPass123", "Parent"),
        ("admin@wisdom.com", "AdminPass123", "Master Admin"),
    ]

    for email, pwd, role in users_to_create:
        info = create_user(email, pwd, role)
        print(f"Created {info['email']} with role {info['role']} and uid {info['uid']}")

    # List first few users
    print("\nExisting users:")
    for user in list_users()[:5]:
        print(user.uid, user.email, user.custom_claims)

if __name__ == "__main__":
    main()
