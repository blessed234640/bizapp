from django.shortcuts import render
from django.db.models import Count
from .models import Task

def dashboard(request):
    stats = Task.objects.values('status').annotate(count=Count('id'))
    return render(request, 'dashboard.html', {'stats': stats})