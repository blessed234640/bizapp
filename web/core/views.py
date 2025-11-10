from django.shortcuts import render
import requests

def dashboard(request):
    """Главный дашборд"""
    context = {
        'stats': get_task_stats(),
    }
    return render(request, 'dashboard.html', context)

def get_task_stats():
    """Получение статистики задач из FastAPI"""
    try:
        response = requests.get('http://api:8000/reports/tasks-stats/')
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []