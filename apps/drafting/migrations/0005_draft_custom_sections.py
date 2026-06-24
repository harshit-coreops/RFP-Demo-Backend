from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drafting', '0004_boilerplateclause'),
    ]

    operations = [
        migrations.AddField(
            model_name='draft',
            name='use_custom_sections',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='draft',
            name='custom_sections',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
