from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0002_seed_sample_jobs'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='experience',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.RenameField(
            model_name='job',
            old_name='created_at',
            new_name='posted_date',
        ),
        migrations.AlterModelOptions(
            name='job',
            options={'ordering': ['-posted_date', 'id']},
        ),
    ]
