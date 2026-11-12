from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/applied/', views.applied_jobs, name='applied_jobs'),
    path('jobs/saved/', views.saved_jobs, name='saved_jobs'),
    path(
        'jobs/applications/<int:application_id>/status/',
        views.update_application_status,
        name='update_application_status',
    ),
    path(
        'jobs/applications/<int:application_id>/resume/',
        views.download_applicant_resume,
        name='download_applicant_resume',
    ),
    path('jobs/create/', views.create_job, name='create_job'),
    path('jobs/<int:job_id>/', views.job_detail, name='job_detail'),
    path('jobs/<int:job_id>/edit/', views.edit_job, name='edit_job'),
    path('jobs/<int:job_id>/delete/', views.delete_job, name='delete_job'),
    path('jobs/<int:job_id>/apply/', views.apply_to_job, name='apply_to_job'),
    path('jobs/<int:job_id>/save/', views.save_job, name='save_job'),
    path('jobs/<int:job_id>/unsave/', views.unsave_job, name='unsave_job'),
]
