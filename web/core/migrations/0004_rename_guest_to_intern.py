from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_department'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;",
                "UPDATE users SET role = 'intern' WHERE role = 'guest';",
                "ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('admin', 'manager', 'user', 'intern'));",
                "ALTER TABLE users ALTER COLUMN role SET DEFAULT 'intern';",
                "UPDATE role_upgrade_requests SET requested_role = 'intern' WHERE requested_role = 'guest';",
                "UPDATE role_upgrade_requests SET current_user_role = 'intern' WHERE current_user_role = 'guest';",
            ],
            reverse_sql=[
                "ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;",
                "UPDATE users SET role = 'guest' WHERE role = 'intern';",
                "ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('admin', 'manager', 'user', 'guest'));",
                "ALTER TABLE users ALTER COLUMN role SET DEFAULT 'guest';",
                "UPDATE role_upgrade_requests SET requested_role = 'guest' WHERE requested_role = 'intern';",
                "UPDATE role_upgrade_requests SET current_user_role = 'guest' WHERE current_user_role = 'intern';",
            ],
        ),
    ]
