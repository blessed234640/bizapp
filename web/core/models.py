from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'departments'

    def __str__(self):
        return self.name

class User(AbstractUser):
    ROLE_CHOICES = (
        ('intern', 'Стажер'),
        ('user', 'Пользователь'),
        ('manager', 'Менеджер'),
        ('admin', 'Администратор'),
    )

    email = models.EmailField(unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='intern')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    
    from .managers import CustomUserManager
    objects = CustomUserManager()

    class Meta:
        managed = False
        db_table = 'users'

    def save(self, *args, **kwargs):
        # Convert empty string email to None (NULL in DB) to satisfy unique constraint
        if self.email == "":
            self.email = None

        # Синхронизируем флаги доступа Django с нашей ролью
        if self.role == 'admin':
            self.is_superuser = True
            self.is_staff = True
        else:
            self.is_superuser = False
            self.is_staff = False
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.username} ({self.role})"

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
    current_user_role = models.CharField(max_length=20, choices=User.ROLE_CHOICES)
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
        managed = False
        db_table = 'role_upgrade_requests'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Если заявка одобрена, автоматически меняем роль пользователя
        if self.status == 'approved' and self.id:
            old_instance = RoleUpgradeRequest.objects.get(id=self.id)
            if old_instance.status != 'approved':
                user = self.user
                user.role = self.requested_role
                user.save()
                self.reviewed_at = timezone.now()
        super().save(*args, **kwargs)

class Project(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        managed = False
        db_table = 'projects'

class ProjectMember(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'project_members'
        unique_together = ('project', 'user')

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
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        db_column='assigned_to'
    )
    metadata = models.JSONField(null=True)
    deadline = models.DateTimeField(null=True, blank=True)
    is_critical = models.BooleanField(default=False)
    ai_generated = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    ai_score = models.IntegerField(null=True, blank=True)
    ai_feedback = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'tasks'


class AIReport(models.Model):
    manager = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ai_reports'
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='ai_reports'
    )
    content = models.JSONField()
    report_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'ai_reports'
        unique_together = ('manager', 'project', 'report_date')
        ordering = ['-report_date']

    def __str__(self):
        return f"Отчёт {self.report_date} — {self.project} ({self.manager})"


class EmployeeStats(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='stats'
    )
    total_completed = models.IntegerField(default=0)
    completed_on_time = models.IntegerField(default=0)
    completed_overdue = models.IntegerField(default=0)
    avg_score = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'employee_stats'

    def __str__(self):
        return f"Статистика: {self.user.username} (avg: {self.avg_score})"

class TaskLog(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=50)
    details = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'task_logs'