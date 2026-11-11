from django.db import migrations

EXPERIENCE_MAP = {
    'Python / Django Developer': '1-3 years',
    'Frontend UI/UX Engineer': '1-2 years',
    'Data & Analytics Associate': '0-2 years',
    'Backend API Engineer': '2-4 years',
    'Product Designer': '2-5 years',
    'Cloud DevOps Specialist': '3-5 years',
}


def populate_experience(apps, schema_editor):
    Job = apps.get_model('jobs', 'Job')
    for title, exp in EXPERIENCE_MAP.items():
        Job.objects.filter(title=title, experience='').update(experience=exp)


def clear_experience(apps, schema_editor):
    Job = apps.get_model('jobs', 'Job')
    Job.objects.filter(title__in=list(EXPERIENCE_MAP.keys())).update(experience='')


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0003_job_experience_rename_created_at_posted_date'),
    ]

    operations = [
        migrations.RunPython(populate_experience, reverse_code=clear_experience),
    ]
