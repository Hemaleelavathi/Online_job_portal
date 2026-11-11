from django.db import migrations

SAMPLE_JOBS = [
    {
        'title': 'Python / Django Developer',
        'company': 'NovaStack Labs',
        'location': 'Bengaluru, IN',
        'job_type': 'Full-Time',
        'salary': '$80k - $105k',
        'skills_required': 'Python, Django, SQLite, REST API',
        'description': 'Build scalable backend APIs, web workflows, and relational database models using Django and SQL.',
    },
    {
        'title': 'Frontend UI/UX Engineer',
        'company': 'CloudForge Digital',
        'location': 'Remote',
        'job_type': 'Remote',
        'salary': '$75k - $95k',
        'skills_required': 'Bootstrap 5, HTML5, CSS3, JavaScript',
        'description': 'Craft responsive interfaces and reusable component systems with modern HTML5, CSS3, and Bootstrap.',
    },
    {
        'title': 'Data & Analytics Associate',
        'company': 'PulseMetrics AI',
        'location': 'Hyderabad, IN',
        'job_type': 'Hybrid',
        'salary': '$68k - $88k',
        'skills_required': 'Python, SQL, Pandas, Visualization',
        'description': 'Analyze hiring trends, prepare clean dashboards, and support product decisions with Python analytics.',
    },
    {
        'title': 'Backend API Engineer',
        'company': 'ApexGrid Systems',
        'location': 'Pune, IN',
        'job_type': 'Full-Time',
        'salary': '$85k - $115k',
        'skills_required': 'Django, PostgreSQL, Auth, Docker',
        'description': 'Design secure authentication services, optimize query performance, and maintain clean test suites.',
    },
    {
        'title': 'Product Designer',
        'company': 'BrightPath Studio',
        'location': 'Remote',
        'job_type': 'Contract',
        'salary': '$60k - $82k',
        'skills_required': 'Figma, UX Research, Prototyping, UI Design',
        'description': 'Lead end-to-end user journeys, wireframes, and accessible design systems for SaaS web portals.',
    },
    {
        'title': 'Cloud DevOps Specialist',
        'company': 'Skyline Tech',
        'location': 'Mumbai, IN',
        'job_type': 'Full-Time',
        'salary': '$90k - $120k',
        'skills_required': 'Linux, CI/CD, AWS, Nginx',
        'description': 'Automate CI/CD pipelines, monitor web service reliability, and manage cloud deployments cleanly.',
    },
]


def seed_jobs(apps, schema_editor):
    Job = apps.get_model('jobs', 'Job')
    for job_data in SAMPLE_JOBS:
        Job.objects.get_or_create(
            title=job_data['title'],
            company=job_data['company'],
            defaults=job_data,
        )


def unseed_jobs(apps, schema_editor):
    Job = apps.get_model('jobs', 'Job')
    for job_data in SAMPLE_JOBS:
        Job.objects.filter(
            title=job_data['title'],
            company=job_data['company'],
            employer__isnull=True,
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_jobs, reverse_code=unseed_jobs),
    ]
