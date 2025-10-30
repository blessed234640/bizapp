from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('guest', 'Гость'),
        ('user', 'Пользователь'),
        ('manager', 'Менеджер'),
        ('admin', 'Администратор'),
    )
    
    # Явно переопределяем ВСЕ поля чтобы избежать конфликтов
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='guest')
    
    # Поля для Django
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    # Кастомные related_name
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        related_name="core_user_set",
        related_query_name="core_user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        related_name="core_user_set", 
        related_query_name="core_user",
    )

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        managed = False
        db_table = 'users'
    
    def __str__(self):
        return f"{self.username} ({self.role})"
    
    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.password_hash = make_password(raw_password)
    
    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password_hash)
    
    @property
    def password(self):
        return self.password_hash
    
    @password.setter
    def password(self, raw_password):
        self.set_password(raw_password)

class RoleUpgradeRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'На рассмотрении'),
        ('approved', 'Одобрена'),
        ('rejected', 'Отклонена'),
    )
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='role_upgrade_requests'
    )
    requested_role = models.CharField(max_length=20, choices=User.ROLE_CHOICES)
    current_user_role = models.CharField(max_length=20, choices=User.ROLE_CHOICES)  # ИЗМЕНИЛ current_role на current_user_role
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_requests'
    )
    
    class Meta:
        db_table = 'role_upgrade_requests'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} -> {self.requested_role} ({self.status})"

class Project(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        managed = False
        db_table = 'projects'
    
    def __str__(self):
        return self.title

class Task(models.Model):
    STATUS_CHOICES = (
        ('pending', 'В ожидании'),
        ('in_progress', 'В работе'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
    )
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField(null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.IntegerField(default=0)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_tasks'
    )

    class Meta:
        managed = False
        db_table = 'tasks'
    
    def __str__(self):
        return self.title

class TaskLog(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=50)
    details = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'task_logs'
    
    def __str__(self):
        return f"{self.task.title} - {self.action}"