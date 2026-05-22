from django.urls import path

from .views import ReportExportView, StatisticsExportView

urlpatterns = [
    path('statistics/', StatisticsExportView.as_view(), name='reports-statistics'),
    path('', ReportExportView.as_view(), name='reports-export'),
]
